import pytest
import asyncio
import json
import sys
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_full_2phase_flow_real_server():
    print("\n[Test] Starting 2-Phase Flow Test (Real Server)...", file=sys.stderr)
    # 실제 서버 주소 사용
    base_url = "http://localhost:8000"
    
    async with AsyncClient(base_url=base_url, timeout=30.0) as ac:
        # 1. Phase 1: 추출 요청
        extract_payload = {
            "hr_id": "user123", "hr_pw": "pw123", "sofotoken": "token123", "prompt": "최신 업적 요약해줘"
        }
        print("[Test] Sending Phase 1 request...", file=sys.stderr)
        resp = await ac.post("/api/extract", json=extract_payload)
        assert resp.status_code == 202
        task_id = resp.json()["task_id"]
        print(f"[Test] Task ID: {task_id}", file=sys.stderr)

        events = []
        
        # 2. SSE 연결
        print("[Test] Connecting to SSE stream...", file=sys.stderr)
        async with ac.stream("GET", f"/api/status/{task_id}") as response:
            assert response.status_code == 200
            print("[Test] SSE Connection established.", file=sys.stderr)
            
            async for line in response.aiter_lines():
                if not line.strip(): continue
                print(f"[SSE Rx] {line}", file=sys.stderr)
                
                if line.startswith("event:"):
                    event_type = line[len("event:"):].strip()
                    continue
                
                if line.startswith("data:"):
                    data_str = line[len("data:"):].strip()
                    data = json.loads(data_str)
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

        # 3. 검증
        assert any(e["event"] == "progress" for e in events)
        assert any(e["event"] == "extract_result" for e in events)
        assert any(e["event"] == "final_result" for e in events)
        print("[Test] All assertions passed!", file=sys.stderr)
