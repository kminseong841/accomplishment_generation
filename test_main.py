import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_login_success():
    # [테스트 및 실행 요구사항] FastAPI의 ASGI 앱과 직접 통신하는 AsyncClient 설정
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Phase 1: 로그인 요청 (admin/1234)
        response = await ac.post("/api/login", json={"user_id": "admin", "user_pw": "1234"})
        assert response.status_code == 202
        data = response.json()
        task_id = data["task_id"]
        assert data["status"] == "PENDING"

        # Phase 3: 상태 확인 폴링 (Polling)
        # SUCCESS 상태가 될 때까지 최대 10번 시도 (0.5초 간격)
        status_data = {}
        for _ in range(10):
            await asyncio.sleep(0.5)
            status_resp = await ac.get(f"/api/status/{task_id}")
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            if status_data["status"] != "PENDING":
                break
        
        # 결과 검증: SUCCESS 여부 확인
        assert status_data["status"] == "SUCCESS"
        assert status_data["message"] is None

@pytest.mark.asyncio
async def test_login_failed():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Phase 1: 로그인 요청 (admin/wrong_pw)
        response = await ac.post("/api/login", json={"user_id": "admin", "user_pw": "wrong_pw"})
        assert response.status_code == 202
        data = response.json()
        task_id = data["task_id"]
        assert data["status"] == "PENDING"

        # Phase 3: 상태 확인 폴링 (Polling)
        status_data = {}
        for _ in range(10):
            await asyncio.sleep(0.5)
            status_resp = await ac.get(f"/api/status/{task_id}")
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            if status_data["status"] != "PENDING":
                break
        
        # 결과 검증: FAILED 여부 및 에러 메시지 확인
        assert status_data["status"] == "FAILED"
        assert status_data["message"] == "Invalid Credentials"
