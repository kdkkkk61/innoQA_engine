# QA 대시보드 통합 스펙

> **이 문서를 받는 Claude에게**
> 참조용 스펙이다. 구현 방식·폴더 구조·코드 스타일은 자유롭게 결정해도 된다.
> **[필수]** 항목과 **[흐름]** 섹션은 반드시 지켜야 백엔드와 연동된다.

---

## 시스템 구성

```
innoRelease 서버 (192.168.13.55:8090)   — 릴리즈 파이프라인 관리
         ↕ 프록시 경유
Flask 백엔드 (localhost:5000)            — QA 툴 실행 + DB + innoRelease 연동 (완성)
         ↕
React 대시보드 (새로 개발)               — 이 문서의 대상
```

---

## 기술 스택 (고정)

```
TypeScript 5.7 / React 19 / Vite 6
TailwindCSS 3.4 + ir-* CSS (innoRelease 프론트와 동일 디자인 시스템)
Redux Toolkit 2.3 / React Router v7
axios / lucide-react / i18next / Inter 폰트
```

---

## [필수] 제약 사항

**① innoRelease 직접 호출 금지** — CORS 차단
```
❌ axios.get('http://192.168.13.55:8090/...')
✅ axios.get('http://localhost:5000/dashboard/innorelease/api/...')
```

**② QA 요청 큐 "테스트 실행" 버튼 클릭 순서**
```
1. POST /set-pipeline      { pipeline_id, pipeline_repo_id, pipeline_product, test_url }
2. 폴링 시작               GET /pipeline-status  5초 간격
3. window.open('http://localhost:5000/', '_blank')
```
`test_url`을 함께 보내야 QA 툴이 올바른 서버를 테스트한다.

**③ 테스트 완료 감지**
`/pipeline-status` 응답에서 `status === 'done' && run_id != null` → 완료
자동으로 run_id를 승인/반려 패널에 채우고 패널을 열어준다.

---

## [흐름] QA 요청 큐 전체 사이클

```
① innoRelease에서 "통합 QA시작" → pipeline TESTING 상태 전환

② 대시보드 "동기화"
   POST /dashboard/qa-queue/sync
   → TESTING 파이프라인을 qa_requests 테이블에 저장

③ QA 요청 큐 테이블에서:
   - 제품 코드 선택 (1~7)
     POST /dashboard/qa-queue/{id}/set-product  { inno_product: 3 }
   - 테스트 대상 URL 입력 (테스터가 직접 — VM 또는 서버 주소)
     POST /dashboard/qa-queue/{id}/set-test-url  { test_url: "http://..." }
   - [선택] 테스트 환경 갱신 (AGENT 타입 파이프라인만)
     POST /dashboard/qa-queue/{id}/refresh-env  { agent_id: N }

④ "테스트 실행" 클릭
   → POST /set-pipeline (위 ② 필수 순서 참고)
   → QA 툴 새 탭으로 열림
   → 테스터가 테스트 진행

⑤ 테스트 완료 (자동)
   → QA 툴이 Flask 서버로 결과 업로드 (runs 테이블 저장)
   → /pipeline-status 폴링이 run_id 감지
   → 승인/반려 패널 자동 오픈

⑥ 승인 또는 반려
   POST /dashboard/qa-queue/{id}/complete
   → innoRelease QA 레코드 등록 (HTML 리포트 첨부)
   → innoRelease pipeline approve/reject
   → 승인 시 innoRelease 이력에 우리 결과 URL 자동 기록
     (approval.testEnvInfo: "QA 결과: http://서버/dashboard/runs/15")
```

---

## Flask API 목록

### 대시보드 데이터 (JSON)

| 경로 | 설명 |
|------|------|
| `GET /dashboard/api/stats` | KPI 통계 (total_runs, pass_rate, recent_trend) |
| `GET /dashboard/api/runs` | 실행 이력 목록 (`?p=제품명&limit=N`) |
| `GET /dashboard/api/runs/{id}` | 실행 상세 (`{run, results, diff, report_url}`) |
| `GET /dashboard/api/qa-requests` | QA 요청 큐 목록 (`?status=TESTING`) |
| `GET /dashboard/report/{id}` | HTML 리포트 파일 (iframe/새 탭) |

### QA 요청 큐

| 경로 | Body | 설명 |
|------|------|------|
| `POST /dashboard/qa-queue/sync` | — | TESTING 파이프라인 동기화 |
| `POST /dashboard/qa-queue/{id}/set-product` | `{inno_product}` | 제품 코드 저장 |
| `POST /dashboard/qa-queue/{id}/set-test-url` | `{test_url}` | 테스트 대상 URL 저장 |
| `POST /dashboard/qa-queue/{id}/refresh-env` | `{agent_id}` | 테스트 환경 갱신 |
| `POST /dashboard/qa-queue/{id}/complete` | 아래 참고 | 승인/반려 처리 |

`/complete` Body:
```json
{ "action": "approve", "comment": "", "run_id": 15,
  "inno_product": 3, "repo_id": 5, "platform": "MANAGER" }
```

### 테스트 실행 연동

| 경로 | 설명 |
|------|------|
| `POST /set-pipeline` | `{pipeline_id, pipeline_repo_id, pipeline_product, test_url}` |
| `GET /pipeline-status` | `{status, pipeline_id, run_id}` |

### innoRelease 프록시

| 경로 | 설명 |
|------|------|
| `GET /dashboard/innorelease/api/pipelines?status=TESTING` | 파이프라인 목록 |
| `GET /dashboard/innorelease/api/qa?product=3` | QA 레코드 목록 |

---

## 데이터 구조

### qa_requests 테이블 (QA 요청 큐)

```
pipeline_id    innoRelease pipeline ID
repo_id        저장소 ID
repo_name      저장소명
branch         브랜치명
version_hint   버전 (예: "3.2.1")
release_target "SERVER"(매니저) | "AGENT"(에이전트)
inno_product   1~7 (우리가 선택)
test_url       테스트 대상 서버 주소 (테스터 직접 입력)
status         TESTING | APPROVED | REJECTED
run_id         완료 후 연결된 runs.id
```

### 제품 코드

```
1 innoECM  2 리자드백업  3 랜섬크런처  4 엔파우치  5 시큐어존  6 이노마크  7 이노로그
```

### 파이프라인 상태 색상

```
PENDING_QA 노랑  TESTING 파랑  APPROVED 초록  REJECTED 빨강  DEPLOYED 보라
```

---

## 구현할 화면

| 화면 | 핵심 기능 |
|------|----------|
| 대시보드 홈 | KPI (총 실행, PASS율, TESTING 파이프라인 수), 추세 차트 |
| 실행 이력 | runs 목록, 제품 필터, 클릭 시 상세 |
| 실행 상세 | 항목별 결과표, HTML 리포트 iframe/새 탭 |
| **QA 요청 큐** | 동기화→제품선택→URL입력→환경갱신→실행→폴링→승인/반려 |
| innoRelease 연동 | 파이프라인 현황, QA 레코드 제품별 목록 |

QA 요청 큐가 핵심 화면이다. 테이블 한 행에 다음이 모두 들어간다:
- 파이프라인 정보 (저장소/브랜치/버전/대상)
- 제품 코드 선택 셀렉트
- 테스트 대상 URL 입력란
- 테스트 환경 갱신 버튼 (AGENT 타입일 때만)
- 테스트 실행 버튼
- 상태 (TESTING/APPROVED/REJECTED)
- 승인/반려 버튼 (TESTING 상태일 때)
