"""nPouch 엔파우치 정책 — 시나리오 3: ADD 동작 검증 (origin_protect sc3 패턴 + nPouch 특수).

12 메서드 (사용자 보고 2026-06-01):
  - sc3a: 필수 빈값 차단 (정책 이름)
  - sc3b: 이름 중복 차단
  - sc3c: 입력 마스킹 (숫자/음수/소수점/한글)
  - sc3d: 3000자 server reject 8 필드
  - sc3e: 원본보호 정책 picker → KEEP 선택 → 적용 list 추가 ⭐
  - sc3f: 적용 list 삭제 동작 ⭐
  - sc3g: 서버 통신 2 단계 종속 (메인→오프라인→인증없이/거부)
  - sc3h: 인증없이/열람거부 배타적
  - sc3i: 확장자 필터 추가/제거
  - sc3j: PDF 메인 ON + 하위 OFF 결함 추정
  - sc3k: 색상 picker 변경
  - sc3l: 정상 저장

의존성: [AUTO_KEEP]_sc5_origin_protect (원본보호 정책 picker 선택 시 활용).
"""
from pages.npouch_policy_page import NpouchPolicyPage
from tests.npouch_policy._base import NpouchPolicyBase


# ─────────────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────────────
SERVER_ERR = "서버에서 오류가 발생 하였습니다."


def _save_click(page):
    """ADD 모달 저장 (등록) 버튼 — trusted click + overlay 우회."""
    page.page.evaluate(
        "() => { const o = document.getElementById('qa-block-overlay'); "
        "if (o) o.style.pointerEvents = 'none'; }"
    )
    try:
        page.page.locator(
            "div#addItemModal.in .modal-footer button.btn-primary:visible"
        ).first.click(force=True, timeout=5000)
    finally:
        page.page.evaluate(
            "() => { const o = document.getElementById('qa-block-overlay'); "
            "if (o) o.style.pointerEvents = 'all'; }"
        )
    page.page.wait_for_timeout(800)


def _select_origin_protect_keep(page, keep_name: str = "[AUTO_KEEP]_sc5_origin_protect") -> tuple[bool, str]:
    """원본보호 정책 picker → KEEP 선택 → 등록 (사용자 보고 2026-06-01 강화).

    사용자 보고:
      - picker thead 의 첫 cb = "전체선택" — 제외 (tbody tr 만 사용)
      - KEEP 없으면 맨 위 정책 fallback
      - 등록 click 후 적용 list 갱신 wait 추가
    """
    # 정책선택 버튼 click (overlay 우회)
    page.page.evaluate(
        "() => { const o = document.getElementById('qa-block-overlay'); "
        "if (o) o.style.pointerEvents = 'none'; }"
    )
    try:
        page.page.locator(page.SEL_ORIGIN_PROTECT_BTN).first.click(force=True, timeout=5000)
    finally:
        page.page.evaluate(
            "() => { const o = document.getElementById('qa-block-overlay'); "
            "if (o) o.style.pointerEvents = 'all'; }"
        )
    page.page.wait_for_timeout(800)

    pickers = page.page.locator(".c-ui-modal-dialog:visible")
    if pickers.count() == 0:
        return False, "picker 모달 진입 실패 (.c-ui-modal-dialog visible 없음)"
    picker = pickers.last

    # tbody 안 row 만 — thead 의 "전체선택" 제외
    tbody_rows = picker.locator("table tbody tr")
    row_count = tbody_rows.count()
    if row_count == 0:
        try:
            picker.locator("button:has-text('취소')").first.click(force=True, timeout=2000)
        except Exception:
            pass
        return False, "picker tbody row 0개"

    # KEEP 없으면 맨 위 (idx=0) fallback
    target_row = tbody_rows.filter(has_text=keep_name).first
    used_fallback = False
    target_label = keep_name
    if target_row.count() == 0:
        target_row = tbody_rows.first
        used_fallback = True
        try:
            target_label = target_row.locator("td").nth(1).inner_text().strip()[:40]
        except Exception:
            target_label = "(맨 위 첫 행)"

    cb = target_row.locator("input[type='checkbox']").first
    if cb.count() == 0:
        try:
            picker.locator("button:has-text('취소')").first.click(force=True, timeout=2000)
        except Exception:
            pass
        return False, f"target row 체크박스 미발견 (target={target_label!r})"
    try:
        cb.evaluate("el => el.click()")
        page.page.wait_for_timeout(200)
    except Exception as e:
        return False, f"체크박스 click 예외: {e!r}"
    checked_now = False
    try:
        checked_now = cb.is_checked()
        if not checked_now:
            cb.evaluate("el => el.click()")
            page.page.wait_for_timeout(200)
            checked_now = cb.is_checked()
    except Exception:
        pass

    # 등록 click — JS evaluate find (정확 text match, Chrome MCP 검증 2026-06-01)
    # Playwright :has-text 가 partial match 라 잘못된 button 잡을 수 있어 JS find 사용
    reg_clicked = page.page.evaluate(
        """() => {
            const pickers = Array.from(document.querySelectorAll('.c-ui-modal-dialog')).filter(p => p.offsetParent);
            if (!pickers.length) return false;
            const p = pickers[pickers.length-1];
            const btn = Array.from(p.querySelectorAll('button')).find(b => b.textContent.trim() === '등록');
            if (!btn) return false;
            btn.click();
            return true;
        }"""
    )
    if not reg_clicked:
        return False, f"등록 버튼 미발견 (target={target_label!r})"
    page.page.wait_for_timeout(1000)  # 적용 list 갱신 wait

    return True, (
        f"picker tbody row={row_count} / target={target_label!r} "
        f"(fallback={used_fallback}) / cb checked={checked_now} / 등록 완료"
    )


