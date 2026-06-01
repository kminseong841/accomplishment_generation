import pytest
import asyncio
import json
import sys
import subprocess
import time
import httpx

@pytest.fixture(scope="module")
def server():
    # uvicorn 서버를 별도 프로세스로 실행
    proc = subprocess.Popen(
        ["uv run uvicorn main:app --host 127.0.0.1 --port 8001"], # 다른 포트 사용
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # 서버가 뜰 때까지 잠시 대기
    time.sleep(2)
    yield "http://127.0.0.1:8001"
    # 테스트 종료 후 서버 프로세스 종료
    proc.terminate()
    proc.wait()

@pytest.mark.asyncio
async def test_task_cancellation_and_polling(server):
    print("\n[Test] Starting Cancellation and Polling Test...", file=sys.stderr)
    base_url = server
    
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as ac:
        # 1. Phase 1: 추출 요청
        extract_payload = {
            "hr_id": "user123", "hr_pw": "pw123", "prompt": "최신 업적 요약해줘"
        }
        print("[Test] Sending Phase 1 request...", file=sys.stderr)
        resp = await ac.post(
            "/api/extract", 
            json=extract_payload,
            headers={"Authorization": "token123"}
        )
        assert resp.status_code == 202
        task_id = resp.json()["task_id"]
        print(f"[Test] Task ID created: {task_id}", file=sys.stderr)

        # 2. 중간에 취소 요청 보내기 (작업이 진행 중일 때)
        await asyncio.sleep(0.15) # 진행 중 상태가 되도록 잠시 대기
        print("[Test] Sending Cancel request...", file=sys.stderr)
        cancel_resp = await ac.post(f"/api/cancel/{task_id}")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "CANCELED"
        print("[Test] Cancel response received.", file=sys.stderr)

        # 3. 폴링을 통해 상태 확인
        print("[Test] Polling status...", file=sys.stderr)
        poll_resp = await ac.get(f"/api/poll/{task_id}")
        assert poll_resp.status_code == 200
        status_data = poll_resp.json()
        print(f"[Test] Polled status: {status_data['status']}", file=sys.stderr)
        assert status_data["status"] == "CANCELED"
        
        # 4. SSE 연결 시도 시 CANCELED 이벤트가 바로 오는지 확인
        print("[Test] Connecting to SSE to check cancellation event...", file=sys.stderr)
        async with ac.stream("GET", f"/api/status/{task_id}") as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if "event: canceled" in line:
                    print("[Test] CANCELED event received via SSE. Success.", file=sys.stderr)
                    break

        print("[Test] All cancellation assertions passed!", file=sys.stderr)
