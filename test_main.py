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
        ["uv run uvicorn main:app --host 127.0.0.1 --port 8000"],
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # 서버가 뜰 때까지 잠시 대기
    time.sleep(2)
    yield "http://127.0.0.1:8000"
    # 테스트 종료 후 서버 프로세스 종료
    proc.terminate()
    proc.wait()

@pytest.mark.asyncio
async def test_full_2phase_flow_real_server(server):
    print("\n[Test] Starting 2-Phase Flow Test (Real Server)...", file=sys.stderr)
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

        events = []
        
        # 2. SSE 연결 및 이벤트 수집
        print("[Test] Connecting to SSE stream...", file=sys.stderr)
        async with ac.stream("GET", f"/api/status/{task_id}") as response:
            assert response.status_code == 200
            print("[Test] SSE Connection established.", file=sys.stderr)
            
            event_type = None
            async for line in response.aiter_lines():
                line = line.strip()
                if not line: continue
                
                print(f"[SSE Rx] {line}", file=sys.stderr)
                
                if line.startswith("event:"):
                    event_type = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data = json.loads(line[len("data:"):].strip())
                    events.append({"event": event_type, "data": data})

                    if event_type == "extract_result":
                        print("[Test] Phase 1 Success! Triggering Phase 2...", file=sys.stderr)
                        gen_payload = {
                            "task_id": task_id,
                            "selected_contexts": data["contexts"][:2],
                            "prompt": "더 정중하게 써줘"
                        }
                        await ac.post("/api/generate", json=gen_payload)

                    if event_type == "final_result":
                        print("[Test] Final Result received. Success.", file=sys.stderr)
                        break

        # 3. 결과 검증
        progress_events = [e for e in events if e["event"] == "progress"]
        assert len(progress_events) == 3
        assert any(e["event"] == "extract_result" for e in events)
        assert any(e["event"] == "final_result" for e in events)
        print("[Test] All assertions passed!", file=sys.stderr)
