import subprocess
import time
import httpx
import json
import sys

def run_integration_test():
    print("Starting Uvicorn server...")
    # 서버를 백그라운드 프로세스로 실행
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8001"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # 서버가 뜰 때까지 잠시 대기
    time.sleep(3)
    
    try:
        base_url = "http://127.0.0.1:8001"
        
        # 1. Phase 1 요청
        print("Sending Phase 1 request...")
        resp = httpx.post(f"{base_url}/api/extract", json={
            "hr_id": "user123", "hr_pw": "pw123", "sofotoken": "token123", "prompt": "test"
        })
        task_id = resp.json()["task_id"]
        print(f"Task ID: {task_id}")

        # 2. SSE 수신
        print("Connecting to SSE...")
        with httpx.stream("GET", f"{base_url}/api/status/{task_id}", timeout=60.0) as r:
            event_type = None
            for line in r.iter_lines():
                if not line: continue
                
                print(f"Raw Line: {line}")
                if line.startswith("event:"):
                    event_type = line[len("event: "):].strip()
                elif line.startswith("data:"):
                    data = json.loads(line[len("data: "):].strip())
                    print(f"Event: {event_type}, Data: {data}")
                    
                    if event_type == "extract_result":
                        print("Phase 1 success! Sending Phase 2 request...")
                        httpx.post(f"{base_url}/api/generate", json={
                            "task_id": task_id,
                            "selected_contexts": data["contexts"][:1],
                            "prompt": "finish it"
                        })
                    
                    if event_type == "final_result":
                        print("Final Result received! Test SUCCESS.")
                        break
        
    except Exception as e:
        print(f"Test FAILED: {e}")
        # 서버 로그 출력
        stdout, stderr = server_process.communicate(timeout=1)
        print("Server Stdout:", stdout.decode())
        print("Server Stderr:", stderr.decode())
        sys.exit(1)
    finally:
        print("Shutting down server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    run_integration_test()
