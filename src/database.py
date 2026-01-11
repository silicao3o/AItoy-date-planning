from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import Optional

Base = declarative_base()


class User(Base):
    """사용자 테이블"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 관계
    workflows = relationship("Workflow", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Workflow(Base):
    """워크플로우 실행 기록 테이블"""
    __tablename__ = 'workflows'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # 워크플로우 메타데이터
    name = Column(String(255), nullable=False, default="Trip Planning Workflow")
    status = Column(String(50), nullable=False, default="running")  # running, completed, failed, cancelled
    
    # 입력 데이터
    user_input = Column(Text, nullable=False)  # 사용자 초기 입력
    input_type = Column(String(50), nullable=True)  # region, specific_place
    
    # 설정 (JSON으로 저장)
    time_settings = Column(JSON, nullable=True)  # TimeSettings 객체
    date_theme = Column(JSON, nullable=True)  # DateTheme 객체
    user_intent = Column(JSON, nullable=True)  # UserIntent 객체
    
    # 검색 설정
    search_radius = Column(Integer, default=2000)
    
    # 최종 결과
    final_itinerary = Column(JSON, nullable=True)  # List[ScheduleItem]
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # 관계
    user = relationship("User", back_populates="workflows")
    nodes = relationship("Node", back_populates="workflow", cascade="all, delete-orphan", order_by="Node.execution_order")
    generations = relationship("Generation", back_populates="workflow", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Workflow(id={self.id}, user_id={self.user_id}, status='{self.status}')>"


class Node(Base):
    """워크플로우 노드 실행 기록 테이블"""
    __tablename__ = 'nodes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Integer, ForeignKey('workflows.id'), nullable=False, index=True)
    
    # 노드 정보
    node_name = Column(String(255), nullable=False)  # analyze_user_input, discover_activity_places 등
    node_type = Column(String(100), nullable=False)  # analysis, search, generation, routing 등
    execution_order = Column(Integer, nullable=False)  # 실행 순서
    
    # 노드 상태
    status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, failed, skipped
    
    # 노드별 State 저장 (JSON)
    # 각 노드에서 생성/수정된 state 데이터를 저장
    state_data = Column(JSON, nullable=True)  # 노드 실행 후의 전체 state 또는 변경된 부분
    
    # 노드 입력/출력
    input_data = Column(JSON, nullable=True)  # 노드 입력 데이터
    output_data = Column(JSON, nullable=True)  # 노드 출력 데이터
    
    # 에러 정보
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # 타임스탬프
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)  # 실행 시간 (밀리초)
    
    # 관계
    workflow = relationship("Workflow", back_populates="nodes")
    
    def __repr__(self):
        return f"<Node(id={self.id}, workflow_id={self.workflow_id}, node_name='{self.node_name}', status='{self.status}')>"


class Generation(Base):
    """LLM 생성 기록 테이블"""
    __tablename__ = 'generations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Integer, ForeignKey('workflows.id'), nullable=False, index=True)
    node_id = Column(Integer, ForeignKey('nodes.id'), nullable=True, index=True)  # 어떤 노드에서 생성되었는지
    
    # 모델 정보
    model_name = Column(String(255), nullable=False)  # llama3.2, gpt-4 등
    model_provider = Column(String(100), nullable=True)  # ollama, openai 등
    
    # 프롬프트 정보
    system_prompt = Column(Text, nullable=True)
    user_prompt = Column(Text, nullable=False)
    full_prompt = Column(Text, nullable=True)  # 전체 프롬프트 (디버깅용)
    
    # 생성 결과
    output = Column(Text, nullable=False)
    parsed_output = Column(JSON, nullable=True)  # JSON 파싱된 결과 (있는 경우)
    
    # 생성 메타데이터
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    
    # 토큰 사용량
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    
    # 성능 메트릭
    latency_ms = Column(Integer, nullable=True)  # 응답 시간 (밀리초)
    
    # 에러 정보
    error_message = Column(Text, nullable=True)
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 관계
    workflow = relationship("Workflow", back_populates="generations")
    node = relationship("Node")
    
    def __repr__(self):
        return f"<Generation(id={self.id}, model='{self.model_name}', workflow_id={self.workflow_id})>"


# 데이터베이스 초기화 함수
def init_db(db_url: Optional[str] = None):
    """데이터베이스 초기화
    
    Args:
        db_url: 데이터베이스 URL. None이면 환경 변수 DATABASE_URL 사용
        
    Returns:
        SQLAlchemy Engine
    """
    import os
    from dotenv import load_dotenv
    
    if db_url is None:
        load_dotenv()
        db_url = os.getenv("DATABASE_URL")
        
        if not db_url:
            raise ValueError(
                "DATABASE_URL environment variable is not set. "
                "Please add it to your .env file.\n"
                "Example for Neon PostgreSQL:\n"
                "DATABASE_URL=postgresql://user:password@ep-xxx.region.aws.neon.tech/dbname?sslmode=require"
            )
    
    # PostgreSQL 연결 풀 설정 (Neon 최적화)
    engine = create_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,  # 연결 유효성 검사
        pool_size=5,
        max_overflow=10
    )
    
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """세션 생성"""
    Session = sessionmaker(bind=engine)
    return Session()


# 편의 함수들
def create_user(session, username: str, email: Optional[str] = None) -> User:
    """사용자 생성"""
    user = User(username=username, email=email)
    session.add(user)
    session.commit()
    return user


def create_workflow(session, user_id: int, user_input: str, **kwargs) -> Workflow:
    """워크플로우 생성"""
    workflow = Workflow(
        user_id=user_id,
        user_input=user_input,
        **kwargs
    )
    session.add(workflow)
    session.commit()
    return workflow


def create_node(session, workflow_id: int, node_name: str, node_type: str, 
                execution_order: int, **kwargs) -> Node:
    """노드 생성"""
    node = Node(
        workflow_id=workflow_id,
        node_name=node_name,
        node_type=node_type,
        execution_order=execution_order,
        **kwargs
    )
    session.add(node)
    session.commit()
    return node


def create_generation(session, workflow_id: int, model_name: str, 
                     user_prompt: str, output: str, **kwargs) -> Generation:
    """생성 기록 생성"""
    generation = Generation(
        workflow_id=workflow_id,
        model_name=model_name,
        user_prompt=user_prompt,
        output=output,
        **kwargs
    )
    session.add(generation)
    session.commit()
    return generation
