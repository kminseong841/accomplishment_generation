import pytest
import asyncio
import json
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_login_and_sse_status_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. 로그인 요청
        response = await ac.post("/api/login", json={"user_id": "admin", "user_pw": "1234"})
        assert response.status_code == 202
        task_id = response.json()["task_id"]

        # 2. SSE 연결 및 데이터 수신
        # httpx.stream을 사용하여 SSE 이벤트를 실시간으로 읽음
        async with ac.stream("GET", f"/api/status/{task_id}") as response:
            assert response.status_code == 200
            
            final_result = None
            # 응답 라인을 하나씩 읽으며 이벤트 파싱
            async for line in response.aiter_lines():
                if line.startswith("event: result"):
                    # 다음 줄은 'data: ...' 형태임
                    continue
                if line.startswith("data:"):
                    data_str = line[len("data: "):]
                    # JSON 데이터 파싱 (ping 이벤트는 건너뜀)
                    if "SUCCESS" in data_str:
                        final_result = json.loads(data_str)
                        break
            
            # 3. 결과 검증
            assert final_result is not None
            assert final_result["status"] == "SUCCESS"
            assert "summary" in final_result["result"]
            assert final_result["result"]["scraped_data"]["site_1"].startswith("사이트 1")

@pytest.mark.asyncio
async def test_login_and_sse_status_failed():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. 로그인 실패 요청
        response = await ac.post("/api/login", json={"user_id": "admin", "user_pw": "wrong_pw"})
        assert response.status_code == 202
        task_id = response.json()["task_id"]

        # 2. SSE 연결 및 에러 데이터 수신
        async with ac.stream("GET", f"/api/status/{task_id}") as response:
            final_result = None
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data_str = line[len("data: "):]
                    if "FAILED" in data_str:
                        final_result = json.loads(data_str)
                        break
            
            # 3. 결과 검증
            assert final_result is not None
            assert final_result["status"] == "FAILED"
            assert final_result["message"] == "Invalid Credentials"