class TestNpouchPolicyScenario3Add(NpouchPolicyBase):
    """엔파우치 정책 — sc3: ADD 동작 검증 (12 메서드)."""

    # ==================================================================
    # sc3a — 필수 빈값 차단 (정책 이름)
    # ==================================================================
    def test_scenario3a_required_name_empty_blocked(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 3a: 정책 이름 빈값 차단 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        page.open_add_modal()
        # 정책 이름 비운 채 저장
        page.page.locator(page.SEL_POLICY_NAME).fill("")
        _save_click(page)

        msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        expected = "정책 이름"  # 차단 메시지에 포함되어야
        self._add("pass" if expected in msg else "fail",
                  "sc3a — 정책 이름 빈값 차단 메시지",
                  f"입력: 빈값 / 결과 msg: {msg!r} (기대 '{expected}' 포함)",
                  sc=3, highlight=page.page.locator(page.SEL_POLICY_NAME))
        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3b — 이름 중복 차단
    # ==================================================================
    def test_scenario3b_name_duplicate_blocked(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 3b: 이름 중복 차단 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        NAME = "[AUTO]_sc3b_dup"
        # 1차 — 정상 저장
        page.open_add_modal()
        page.page.locator(page.SEL_POLICY_NAME).fill(NAME)
        _save_click(page)
        if page.is_confirm_modal_visible(timeout=2000):
            page.dismiss_confirm_modal()
        page.page.wait_for_timeout(500)

        # 2차 — 같은 이름 저장
        page.navigate_to()
        page.open_add_modal()
        page.page.locator(page.SEL_POLICY_NAME).fill(NAME)
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        self._add("pass" if "이미" in msg or "중복" in msg else "fail",
                  "sc3b — 정책 이름 중복 차단 메시지",
                  f"입력: 동일 '{NAME}' 재저장 / 결과 msg: {msg!r} (기대 '이미/중복' 포함)",
                  sc=3, highlight=page.page.locator(page.SEL_POLICY_NAME))
        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3c — 입력 마스킹 (숫자만, 음수/소수점/한글 reset)
    # ==================================================================
    def test_scenario3c_number_input_masking(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 3c: 숫자 입력 마스킹 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 1) fill 직후 마스킹 검증 (음수/소수점/문자 → reset 또는 그대로)
        masking_cases = [
            (page.SEL_MAX_READ_COUNT_VAL, "1.5",  "최대 열람횟수 '1.5' 소수점"),
            (page.SEL_MAX_READ_COUNT_VAL, "-5",   "최대 열람횟수 '-5' 음수"),
            (page.SEL_MAX_READ_COUNT_VAL, "abc",  "최대 열람횟수 'abc' 한글/문자"),
            (page.SEL_MAX_READ_DAY_VAL,   "0.5",  "최대 유효기간 '0.5' 소수점"),
        ]
        for sel, inp, desc in masking_cases:
            loc = page.page.locator(sel)
            loc.fill("")
            page.page.wait_for_timeout(80)
            loc.fill(inp)
            page.page.wait_for_timeout(150)
            actual = loc.input_value()
            ok = actual != inp or actual == ""
            self._add("pass" if ok else "warn",
                      f"sc3c — {desc}",
                      f"입력: {inp!r} → 실제: {actual!r} (마스킹 동작 사실 확보)",
                      sc=3, highlight=loc)

        # 2) 비밀번호 최소 '5' — 사용자 보고 2026-06-01: 마스킹 X, 저장 시 차단 메시지
        page.page.locator(page.SEL_POLICY_NAME).fill("[AUTO]_sc3c_pw_probe")
        page.page.locator(page.SEL_PW_MIN).fill("5")
        page.page.wait_for_timeout(100)
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        # 사용자 보고 기대: "암호 최소 글자수는 9~15자리로 입력해주세요." 차단
        blocked_ok = ("9~15" in msg) or ("암호" in msg and "글자수" in msg) or ("최소" in msg)
        self._add("pass" if blocked_ok else "fail",
                  "sc3c — 비밀번호 최소 '5' (제약: 9 이상) — 저장 시 차단 메시지",
                  f"입력: 5 / 저장 결과 msg: {msg!r} (기대: '9~15' 또는 '암호…글자수' 차단)",
                  sc=3, highlight=page.page.locator(page.SEL_PW_MIN))
        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3d — 3000자 server reject (8 필드)
    # ==================================================================
    def test_scenario3d_3000char_server_reject(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 3d: 3000자 server reject ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()

        text_3000 = "X" * 3000
        # PDF 워터마크 텍스트 2 필드 추가 (사용자 보고 2026-06-01)
        targets = [
            ("정책 이름",         page.SEL_POLICY_NAME),
            ("열람 파일 인증 서버 URL", page.SEL_CERT_URL),
            ("허용 인쇄 브랜드",  page.SEL_ALLOW_PRINT_BRAND),
            ("제외 인쇄 포트",    page.SEL_EXCEPT_PRINT_PORT),
            ("HTML 문서 제목",   page.SEL_HTML_DOC_NAME),
            ("HTML 연락처",       page.SEL_HTML_CONTACT),
            ("커스텀 옵션값",     page.SEL_CUSTOM_OPTION),
            ("바둑판 워터마크 문구",     page.SEL_SHOOT_WM_TEXT),     # PDF 탭
            ("중앙 워터마크 표시 내용",  page.SEL_CENTER_WM_TEXT),    # PDF 탭
        ]
        pdf_text_selectors = {page.SEL_SHOOT_WM_TEXT, page.SEL_CENTER_WM_TEXT}
        for label, sel in targets:
            page.open_add_modal()
            try:
                # 필수 정책 이름 채움 — 매 iteration 다른 이름 (사용자 보고 2026-06-01: 중복 차단 fix)
                if sel != page.SEL_POLICY_NAME:
                    safe_label = label.replace(" ", "_").replace("/", "_")[:20]
                    page.page.locator(page.SEL_POLICY_NAME).fill(f"[AUTO]_sc3d_{safe_label}")
                # PDF 탭 텍스트는 탭 진입 + 워터마크 토글 ON 필요
                if sel in pdf_text_selectors:
                    page.activate_tab("PDF문서 보호 기능 설정")
                    page.page.evaluate(
                        """() => {
                            const wm = document.getElementById('isPdfWaterMark');
                            if (wm && !wm.checked) wm.click();
                            if (document.getElementById('shootPreventWaterMarkText') ===
                                document.activeElement) return;
                            const shoot = document.getElementById('isShootPreventWaterMark');
                            const center = document.getElementById('isPdfWaterMarkMain');
                            if (shoot && !shoot.checked) shoot.click();
                            if (center && !center.checked) center.click();
                        }"""
                    )
                    page.page.wait_for_timeout(200)
                page.page.locator(sel).fill(text_3000)
                _save_click(page)
                msg = ""
                if page.is_confirm_modal_visible(timeout=3000):
                    msg = page.get_confirm_message()
                    page.dismiss_confirm_modal()
                # 분류 (사용자 보고 2026-06-01 정확화):
                #   - msg == SERVER_ERR → warn (결함 재현 — 클라 가드 부재 + 서버 generic)
                #   - msg 에 "최대 N자" / "길이" → pass (명확한 차단 메시지)
                #   - msg == "저장 하였습니다" → pass (제약 없음, server 수용)
                #   - 그 외 → fail
                is_server_err = msg == SERVER_ERR
                is_saved = ("저장" in msg or "등록" in msg) and "오류" not in msg
                has_explicit_limit = ("최대" in msg) or ("자 이하" in msg) or ("길이" in msg)
                if is_server_err:
                    status = "warn"
                    note = "(generic '서버 오류' 재현 시 warn = known_bug)"
                elif is_saved:
                    status = "pass"
                    note = "(3000자 저장 허용 — server 제약 없음, 정상 동작)"
                elif has_explicit_limit:
                    status = "pass"
                    note = "(명확한 '최대 N자' 차단 메시지)"
                else:
                    status = "fail"
                    note = "(기대와 다른 응답)"
                self._add(status,
                          f"sc3d — '{label}' 3000자 저장",
                          f"입력: 'X'*3000 / 결과 msg: {msg!r} {note}",
                          sc=3, highlight=page.page.locator(sel))
            finally:
                try:
                    page.close_modal()
                except Exception:
                    pass
                page.navigate_to()

    # ==================================================================
    # sc3e — 원본보호 정책 picker → KEEP 선택 → 적용 list 추가 ⭐
    # ==================================================================
    def test_scenario3e_origin_protect_picker_select(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 3e: 원본보호 정책 picker → KEEP 선택 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 원본보호 정책 적용 토글 ON 보장
        cb = page.page.locator(page.SEL_ORIGIN_PROTECT).first
        if not cb.is_checked():
            cb.evaluate("el => el.click()")
            page.page.wait_for_timeout(200)

        # picker → KEEP 선택
        ok, detail = _select_origin_protect_keep(page)
        self._add("pass" if ok else "fail",
                  "sc3e — 원본보호 정책 picker 진입 + KEEP 선택 + 등록",
                  detail, sc=3,
                  highlight=page.page.locator(page.SEL_ORIGIN_PROTECT_BTN))
        if not ok:
            try:
                page.close_modal()
            except Exception:
                pass
            return

        # 적용 list 에 KEEP 정책 추가 확인
        applied_rows = page.page.locator("tbody#originProtectPolicyList tr")
        cnt = applied_rows.count()
        has_keep = page.page.locator(
            "tbody#originProtectPolicyList tr:has-text('[AUTO_KEEP]_sc5_origin_protect')"
        ).count() > 0
        self._add("pass" if has_keep else "fail",
                  "sc3e — 적용 list 에 KEEP 정책 행 추가 확인",
                  f"적용 list row 수={cnt} / KEEP 포함={has_keep}",
                  sc=3,
                  highlight=page.page.locator("tbody#originProtectPolicyList"))
        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3f — 적용 list 삭제 동작 ⭐
    # ==================================================================
    def test_scenario3f_applied_list_remove(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 3f: 적용 list 삭제 동작 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 원본보호 토글 ON + KEEP 선택
        cb = page.page.locator(page.SEL_ORIGIN_PROTECT).first
        if not cb.is_checked():
            cb.evaluate("el => el.click()")
            page.page.wait_for_timeout(200)
        ok, _ = _select_origin_protect_keep(page)
        if not ok:
            self._add("skip", "sc3f — picker 선택 실패로 삭제 검증 skip", "", sc=3)
            try:
                page.close_modal()
            except Exception:
                pass
            return

        # 삭제 버튼 — Chrome MCP 검증 2026-06-01: tbody#originProtectPolicyList button.deleteBtn
        before_cnt = page.page.locator("tbody#originProtectPolicyList tr").count()
        clicked = page.page.evaluate(
            """() => {
                const tbody = document.getElementById('originProtectPolicyList');
                if (!tbody) return false;
                const btn = tbody.querySelector('button.deleteBtn');
                if (!btn) return false;
                btn.click();
                return true;
            }"""
        )
        page.page.wait_for_timeout(500)
        after_cnt = page.page.locator("tbody#originProtectPolicyList tr").count()
        removed_ok = after_cnt < before_cnt
        self._add("pass" if removed_ok else "warn",
                  "sc3f — 적용 list 의 정책 삭제 동작",
                  f"클릭됨={clicked} / row 변화: {before_cnt} → {after_cnt} (감소 기대)",
                  sc=3,
                  highlight=page.page.locator("tbody#originProtectPolicyList"))
        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3g — 서버 통신 2 단계 종속 (메인 → 오프라인 → 인증없이/거부)
    # ==================================================================
    def test_scenario3g_server_auth_nested_dependencies(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 3g: 서버 통신 2 단계 종속 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 1) 메인 OFF (default) → 종속 4 다 disabled
        children = {
            "2차인증":         page.SEL_COLLECT_LOCATION,
            "오프라인 정책":   page.SEL_OFFLINE_POLICY,
            "인증없이 열람":   page.SEL_ALLOW_OFFLINE,
            "열람 거부":       page.SEL_DENY_OFFLINE,
        }
        for label, sel in children.items():
            disabled = not page.page.locator(sel).is_enabled()
            self._add("pass" if disabled else "fail",
                      f"sc3g — 메인 OFF → '{label}' disabled",
                      f"결과: disabled={disabled} (기대 True)", sc=3,
                      highlight=page.page.locator(sel))

        # 2) 메인 ON → 1단계 종속 (2차인증 + 오프라인 정책) 활성, 2단계 아직 disabled
        page.page.locator(page.SEL_SERVER_AUTH).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(200)
        for label, sel in [("2차인증", page.SEL_COLLECT_LOCATION),
                           ("오프라인 정책", page.SEL_OFFLINE_POLICY)]:
            enabled = page.page.locator(sel).is_enabled()
            self._add("pass" if enabled else "fail",
                      f"sc3g — 메인 ON → '{label}' 활성 (1단계 종속)",
                      f"결과: enabled={enabled} (기대 True)", sc=3,
                      highlight=page.page.locator(sel))
        for label, sel in [("인증없이 열람", page.SEL_ALLOW_OFFLINE),
                           ("열람 거부", page.SEL_DENY_OFFLINE)]:
            disabled = not page.page.locator(sel).is_enabled()
            self._add("pass" if disabled else "fail",
                      f"sc3g — 메인 ON + 오프라인 OFF → '{label}' disabled (2단계 종속)",
                      f"결과: disabled={disabled} (기대 True)", sc=3,
                      highlight=page.page.locator(sel))

        # 3) 오프라인 정책 ON → 2단계 종속 활성
        page.page.locator(page.SEL_OFFLINE_POLICY).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(200)
        for label, sel in [("인증없이 열람", page.SEL_ALLOW_OFFLINE),
                           ("열람 거부", page.SEL_DENY_OFFLINE)]:
            enabled = page.page.locator(sel).is_enabled()
            self._add("pass" if enabled else "fail",
                      f"sc3g — 오프라인 ON → '{label}' 활성 (2단계 종속)",
                      f"결과: enabled={enabled} (기대 True)", sc=3,
                      highlight=page.page.locator(sel))
        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3h — 인증없이/열람거부 배타적 (둘 중 하나 체크 시 나머지 disabled)
    # ==================================================================
    def test_scenario3h_offline_mutually_exclusive(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 3h: 인증없이/거부 배타적 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 메인 + 오프라인 ON
        page.page.locator(page.SEL_SERVER_AUTH).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(150)
        page.page.locator(page.SEL_OFFLINE_POLICY).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(200)

        # 인증없이 열람 ON → 열람 거부 disabled 또는 자동 OFF
        page.page.locator(page.SEL_ALLOW_OFFLINE).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(200)
        deny_state = page.page.evaluate(
            f"() => {{ const el = document.querySelector('{page.SEL_DENY_OFFLINE}'); "
            "return el ? {disabled: el.disabled, checked: el.checked} : null; }"
        )
        excl_ok_1 = deny_state and (deny_state.get("disabled") or not deny_state.get("checked"))
        self._add("pass" if excl_ok_1 else "warn",
                  "sc3h — '인증없이 열람' ON → '열람 거부' 배타적 (disabled 또는 OFF)",
                  f"결과: deny_state={deny_state} (기대: disabled=True 또는 checked=False)",
                  sc=3, highlight=page.page.locator(page.SEL_DENY_OFFLINE))

        # 반대 — 인증없이 열람 OFF + 열람 거부 ON → 인증없이 열람 disabled
        page.page.locator(page.SEL_ALLOW_OFFLINE).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(150)
        page.page.locator(page.SEL_DENY_OFFLINE).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(200)
        allow_state = page.page.evaluate(
            f"() => {{ const el = document.querySelector('{page.SEL_ALLOW_OFFLINE}'); "
            "return el ? {disabled: el.disabled, checked: el.checked} : null; }"
        )
        excl_ok_2 = allow_state and (allow_state.get("disabled") or not allow_state.get("checked"))
        self._add("pass" if excl_ok_2 else "warn",
                  "sc3h — '열람 거부' ON → '인증없이 열람' 배타적 (disabled 또는 OFF)",
                  f"결과: allow_state={allow_state} (기대: disabled=True 또는 checked=False)",
                  sc=3, highlight=page.page.locator(page.SEL_ALLOW_OFFLINE))
        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3i — 확장자 필터 추가/제거 + 토글 disabled
    # ==================================================================
    def test_scenario3i_extension_filter_add_remove(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 3i: 확장자 필터 추가/제거 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 추가 — input + 추가 버튼
        page.page.locator(page.SEL_EXT_INPUT).fill("testext")
        add_btn = page.page.locator("button#addExtensions").first
        clicked_add = False
        if add_btn.count() > 0:
            try:
                add_btn.evaluate("el => el.click()")
                page.page.wait_for_timeout(300)
                clicked_add = True
            except Exception:
                pass
        # 추가된 확장자 list 확인 (textarea / list 내 'testext')
        added = page.page.evaluate(
            """() => {
                const txt = document.body.innerText || '';
                return txt.includes('testext');
            }"""
        )
        self._add("pass" if (clicked_add and added) else "warn",
                  "sc3i — 확장자 'testext' 추가 동작",
                  f"클릭됨={clicked_add} / list 포함={added}",
                  sc=3, highlight=page.page.locator(page.SEL_EXT_INPUT))

        # 토글 OFF → 입력 disabled 확인
        page.page.locator(page.SEL_EXT_FILTER).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(200)
        input_disabled = not page.page.locator(page.SEL_EXT_INPUT).is_enabled()
        self._add("pass" if input_disabled else "fail",
                  "sc3i — 확장자 필터 토글 OFF → 입력 disabled",
                  f"결과: disabled={input_disabled} (기대 True)", sc=3,
                  highlight=page.page.locator(page.SEL_EXT_INPUT))
        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3j — PDF 메인 ON + 하위 OFF 저장 → 보호 동작 안 함 (결함 추정)
    # ==================================================================
    def test_scenario3j_pdf_main_on_sub_off_save(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 3j: PDF 메인 ON + 하위 OFF 결함 추정 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 정책 이름 채움
        page.page.locator(page.SEL_POLICY_NAME).fill("[AUTO]_sc3j_pdf_probe")

        # PDF 탭 진입
        page.activate_tab("PDF문서 보호 기능 설정")

        # PDF 메인 ON 확인 (default ON, Chrome MCP 사실 확보 2026-06-01)
        pdf_main_state = page.page.evaluate(
            "() => { const el = document.getElementById('isPdfProtect'); "
            "return el ? {checked: el.checked, disabled: el.disabled} : null; }"
        )
        if not pdf_main_state.get("checked"):
            page.page.evaluate("document.getElementById('isPdfProtect').click()")
            page.page.wait_for_timeout(200)

        # 하위 (PDF 프린트 + 워터마크) OFF 보장 — 메인 ON 상태에서 하위 default false
        # 사용자 보고: 메인 OFF 시 하위 disabled. 메인 ON 시 하위 default false 자연스러움.
        sub_state = page.page.evaluate(
            """() => ({
                pdf_print: {
                    checked: document.getElementById('isPdfPrint').checked,
                    disabled: document.getElementById('isPdfPrint').disabled
                },
                pdf_wm: {
                    checked: document.getElementById('isPdfWaterMark').checked,
                    disabled: document.getElementById('isPdfWaterMark').disabled
                }
            })"""
        )

        # 저장 시도
        _save_click(page)
        msg = ""
        modal_visible = page.is_confirm_modal_visible(timeout=2000)
        if modal_visible:
            msg = page.get_confirm_message()
        is_saved = "저장" in msg or "등록" in msg
        # 캡처 — modal 닫히기 전에 _add 호출 (confirm 모달 visible 시점)
        # 결함 가설: 메인 ON 인데 하위 OFF 라도 저장됨 → 실제 보호 동작 안 함
        # → 저장됨 = 결함 재현 (warn) / 저장 안 됨 (차단 메시지) = 정상
        # 사용자 추정 결함 (2026-06-01): PDF 메인 ON 인데 하위 (프린트/워터마크) 둘 다 OFF
        # → 메인 ON 의미 무효 (사실상 PDF 보호 동작 안 됨)
        # → 저장 허용되면 결함 재현 (warn)
        # 사용자 추정 결함 (2026-06-01): PDF 메인 ON 인데 하위 (프린트/워터마크) 둘 다 OFF
        # → 메인 ON 의미 무효 (사실상 PDF 보호 동작 안 됨)
        # Chrome MCP 사실 (2026-06-01):
        #   - 메인 OFF → 하위 disabled (자동)
        #   - 메인 ON 다시 → 하위 default false (이전 값 잔존 안 함)
        #   = 메인 ON + 하위 OFF 상태가 자연스러운 default → server 저장 허용 여부가 결함 핵심
        # 사용자 보고 정정 (2026-06-01): "하위 옵션 없다고 문제는 아님"
        # → sc3j 의 결함 가설 폐기. 사실 확보만 (pass 처리).
        # 진짜 결함은 sc3m — 중간 토글 OFF 시 하위 disabled 안 됨.
        self._add("pass",
                  "sc3j — [PDF 보호] 메인 ON + 하위 OFF 저장 동작 (사실 확보, 결함 아님)",
                  f"입력 상태: PDF 보호={pdf_main_state.get('checked')} / "
                  f"isPdfPrint={sub_state.get('pdf_print', {}).get('checked')} / "
                  f"isPdfWaterMark={sub_state.get('pdf_wm', {}).get('checked')} | "
                  f"저장 결과 msg={msg!r} | "
                  f"사용자 정정: 메인 ON 인데 하위 OFF 상태가 자연스럽게 가능 — 결함 아님 "
                  f"(진짜 결함은 sc3m 의 중간 토글 OFF 시 하위 disabled 누락)",
                  sc=3)
        if modal_visible:
            page.dismiss_confirm_modal()
        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3k — 색상 picker 변경 동작
    # ==================================================================
    def test_scenario3k_color_picker_change(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 3k: 색상 picker 변경 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()
        page.activate_tab("PDF문서 보호 기능 설정")

        # 화면 중앙 워터마크 ON
        center = page.page.locator(page.SEL_CENTER_WM).first
        if not center.is_checked():
            center.evaluate("el => el.click()")
            page.page.wait_for_timeout(200)

        # 색상 변경 — input[type='color'] 의 value 직접 set
        new_color = "#ff0000"  # 빨강
        color_loc = page.page.locator(page.SEL_CENTER_WM_COLOR).first
        color_loc.evaluate(
            f"el => {{ el.value = '{new_color}'; "
            "el.dispatchEvent(new Event('input', {bubbles: true})); "
            "el.dispatchEvent(new Event('change', {bubbles: true})); }"
        )
        page.page.wait_for_timeout(200)
        actual = color_loc.input_value()
        self._add("pass" if actual.lower() == new_color else "fail",
                  "sc3k — 색상 picker 값 변경 (#000000 → #ff0000)",
                  f"기대: {new_color!r} / 실제: {actual!r}",
                  sc=3, highlight=color_loc)
        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3m — PDF 중간 토글 종속 disabled 결함 (사용자 보고 2026-06-01)
    # ==================================================================
    def test_scenario3m_pdf_intermediate_toggle_dependency_defect(self, logged_in_page, settings):
        """sc3m — PDF '워터마크 표시하기' (중간 토글) OFF → 하위 disabled 안 됨 결함 🔴.

        사용자 보고 2026-06-01 + Chrome MCP 사실:
          - 메인 토글 (isPdfProtect) OFF → 하위 disabled ✓ (정상)
          - 중간 토글 (isPdfWaterMark) OFF → 하위 (바둑판/중앙/텍스트/색상) disabled 안 됨 🔴
          = 종속 패턴 결함 — 중간 토글 단계에서 종속 차단 동작 누락
        """
        print("\n━━ [엔파우치 정책] 시나리오 3m: PDF 중간 토글 종속 disabled 결함 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()
        page.activate_tab("PDF문서 보호 기능 설정")

        # 1) 전체 ON 상태 만들기 (메인 + 중간 + 하위 2 + 하위 텍스트 등)
        page.page.evaluate(
            """() => {
                const ids = ['isPdfProtect', 'isPdfWaterMark', 'isShootPreventWaterMark', 'isPdfWaterMarkMain'];
                ids.forEach(id => {
                    const el = document.getElementById(id);
                    if (el && !el.checked) el.click();
                });
            }"""
        )
        page.page.wait_for_timeout(300)

        # 2) 중간 토글 (isPdfWaterMark) OFF
        page.page.evaluate("document.getElementById('isPdfWaterMark').click()")
        page.page.wait_for_timeout(300)

        # 3) 하위 상태 dump
        after = page.page.evaluate(
            """() => ({
                wm_main: document.getElementById('isPdfWaterMark').checked,
                shoot_wm: {
                    checked: document.getElementById('isShootPreventWaterMark').checked,
                    disabled: document.getElementById('isShootPreventWaterMark').disabled
                },
                center_wm: {
                    checked: document.getElementById('isPdfWaterMarkMain').checked,
                    disabled: document.getElementById('isPdfWaterMarkMain').disabled
                },
                shoot_text_disabled: document.getElementById('shootPreventWaterMarkText').disabled,
                center_text_disabled: document.getElementById('pdfWaterMarkAddText').disabled,
                color_disabled: document.getElementById('pdfWaterMarkAddTextColor').disabled,
            })"""
        )

        # 검증 — 중간 OFF 면 하위 다 disabled=true 이어야 정상. 현재 동작은 disabled=false 잔존.
        children_status = [
            ("바둑판 워터마크 토글", after.get("shoot_wm", {}).get("disabled")),
            ("중앙 워터마크 토글",   after.get("center_wm", {}).get("disabled")),
            ("바둑판 워터마크 텍스트", after.get("shoot_text_disabled")),
            ("중앙 워터마크 표시 내용", after.get("center_text_disabled")),
            ("중앙 워터마크 색상",   after.get("color_disabled")),
        ]
        any_enabled_child = any((not disabled) for _, disabled in children_status)
        children_summary = " / ".join(
            f"{name} disabled={disabled}" for name, disabled in children_status
        )

        # 사용자 의도 결함 — 중간 OFF 인데 하위 disabled 안 됨 → 결함 재현 (warn)
        if any_enabled_child and not after.get("wm_main"):
            self._add("warn",
                      "sc3m — [PDF] 중간 토글 '워터마크 표시하기' OFF → 하위 disabled 안 됨 🔴 (known_bug 후보)",
                      f"중간 wm_main OFF 직후 하위 상태: {children_summary} | "
                      f"결함 의미: 종속 차단 누락 — 메인 토글만 동작, 중간 토글에서는 종속 disabled 안 함",
                      sc=3, highlight=page.page.locator(page.SEL_PDF_WATERMARK))
        else:
            self._add("pass",
                      "sc3m — [PDF] 중간 토글 OFF → 하위 disabled 정상 동작",
                      f"하위 상태: {children_summary}", sc=3)

        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3l — 정상 저장 (필수 + 옵션 채움)
    # ==================================================================
    def test_scenario3l_normal_save(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 3l: 정상 저장 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()

        NAME = "[AUTO]_sc3l_normal_save"
        page.open_add_modal()
        page.page.locator(page.SEL_POLICY_NAME).fill(NAME)

        # 원본보호 정책 적용 + KEEP 선택 (의존성)
        cb = page.page.locator(page.SEL_ORIGIN_PROTECT).first
        if not cb.is_checked():
            cb.evaluate("el => el.click()")
            page.page.wait_for_timeout(150)
        ok_picker, picker_detail = _select_origin_protect_keep(page)

        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=3000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        is_saved = "저장" in msg or "등록" in msg
        self._add("pass" if is_saved else "fail",
                  "sc3l — 정상 저장 (필수 + KEEP 정책 연계)",
                  f"입력: {NAME} + 원본보호 KEEP / picker: {picker_detail} / msg: {msg!r}",
                  sc=3)

    # ==================================================================
    # sc3n — 숫자 빈값 저장 → 검증 일관성 위반 결함 (사용자 보고 2026-06-01)
    # ==================================================================
    def test_scenario3n_empty_number_silent_zero_conversion(self, logged_in_page, settings):
        """sc3n — 숫자 필드 검증 일관성 위반 결함 🔴.

        사용자 보고 2026-06-01 핵심:
          - 다른 값 (예: 5) 입력 시 "9 이상" 등 alert 차단 동작 ✓
          - 그러나 빈값 또는 0 은 그대로 저장됨 → 재오픈 시 0
          = 같은 필드의 검증 일관성 위반 (5 는 차단 / 0 은 통과)
          = 실제 비번 정책/제한 무력화 결함

        검증 흐름: 매 iteration 다른 정책 이름 → 빈값 저장 → 재오픈 → 0 확인
        (첨부파일 개수는 도메인 의도 0 허용 — 검증 제외)
        """
        print("\n━━ [엔파우치 정책] 시나리오 3n: 숫자 빈값 → 0 silent 변환 결함 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        # 검증 일관성 위반 의심 — 빈값/0 저장 시 차단 vs 통과
        # 사용자 보고: 5 입력 시 "9 이상" 차단되는데 빈값/0 은 그대로 저장됨
        # → 같은 필드 검증 일관성 결함 (제외: 첨부파일 개수 — 0 OK 도메인 의도)
        cases = [
            ("최대 열람횟수",       page.SEL_MAX_READ_COUNT_VAL,  "view_cnt", "1 이상 200 이하"),
            ("최대 유효기간",       page.SEL_MAX_READ_DAY_VAL,    "view_day", "1 이상 1000 이하"),
            ("비밀번호 최소 글자수", page.SEL_PW_MIN,              "pw_min",   "9 ~ 15"),
            ("비밀번호 최대 글자수", page.SEL_PW_MAX,              "pw_max",   "9 ~ 15"),
            ("동일문자 허용 개수",   page.SEL_PW_SAME_LETTER,      "pw_same",  "3 이상"),
            ("연속글자 허용 개수",   page.SEL_PW_CONTINUE_LETTER,  "pw_cont",  "3 이상"),
            # 첨부파일 개수 — 사용자 정정: 0 도메인 의도, 검증 제외
        ]
        for label, sel, suffix, hint in cases:
            NAME = f"[AUTO]_sc3n_{suffix}"
            page.open_add_modal()
            try:
                page.page.locator(page.SEL_POLICY_NAME).fill(NAME)
                page.page.locator(sel).fill("")
                page.page.wait_for_timeout(150)
                _save_click(page)
                msg = ""
                if page.is_confirm_modal_visible(timeout=2000):
                    msg = page.get_confirm_message()
                    page.dismiss_confirm_modal()
                is_saved = "저장" in msg or "등록" in msg
                blocked = ("입력" in msg) or ("이상" in msg) or ("암호" in msg) or ("열람" in msg)

                if blocked:
                    self._add("pass",
                              f"sc3n — '{label}' 빈값 저장 차단 메시지 (검증 일관성 정상)",
                              f"입력: '' / msg: {msg!r} / hint: '{hint}' (server 차단 — 정상)",
                              sc=3, highlight=page.page.locator(sel))
                    try:
                        page.close_modal()
                    except Exception:
                        pass
                elif is_saved:
                    # 결함 재현 — 저장됨 + 재오픈 시 값 확인
                    try:
                        page.close_modal()
                    except Exception:
                        pass
                    page.navigate_to()
                    page.page.wait_for_timeout(500)
                    if page.is_policy_exists(NAME):
                        page.open_modify_modal(NAME)
                        reopened_val = page.page.locator(sel).input_value()
                        self._add("warn",
                                  f"sc3n — '{label}' 빈값 저장 검증 일관성 위반 결함 🔴 (known_bug 후보)",
                                  f"입력: '' / 저장 msg: {msg!r} / 재오픈 값: {reopened_val!r} | "
                                  f"결함 의미: 같은 필드에 다른 값 (예: 5) 입력 시 '{hint}' alert 차단되는데, "
                                  f"빈값/0 만 통과 → 검증 일관성 위반 → 실제 정책 무력화",
                                  sc=3, highlight=page.page.locator(sel))
                        try:
                            page.close_modal()
                        except Exception:
                            pass
                    else:
                        self._add("fail",
                                  f"sc3n — '{label}' 빈값 저장 후 list 미발견",
                                  f"저장 msg={msg!r} 이지만 '{NAME}' list 에 없음",
                                  sc=3)
                else:
                    self._add("fail",
                              f"sc3n — '{label}' 빈값 저장 결과 비정상",
                              f"입력: '' / msg: {msg!r} (차단도 저장도 아님)",
                              sc=3, highlight=page.page.locator(sel))
                    try:
                        page.close_modal()
                    except Exception:
                        pass
            except Exception as e:
                self._add("fail", f"sc3n — '{label}' 검증 예외", f"예외: {e!r}", sc=3)
                try:
                    page.close_modal()
                except Exception:
                    pass

        # 5: 원본보호 정책 사실 확보 (사용자 정정 2026-06-01: 원본보호 자체가 필수 아님)
        # → ON + picker 미선택, OFF 둘 다 사실 확보만 (결함 가설 폐기)
        NAME_OP = "[AUTO]_sc3n_op_unselected"
        page.navigate_to()
        page.open_add_modal()
        page.page.locator(page.SEL_POLICY_NAME).fill(NAME_OP)
        # 원본보호 체크박스 ON + picker 안 엶 → 저장 시도
        cb = page.page.locator(page.SEL_ORIGIN_PROTECT).first
        if not cb.is_checked():
            cb.evaluate("el => el.click()")
            page.page.wait_for_timeout(150)
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        is_saved_on = "저장" in msg or "등록" in msg
        self._add("pass",
                  "sc3n — [사실 확보] 원본보호 정책 ON + picker 미선택 저장 동작",
                  f"입력: 체크박스 ON, picker 안 엶 / msg: {msg!r} "
                  f"(원본보호 자체 필수 아님 — 결함 가설 폐기, 사실만)",
                  sc=3)
        try:
            page.close_modal()
        except Exception:
            pass

        # 6: 원본보호 OFF 상태 저장 (필수 아님 확인)
        NAME_OFF = "[AUTO]_sc3n_op_off"
        page.navigate_to()
        page.open_add_modal()
        page.page.locator(page.SEL_POLICY_NAME).fill(NAME_OFF)
        cb_off = page.page.locator(page.SEL_ORIGIN_PROTECT).first
        if cb_off.is_checked():
            cb_off.evaluate("el => el.click()")
            page.page.wait_for_timeout(150)
        _save_click(page)
        msg_off = ""
        if page.is_confirm_modal_visible(timeout=2000):
            msg_off = page.get_confirm_message()
            page.dismiss_confirm_modal()
        is_saved_off = "저장" in msg_off or "등록" in msg_off
        self._add("pass" if is_saved_off else "warn",
                  "sc3n — 원본보호 OFF 상태 정상 저장 (필수 아님 — 사용자 정정 2026-06-01)",
                  f"입력: 원본보호 체크박스 OFF / msg: {msg_off!r} "
                  f"(원본보호 자체 필수 아니라 OFF 도 저장 가능해야 정상)",
                  sc=3)
        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3o — 비밀번호 최대 < 최소 + 동일/연속 < 3 차단
    # ==================================================================
    def test_scenario3o_password_constraints(self, logged_in_page, settings):
        """sc3o — 비밀번호 제약 위반 (max<min / 동일·연속 < 3)."""
        print("\n━━ [엔파우치 정책] 시나리오 3o: 비밀번호 제약 위반 차단 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()

        # 사용자 보고 2026-06-01: 범위 밖 값 (예: 5) 는 server 가 무조건 차단 — 의미 없음
        # → 9~15 범위 내에서 "최대 < 최소" 케이스로 진짜 결함 검증
        cases = [
            ("최대(10) < 최소(12) — 둘 다 9~15 범위 내",
             [(page.SEL_PW_MIN, "12"), (page.SEL_PW_MAX, "10")],
             ["큰 숫자", "최소", "최대 글자수"]),
            ("동일문자 < 3 (값=2)",
             [(page.SEL_PW_SAME_LETTER, "2")],
             ["3 이상", "동일"]),
            ("연속글자 < 3 (값=1)",
             [(page.SEL_PW_CONTINUE_LETTER, "1")],
             ["3 이상", "연속"]),
        ]
        for label, fills, keywords in cases:
            page.open_add_modal()
            try:
                page.page.locator(page.SEL_POLICY_NAME).fill(f"[AUTO]_sc3o_{label[:8]}")
                for sel, val in fills:
                    page.page.locator(sel).fill(val)
                _save_click(page)
                msg = ""
                if page.is_confirm_modal_visible(timeout=2000):
                    msg = page.get_confirm_message()
                blocked = any(kw in msg for kw in keywords)
                self._add("pass" if blocked else "warn",
                          f"sc3o — '{label}' 차단 메시지",
                          f"입력: {fills} / msg: {msg!r} (기대 키워드: {keywords} 중 하나 차단)",
                          sc=3, highlight=page.page.locator(page.SEL_CONFIRM_MODAL).first if msg else None)
                if page.is_confirm_modal_visible(timeout=500):
                    page.dismiss_confirm_modal()
            finally:
                try:
                    page.close_modal()
                except Exception:
                    pass

    # ==================================================================
    # sc3p — 숫자 범위 초과 (열람횟수 > 200 / 유효기간 > 1000)
    # ==================================================================
    def test_scenario3p_number_range_overflow(self, logged_in_page, settings):
        """sc3p — 숫자 필드 yaml 범위 초과 (마스킹 또는 server reject)."""
        print("\n━━ [엔파우치 정책] 시나리오 3p: 숫자 범위 초과 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()

        cases = [
            ("열람횟수 250 (>200)", page.SEL_MAX_READ_COUNT_VAL, "250", "200"),
            ("유효기간 1500 (>1000)", page.SEL_MAX_READ_DAY_VAL, "1500", "1000"),
        ]
        for label, sel, val, limit in cases:
            page.open_add_modal()
            try:
                page.page.locator(page.SEL_POLICY_NAME).fill(f"[AUTO]_sc3p_{label[:8]}")
                loc = page.page.locator(sel)
                loc.fill("")
                loc.fill(val)
                page.page.wait_for_timeout(200)
                masked_val = loc.input_value()
                # 마스킹 케이스 — DOM 에서 이미 범위 잘림
                masked = (masked_val != val)
                _save_click(page)
                msg = ""
                if page.is_confirm_modal_visible(timeout=2000):
                    msg = page.get_confirm_message()
                    page.dismiss_confirm_modal()
                blocked = (limit in msg) or ("이상" in msg) or ("이하" in msg)
                ok = masked or blocked
                self._add("pass" if ok else "warn",
                          f"sc3p — '{label}' 범위 초과 처리",
                          f"입력: {val} → 마스킹된 값: {masked_val!r} (마스킹={masked}) / "
                          f"server msg: {msg!r} (기대: '{limit}' 차단 또는 마스킹)",
                          sc=3, highlight=loc)
            finally:
                try:
                    page.close_modal()
                except Exception:
                    pass

    # ==================================================================
    # sc3q — 확장자 추가 중복/빈값/형식 차단 (origin_protect sc3d 패턴)
    # ==================================================================
    def test_scenario3q_extension_add_blocked_cases(self, logged_in_page, settings):
        """sc3q — 확장자 input + 추가 시 중복/빈값/형식 차단 메시지."""
        print("\n━━ [엔파우치 정책] 시나리오 3q: 확장자 추가 차단 케이스 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 첫 정상 추가
        page.page.locator(page.SEL_EXT_INPUT).fill("doc")
        page.page.locator("button#addExtensions").first.evaluate("el => el.click()")
        page.page.wait_for_timeout(200)

        cases = [
            ("중복 추가 'doc'",     "doc",  "이미"),
            ("빈값 추가",            "",     "입력"),
            ("특수문자 '$@%'",      "$@%",  "특수"),
            ("한글 '한글'",          "한글",  "한글"),
        ]
        for label, inp, kw in cases:
            page.page.locator(page.SEL_EXT_INPUT).fill(inp)
            page.page.locator("button#addExtensions").first.evaluate("el => el.click()")
            page.page.wait_for_timeout(200)
            msg = ""
            if page.is_confirm_modal_visible(timeout=1500):
                msg = page.get_confirm_message()
                page.dismiss_confirm_modal()
            blocked = (kw in msg) or ("확장자" in msg and "입력" in msg)
            self._add("pass" if blocked else "warn",
                      f"sc3q — 확장자 '{label}' 차단 메시지",
                      f"입력: {inp!r} / msg: {msg!r} (기대: '{kw}' 차단)",
                      sc=3, highlight=page.page.locator(page.SEL_EXT_INPUT))
        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3r — 워터마크 자동 토큰 (PC정보/현재시간 체크 시 [/PCINFO/][/TIME/])
    # ==================================================================
    def test_scenario3r_watermark_auto_token(self, logged_in_page, settings):
        """sc3r — PDF 워터마크 PC정보/현재시간 체크 시 텍스트 자동 토큰 삽입."""
        print("\n━━ [엔파우치 정책] 시나리오 3r: 워터마크 자동 토큰 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()
        page.activate_tab("PDF문서 보호 기능 설정")

        # 메인 + 중간 + 바둑판 ON
        for sel in [page.SEL_PDF_PROTECT, page.SEL_PDF_WATERMARK, page.SEL_SHOOT_WM]:
            el = page.page.locator(sel).first
            if not el.is_checked():
                el.evaluate("el => el.click()")
                page.page.wait_for_timeout(100)

        # 바둑판 PC 정보 + 현재시간 ON
        for sel in [page.SEL_SHOOT_WM_PC, page.SEL_SHOOT_WM_TIME]:
            el = page.page.locator(sel).first
            if not el.is_checked():
                el.evaluate("el => el.click()")
                page.page.wait_for_timeout(200)

        text_val = page.page.locator(page.SEL_SHOOT_WM_TEXT).input_value()
        has_pcinfo = "PCINFO" in text_val
        has_time = "TIME" in text_val
        self._add("pass" if has_pcinfo and has_time else "warn",
                  "sc3r — 바둑판 워터마크 PC/시간 체크 → 자동 토큰 [/PCINFO/][/TIME/] 삽입",
                  f"text 값: {text_val!r} / PCINFO 포함={has_pcinfo} / TIME 포함={has_time}",
                  sc=3, highlight=page.page.locator(page.SEL_SHOOT_WM_TEXT))

        # PC 정보 OFF → 텍스트 자동 [/PCINFO/] 제거
        page.page.locator(page.SEL_SHOOT_WM_PC).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(200)
        text_after = page.page.locator(page.SEL_SHOOT_WM_TEXT).input_value()
        pcinfo_removed = "PCINFO" not in text_after
        self._add("pass" if pcinfo_removed else "warn",
                  "sc3r — PC 정보 OFF → 자동 [/PCINFO/] 토큰 제거",
                  f"text 값 (PC OFF 후): {text_after!r} / PCINFO 제거됨={pcinfo_removed}",
                  sc=3, highlight=page.page.locator(page.SEL_SHOOT_WM_TEXT))
        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3s — 인쇄 옵션 라디오 X/O 전환 + 첨부파일 마스킹
    # ==================================================================
    def test_scenario3s_print_radio_and_attachment(self, logged_in_page, settings):
        """sc3s — 인쇄 옵션 X/O 전환 + 첨부파일 개수 숫자 마스킹."""
        print("\n━━ [엔파우치 정책] 시나리오 3s: 인쇄 옵션 라디오 + 첨부파일 마스킹 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 인쇄 옵션 X 라디오 선택 → 상태 확인
        page.page.locator(page.SEL_PRINT_X).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(150)
        x_checked = page.page.locator(page.SEL_PRINT_X).is_checked()
        o_checked = page.page.locator(page.SEL_PRINT_O).is_checked()
        self._add("pass" if x_checked and not o_checked else "warn",
                  "sc3s — 인쇄 옵션 라디오 X 선택 → O 자동 해제 (배타)",
                  f"X={x_checked} / O={o_checked} (기대: X=True, O=False)",
                  sc=3, highlight=page.page.locator(page.SEL_PRINT_X))

        # O 선택 → 상태 반전
        page.page.locator(page.SEL_PRINT_O).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(150)
        x_after = page.page.locator(page.SEL_PRINT_X).is_checked()
        o_after = page.page.locator(page.SEL_PRINT_O).is_checked()
        self._add("pass" if o_after and not x_after else "warn",
                  "sc3s — 인쇄 옵션 라디오 O 선택 → X 자동 해제 (배타)",
                  f"X={x_after} / O={o_after} (기대: X=False, O=True)",
                  sc=3, highlight=page.page.locator(page.SEL_PRINT_O))

        # 첨부파일 개수 마스킹 (소수점 / 음수 / 문자)
        masking_cases = [
            ("1.5", "소수점"),
            ("-5",  "음수"),
            ("abc", "문자"),
        ]
        for inp, desc in masking_cases:
            loc = page.page.locator(page.SEL_FILE_COUNT_VAL)
            loc.fill("")
            page.page.wait_for_timeout(80)
            loc.fill(inp)
            page.page.wait_for_timeout(150)
            actual = loc.input_value()
            masked = actual != inp
            self._add("pass" if masked else "warn",
                      f"sc3s — 첨부파일 개수 '{inp}' {desc} 마스킹",
                      f"입력: {inp!r} → 실제: {actual!r} (마스킹 동작 사실)",
                      sc=3, highlight=loc)
        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3u — 메인 토글 OFF → 하위 disabled 종속 (사용자 보고 2026-06-02)
    # ==================================================================
    def test_scenario3u_other_toggles_dependency_disabled(self, logged_in_page, settings):
        """sc3u — 메인 토글 OFF 시 하위 필드 disabled (입력 불가) 종속 검증.

        검증 대상 (sc3g/i/m 외 추가):
          - isMaxReadCount OFF → maxReadCount disabled
          - isMaxReadDay OFF → maxReadDay disabled
          - isOpenFilePassword OFF → 비번 종속 6 disabled
          - isPrintOption OFF → 인쇄 종속 4 disabled
          - isNpPackageFileCreateFileCount OFF → 파일개수 disabled
        """
        print("\n━━ [엔파우치 정책] 시나리오 3u: 메인 토글 OFF → 하위 disabled 종속 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # (메인 토글, 종속 selector list, 라벨 list)
        groups = [
            ("열람횟수 설정", page.SEL_MAX_READ_COUNT_TOGGLE,
             [(page.SEL_MAX_READ_COUNT_VAL, "최대 열람횟수")]),
            ("열람 유효기간 설정", page.SEL_MAX_READ_DAY_TOGGLE,
             [(page.SEL_MAX_READ_DAY_VAL, "최대 유효기간")]),
            ("열기암호 사용", page.SEL_PW_TOGGLE,
             [(page.SEL_PW_MIN, "비번 최소"),
              (page.SEL_PW_MAX, "비번 최대"),
              (page.SEL_PW_SAME_LETTER, "동일문자"),
              (page.SEL_PW_CONTINUE_LETTER, "연속글자"),
              (page.SEL_PW_NUMBER_LETTER, "문자+숫자"),
              (page.SEL_PW_SPECIAL_LETTER, "특수문자")]),
            ("인쇄 옵션 사용", page.SEL_PRINT_OPTION,
             [(page.SEL_PRINT_X, "인쇄 차단"),
              (page.SEL_PRINT_O, "인쇄 허용"),
              (page.SEL_ALLOW_PRINT_BRAND, "허용 브랜드"),
              (page.SEL_EXCEPT_PRINT_PORT, "제외 포트")]),
            ("첨부파일 개수 제한", page.SEL_FILE_COUNT_TOGGLE,
             [(page.SEL_FILE_COUNT_VAL, "파일개수")]),
        ]
        for group_name, main_sel, children in groups:
            # 메인 토글 OFF (default ON 이므로 click 1회)
            el = page.page.locator(main_sel).first
            if el.is_checked():
                el.evaluate("el => el.click()")
                page.page.wait_for_timeout(200)

            # 모든 하위 disabled 확인
            for child_sel, child_label in children:
                disabled = page.page.evaluate(
                    f"() => {{ const el = document.querySelector('{child_sel}'); "
                    "return el ? el.disabled : null; }"
                )
                self._add("pass" if disabled else "warn",
                          f"sc3u — [{group_name}] OFF → '{child_label}' disabled",
                          f"결과: disabled={disabled} (기대 True)",
                          sc=3, highlight=page.page.locator(child_sel).first)

            # 메인 ON 복귀 (다음 group 영향 방지)
            if not el.is_checked():
                el.evaluate("el => el.click()")
                page.page.wait_for_timeout(150)

        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3v — HTML 가이드 파일추가 (테스트 제외, 수동 안내)
    # ==================================================================
    def test_scenario3v_html_logo_upload_manual_required(self, logged_in_page, settings):
        """sc3v — HTML 가이드 로고 이미지 파일추가 — 자동화 제외, 사용자 수동 업로드 필요.

        사용자 명령 2026-06-02: 업로드 테스트는 사용자가 직접 해야 함.
        자동화 fail/warn 대신 'error (수동 필요)' 표시 — 사용자가 직접 진행 확인.
        """
        print("\n━━ [엔파우치 정책] 시나리오 3v: HTML 파일추가 수동 안내 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 로고 이미지 input + 파일추가 버튼 존재 확인만
        logo_present = page.page.locator(page.SEL_LOGO_IMG).count() > 0
        attach_btn_present = page.page.locator("button#attachBtn, button:has-text('파일추가')").count() > 0

        # 자동화 제외 — 사용자 수동 필요 안내
        self._add("warn",
                  "sc3v — [HTML 가이드] 로고 이미지 파일추가 (자동화 제외 — 사용자 수동 업로드 필요) 🟡",
                  f"selector: logo input={page.SEL_LOGO_IMG} (present={logo_present}) / "
                  f"파일추가 버튼 (present={attach_btn_present}) | "
                  f"사용자 명령 2026-06-02: 업로드 테스트는 사용자가 직접 해야 함. "
                  f"수동 진행 후 결함 발견 시 별도 보고. (자동 fail/warn 처리 X)",
                  sc=3, highlight=page.page.locator(page.SEL_LOGO_IMG).first if logo_present else None)
        try:
            page.close_modal()
        except Exception:
            pass

    # ==================================================================
    # sc3t — picker 전체선택 동작 (header cb)
    # ==================================================================
    def test_scenario3t_picker_select_all(self, logged_in_page, settings):
        """sc3t — 원본보호 정책 picker thead 의 '전체선택' 체크박스 동작."""
        print("\n━━ [엔파우치 정책] 시나리오 3t: picker 전체선택 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 원본보호 ON + picker 진입
        cb = page.page.locator(page.SEL_ORIGIN_PROTECT).first
        if not cb.is_checked():
            cb.evaluate("el => el.click()")
            page.page.wait_for_timeout(150)
        page.page.locator(page.SEL_ORIGIN_PROTECT_BTN).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(800)

        # thead cb (전체선택) click → tbody 모든 cb 체크 확인
        result = page.page.evaluate(
            """() => {
                const pickers = Array.from(document.querySelectorAll('.c-ui-modal-dialog')).filter(p => p.offsetParent);
                const p = pickers[pickers.length-1];
                const headerCb = p.querySelector('thead input[type=checkbox]');
                if (!headerCb) return {error: 'no header cb'};
                headerCb.click();
                const tbodyCbs = Array.from(p.querySelectorAll('tbody input[type=checkbox]'));
                const total = tbodyCbs.length;
                const checked = tbodyCbs.filter(cb => cb.checked).length;
                return { total, checked, all_checked: total === checked };
            }"""
        )
        page.page.wait_for_timeout(200)
        all_checked = result.get("all_checked", False)
        self._add("pass" if all_checked else "warn",
                  "sc3t — picker thead '전체선택' → 모든 tbody cb 체크",
                  f"결과: total={result.get('total')} / checked={result.get('checked')} / "
                  f"all_checked={all_checked}",
                  sc=3)

        # picker 닫기 (취소)
        page.page.evaluate(
            """() => {
                const pickers = Array.from(document.querySelectorAll('.c-ui-modal-dialog')).filter(p => p.offsetParent);
                const p = pickers[pickers.length-1];
                const btn = Array.from(p.querySelectorAll('button')).find(b => b.textContent.trim() === '취소');
                if (btn) btn.click();
            }"""
        )
        page.page.wait_for_timeout(300)
        try:
            page.close_modal()
        except Exception:
            pass
