# app이 작동할 때 특정 task id를 지울 수 있는 cancel api를 설계하고 싶어.
- 현재는 SSE 방식으로 status를 제공하지만, polling 방식으로 status를 조회한다고 '가정'할것
- 단순히 task_id로 api를 routing 해서, DB 객체(딕셔너리)에 있는 값을 그냥 None으로 만들면 되는지, 아니면 딕셔너리의 키값 자체를 지우면 되는지, 여러 클라이언트에서 요청을 넣을때 문제는 없는지 등을 고려할 것.
