"""
validators/overflow.py — 입력 오버플로 시나리오 검증

태그 입력 필드에 매우 긴 값(overflow_length)을 추가한 뒤 등록을 시도하여
클라이언트/서버 길이 제한 존재 여부를 확인한다.

검증 흐름:
  1. 필수 필드 채우기 (fill_required)
  2. 긴 값을 태그 컨테이너에 추가
     → 클라이언트가 차단하면 pass 기록 후 종료
  3. 등록 버튼 클릭
  4. __globalMessageModal 감지:
     - 확인/저장 다이얼로그 → 확인 클릭 후 재확인
     - 서버 오류 텍스트 감지 → known_bug 기록
     - 등록 성공 (오류 없음) → warn 기록 (서버 제한도 없음)
  5. 모달 dismiss → 추가 모달 닫기 (정리)

YAML 예시 (config/scan_hints/{page_id}.yaml):

  overflow_tests:
    confirm_modal: "div#__globalMessageModal.in"
    confirm_btn:   "div#__globalMessageModal button:has-text('확인')"
    cancel_btn:    "div#addItemModal button.btn-default"   # 닫기 버튼
    register_btn:  "button[add-btn]"

    cases:
      - label:          "보호할 확장자 오버플로"
        overflow_length: 500
        tag_input:
          input:      "input#protectExtension"
          add_btn:    "button#extensionAttachBtn"
          container:  "div#protectExtensionList"
        fill_required:
          - { selector: "input#rcDetectPolicyName", value: "[AUTO]_overflow" }
        order: 500
"""
from __future__ import annotations

from core.models import PageScanReport, ScanResult

# 서버 오류로 판단하는 모달 텍스트 키워드
_SERVER_ERROR_KW = ["서버에서 오류", "오류가 발생", "Error", "실패"]
# 저장 확인 다이얼로그로 판단하는 키워드
_CONFIRM_KW = ["저장하시겠습니까", "확인하시겠습니까", "등록하시겠습니까"]

_PHASE = 6  # 오버플로 시나리오는 시나리오 6으로 고정 (CLAUDE.md 표준)


def scan_overflow_tests(
    page,
    hints: dict,
    report: PageScanReport,
    open_modal_fn=None,
) -> None:
    """overflow_tests 섹션의 각 케이스를 순서대로 실행해 결과를 report에 추가.

    open_modal_fn: 각 케이스 시작 전 모달을 여는 함수 (page_obj.open_add_modal).
                   None이면 모달이 이미 열려 있다고 가정.
    """
    cfg = hints.get("overflow_tests")
    if not cfg:
        return

    confirm_modal_sel = cfg.get("confirm_modal", "div#__globalMessageModal.in")
    confirm_btn_sel   = cfg.get("confirm_btn",   "div#__globalMessageModal button:has-text('확인')")
    cancel_btn_sel    = cfg.get("cancel_btn",    "div#addItemModal button.btn-default")
    register_btn_sel  = cfg.get("register_btn",  "button[add-btn]")

    for case in cfg.get("cases", []):
        # 케이스 시작 전 모달 열기 (_run_case의 finally에서 닫기 버튼으로 닫으므로 매번 재오픈)
        if open_modal_fn is not None:
            try:
                open_modal_fn()
            except Exception as e:
                report.results.append(ScanResult(
                    pattern="overflow",
                    selector=case.get("tag_input", {}).get("input", ""),
                    label=case.get("label", "오버플로 테스트"),
                    status="error",
                    detail=f"모달 열기 실패: {e}",
                    order=case.get("order", 500),
                    phase=_PHASE,
                ))
                continue

        result = _run_case(
            page, case,
            confirm_modal_sel=confirm_modal_sel,
            confirm_btn_sel=confirm_btn_sel,
            cancel_btn_sel=cancel_btn_sel,
            register_btn_sel=register_btn_sel,
        )
        report.results.append(result)


# ──────────────────────────────────────────────────────────────────────────────
# 내부 구현
# ──────────────────────────────────────────────────────────────────────────────

