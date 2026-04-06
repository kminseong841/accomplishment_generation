from fastapi import FastAPI, BackgroundTasks, HTTPException, status, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import asyncio
import uuid
import json
from typing import Dict, Optional, Any

app = FastAPI()

# [TO_DO 요구사항 1] 데이터 포맷 변경 (Pydantic 모델)
class ScrapedData(BaseModel):
    site_1: str
    site_2: str
    site_3: str

class MeritReportResult(BaseModel):
    summary: str
    scraped_data: ScrapedData

# 상태 머신 구조 업데이트
# task_id: {"status": "PENDING" | "SUCCESS" | "FAILED", "result": Optional[Dict], "message": Optional[str]}
tasks_db: Dict[str, Dict[str, Any]] = {}

VALID_USER_ID = "admin"
VALID_USER_PW = "1234"

class LoginRequest(BaseModel):
    user_id: str
    user_pw: str

class TaskResponse(BaseModel):
    task_id: str
    status: str

# [TO_DO 요구사항 1] 결과 데이터 하드코딩 (Prototype)
async def generate_merit_report_task(task_id: str, user_id: str, user_pw: str):
    await asyncio.sleep(2) # 크롤링 및 LLM 요약 시뮬레이션
    
    if user_id == VALID_USER_ID and user_pw == VALID_USER_PW:
        # Pydantic 모델을 사용하여 구조화된 데이터 생성
        result = MeritReportResult(
            summary="이 공적조서는 행정 효율화 및 시스템 고도화에 기여한 공로를 요약함.",
            scraped_data=ScrapedData(
                site_1="사이트 1: 과거 포상 이력 없음 확인",
                site_2="사이트 2: 징계 사실 없음 확인",
                site_3="사이트 3: 재직 기간 10년 이상 확인"
            )
        )
        # JSON 직렬화하여 저장 (dict로 변환)
        tasks_db[task_id] = {
            "status": "SUCCESS", 
            "result": result.model_dump(), 
            "message": None
        }
    else:
        tasks_db[task_id] = {
            "status": "FAILED", 
            "result": None, 
            "message": "Invalid Credentials"
        }

@app.post("/api/login", status_code=status.HTTP_202_ACCEPTED, response_model=TaskResponse)
async def login(request: LoginRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    tasks_db[task_id] = {"status": "PENDING", "result": None, "message": None}
    background_tasks.add_task(generate_merit_report_task, task_id, request.user_id, request.user_pw)
    return {"task_id": task_id, "status": "PENDING"}

# [TO_DO 요구사항 2] 통신 방식 변경 (SSE 도입)
@app.get("/api/status/{task_id}")
async def get_status_sse(task_id: str, request: Request):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        timeout = 30 # 최대 30초 대기
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # 클라이언트 연결 끊김 확인
            if await request.is_disconnected():
                break

            task_info = tasks_db.get(task_id)
            if not task_info:
                yield {"event": "error", "data": "Task disappeared"}
                break

            # 상태가 변경되었을 때 데이터 전송
            if task_info["status"] in ["SUCCESS", "FAILED"]:
                yield {
                    "event": "result",
                    "data": json.dumps(task_info)
                }
                break
            
            # 타임아웃 확인
            if asyncio.get_event_loop().time() - start_time > timeout:
                yield {"event": "timeout", "data": "Processing timeout"}
                break

            # 주기적으로 상태 감시 (0.5초 간격)
            yield {"event": "ping", "data": "processing"}
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
