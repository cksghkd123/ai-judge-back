# AI Judge — Backend

증거와 반박을 제출하면 AI 판사가 판결문을 작성하는 웹 서비스의 API 서버입니다.

프론트엔드: [ai-judge-front](https://github.com/cksghkd123/ai-judge-front) · 데모: https://ttt-ai-judge.vercel.app

## 무엇을 하는 서비스인가

1. 청구인이 사건을 만들고 상대방을 초대합니다.
2. 양측이 각자 증거를 제출하고, 상대 증거에 반박합니다.
3. 제출이 끝나면 AI 판사가 사건·증거·반박을 읽고 판결문을 작성합니다.
4. 판사(에이전트)마다 판단 성향과 말투가 다릅니다.

## 기술 스택

- **FastAPI** (Python 3.12) — REST API
- **Supabase** — PostgreSQL, Auth(JWT), Storage
- **Anthropic Claude API** — 판결문 생성
- **Nuxt 3 / Vue** — 프론트엔드 (별도 저장소)

## 설계에서 신경 쓴 것

### 판사(에이전트) 추가를 배포와 분리

판사마다 판단 기준과 말투가 달라야 하는데, 에이전트를 추가할 때마다 코드를 고치고 재배포하는 구조는 확장이 어려웠습니다.

기본 에이전트만 코드에 두고 나머지는 `judge_agents` 테이블에서 조회합니다. 프롬프트는 페르소나·말투·이미지 필드로 쪼개 두어, 새 판사를 추가할 때 데이터만 넣으면 됩니다. 판결 요청 경로는 에이전트와 무관하게 하나로 유지했습니다.

```
app/judge/agents.py    # 에이전트 조회 (기본값은 코드, 나머지는 DB)
app/judge/prompts.py   # 시스템/유저 프롬프트 조립
app/judge/ai.py        # 데이터 수집 → 프롬프트 → AI 호출 → 결과 반영
```

### 권한은 애플리케이션이 아니라 DB에서

사건 단계마다 청구인과 피청구인이 볼 수 있는 범위가 다릅니다. 이 판단을 API 코드에 흩어 놓으면 누락이 생기기 쉬워서, Supabase RLS 정책으로 행 단위 권한을 처리했습니다.

- 사용자 토큰으로 만든 클라이언트(`get_supabase_for_user`) — RLS가 적용된 일반 조회·쓰기
- 서비스 롤 클라이언트(`get_supabase`) — 판결 생성처럼 서버가 직접 처리하는 작업

### 판결 생성은 비동기로

LLM 호출은 응답까지 수십 초가 걸립니다. 요청을 붙잡아 두는 대신 `BackgroundTasks`로 넘기고, 사건 상태를 `judging → completed`로 전이시킵니다. 클라이언트는 상태를 폴링해 결과를 가져갑니다.

### 스키마 변경은 마이그레이션으로만

대시보드에서 손으로 바꾸지 않고 `supabase/migrations/`에 SQL 파일로 남깁니다.

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/health` | 헬스체크 |
| GET | `/auth/me`, `/me` | 로그인 사용자 정보 |
| GET | `/judge/agents` | 판사(에이전트) 목록 |
| POST | `/judge/case` | 사건 생성 |
| POST | `/judge/case/join` | 초대 코드로 사건 참여 |
| GET | `/judge/cases` | 내 사건 목록 |
| GET | `/judge/case/{id}` | 사건 상세 |
| POST | `/judge/case/{id}/evidence` | 증거 업로드 |
| POST | `/judge/case/{id}/evidence/complete` | 증거 제출 마감 |
| POST | `/judge/case/{id}/rebuttal/complete` | 반박 제출 마감 → 판결 시작 |

## 실행

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp app/.env.example app/.env   # Supabase / Anthropic 키 입력
uvicorn app.main:app --reload
```

필요한 환경변수는 `app/config.py`에 정의돼 있습니다. `SUPABASE_SERVICE_ROLE_KEY`는 RLS를 우회하므로 서버에서만 사용합니다.

## 구조

```
app/
├── api/         # 라우터 (auth, me, judge, health)
├── auth/        # Supabase JWT 검증
├── clients/     # Supabase 클라이언트 (서비스 롤 / 사용자 토큰)
├── judge/       # 에이전트·프롬프트·AI 호출
├── schemas/     # Pydantic 모델
└── config.py
supabase/migrations/   # 스키마 변경 이력
```
