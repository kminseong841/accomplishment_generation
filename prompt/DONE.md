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

--------------------------------------------
--------------------------------------------

# 작업 지시서: 공적조서 결과 반환 API 고도화

현재 비동기 작업 큐로 동작하는 FastAPI 프로젝트에 다음 사항을 적용하여 코드를 리팩토링해 줘. 공식 문서(FastAPI, sse-starlette)를 참고하여 환각 없이 정확한 코드를 작성할 것.

<조건>
- 내부망에 작성된 '공적 조서 생성 코드'를 복사 붙여넣기 할 수 없으므로, 공적 조서 내용과 3개의 사이트에서 크롤링한 내용은 prototype으로 하드코딩해서 사용할 것.

## 1. 데이터 포맷 변경 (JSON Serialization)
- 백그라운드 작업이 완료된 후 생성되는 결과물(요약된 공적조서 내용, 3개 사이트 스크래핑 내용)은 DataFrame이 아닌, Pydantic 모델을 활용한 구조화된 JSON 문자열로 직렬화하여 상태 머신에 저장할 것.
- JSON 응답 구조 예시: `{"summary": "...", "scraped_data": {"site_1": "...", ...}}`

## 2. 통신 방식 변경 (SSE 도입)
- 기존의 단순 Polling 방식의 `/api/status/{task_id}` 엔드포인트를 **SSE (Server-Sent Events)** 방식으로 변경할 것.
- FastAPI에서 `StreamingResponse` 또는 `sse-starlette` 패키지를 사용하여, 클라이언트가 1회 연결하면 서버 내부의 asyncio 루프가 상태 변화를 감지하다가 작업 완료(SUCCESS) 시점에 JSON 데이터를 Push 하고 연결을 종료하도록 구현할 것.
- 무한 대기를 방지하기 위한 적절한 타임아웃 처리를 포함할 것.


--------------------------------------------

--------------------------------------------

# 작업 지시서: 공적조서 2-Phase 아키텍처 및 세밀한 SSE 진행 상태 구현

현재의 단일 백그라운드 태스크 구조를 2개의 독립적인 Task와 엔드포인트로 완전히 분리하고, 스크래핑 진행 상황을 세밀하게 전달하는 프로토타입을 작성해 줘. (보안상 실제 크롤링/LLM 코드는 배제하고 `asyncio.sleep`을 활용한 Mockup 코드로 작성할 것)

## 1. 데이터 모델 정의 (Pydantic)
- `./model/request.py` 의 코드를 참고할 것
- `tasks_db` (상태 머신): 기존 구조를 유지하되, 스크래핑 진행도를 추적하기 위해 `progress` (완료된 사이트 이름을 담는 리스트) 필드를 추가할 것.

## 2. API 엔드포인트 및 Background Tasks 분리
다음 2개의 POST 엔드포인트를 만들고, 각각 독립적인 비동기 함수를 `BackgroundTasks`에 `add_task` 하도록 구현할 것.

**A. `POST /api/extract` (Extracting Task)**
- `InitialRequest`를 받음.
- 백그라운드 함수 (`extracting_task`):
  1. 3개의 사이트를 순차적(또는 `asyncio.gather`로 동시)으로 스크래핑하는 것을 시뮬레이션함 (`await asyncio.sleep(1)` 반복).
  2. **[핵심]** 각 사이트 스크래핑이 끝날 때마다 `tasks_db[task_id]["progress"]` 리스트에 해당 사이트 이름(예: "site_1")을 append 할 것.
  3. 3개 사이트 완료 후, LLM 요약을 시뮬레이션하고 최종 결과(공적요지, 내용)를 `tasks_db`의 `result`에 저장 후 상태를 `EXTRACT_SUCCESS`로 변경.

**B. `POST /api/generate` (Generating Task)**
- `GenerationRequest`를 받음.
- 클라이언트가 이전 Task의 결과 중 일부(`selected_contexts`)만 골라서 다시 요청하는 엔드포인트임.
- 백그라운드 함수 (`generating_task`):
  1. `tasks_db`의 상태를 다시 `GENERATING`으로 변경.
  2. 전달받은 `selected_contexts`를 바탕으로 LLM 재생성을 시뮬레이션 (`await asyncio.sleep(2)`).
  3. 완료 시 상태를 `GENERATE_SUCCESS`로 변경하고 최종 문서 결과를 저장.

## 3. SSE 엔드포인트 고도화 (`GET /api/status/{task_id}`)
- 클라이언트가 하나의 엔드포인트로 두 Task의 상태를 모두 추적할 수 있어야 함.
- `while True` 루프 내에서 상태를 감지하여 다음 이벤트를 yield 할 것:
  - **진행 이벤트:** `tasks_db`의 `progress` 리스트 길이를 추적하여, 새로운 사이트가 추가될 때마다 `event: progress`, `data: {"site": "site_1", "status": "done"}` 형태의 가벼운 JSON 메시지를 push 할 것 (데이터 전체를 보내지 않음).
  - **1차 완료 이벤트:** 상태가 `EXTRACT_SUCCESS`가 되면 요약된 전체 데이터를 push. (이후 UI에서 사용자가 선택할 수 있도록 연결 유지 또는 종료 플래그 제공)
  - **최종 완료 이벤트:** 상태가 `GENERATE_SUCCESS`가 되면 최종 재생성된 문서를 push 하고 연결 종료(`break`).

## 4. 제약 사항
- 모든 비동기 통신 및 SSE 구현은 `FastAPI` 및 `sse-starlette` 공식 문서의 패턴을 준수할 것.
- 블로킹(Blocking) 코드가 절대 포함되지 않도록 주의할 것.
--------------------------------------------

--------------------------------------------

DB에 저장되는 데이터를 정확한 데이터 모델로 정의하려고 해.

- task_id로 DB의 정보를 조회 가능
- 조회한 정보는 'status, 'content' 'message'가 있음.
- content는 'data_extracted', data_generated'가 있음
- data_extracted에는 'hr', 'assessment', 'onnara'가 있음
- data_generated에는 'summary', 'accomplishment'가 있음
- hr은 HrDocument라는 데이터 모델을 타입으로 가짐
- assessment는 list[AssessmentDocument]라는 데이터 모델을 타입으로 가짐
- onnara는 list[OnnarDocument]라는 데이터 모델을 타입으로 가짐.
- summary, accomplishment는 str을 타입으로 가짐