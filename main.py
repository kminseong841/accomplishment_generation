from fastapi import FastAPI, HTTPException, status, Request, Header
from fastapi.responses import StreamingResponse
import asyncio
import uuid
import json
from typing import Dict, List, Any, Optional

from model.request import InitialRequest, GenerationRequest, TaskStatus

app = FastAPI()

# 인메모리 DB 구조
tasks_db: Dict[str, Dict[str, Any]] = {}

# --- Background Tasks ---

async def extracting_task(task_id: str, req: InitialRequest, sofotoken: str):
    try:
        tasks_db[task_id]["status"] = TaskStatus.EXTRACTING
        sites = ["site_korea", "site_police", "site_gov"]
        for site in sites:
            await asyncio.sleep(0.1)
            tasks_db[task_id]["progress"].append(site)
        await asyncio.sleep(0.1)
        tasks_db[task_id]["result"] = {
            "summary": "Summary...",
            "contexts": ["Ctx 1", "Ctx 2", "Ctx 3"]
        }
        tasks_db[task_id]["status"] = TaskStatus.EXTRACT_SUCCESS
    except asyncio.CancelledError:
        tasks_db[task_id]["status"] = TaskStatus.CANCELED
        print(f"Task {task_id} was explicitly canceled.")
        raise # 상위 루프로 전파
    except Exception as e:
        tasks_db[task_id]["status"] = TaskStatus.FAILED
        tasks_db[task_id]["message"] = str(e)

async def generating_task(task_id: str, req: GenerationRequest):
    try:
        tasks_db[task_id]["status"] = TaskStatus.GENERATING
        await asyncio.sleep(0.1)
        tasks_db[task_id]["final_doc"] = f"Final document based on {len(req.selected_contexts)} contexts."
        tasks_db[task_id]["status"] = TaskStatus.GENERATE_SUCCESS
    except asyncio.CancelledError:
        tasks_db[task_id]["status"] = TaskStatus.CANCELED
        print(f"Task {task_id} was explicitly canceled.")
        raise
    except Exception as e:
        tasks_db[task_id]["status"] = TaskStatus.FAILED
        tasks_db[task_id]["message"] = str(e)

# --- API Endpoints ---

@app.post("/api/extract", status_code=status.HTTP_202_ACCEPTED)
async def extract(request: InitialRequest, authorization: str = Header(...)):
    task_id = str(uuid.uuid4())
    tasks_db[task_id] = {
        "status": TaskStatus.PENDING,
        "progress": [],
        "result": None,
        "final_doc": None,
        "message": None,
        "task_worker": None
    }
    task = asyncio.create_task(extracting_task(task_id, request, authorization))
    tasks_db[task_id]["task_worker"] = task
    return {"task_id": task_id, "status": TaskStatus.PENDING}

@app.post("/api/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate(request: GenerationRequest):
    if request.task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    
    tasks_db[request.task_id]["status"] = TaskStatus.GENERATING
    task = asyncio.create_task(generating_task(request.task_id, request))
    tasks_db[request.task_id]["task_worker"] = task
    return {"task_id": request.task_id, "status": TaskStatus.GENERATING}

@app.post("/api/cancel/{task_id}")
async def cancel_task(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = tasks_db[task_id]
    current_status = task_info["status"]
    
    # 이미 완료되었거나 취소된 작업은 취소할 수 없음
    if current_status in [TaskStatus.EXTRACT_SUCCESS, TaskStatus.GENERATE_SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELED]:
        return {"task_id": task_id, "status": current_status, "message": "Task already finished or cannot be canceled"}

    # 백그라운드 작업 중단
    worker = task_info.get("task_worker")
    if worker and not worker.done():
        worker.cancel()
    
    task_info["status"] = TaskStatus.CANCELED
    return {"task_id": task_id, "status": TaskStatus.CANCELED}

@app.get("/api/poll/{task_id}")
async def poll_status(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = tasks_db[task_id]
    # 보안상 task_worker 객체는 제외하고 반환
    return {
        "task_id": task_id,
        "status": task_info["status"],
        "progress": task_info["progress"],
        "result": task_info["result"],
        "final_doc": task_info["final_doc"],
        "message": task_info["message"]
    }

@app.get("/api/status/{task_id}")
async def get_status_sse(task_id: str, request: Request):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        # 버퍼를 밀어내기 위한 주석 전송
        yield ": ping\n\n"
        yield "event: connected\ndata: {\"status\": \"ready\"}\n\n"
        
        last_progress_idx = 0
        last_sent_status = None
        
        while True:
            if await request.is_disconnected():
                break

            task_info = tasks_db.get(task_id)
            if not task_info: break

            # 1. Progress
            current_progress = task_info["progress"]
            if len(current_progress) > last_progress_idx:
                for i in range(last_progress_idx, len(current_progress)):
                    data = json.dumps({"site": current_progress[i], "status": "done"})
                    yield f"event: progress\ndata: {data}\n\n"
                last_progress_idx = len(current_progress)

            # 2. Status
            current_status = task_info["status"]
            if current_status != last_sent_status:
                if current_status == TaskStatus.EXTRACT_SUCCESS:
                    yield f"event: extract_result\ndata: {json.dumps(task_info['result'])}\n\n"
                elif current_status == TaskStatus.GENERATE_SUCCESS:
                    yield f"event: final_result\ndata: {json.dumps({'final_doc': task_info['final_doc']})}\n\n"
                    break
                elif current_status == TaskStatus.FAILED:
                    yield f"event: error\ndata: {json.dumps({'message': task_info.get('message', 'Err')})}\n\n"
                    break
                elif current_status == TaskStatus.CANCELED:
                    yield f"event: canceled\ndata: {json.dumps({'message': 'Task was canceled'})}\n\n"
                    break
                last_sent_status = current_status

            await asyncio.sleep(0.05)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
