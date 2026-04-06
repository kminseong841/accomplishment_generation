from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from pydantic import BaseModel
import asyncio
import uuid
from typing import Dict, Optional

app = FastAPI()

# [아키텍처 요구사항 2] 상태 머신 (in-memory dictionary)
# task_id: {"status": "PENDING" | "SUCCESS" | "FAILED", "message": Optional[str]}
tasks_db: Dict[str, Dict[str, Optional[str]]] = {}

# [비즈니스 로직 요구사항 1] 하드코딩된 인증 정보
VALID_USER_ID = "admin"
VALID_USER_PW = "1234"

class LoginRequest(BaseModel):
    user_id: str
    user_pw: str

class TaskResponse(BaseModel):
    task_id: str
    status: str

# [비즈니스 로직 요구사항 3] Phase 2 (백그라운드 처리)
async def verify_credentials_task(task_id: str, user_id: str, user_pw: str):
    # 시뮬레이션을 위한 2초 대기
    await asyncio.sleep(2)
    
    if user_id == VALID_USER_ID and user_pw == VALID_USER_PW:
        tasks_db[task_id] = {"status": "SUCCESS", "message": None}
    else:
        tasks_db[task_id] = {"status": "FAILED", "message": "Invalid Credentials"}

# [비즈니스 로직 요구사항 2] Phase 1 (요청 접수)
@app.post("/api/login", status_code=status.HTTP_202_ACCEPTED, response_model=TaskResponse)
async def login(request: LoginRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    tasks_db[task_id] = {"status": "PENDING", "message": None}
    
    # [아키텍처 요구사항 1] 비동기 작업 큐 (BackgroundTasks 사용)
    background_tasks.add_task(verify_credentials_task, task_id, request.user_id, request.user_pw)
    
    return {"task_id": task_id, "status": "PENDING"}

# [비즈니스 로직 요구사항 4] Phase 3 (상태 확인)
@app.get("/api/status/{task_id}", response_model=Dict[str, Optional[str]])
async def get_status(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
