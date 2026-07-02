# 이슈 스크린샷 캡처 규칙 (빨간 테두리 하이라이트)

> fail/warn 검증 항목 작성 시 반드시 이 규칙을 따른다.
> 근거 코드: `tests/secure_zone_policy/_base.py` `_ss()`(20-91) / `_r()`(98-113),
> 각 페이지 `_base.py` `_add()` (예: `tests/secure_zone_template_manage_folder/_base.py` 95-118).
> 검증 실측: 2026-07-02 (아래 '검증된 사례').

---

## 1. 캡처 파이프라인 (코드 인용)

```
_add(status, label, detail, sc, highlight, repro, screenshot, merge_key)
  └→ _r(..., page=cap, highlight=...)          # cap = fail/warn && screenshot=True 일 때만 page
       └→ _ss(page, label, highlight)          # PNG 저장 → extra["screenshot"]
            └→ html_reporter 결함 카드 '📷 스크린샷 보기' (data URI 임베드)
```

- 캡처 조건 (`_base.py _add`): `status in ("fail", "warn")` **이고** `screenshot=True`(기본).
  pass/skip 은 캡처 없음.
- 저장 위치: `reports/screenshots/BUG_<라벨40자>_<epoch ms>.png`

## 2. highlight 인자 — 핵심 규칙

**fail/warn 이 나올 수 있는 검증에는 이슈 요소의 Locator 를 `highlight=` 로 넘긴다.**

| highlight | 결과 (`_ss` 20-79) |
|---|---|
| Locator 전달 | 요소에 `3px solid #ff2d2d` outline + 반투명 boxShadow → scroll_into_view → **요소 주변 crop** |
| 미전달 (기본 None) | **테두리 없는 전체 페이지 캡처** — 리포트에서 이슈 위치 식별 불가 (누락의 주원인) |

- pass 시 highlight 는 무시되므로 (`_add` 109-112: fail/warn 아니면 None 처리) **조건 없이 항상 넘겨도 안전**하다.
- 다중 매칭 Locator: `count()>1` 이면 **최대 6개 전부** 강조 + union 영역 crop (`_ss` 35-36, 69-74).
  중복 행 증거화에 사용 — 예: sc3m `highlight=page.page.locator("table tbody")`.
- crop 크기: 단일 요소 780×230 (넓은 필드=중앙 정렬 / 좁은 요소=우측 라벨 보이게 좌측 190px 오프셋, `_ss` 60-68).

## 3. 누락·오지정이 생기는 원인 (실측)

1. **highlight 미전달** — 가장 흔함. 전체 화면만 찍혀 어디가 이슈인지 안 보임.
   실측: sc4j 첫 실행(2026-07-02 08:25) fail 스크린샷 = 테두리 없는 전체 화면.
2. **캡처 타이밍 vs 경고 모달**: `submit_and_message`/`content_save_message` 류 helper 는
   경고 모달을 **읽고 dismiss 한 뒤** 반환한다 → `_add` 시점엔 모달이 이미 없다.
   **경고 모달 자체를 하이라이트 대상으로 삼지 말 것.** 증거로 남길 화면 상태(행/필드)를 하이라이트한다.
3. **silent 강등**: highlight 요소가 안 잡히면(숨김·detach → `bounding_box()` None/예외)
   예외 없이 테두리 없는 전체 캡처로 떨어진다 (`_ss` 51-53). 스테일 모달에서 `.first` 가
   숨은 요소를 잡는 경우 포함 — 하이라이트 대상은 **캡처 시점에 화면에 보이는 요소**여야 한다.
4. `screenshot=False` 는 화면 증거가 무의미한 항목([수동 확인 필요] warn 표식 등)에만 사용.

## 4. 작성 체크리스트 (fail/warn 가능 항목마다)

- [ ] `highlight=` 로 이슈 요소 Locator 전달했는가
- [ ] 그 요소가 **`_add` 호출 시점에 화면에 보이는가** (모달 dismiss/닫기 이후 아닌가)
- [ ] 값 이슈면 값이 보이는 요소(입력 필드·행)를, 중복 이슈면 다중 매칭 Locator 를 지정했는가
- [ ] 화면 증거가 없는 항목(수동확인 표식)인가 → `screenshot=False`
- [ ] **캡처 지점 = 판정 지점**(사용자 지시 2026-07-02): 판정 분기마다 원인이 보이는 화면에서 `_add` 를 호출.
  예: "비움 미저장" fail = **편집 모달을 다시 연 상태**에서 잔존 값 필드 하이라이트(실제로 열어보면 남아있다는 증거)
  / "표시 불일치" warn = 속성 모달의 해당 행 하이라이트. 판정 근거(재로드 값)와 다른 화면(속성)을 찍으면 증거가 안 됨
  — 분기별로 `_add` 위치를 나눠서 해당 화면이 열려 있을 때 캡처한다 (적용 예: 특수폴더 sc5c).

## 5. 다중 스크린샷 (`_shot` + `_add(screenshots=[...])`)

**기본은 1장.** 판정이 **두 화면의 대조**로 확정될 때만 한 장 더 — "필요한 경우 한 번 더 찍어 확정"(사용자 지시 2026-07-02).

| 판정 유형 | 장수 |
|---|---|
| 단일 화면에서 이슈가 보임(중복 행, 잘못된 표시값, 잔존 값) | 1장 (`_add` 기본 캡처) |
| 두 화면이 모두 증거(예: 편집 모달=비워짐 + 속성 모달=옛값 잔존) | 2장 — `_shot()` 로 원인 화면 추가 캡처 |

- `_shot(label, highlight=)` 은 **warn/fail 확정 후** 해당 화면을 다시 열어 호출 — pass 경로에서 불필요한 캡처(고아 파일) 금지.
- 각 장은 반드시 highlight crop — 전면 캡처 여러 장은 리포트(base64 임베드) 비대화.
- 리포터는 `screenshots`(이전 시점) → `screenshot`(_add 시점) 시간순으로 표시, summary 에 '(N장)' 표기.
- 적용 예: 특수폴더 sc5c(설명 비움·매핑 제거 warn 분기).

## 6. 검증된 사례 (2026-07-02, reports/screenshots 실물 확인)

| 스크린샷 | 판정 |
|---|---|
| `BUG_sc3m___복사_충돌...08:21` | ✅ 정상 — 중복 `_copy` 행 2개 모두 빨간 테두리 + tbody 영역 crop |
| `BUG_sc4j___폴더_항목_경로...08:25` | ❌ 누락 — highlight 미전달로 테두리 없는 전체 화면 (→ sc4j 에 highlight 보강 완료) |