def _run_case(
    page,
    case: dict,
    confirm_modal_sel: str,
    confirm_btn_sel: str,
    cancel_btn_sel: str,
    register_btn_sel: str,
) -> ScanResult:
    label        = case.get("label", "오버플로 테스트")
    overflow_len = case.get("overflow_length", 500)
    order        = case.get("order", 500)
    tag_cfg      = case.get("tag_input", {})
    inp_sel      = tag_cfg.get("input", "")
    add_btn_sel  = tag_cfg.get("add_btn", "")
    cont_sel     = tag_cfg.get("container", "")

    try:
        # ── 1. 필수 필드 채우기 ───────────────────────────────────────
        for field in case.get("fill_required", []):
            sel = field.get("selector", "")
            val = field.get("value", "")
            if not sel:
                continue
            loc = page.locator(sel).first
            if loc.count() > 0:
                loc.fill(val)
                page.wait_for_timeout(150)

            # tag 타입 필드: 짧은 값 추가 (예: 확장자 필드)
            if field.get("type") == "tag_add":
                t_inp = field.get("tag_input_sel", "")
                t_btn = field.get("tag_btn_sel", "")
                t_val = field.get("tag_value", "txt")
                if t_inp and t_btn:
                    _fill_tag(page, t_inp, t_btn, t_val)

            # 토글 ON (예외처리 탭 등)
            if field.get("type") == "toggle_on":
                tog = page.locator(sel).first
                if tog.count() > 0 and not tog.is_checked():
                    tog.evaluate("el => el.click()")
                    page.wait_for_timeout(300)

        # ── 2. 긴 값 태그 추가 ────────────────────────────────────────
        long_val = "a" * overflow_len
        inp_loc  = page.locator(inp_sel).first
        add_loc  = page.locator(add_btn_sel).first
        cont_loc = page.locator(cont_sel)

        if inp_loc.count() == 0:
            return ScanResult(
                pattern="overflow", selector=inp_sel, label=label,
                status="skip", detail=f"입력 요소 없음: {inp_sel}",
                order=order, phase=_PHASE,
            )

        # Native setter — AngularJS ng-model이 우선되므로 dispatchEvent로 동기화
        inp_loc.evaluate(
            "(el, v) => {"
            "  const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;"
            "  s.call(el, v);"
            "  el.dispatchEvent(new Event('input',  {bubbles:true}));"
            "  el.dispatchEvent(new Event('change', {bubbles:true})); }",
            long_val,
        )
        page.wait_for_timeout(200)
        add_loc.evaluate("el => el.click()")
        page.wait_for_timeout(500)

        before_count = cont_loc.evaluate(
            "el => el.querySelectorAll(':scope > *').length"
        )
        if before_count == 0:
            return ScanResult(
                pattern="overflow", selector=inp_sel, label=label,
                status="pass",
                detail=f"클라이언트에서 {overflow_len}자 입력 차단 (태그 미추가)",
                order=order, phase=_PHASE,
            )

        # ── 3. 등록 버튼 클릭 ─────────────────────────────────────────
        page.locator(register_btn_sel).first.evaluate("el => el.click()")
        page.wait_for_timeout(1500)

        # ── 4. 모달 감지 및 판단 ──────────────────────────────────────
        is_error = _handle_modal(
            page, confirm_modal_sel, confirm_btn_sel
        )

        # ── 5. 결과 기록 ──────────────────────────────────────────────
        if is_error is True:
            return ScanResult(
                pattern="overflow", selector=inp_sel, label=label,
                status="known_bug",
                detail=(
                    f"클라이언트 글자수 제한 없음 — {overflow_len}자 태그 추가 후 "
                    "등록 시 서버 오류 발생 (클라이언트 측 입력 길이 검증 누락)"
                ),
                order=order, phase=_PHASE,
            )
        elif is_error is False:
            # 오류 없이 등록 성공 — 서버도 제한 없음
            return ScanResult(
                pattern="overflow", selector=inp_sel, label=label,
                status="known_bug",
                detail=(
                    f"클라이언트/서버 모두 글자수 제한 없음 — "
                    f"{overflow_len}자 태그 등록 성공 (DB/서버 측 검증도 누락)"
                ),
                order=order, phase=_PHASE,
            )
        else:
            # 모달 미출현
            return ScanResult(
                pattern="overflow", selector=inp_sel, label=label,
                status="error",
                detail="등록 후 응답 모달이 나타나지 않음 (타임아웃 또는 다른 UI 처리)",
                order=order, phase=_PHASE,
            )

    except Exception as e:
        return ScanResult(
            pattern="overflow", selector=inp_sel, label=label,
            status="error", detail=str(e),
            order=order, phase=_PHASE,
        )
    finally:
        # ── 정리: 추가 모달 닫기 ─────────────────────────────────────
        _safe_close_modal(page, cancel_btn_sel)


def _fill_tag(page, inp_sel: str, btn_sel: str, value: str) -> None:
    """태그 입력 필드에 단일 값을 추가 (Playwright fill + JS click)."""
    loc = page.locator(inp_sel).first
    btn = page.locator(btn_sel).first
    if loc.count() == 0 or btn.count() == 0:
        return
    loc.fill(value)
    page.wait_for_timeout(150)
    btn.evaluate("el => el.click()")
    page.wait_for_timeout(350)


def _handle_modal(
    page,
    modal_sel: str,
    confirm_btn_sel: str,
) -> bool | None:
    """
    글로벌 메시지 모달을 감지하고 필요 시 확인 클릭.

    반환:
      True  — 서버 오류 텍스트 감지됨
      False — 모달 출현했으나 오류 아님 (성공 메시지 or 확인 후 정상 처리)
      None  — 모달 자체가 출현하지 않음
    """
    modal_loc = page.locator(modal_sel)
    if modal_loc.count() == 0:
        return None

    modal_text = modal_loc.inner_text()

    # 서버 오류 → 확인 클릭 후 True 반환
    if any(kw in modal_text for kw in _SERVER_ERROR_KW):
        _click_if_exists(page, confirm_btn_sel)
        page.wait_for_timeout(400)
        return True

    # 저장 확인 다이얼로그 → 확인 클릭 후 서버 응답 재확인
    if any(kw in modal_text for kw in _CONFIRM_KW):
        _click_if_exists(page, confirm_btn_sel)
        page.wait_for_timeout(1500)
        # 서버 응답으로 새 모달이 떴는지 확인
        if modal_loc.count() > 0:
            err_text = modal_loc.inner_text()
            _click_if_exists(page, confirm_btn_sel)
            page.wait_for_timeout(400)
            return any(kw in err_text for kw in _SERVER_ERROR_KW)
        return False  # 모달 사라짐 = 저장 성공

    # 알 수 없는 모달 → dismiss 후 False
    _click_if_exists(page, confirm_btn_sel)
    page.wait_for_timeout(400)
    return False


def _click_if_exists(page, selector: str) -> None:
    loc = page.locator(selector).first
    if loc.count() > 0:
        try:
            loc.evaluate("el => el.click()")
        except Exception:
            pass


def _safe_close_modal(page, cancel_btn_sel: str) -> None:
    """추가 모달이 열려 있으면 닫기 버튼으로 닫는다."""
    try:
        loc = page.locator(cancel_btn_sel).first
        if loc.count() > 0:
            loc.evaluate("el => el.click()")
            page.wait_for_timeout(400)
    except Exception:
        pass
