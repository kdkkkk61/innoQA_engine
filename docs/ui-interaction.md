# UI 상호작용 원칙

> 태그: [공통 — 클릭/인코딩 문제 발생 시]
> 클릭이 동작하지 않거나, UnicodeEncodeError, 오버레이 관련 문제가 발생할 때 이 문서를 읽는다.

---

## 오버레이 개요

테스트 실행 중 사람의 실수 클릭을 막기 위해 전체화면 오버레이(`qa-block-overlay`)를 주입한다.
**테스트가 최우선**이다. 자동화 클릭에 오버레이가 방해가 되면 잠깐 꺼도 된다.

---

## 클릭 방식 선택 기준

| 상황 | 방식 | 이유 |
|---|---|---|
| 버튼 / 모달 내부 요소 | `locator.evaluate("el => el.click()")` | JS 직접 호출 → hit-testing 우회, overlay 무관 |
| 테이블 행 선택 (tActive 필요) | `_toggle_overlay(False)` + `click(force=True)` | native 마우스 이벤트 필요 (mousedown → AngularJS tActive 반응) |
| 체크박스 | `checkbox.evaluate("el => el.click()")` | JS 직접 호출로 충분 |

---

## `_toggle_overlay` 사용 가능 범위

`_toggle_overlay` 메서드(`pages/base_page.py`에 정의)는 overlay의 `pointer-events`를 On/Off 전환한다.

```
가능  : 테이블 행 클릭, 체크박스 등 페이지 내 단순 상태 변경
불가  : SPA 네비게이션 발생 시 (navigate_to, 메뉴 클릭 등)
        → add_init_script가 페이지 로드마다 overlay를 pointer-events:all로 재주입하기 때문
```

---

## 테이블 행 클릭 표준 패턴

(코드 예시: `_toggle_overlay(False)` → `wait_for_timeout(80)` → `click(force=True, timeout=3000)` → `finally _toggle_overlay(True)`)

- `force=True` : actionability 30초 대기 제거 → hang 방지
- `_toggle_overlay(False)` : 좌표 클릭이 row에 실제로 닿도록 overlay 차단 해제
- **두 가지 모두 필요하다. 하나만 쓰면 안 된다.**

---

## Windows CP949 인코딩 규칙

- Python 소스 파일의 `print()` / `log.info()` 등에 **이모지 사용 금지**
- 이모지는 CP949(한국어 Windows 기본 인코딩)에서 `UnicodeEncodeError` 발생
- ASCII 대체 텍스트 사용: `[OK]`, `[FAIL]`, `[WARN]`, `[SKIP]`, `[ERR]`, `[TIP]`
- HTML 템플릿(`.html`)은 UTF-8이므로 이모지 사용 가능

---

## 관련 문서

- `pages/base_page.py` — `_toggle_overlay` 정의 위치
- `docs/architecture.md` — 레이어 구조, pages/ 규칙
