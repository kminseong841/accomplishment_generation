use context7. Context7의 find-docs 스킬을 사용해 최신 FastAPI 및 pytest의 비동기 테스트 공식 문서를 참고하여, 아래 요구사항을 충족하는 Python 백엔드 프로토타입을 작성하고 테스트까지 자동 실행해 줘.

[아키텍처 요구사항]
1. 비동기 작업 큐 (Async Task Queue): FastAPI의 BackgroundTasks 또는 asyncio를 사용하여, 클라이언트의 요청을 받으면 메인 스레드를 블로킹하지 않고 백그라운드 작업으로 넘길 것.
2. 상태 머신 (State Machine): in-memory dictionary를 사용하여 task_id를 키값으로 상태(PENDING, SUCCESS, FAILED)를 관리할 것.

[비즈니스 로직 요구사항]
1. 하드코딩된 인증 정보: 시스템 내부에 올바른 user_id="admin", user_pw="1234" 가 있다고 가정함.
2. Phase 1 (요청 접수): 클라이언트가 POST /api/login 으로 id와 pw를 보내면, 즉시 고유한 task_id를 생성하고 상태를 'PENDING'으로 저장한 뒤 task_id를 202 Accepted로 반환함.
3. Phase 2 (백그라운드 처리): 백그라운드 큐에서 해당 id/pw를 검증함 (시뮬레이션을 위해 asyncio.sleep(2) 추가). 일치하면 상태를 'SUCCESS'로, 실패하면 'FAILED'와 함께 에러 메시지("Invalid Credentials")를 상태 머신에 업데이트함.
4. Phase 3 (상태 확인): 클라이언트가 GET /api/status/{task_id} 를 호출하여 현재 상태를 확인할 수 있어야 함.

[테스트 및 실행 요구사항]
1. 위의 로직을 `main.py` 파일로 작성할 것.
2. FastAPI의 TestClient 또는 httpx를 사용하여, 정상 로그인 케이스와 실패 케이스(잘못된 비번)를 모두 검증하는 비동기 테스트 코드를 `test_main.py`로 작성할 것.
3. 테스트 코드는 클라이언트가 /api/login을 호출한 후, while 루프를 통해 /api/status/{task_id}를 주기적으로 폴링(Polling)하여 최종 상태(SUCCESS 또는 FAILED)를 확인하는 흐름까지 완벽하게 구현할 것.
4. 파일 작성이 완료되면, 터미널 명령어를 사용해 `pytest test_main.py -v`를 직접 실행하고 그 결과를 나에게 분석해서 보여줄 것.