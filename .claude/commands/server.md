개발 서버를 시작합니다.

사전 요구사항:
- Ollama가 실행 중이어야 합니다 (`ollama serve`)
- 환경 변수가 설정되어 있어야 합니다 (.env)

```bash
uvicorn src.server:app --reload --port 8000
```
