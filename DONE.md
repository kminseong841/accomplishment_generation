
--------------------------------------------


- [ ] `main.py`: `BackgroundTasks`를 제거하고 `asyncio.create_task`를 사용하여 백그라운드 태스크 실행 (실시간 SSE 연동 최적화)
- [ ] `main.py`: `extract`, `generate` 엔드포인트의 파라미터 및 로직 수정
- [ ] `test_main.py`: 수정된 비동기 로직이 정상적으로 실시간 이벤트를 수집하는지 검증
- [ ] 전체 테스트 (`uv run pytest`) 수행 및 결과 확인
