"""
데이터베이스 로깅 헬퍼
워크플로우 실행 중 state와 LLM 생성 기록을 자동으로 DB에 저장
"""
from datetime import datetime
from typing import Optional, Dict, Any
import json
from contextlib import contextmanager

from database import (
    get_session, 
    User, Workflow, Node, Generation,
    create_user, create_workflow, create_node, create_generation
)
from state import TripState
from models import TimeSettings, DateTheme, UserIntent, ScheduleItem


class DatabaseLogger:
    """워크플로우 실행을 데이터베이스에 기록하는 헬퍼 클래스"""
    
    def __init__(self, engine):
        self.engine = engine
        self.session = get_session(engine)
        self.current_workflow_id: Optional[str] = None
        self.current_user_id: Optional[int] = None
        self.node_execution_order = 0
        
    def close(self):
        """세션 종료"""
        self.session.close()
    
    def get_or_create_user(self, username: str, email: Optional[str] = None) -> User:
        """사용자 가져오기 또는 생성"""
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            user = create_user(self.session, username, email)
        self.current_user_id = user.id
        return user
    
    def start_workflow(self, user_id: int, state: TripState, session_id: str = None, workflow_id: str = None) -> Workflow:
        """워크플로우 시작 기록"""
        # state에서 필요한 정보 추출
        time_settings_dict = None
        if state.get("time_settings"):
            ts = state["time_settings"]
            time_settings_dict = {
                "enabled": ts.enabled,
                "start_time": ts.start_time,
                "duration_hours": ts.duration_hours
            }
        
        date_theme_dict = None
        if state.get("date_theme"):
            dt = state["date_theme"]
            date_theme_dict = {
                "theme": dt.theme,
                "atmosphere": dt.atmosphere
            }
        
        user_intent_dict = None
        if state.get("user_intent"):
            ui = state["user_intent"]
            user_intent_dict = ui.model_dump()
        
        workflow = create_workflow(
            self.session,
            user_id=user_id,
            user_input=state.get("user_input", ""),
            input_type=state.get("input_type"),
            session_id=session_id,
            workflow_id=workflow_id,
            time_settings=time_settings_dict,
            date_theme=date_theme_dict,
            user_intent=user_intent_dict,
            search_radius=state.get("search_radius", 2000),
            status="running"
        )
        
        self.current_workflow_id = workflow.id
        self.node_execution_order = 0
        return workflow
    
    def log_node_start(self, node_name: str, node_type: str, 
                       input_data: Optional[Dict[str, Any]] = None) -> Node:
        """노드 실행 시작 기록"""
        if not self.current_workflow_id:
            raise ValueError("Workflow not started. Call start_workflow first.")
        
        self.node_execution_order += 1
        
        if input_data:
            input_data = self._serialize_state(input_data)
        
        node = create_node(
            self.session,
            workflow_id=self.current_workflow_id,
            node_name=node_name,
            node_type=node_type,
            execution_order=self.node_execution_order,
            status="running",
            started_at=datetime.utcnow(),
            input_data=input_data
        )
        
        return node
    
    def log_node_complete(self, node_id: str, state: TripState, 
                         output_data: Optional[Dict[str, Any]] = None):
        """노드 실행 완료 기록"""
        node = self.session.query(Node).filter_by(id=node_id).first()
        if not node:
            return
        
        # state를 JSON 직렬화 가능한 형태로 변환
        state_data = self._serialize_state(state)
        
        node.status = "completed"
        node.completed_at = datetime.utcnow()
        node.state_data = state_data
        node.output_data = output_data
        
        if node.started_at:
            duration = (node.completed_at - node.started_at).total_seconds() * 1000
            node.duration_ms = int(duration)
        
        self.session.commit()
    
    def log_node_error(self, node_id: str, error_message: str, traceback: Optional[str] = None):
        """노드 실행 에러 기록"""
        node = self.session.query(Node).filter_by(id=node_id).first()
        if not node:
            return
        
        node.status = "failed"
        node.completed_at = datetime.utcnow()
        node.error_message = error_message
        node.error_traceback = traceback
        
        if node.started_at:
            duration = (node.completed_at - node.started_at).total_seconds() * 1000
            node.duration_ms = int(duration)
        
        self.session.commit()
    
    def log_node_skip(self, node_name: str, node_type: str, reason: str):
        """노드 스킵 기록"""
        if not self.current_workflow_id:
            return
        
        self.node_execution_order += 1
        
        node = create_node(
            self.session,
            workflow_id=self.current_workflow_id,
            node_name=node_name,
            node_type=node_type,
            execution_order=self.node_execution_order,
            status="skipped",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            output_data={"skip_reason": reason}
        )
    
    def log_generation(self, model_name: str, user_prompt: str, output: str,
                      node_id: Optional[str] = None,
                      system_prompt: Optional[str] = None,
                      parsed_output: Optional[Dict] = None,
                      model_provider: Optional[str] = None,
                      temperature: Optional[float] = None,
                      max_tokens: Optional[int] = None,
                      latency_ms: Optional[int] = None,
                      **kwargs) -> Generation:
        """LLM 생성 기록"""
        if not self.current_workflow_id:
            raise ValueError("Workflow not started. Call start_workflow first.")
        
        generation = create_generation(
            self.session,
            workflow_id=self.current_workflow_id,
            node_id=node_id,
            model_name=model_name,
            model_provider=model_provider,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output=output,
            parsed_output=parsed_output,
            temperature=temperature,
            max_tokens=max_tokens,
            latency_ms=latency_ms,
            **kwargs
        )
        
        return generation
    
    def complete_workflow(self, state: TripState, status: str = "completed"):
        """워크플로우 완료 기록"""
        if not self.current_workflow_id:
            return
        
        workflow = self.session.query(Workflow).filter_by(id=self.current_workflow_id).first()
        if not workflow:
            return
        
        # 최종 일정 저장
        final_itinerary = None
        if state.get("final_itinerary"):
            final_itinerary = [item.model_dump() for item in state["final_itinerary"]]
        
        workflow.status = status
        workflow.completed_at = datetime.utcnow()
        workflow.final_itinerary = final_itinerary
        
        # 최종 state 업데이트
        if state.get("user_intent"):
            workflow.user_intent = state["user_intent"].model_dump()
        
        self.session.commit()
    
    def fail_workflow(self, error_message: str):
        """워크플로우 실패 기록"""
        if not self.current_workflow_id:
            return
        
        workflow = self.session.query(Workflow).filter_by(id=self.current_workflow_id).first()
        if not workflow:
            return
        
        workflow.status = "failed"
        workflow.completed_at = datetime.utcnow()
        
        self.session.commit()
    
    def _serialize_state(self, state: TripState) -> Dict[str, Any]:
        """TripState를 JSON 직렬화 가능한 딕셔너리로 변환"""
        serialized = {}
        
        for key, value in state.items():
            if value is None:
                serialized[key] = None
            elif isinstance(value, (str, int, float, bool)):
                serialized[key] = value
            elif isinstance(value, list):
                # Location, ScheduleItem 등의 리스트 처리
                serialized[key] = [
                    item.model_dump() if hasattr(item, 'model_dump') else item
                    for item in value
                ]
            elif hasattr(value, 'model_dump'):
                # Pydantic 모델
                serialized[key] = value.model_dump()
            else:
                # 기타 (dict 등)
                try:
                    json.dumps(value)  # JSON 직렬화 가능한지 체크
                    serialized[key] = value
                except (TypeError, ValueError):
                    serialized[key] = str(value)
        
        return serialized
    
    @contextmanager
    def node_context(self, node_name: str, node_type: str, 
                     input_data: Optional[Dict] = None):
        """노드 실행 컨텍스트 매니저"""
        node = self.log_node_start(node_name, node_type, input_data)
        try:
            yield node
        except Exception as e:
            import traceback
            self.log_node_error(node.id, str(e), traceback.format_exc())
            raise
    
    def get_workflow_history(self, user_id: int, limit: int = 10):
        """사용자의 워크플로우 히스토리 조회"""
        workflows = (
            self.session.query(Workflow)
            .filter_by(user_id=user_id)
            .order_by(Workflow.created_at.desc())
            .limit(limit)
            .all()
        )
        return workflows
    
    def get_workflow_details(self, workflow_id: str):
        """워크플로우 상세 정보 조회 (노드 포함)"""
        workflow = self.session.query(Workflow).filter_by(id=workflow_id).first()
        if not workflow:
            return None
        
        return {
            "workflow": workflow,
            "nodes": workflow.nodes,
            "generations": workflow.generations
        }
