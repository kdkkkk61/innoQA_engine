"""nPouch 엔파우치 정책 — 시나리오 4: EDIT (수정 모달) 동작 검증.

사용자 명령 2026-06-02: sc3 의 검증 대부분 EDIT 모달에서 한번 더.

origin_protect sc4 패턴:
  - sc3 의 검증 영역을 EDIT 모달에서 동일 동작 확인
  - EDIT 고유 결함 (silent revert / 이름 중복 검증 부재 등) 분기 처리

기준 정책: sc3l 의 [AUTO]_sc3l_normal_save (없으면 EDIT 가능한 다른 [AUTO]_ 정책).
"""
from pages.npouch_policy_page import NpouchPolicyPage
from tests.npouch_policy._base import NpouchPolicyBase
from tests.npouch_policy.test_scenario3_add import _save_click, _select_origin_protect_keep


SC3L_NAME = "[AUTO]_sc3l_normal_save"
SERVER_ERR = "서버에서 오류가 발생 하였습니다."


# ─────────────────────────────────────────────────────────────────
# Helper — EDIT 진입 + 기준 정책 보장
# ─────────────────────────────────────────────────────────────────
def _ensure_sc3l_policy(page) -> bool:
    """sc3l 정책 없으면 자동 생성 (sc4 단독 실행 지원)."""
    page.navigate_to()
    page.page.wait_for_timeout(300)
    if page.is_policy_exists(SC3L_NAME):
        return True
    # 자동 생성 — 필수 5 + KEEP 연계
    page.open_add_modal()
    page.page.locator(page.SEL_POLICY_NAME).fill(SC3L_NAME)
    cb = page.page.locator(page.SEL_ORIGIN_PROTECT).first
    if not cb.is_checked():
        cb.evaluate("el => el.click()")
        page.page.wait_for_timeout(150)
    _select_origin_protect_keep(page)
    _save_click(page)
    if page.is_confirm_modal_visible(timeout=3000):
        page.dismiss_confirm_modal()
    page.page.wait_for_timeout(500)
    return page.is_policy_exists(SC3L_NAME)


def _enter_edit_modal(page, name: str) -> bool:
    """EDIT 모달 진입 — search input reset → row 더블클릭 → 수정 버튼."""
    page.navigate_to()
    page.page.wait_for_timeout(400)
    try:
        page.page.locator(page.SEL_SEARCH_INPUT).fill("")
        page.page.wait_for_timeout(200)
    except Exception:
        pass
    try:
        page.open_modify_modal(name)
        page.page.wait_for_timeout(500)
        return page.page.locator(page.SEL_MODAL_OPEN).count() > 0
    except Exception as e:
        print(f"[_enter_edit_modal] 예외: {e!r}")
        return False


def _safe_close_modal(page) -> None:
    """EDIT 모달 안전 닫기 — close_modal 의 30초 default timeout 우회 (사용자 보고 2026-06-03).

    이전: page.close_modal() → click_attached 30초 timeout (모달 이미 닫혀있으면 누적 낭비)
    이후: 직접 click(force=True, timeout=2000) + visible 체크 강화
    """
    try:
        modal = page.page.locator(page.SEL_MODAL_OPEN)
        if modal.count() == 0:
            return  # 이미 닫힘 — 즉시 return
        cancel_btn = page.page.locator(
            "div#addItemModal.in .modal-footer button:has-text('취소'):visible"
        ).first
        if cancel_btn.count() > 0:
            cancel_btn.click(force=True, timeout=2000)
        page.page.wait_for_timeout(200)
    except Exception:
        pass


class TestNpouchPolicyScenario4Modify(NpouchPolicyBase):
    """엔파우치 정책 — sc4: EDIT 동작 검증 (sc3 영역 한번 더 + EDIT 고유)."""

    # ==================================================================
    # sc4a — EDIT 진입 + 저장값 load 검증
    # ==================================================================
    def test_scenario4a_edit_enter_and_load(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4a: EDIT 진입 + 저장값 load ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3l_policy(page)

        opened = _enter_edit_modal(page, SC3L_NAME)
        self._add("pass" if opened else "fail",
                  "sc4a — EDIT 모달 진입",
                  f"입력: {SC3L_NAME!r} / 결과: opened={opened}", sc=4)
        if not opened:
            return

        loaded = page.page.evaluate(
            """() => ({
                name: document.getElementById('npPolicyName').value,
                max_read_count: document.getElementById('maxReadCount').value,
                max_read_day: document.getElementById('maxReadDay').value,
                pw_min: document.getElementById('passwordMinDigit').value,
                pw_max: document.getElementById('passwordMaxDigit').value,
                is_origin_protect: document.getElementById('isOriginProtectPolicy').checked,
                is_pdf_protect: document.getElementById('isPdfProtect').checked,
            })"""
        )
        # 저장값 정확 load 검증 (sc3l 기준)
        checks = {
            "name": SC3L_NAME,
            "max_read_count": "3",
            "max_read_day": "5",
            "pw_min": "9",
            "pw_max": "16",
            "is_origin_protect": True,
            "is_pdf_protect": True,
        }
        # 숨김(display:none) 필드는 저장값이 default(0)라 load 검증 불가 → skip.
        field_sel = {
            "max_read_count": page.SEL_MAX_READ_COUNT_VAL,
            "max_read_day":   page.SEL_MAX_READ_DAY_VAL,
            "pw_min":         page.SEL_PW_MIN,
            "pw_max":         page.SEL_PW_MAX,
        }
        for k, expected in checks.items():
            sel = field_sel.get(k)
            if sel and not page.feature_available(sel):
                self._add("skip", f"sc4a — '{k}' 저장값 load (이 빌드 미표시 → 검증 건너뜀)",
                          f"대상 {sel} 미표시 — sc0 변경사항 참조", sc=4, screenshot=False)
                continue
            actual = loaded.get(k)
            ok = actual == expected
            self._add("pass" if ok else "fail",
                      f"sc4a — '{k}' 저장값 정확 load",
                      f"기대: {expected!r} / 실제: {actual!r}", sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4b — EDIT 이름 빈값 silent revert 검증 (origin_protect sc4b known_bug 패턴)
    # ==================================================================
    def test_scenario4b_edit_name_empty_silent_revert(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4b: EDIT 이름 빈값 silent revert ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3l_policy(page)

        _enter_edit_modal(page, SC3L_NAME)
        page.page.locator(page.SEL_POLICY_NAME).fill("")
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        # silent revert: 빈값 저장됐는데 실제로는 원래 이름 보존
        is_saved = "저장" in msg and "오류" not in msg
        if is_saved:
            page.navigate_to()
            page.page.wait_for_timeout(500)
            reverted = page.is_policy_exists(SC3L_NAME)
            self._add("warn" if reverted else "fail",
                      "sc4b — EDIT 이름 빈값 silent revert + 거짓 성공 메시지 🟡 (known_bug)",
                      f"입력: '' / msg: {msg!r} / silent revert (이름 보존): {reverted} "
                      f"(ADD sc3a 차단 메시지 vs EDIT 거짓 성공 — data 안전, UX 결함)",
                      sc=4, highlight=page.page.locator(page.SEL_POLICY_NAME))
        else:
            self._add("pass" if ("정책 이름" in msg) else "fail",
                      "sc4b — EDIT 이름 빈값 차단 메시지 (정상)",
                      f"msg: {msg!r}", sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4c — EDIT 이름 중복 검증 부재 결함 (origin_protect sc4c known_bug)
    # ==================================================================
    def test_scenario4c_edit_name_duplicate_unchecked(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4c: EDIT 이름 중복 검증 부재 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3l_policy(page)

        # 다른 정책 ADD (sc3l 외 다른 이름)
        OTHER = "[AUTO]_sc4c_other"
        if not page.is_policy_exists(OTHER):
            page.open_add_modal()
            page.page.locator(page.SEL_POLICY_NAME).fill(OTHER)
            _save_click(page)
            if page.is_confirm_modal_visible(timeout=2000):
                page.dismiss_confirm_modal()

        # sc3l 이름 EDIT → OTHER 이름으로 변경 (중복)
        _enter_edit_modal(page, SC3L_NAME)
        page.page.locator(page.SEL_POLICY_NAME).fill(OTHER)
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        is_saved = "저장" in msg and "오류" not in msg
        # 결함: EDIT 중복 검증 부재 — 같은 이름으로 변경 시 차단 안 함 → 저장 성공
        self._add("warn" if is_saved else "pass",
                  "sc4c — EDIT 이름 중복 검증 부재 결함 🔴 (known_bug 후보)" if is_saved else
                  "sc4c — EDIT 이름 중복 차단 (정상)",
                  f"입력: {SC3L_NAME} → {OTHER} (이미 존재) / msg: {msg!r} / "
                  f"결함 재현 (success): {is_saved}",
                  sc=4, highlight=page.page.locator(page.SEL_POLICY_NAME))
        _safe_close_modal(page)

    # ==================================================================
    # sc4d — EDIT 숫자 마스킹 (sc3c 패턴)
    # ==================================================================
    def test_scenario4d_edit_number_masking(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4d: EDIT 숫자 마스킹 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)
        if self._skip_if_missing(page, "sc4d EDIT 숫자 마스킹(열람횟수)",
                                 [page.SEL_MAX_READ_COUNT_VAL], sc=4):
            _safe_close_modal(page); return

        cases = [
            (page.SEL_MAX_READ_COUNT_VAL, "1.5",  "EDIT 열람횟수 '1.5' 소수점"),
            (page.SEL_MAX_READ_COUNT_VAL, "-5",   "EDIT 열람횟수 '-5' 음수"),
            (page.SEL_MAX_READ_COUNT_VAL, "abc",  "EDIT 열람횟수 'abc' 문자"),
        ]
        for sel, inp, desc in cases:
            loc = page.page.locator(sel)
            loc.fill("")
            page.page.wait_for_timeout(80)
            loc.fill(inp)
            page.page.wait_for_timeout(150)
            actual = loc.input_value()
            ok = actual != inp or actual == ""
            self._add("pass" if ok else "warn",
                      f"sc4d — {desc}",
                      f"입력: {inp!r} → 실제: {actual!r} (EDIT 마스킹 sc3c 동일)",
                      sc=4, highlight=loc)
        # 원상복구
        page.page.locator(page.SEL_MAX_READ_COUNT_VAL).fill("3")
        _safe_close_modal(page)

    # ==================================================================
    # sc4e — EDIT 빈값 silent zero conversion 결함 (sc3n 패턴 EDIT 버전)
    # ==================================================================
    def test_scenario4e_edit_empty_silent_zero(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4e: EDIT 빈값 silent zero ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)

        cases = [
            ("비번 최소", page.SEL_PW_MIN, "9 ~ 15"),
            ("비번 최대", page.SEL_PW_MAX, "9 ~ 15"),
            ("동일문자",  page.SEL_PW_SAME_LETTER, "3 이상"),
            ("연속글자",  page.SEL_PW_CONTINUE_LETTER, "3 이상"),
        ]
        for label, sel, hint in cases:
            _enter_edit_modal(page, SC3L_NAME)
            if self._skip_if_missing(page, f"sc4e EDIT '{label}' 빈값", [sel], sc=4):
                _safe_close_modal(page); continue
            page.page.locator(sel).fill("")
            page.page.wait_for_timeout(150)
            _save_click(page)
            msg = ""
            if page.is_confirm_modal_visible(timeout=2000):
                msg = page.get_confirm_message()
                page.dismiss_confirm_modal()
            is_saved = "저장" in msg and "오류" not in msg
            blocked = ("이상" in msg) or ("암호" in msg) or ("입력" in msg)
            if blocked:
                self._add("pass",
                          f"sc4e — EDIT '{label}' 빈값 차단 (정상)",
                          f"msg: {msg!r} / hint: '{hint}'", sc=4, highlight=page.page.locator(sel))
            elif is_saved:
                # 재오픈 후 0 확인
                _enter_edit_modal(page, SC3L_NAME)
                reopened = page.page.locator(sel).input_value()
                self._add("warn",
                          f"sc4e — EDIT '{label}' 빈값 → silent 0 변환 결함 🔴 (sc3n EDIT 버전)",
                          f"입력: '' / msg: {msg!r} / 재오픈 값: {reopened!r} | "
                          f"검증 일관성 위반 ('{hint}' alert 차단 vs 빈값 통과)",
                          sc=4, highlight=page.page.locator(sel))
                # 원상복구
                if label == "비번 최소":
                    page.page.locator(sel).fill("9")
                elif label == "비번 최대":
                    page.page.locator(sel).fill("16")
                else:
                    page.page.locator(sel).fill("3")
                _save_click(page)
                if page.is_confirm_modal_visible(timeout=2000):
                    page.dismiss_confirm_modal()
            else:
                self._add("fail",
                          f"sc4e — EDIT '{label}' 비정상 응답",
                          f"msg: {msg!r}", sc=4)
            _safe_close_modal(page)

    # ==================================================================
    # sc4f — EDIT 원본보호 picker 재선택 + 적용 list 갱신
    # ==================================================================
    def test_scenario4f_edit_origin_protect_picker_reselect(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4f: EDIT 원본보호 picker 재선택 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)

        # 현재 적용 list row 수 확인
        before_cnt = page.page.locator("tbody#originProtectPolicyList tr").count()
        # picker 진입 + KEEP 선택 (이미 등록돼 있더라도 재선택)
        ok, detail = _select_origin_protect_keep(page)
        after_cnt = page.page.locator("tbody#originProtectPolicyList tr").count()
        self._add("pass" if ok else "fail",
                  "sc4f — EDIT 원본보호 picker 재진입 + 선택",
                  f"before row={before_cnt} / picker: {detail} / after row={after_cnt}", sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4g — EDIT 적용 list 삭제 동작
    # ==================================================================
    def test_scenario4g_edit_applied_list_remove(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4g: EDIT 적용 list 삭제 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)

        before = page.page.locator("tbody#originProtectPolicyList tr").count()
        clicked = page.page.evaluate(
            """() => {
                const tbody = document.getElementById('originProtectPolicyList');
                const btn = tbody && tbody.querySelector('button.deleteBtn');
                if (!btn) return false;
                btn.click();
                return true;
            }"""
        )
        page.page.wait_for_timeout(500)
        after = page.page.locator("tbody#originProtectPolicyList tr").count()
        self._add("pass" if (clicked and after < before) else "warn",
                  "sc4g — EDIT 적용 list 삭제 동작",
                  f"클릭: {clicked} / row 변화: {before} → {after}", sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4h — EDIT 서버 통신 2단계 종속 (sc3g EDIT 버전)
    # ==================================================================
    def test_scenario4h_edit_server_auth_nested(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4h: EDIT 서버 통신 종속 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)
        if self._skip_if_missing(page, "sc4h EDIT 서버인증 종속(오프라인)",
                                 [page.SEL_OFFLINE_POLICY], sc=4):
            _safe_close_modal(page); return

        # 메인 OFF default → 종속 4 disabled
        children = [
            ("2차인증", page.SEL_COLLECT_LOCATION),
            ("오프라인 정책", page.SEL_OFFLINE_POLICY),
        ]
        for label, sel in children:
            disabled = not page.page.locator(sel).is_enabled()
            self._add("pass" if disabled else "fail",
                      f"sc4h — EDIT 메인 OFF → '{label}' disabled",
                      f"결과: disabled={disabled}", sc=4)

        # 메인 ON → 1단계 활성
        page.page.locator(page.SEL_SERVER_AUTH).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(200)
        for label, sel in children:
            enabled = page.page.locator(sel).is_enabled()
            self._add("pass" if enabled else "fail",
                      f"sc4h — EDIT 메인 ON → '{label}' 활성",
                      f"결과: enabled={enabled}", sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4i — EDIT 인증없이/거부 배타
    # ==================================================================
    def test_scenario4i_edit_offline_mutually_exclusive(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4i: EDIT 인증없이/거부 배타 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)
        if self._skip_if_missing(page, "sc4i EDIT 오프라인 배타",
                                 [page.SEL_OFFLINE_POLICY], sc=4):
            _safe_close_modal(page); return

        # 메인 + 오프라인 ON
        page.page.locator(page.SEL_SERVER_AUTH).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(150)
        page.page.locator(page.SEL_OFFLINE_POLICY).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(200)

        # 인증없이 ON → 거부 disabled 또는 OFF
        page.page.locator(page.SEL_ALLOW_OFFLINE).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(200)
        deny_state = page.page.evaluate(
            f"() => {{ const el = document.querySelector('{page.SEL_DENY_OFFLINE}'); "
            "return {disabled: el.disabled, checked: el.checked}; }"
        )
        excl_ok = deny_state.get("disabled") or not deny_state.get("checked")
        self._add("pass" if excl_ok else "warn",
                  "sc4i — EDIT '인증없이 열람' ON → '열람 거부' 배타",
                  f"결과: {deny_state} (기대 disabled=True 또는 checked=False)", sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4j — EDIT 확장자 추가 + 중복/빈값/형식 차단 (sc3q EDIT)
    # ==================================================================
    def test_scenario4j_edit_extension_blocked(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4j: EDIT 확장자 차단 케이스 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)

        # 확장자 ON 보장
        ext_toggle = page.page.locator(page.SEL_EXT_FILTER).first
        if not ext_toggle.is_checked():
            ext_toggle.evaluate("el => el.click()")
            page.page.wait_for_timeout(150)

        # 정상 추가 1회
        page.page.locator(page.SEL_EXT_INPUT).fill("test1")
        page.page.locator("button#addExtensions").first.evaluate("el => el.click()")
        page.page.wait_for_timeout(200)

        cases = [
            ("중복 'test1'", "test1", "이미"),
            ("빈값",         "",      "입력"),
            ("한글 'ㄱ'",    "ㄱ",    "한글"),
        ]
        for label, inp, kw in cases:
            page.page.locator(page.SEL_EXT_INPUT).fill(inp)
            page.page.locator("button#addExtensions").first.evaluate("el => el.click()")
            page.page.wait_for_timeout(200)
            msg = ""
            if page.is_confirm_modal_visible(timeout=1500):
                msg = page.get_confirm_message()
                page.dismiss_confirm_modal()
            blocked = (kw in msg) or ("확장자" in msg)
            self._add("pass" if blocked else "warn",
                      f"sc4j — EDIT 확장자 '{label}' 차단",
                      f"입력: {inp!r} / msg: {msg!r}",
                      sc=4, highlight=page.page.locator(page.SEL_EXT_INPUT))
        _safe_close_modal(page)

    # ==================================================================
    # sc4k — EDIT 3000자 server reject (sc3d EDIT)
    # ==================================================================
    def test_scenario4k_edit_3000char(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4k: EDIT 3000자 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)

        targets = [
            ("정책 이름",              page.SEL_POLICY_NAME),
            ("열람 파일 인증 서버 URL", page.SEL_CERT_URL),
            ("허용 인쇄 브랜드",       page.SEL_ALLOW_PRINT_BRAND),
            ("제외 인쇄 포트",         page.SEL_EXCEPT_PRINT_PORT),
            ("HTML 문서 제목",         page.SEL_HTML_DOC_NAME),
            ("HTML 연락처",            page.SEL_HTML_CONTACT),
            ("커스텀 옵션값",          page.SEL_CUSTOM_OPTION),
            ("바둑판 워터마크 문구",   page.SEL_SHOOT_WM_TEXT),
            ("중앙 워터마크 표시 내용", page.SEL_CENTER_WM_TEXT),
        ]
        text_3000 = "X" * 3000
        pdf_text_selectors = {page.SEL_SHOOT_WM_TEXT, page.SEL_CENTER_WM_TEXT}
        for label, sel in targets:
            _enter_edit_modal(page, SC3L_NAME)
            # PDF 탭 텍스트는 탭 진입 + 워터마크 토글 ON (입력 가능 상태)
            if sel in pdf_text_selectors:
                page.activate_tab("PDF문서 보호 기능 설정")
                page.page.evaluate(
                    """() => {
                        ['isPdfProtect','isPdfWaterMark','isShootPreventWaterMark','isPdfWaterMarkMain'].forEach(id => {
                            const el = document.getElementById(id);
                            if (el && !el.checked) el.click();
                        });
                    }"""
                )
                page.page.wait_for_timeout(200)
            page.page.locator(sel).fill(text_3000)
            _save_click(page)
            msg = ""
            if page.is_confirm_modal_visible(timeout=3000):
                msg = page.get_confirm_message()
                page.dismiss_confirm_modal()
            is_server_err = msg == SERVER_ERR
            is_saved = "저장" in msg and "오류" not in msg
            has_limit = "최대" in msg or "자 이하" in msg
            if is_server_err:
                status, note = "warn", "(generic server error 재현 = known_bug)"
            elif is_saved:
                status, note = "pass", "(3000자 server 수용 — 제약 없음)"
            elif has_limit:
                status, note = "pass", "(명확한 '최대 N자' 차단)"
            else:
                status, note = "fail", "(비정상 응답)"
            self._add(status, f"sc4k — EDIT '{label}' 3000자",
                      f"msg: {msg!r} {note}", sc=4, highlight=page.page.locator(sel))
            _safe_close_modal(page)

    # ==================================================================
    # sc4l — EDIT 색상 picker 변경 (sc3k EDIT)
    # ==================================================================
    def test_scenario4l_edit_color_picker(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4l: EDIT 색상 picker 변경 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)
        page.activate_tab("PDF문서 보호 기능 설정")

        # 화면 중앙 워터마크 ON 보장
        center = page.page.locator(page.SEL_CENTER_WM).first
        if not center.is_checked():
            center.evaluate("el => el.click()")
            page.page.wait_for_timeout(200)

        new_color = "#00ff00"
        color_loc = page.page.locator(page.SEL_CENTER_WM_COLOR).first
        color_loc.evaluate(
            f"el => {{ el.value = '{new_color}'; "
            "el.dispatchEvent(new Event('input', {bubbles: true})); "
            "el.dispatchEvent(new Event('change', {bubbles: true})); }"
        )
        page.page.wait_for_timeout(200)
        actual = color_loc.input_value()
        self._add("pass" if actual.lower() == new_color else "fail",
                  "sc4l — EDIT 색상 picker 변경",
                  f"기대: {new_color!r} / 실제: {actual!r}",
                  sc=4, highlight=color_loc)
        _safe_close_modal(page)

    # ==================================================================
    # sc4m — EDIT PDF 중간 토글 종속 결함 (sc3m EDIT)
    # ==================================================================
    def test_scenario4m_edit_pdf_intermediate_dependency_defect(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4m: EDIT PDF 중간 토글 종속 결함 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)
        page.activate_tab("PDF문서 보호 기능 설정")

        # 전체 ON (이미 ON 이면 idempotent)
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
        # 중간 토글 OFF
        page.page.evaluate("document.getElementById('isPdfWaterMark').click()")
        page.page.wait_for_timeout(300)
        after = page.page.evaluate(
            """() => ({
                shoot_disabled: document.getElementById('isShootPreventWaterMark').disabled,
                center_disabled: document.getElementById('isPdfWaterMarkMain').disabled,
                color_disabled: document.getElementById('pdfWaterMarkAddTextColor').disabled,
            })"""
        )
        any_enabled = (not after.get('shoot_disabled')) or (not after.get('center_disabled')) or (not after.get('color_disabled'))
        self._add("warn" if any_enabled else "pass",
                  "sc4m — EDIT PDF 중간 토글 OFF → 하위 disabled 안 됨 🔴 (sc3m EDIT 동일 결함)" if any_enabled else
                  "sc4m — EDIT PDF 중간 토글 OFF → 하위 disabled 정상",
                  f"after: {after}", sc=4, highlight=page.page.locator(page.SEL_PDF_WATERMARK))
        _safe_close_modal(page)

    # ==================================================================
    # sc4n — EDIT 토글 종속 disabled (sc3u EDIT)
    # ==================================================================
    def test_scenario4n_edit_other_toggles_dependency(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4n: EDIT 토글 종속 disabled ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)
        if self._skip_if_missing(page, "sc4n EDIT 토글 종속(열람횟수 등)",
                                 [page.SEL_MAX_READ_COUNT_VAL], sc=4):
            _safe_close_modal(page); return

        groups = [
            ("열람횟수", page.SEL_MAX_READ_COUNT_TOGGLE, [(page.SEL_MAX_READ_COUNT_VAL, "값")]),
            ("열기암호", page.SEL_PW_TOGGLE, [(page.SEL_PW_MIN, "최소"), (page.SEL_PW_MAX, "최대")]),
            ("인쇄 옵션", page.SEL_PRINT_OPTION, [(page.SEL_ALLOW_PRINT_BRAND, "브랜드")]),
        ]
        for group_name, main_sel, children in groups:
            el = page.page.locator(main_sel).first
            if el.is_checked():
                el.evaluate("el => el.click()")
                page.page.wait_for_timeout(200)
            for child_sel, label in children:
                disabled = page.page.evaluate(
                    f"() => {{ const el = document.querySelector('{child_sel}'); "
                    "return el ? el.disabled : null; }"
                )
                self._add("pass" if disabled else "warn",
                          f"sc4n — EDIT [{group_name}] OFF → '{label}' disabled",
                          f"결과: disabled={disabled}", sc=4)
            # 복귀
            if not el.is_checked():
                el.evaluate("el => el.click()")
                page.page.wait_for_timeout(150)
        _safe_close_modal(page)

    # ==================================================================
    # sc4p — EDIT 비밀번호 제약 위반 (sc3o EDIT 버전)
    # ==================================================================
    def test_scenario4p_edit_password_constraints(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4p: EDIT 비번 제약 위반 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)

        cases = [
            ("최대(10) < 최소(12)", [(page.SEL_PW_MIN, "12"), (page.SEL_PW_MAX, "10")],
             ["큰 숫자", "최소", "최대 글자수"]),
            ("동일문자 < 3 (2)", [(page.SEL_PW_SAME_LETTER, "2")], ["3 이상", "동일"]),
            ("연속글자 < 3 (1)", [(page.SEL_PW_CONTINUE_LETTER, "1")], ["3 이상", "연속"]),
        ]
        for label, fills, kws in cases:
            _enter_edit_modal(page, SC3L_NAME)
            if self._skip_if_missing(page, f"sc4p EDIT 비번 '{label}'", [page.SEL_PW_MIN], sc=4):
                _safe_close_modal(page); continue
            for sel, val in fills:
                page.page.locator(sel).fill(val)
            _save_click(page)
            msg = ""
            if page.is_confirm_modal_visible(timeout=2000):
                msg = page.get_confirm_message()
                page.dismiss_confirm_modal()
            blocked = any(kw in msg for kw in kws)
            self._add("pass" if blocked else "warn",
                      f"sc4p — EDIT '{label}' 차단",
                      f"입력: {fills} / msg: {msg!r} / 기대 키워드: {kws}",
                      sc=4)
            _safe_close_modal(page)

    # ==================================================================
    # sc4q — EDIT 숫자 범위 초과 (sc3p EDIT)
    # ==================================================================
    def test_scenario4q_edit_number_range_overflow(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4q: EDIT 숫자 범위 초과 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)

        cases = [
            ("열람횟수 250 (>200)", page.SEL_MAX_READ_COUNT_VAL, "250", "200"),
            ("유효기간 1500 (>1000)", page.SEL_MAX_READ_DAY_VAL, "1500", "1000"),
        ]
        for label, sel, val, limit in cases:
            _enter_edit_modal(page, SC3L_NAME)
            if self._skip_if_missing(page, f"sc4q EDIT '{label}'", [sel], sc=4):
                _safe_close_modal(page); continue
            loc = page.page.locator(sel)
            loc.fill("")
            loc.fill(val)
            page.page.wait_for_timeout(200)
            masked_val = loc.input_value()
            masked = masked_val != val
            _save_click(page)
            msg = ""
            if page.is_confirm_modal_visible(timeout=2000):
                msg = page.get_confirm_message()
                page.dismiss_confirm_modal()
            ok = masked or (limit in msg) or ("이상" in msg) or ("이하" in msg)
            self._add("pass" if ok else "warn",
                      f"sc4q — EDIT '{label}' 범위 초과 처리",
                      f"입력: {val} → 마스킹: {masked_val!r} (masked={masked}) / server msg: {msg!r}",
                      sc=4, highlight=loc)
            _safe_close_modal(page)

    # ==================================================================
    # sc4r — EDIT 워터마크 자동 토큰 (sc3r EDIT)
    # ==================================================================
    def test_scenario4r_edit_watermark_auto_token(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4r: EDIT 워터마크 자동 토큰 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)
        page.activate_tab("PDF문서 보호 기능 설정")

        # 메인/중간/바둑판 ON
        for sel in [page.SEL_PDF_PROTECT, page.SEL_PDF_WATERMARK, page.SEL_SHOOT_WM]:
            el = page.page.locator(sel).first
            if not el.is_checked():
                el.evaluate("el => el.click()")
                page.page.wait_for_timeout(100)
        # PC + TIME ON
        for sel in [page.SEL_SHOOT_WM_PC, page.SEL_SHOOT_WM_TIME]:
            el = page.page.locator(sel).first
            if not el.is_checked():
                el.evaluate("el => el.click()")
                page.page.wait_for_timeout(200)

        text_val = page.page.locator(page.SEL_SHOOT_WM_TEXT).input_value()
        has_pc = "PCINFO" in text_val
        has_time = "TIME" in text_val
        self._add("pass" if has_pc and has_time else "warn",
                  "sc4r — EDIT 워터마크 PC/TIME 체크 → 자동 토큰 [/PCINFO/][/TIME/]",
                  f"text: {text_val!r} / PCINFO={has_pc} / TIME={has_time}",
                  sc=4, highlight=page.page.locator(page.SEL_SHOOT_WM_TEXT))

        # PC OFF → 토큰 제거
        page.page.locator(page.SEL_SHOOT_WM_PC).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(200)
        text_after = page.page.locator(page.SEL_SHOOT_WM_TEXT).input_value()
        pcinfo_removed = "PCINFO" not in text_after
        self._add("pass" if pcinfo_removed else "warn",
                  "sc4r — EDIT PC OFF → [/PCINFO/] 자동 제거",
                  f"text after PC OFF: {text_after!r} / PCINFO 제거={pcinfo_removed}",
                  sc=4, highlight=page.page.locator(page.SEL_SHOOT_WM_TEXT))
        _safe_close_modal(page)

    # ==================================================================
    # sc4s — EDIT 인쇄 라디오 + 첨부파일 마스킹 (sc3s EDIT)
    # ==================================================================
    def test_scenario4s_edit_print_radio_attachment(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4s: EDIT 인쇄 라디오 + 첨부 마스킹 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)

        # 인쇄 옵션 ON 보장
        if not page.page.locator(page.SEL_PRINT_OPTION).is_checked():
            page.page.locator(page.SEL_PRINT_OPTION).first.evaluate("el => el.click()")
            page.page.wait_for_timeout(150)

        # X 선택 → O 해제
        page.page.locator(page.SEL_PRINT_X).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(150)
        x = page.page.locator(page.SEL_PRINT_X).is_checked()
        o = page.page.locator(page.SEL_PRINT_O).is_checked()
        self._add("pass" if x and not o else "warn",
                  "sc4s — EDIT 인쇄 라디오 X → O 자동 해제",
                  f"X={x} / O={o}", sc=4)

        # 첨부파일 마스킹
        if not page.page.locator(page.SEL_FILE_COUNT_TOGGLE).is_checked():
            page.page.locator(page.SEL_FILE_COUNT_TOGGLE).first.evaluate("el => el.click()")
            page.page.wait_for_timeout(150)
        for inp, desc in [("1.5", "소수점"), ("-5", "음수"), ("abc", "문자")]:
            loc = page.page.locator(page.SEL_FILE_COUNT_VAL)
            loc.fill("")
            loc.fill(inp)
            page.page.wait_for_timeout(150)
            actual = loc.input_value()
            self._add("pass" if actual != inp else "warn",
                      f"sc4s — EDIT 첨부파일 '{inp}' {desc} 마스킹",
                      f"입력: {inp!r} → 실제: {actual!r}", sc=4, highlight=loc)
        _safe_close_modal(page)

    # ==================================================================
    # sc4t — EDIT picker 전체선택 (sc3t EDIT)
    # ==================================================================
    def test_scenario4t_edit_picker_select_all(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4t: EDIT picker 전체선택 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)

        # 원본보호 ON 보장
        cb = page.page.locator(page.SEL_ORIGIN_PROTECT).first
        if not cb.is_checked():
            cb.evaluate("el => el.click()")
            page.page.wait_for_timeout(150)
        # picker 진입
        page.page.locator(page.SEL_ORIGIN_PROTECT_BTN).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(800)

        result = page.page.evaluate(
            """() => {
                const pickers = Array.from(document.querySelectorAll('.c-ui-modal-dialog')).filter(p => p.offsetParent);
                const p = pickers[pickers.length-1];
                const headerCb = p.querySelector('thead input[type=checkbox]');
                if (!headerCb) return {error: 'no header cb'};
                headerCb.click();
                const tbodyCbs = Array.from(p.querySelectorAll('tbody input[type=checkbox]'));
                return { total: tbodyCbs.length, checked: tbodyCbs.filter(cb => cb.checked).length };
            }"""
        )
        all_checked = result.get("total") == result.get("checked") and result.get("total", 0) > 0
        self._add("pass" if all_checked else "warn",
                  "sc4t — EDIT picker '전체선택' → 모든 tbody cb 체크",
                  f"total={result.get('total')} / checked={result.get('checked')}",
                  sc=4)

        # picker 닫기
        page.page.evaluate(
            """() => {
                const pickers = Array.from(document.querySelectorAll('.c-ui-modal-dialog')).filter(p => p.offsetParent);
                const p = pickers[pickers.length-1];
                const btn = Array.from(p.querySelectorAll('button')).find(b => b.textContent.trim() === '취소');
                if (btn) btn.click();
            }"""
        )
        page.page.wait_for_timeout(300)
        _safe_close_modal(page)

    # ==================================================================
    # sc4u — EDIT HTML 업로드 수동 안내 (sc3v EDIT)
    # ==================================================================
    def test_scenario4u_edit_html_logo_upload_manual(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4u: EDIT HTML 업로드 수동 안내 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)

        logo_present = page.page.locator(page.SEL_LOGO_IMG).count() > 0
        attach_btn_present = page.page.locator("button#attachBtn, button:has-text('파일추가')").count() > 0
        self._add("warn",
                  "sc4u — EDIT HTML 로고 이미지 (자동화 제외 — 사용자 수동 업로드) 🟡",
                  f"logo input={page.SEL_LOGO_IMG} (present={logo_present}) / "
                  f"파일추가 버튼 (present={attach_btn_present}) | "
                  f"사용자 명령 2026-06-02: 업로드 테스트는 사용자가 직접",
                  sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4v — EDIT PDF 메인+하위 OFF 사실 확보 (sc3j EDIT)
    # ==================================================================
    def test_scenario4v_edit_pdf_main_with_sub_off(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4v: EDIT PDF 메인 ON + 하위 OFF 사실 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)
        page.activate_tab("PDF문서 보호 기능 설정")

        # 메인 ON 보장, 하위 OFF
        page.page.evaluate(
            """() => {
                const m = document.getElementById('isPdfProtect');
                if (m && !m.checked) m.click();
                ['isPdfPrint', 'isPdfWaterMark'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el && el.checked) el.click();
                });
            }"""
        )
        page.page.wait_for_timeout(200)
        state = page.page.evaluate(
            """() => ({
                main: document.getElementById('isPdfProtect').checked,
                print: document.getElementById('isPdfPrint').checked,
                wm: document.getElementById('isPdfWaterMark').checked,
            })"""
        )
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=3000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        # 사용자 정정 2026-06-01: PDF 메인 ON + 하위 OFF 자체는 결함 아님 — 사실 확보만
        self._add("pass",
                  "sc4v — EDIT PDF 메인 ON + 하위 OFF 저장 동작 (사실 확보, 결함 아님)",
                  f"상태: {state} / msg: {msg!r} | "
                  f"사용자 정정: 메인 ON + 하위 OFF 자체는 자연스러운 default — 결함 아님 "
                  f"(진짜 결함은 sc4m 중간 토글 종속 누락)",
                  sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4w — 원본보호 메인 OFF → 적용 list 삭제 버튼 동작 결함 🔴 (사용자 보고 2026-06-02)
    # ==================================================================
    def test_scenario4w_origin_protect_off_delete_still_works_defect(self, logged_in_page, settings):
        """sc4w — 원본보호 메인 OFF 시 하위 (적용 list 삭제) 종속 disabled 안 됨 🔴.

        사용자 보고 2026-06-02:
          - 원본보호 메인 토글 ON + 정책선택 → 적용 list 에 정책 등록
          - 메인 토글 OFF → 하위 disabled 되어야 정상 (정책선택 버튼은 disabled)
          - 그러나 적용 list 의 deleteBtn 동작 (row 사라짐) → 결함

        sc3m / sc4m (PDF 중간 토글) 와 유사 패턴 — 종속 차단 누락.
        """
        print("\n━━ [엔파우치 정책] 시나리오 4w: 원본보호 OFF + 삭제 결함 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)

        # 1) 원본보호 ON + KEEP 선택 (적용 list 갱신)
        cb = page.page.locator(page.SEL_ORIGIN_PROTECT).first
        if not cb.is_checked():
            cb.evaluate("el => el.click()")
            page.page.wait_for_timeout(150)
        if page.page.locator("tbody#originProtectPolicyList tr").count() == 0:
            _select_origin_protect_keep(page)
        before_cnt = page.page.locator("tbody#originProtectPolicyList tr").count()

        # 2) 원본보호 메인 OFF (적용 list 잔존 + 정책선택 버튼 disabled 화면)
        cb.evaluate("el => el.click()")
        page.page.wait_for_timeout(300)
        cb_state = page.page.evaluate(
            f"() => {{ const el = document.querySelector('{page.SEL_ORIGIN_PROTECT}'); "
            "return el ? el.checked : null; }"
        )
        # 정책선택 버튼 disabled 여부
        select_btn_disabled = page.page.evaluate(
            "() => { const b = document.getElementById('addNpouchOriginProtectPolicyBtn'); "
            "return b ? b.disabled : null; }"
        )
        # 적용 list 의 deleteBtn disabled 여부
        delete_btn_disabled = page.page.evaluate(
            """() => {
                const tbody = document.getElementById('originProtectPolicyList');
                if (!tbody) return 'no tbody';
                const btn = tbody.querySelector('button.deleteBtn');
                return btn ? btn.disabled : 'no btn';
            }"""
        )

        # 3) 삭제 버튼 click 시도 → row 사라지는지
        click_result = page.page.evaluate(
            """() => {
                const tbody = document.getElementById('originProtectPolicyList');
                const btn = tbody && tbody.querySelector('button.deleteBtn');
                if (!btn) return 'no btn';
                btn.click();
                return 'clicked';
            }"""
        )
        page.page.wait_for_timeout(500)
        after_cnt = page.page.locator("tbody#originProtectPolicyList tr").count()
        delete_worked = after_cnt < before_cnt

        # 결함 판정: 메인 OFF 상태에서 삭제 동작 = 종속 차단 누락
        if delete_worked:
            self._add("warn",
                      "sc4w — 원본보호 메인 OFF → 적용 list 삭제 동작 결함 🔴 (known_bug 후보)",
                      f"메인 OFF 상태 (checked={cb_state}) / 정책선택 버튼 disabled={select_btn_disabled} / "
                      f"삭제 버튼 disabled={delete_btn_disabled} / click={click_result} / "
                      f"row 변화: {before_cnt} → {after_cnt} (감소={delete_worked}) | "
                      f"결함 의미: 메인 OFF 인데 적용 list 의 삭제 동작 → 종속 차단 누락 "
                      f"(정책선택 버튼은 disabled 됐지만 삭제 버튼은 동작)",
                      sc=4, highlight=page.page.locator("tbody#originProtectPolicyList"))
        else:
            self._add("pass",
                      "sc4w — 원본보호 메인 OFF → 적용 list 삭제 차단 (정상)",
                      f"메인 OFF / 삭제 동작 안 함 (row {before_cnt} → {after_cnt})",
                      sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4x — 시나리오 기반 검증: 메인 ON+값 채움 → OFF → 하위 동작 차단 (10 영역)
    # 사용자 보고 2026-06-02: "값 넣고 OFF 해야 하위 동작 차단 검증 가능"
    # ==================================================================
    def test_scenario4x_main_off_sub_action_blocked_scenario(self, logged_in_page, settings):
        """sc4x — 시나리오 기반 종속 검증.

        패턴:
          1. 메인 ON + 하위 값/click 채움
          2. 메인 OFF
          3. 하위 element 동작 차단 검증 (disabled / click 무효 / fill 무효)

        sc4w 의 원본보호 결함과 같은 패턴 — 다른 영역도 동일 결함 가능성.
        """
        print("\n━━ [엔파우치 정책] 시나리오 4x: 시나리오 기반 종속 동작 차단 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)

        def _scenario_check(label: str, main_sel: str, sub_actions: list, expected_blocks: list):
            """한 영역 시나리오 검증.

            sub_actions: [(sel, action, value)] — action='fill' or 'click'
            expected_blocks: [(sel, check_type)] — check_type='input_value' or 'checked' or 'disabled'
            """
            _enter_edit_modal(page, SC3L_NAME)
            if self._skip_if_missing(page, f"sc4x {label}",
                                     [main_sel] + [a[0] for a in sub_actions], sc=4):
                _safe_close_modal(page); return
            # 1) 메인 ON 보장
            main_el = page.page.locator(main_sel).first
            if not main_el.is_checked():
                main_el.evaluate("el => el.click()")
                page.page.wait_for_timeout(150)
            # 2) 하위 값 채움
            for sel, action, value in sub_actions:
                try:
                    if action == "fill":
                        page.page.locator(sel).fill(value)
                    elif action == "click":
                        page.page.locator(sel).first.evaluate("el => el.click()")
                    page.page.wait_for_timeout(80)
                except Exception:
                    pass
            # 3) 메인 OFF
            main_el.evaluate("el => el.click()")
            page.page.wait_for_timeout(300)
            # 4) 하위 동작 차단 검증
            for sel, check_type in expected_blocks:
                if check_type == "disabled":
                    disabled = page.page.evaluate(
                        f"() => {{ const el = document.querySelector('{sel}'); "
                        "return el ? el.disabled : null; }"
                    )
                    self._add("pass" if disabled else "warn",
                              f"sc4x — [{label}] OFF → '{sel}' disabled",
                              f"결과: disabled={disabled} (기대 True)", sc=4,
                              highlight=page.page.locator(sel).first)
            _safe_close_modal(page)

        # 1) 인쇄 옵션 — ON 시 브랜드/포트 채움 → OFF → disabled
        _scenario_check(
            "인쇄 옵션", page.SEL_PRINT_OPTION,
            [(page.SEL_ALLOW_PRINT_BRAND, "fill", "TestBrand"),
             (page.SEL_EXCEPT_PRINT_PORT, "fill", "TestPort")],
            [(page.SEL_PRINT_X, "disabled"), (page.SEL_PRINT_O, "disabled"),
             (page.SEL_ALLOW_PRINT_BRAND, "disabled"), (page.SEL_EXCEPT_PRINT_PORT, "disabled")],
        )

        # 2) 열기암호 — ON 시 모든 비번 종속 ON/채움 → OFF → disabled
        _scenario_check(
            "열기암호", page.SEL_PW_TOGGLE,
            [(page.SEL_PW_NUMBER_LETTER, "click", None),
             (page.SEL_PW_SPECIAL_LETTER, "click", None)],
            [(page.SEL_PW_MIN, "disabled"), (page.SEL_PW_MAX, "disabled"),
             (page.SEL_PW_SAME_LETTER, "disabled"), (page.SEL_PW_CONTINUE_LETTER, "disabled"),
             (page.SEL_PW_NUMBER_LETTER, "disabled"), (page.SEL_PW_SPECIAL_LETTER, "disabled")],
        )

        # 3) 첨부파일 개수 — ON + 값 → OFF → disabled
        _scenario_check(
            "첨부파일 개수", page.SEL_FILE_COUNT_TOGGLE,
            [(page.SEL_FILE_COUNT_VAL, "fill", "5")],
            [(page.SEL_FILE_COUNT_VAL, "disabled")],
        )

        # 4) 확장자 필터 — ON + 확장자 추가 → OFF → 입력/추가 disabled
        _enter_edit_modal(page, SC3L_NAME)
        ext = page.page.locator(page.SEL_EXT_FILTER).first
        if not ext.is_checked():
            ext.evaluate("el => el.click()")
            page.page.wait_for_timeout(150)
        page.page.locator(page.SEL_EXT_INPUT).fill("docx")
        page.page.locator("button#addExtensions").first.evaluate("el => el.click()")
        page.page.wait_for_timeout(200)
        ext.evaluate("el => el.click()")  # OFF
        page.page.wait_for_timeout(200)
        ext_input_disabled = page.page.evaluate(
            f"() => document.querySelector('{page.SEL_EXT_INPUT}').disabled"
        )
        ext_add_disabled = page.page.evaluate(
            "() => document.getElementById('addExtensions').disabled"
        )
        self._add("pass" if ext_input_disabled else "warn",
                  "sc4x — [확장자 필터] OFF → 확장자 input disabled",
                  f"결과: disabled={ext_input_disabled}", sc=4)
        self._add("pass" if ext_add_disabled else "warn",
                  "sc4x — [확장자 필터] OFF → 추가 버튼 disabled",
                  f"결과: disabled={ext_add_disabled}", sc=4)
        _safe_close_modal(page)

        # 5) PDF 보호 메인 — ON + 워터마크 채움 → OFF → 하위 disabled
        _enter_edit_modal(page, SC3L_NAME)
        page.activate_tab("PDF문서 보호 기능 설정")
        page.page.evaluate(
            """() => {
                ['isPdfProtect','isPdfWaterMark','isPdfWaterMarkMain'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el && !el.checked) el.click();
                });
            }"""
        )
        page.page.wait_for_timeout(200)
        page.page.locator(page.SEL_CENTER_WM_TEXT).fill("PdfTest")
        page.page.wait_for_timeout(100)
        # PDF 메인 OFF
        page.page.evaluate("document.getElementById('isPdfProtect').click()")
        page.page.wait_for_timeout(300)
        pdf_print_disabled = page.page.evaluate(
            "() => document.getElementById('isPdfPrint').disabled"
        )
        center_text_disabled = page.page.evaluate(
            "() => document.getElementById('pdfWaterMarkAddText').disabled"
        )
        color_disabled = page.page.evaluate(
            "() => document.getElementById('pdfWaterMarkAddTextColor').disabled"
        )
        self._add("pass" if pdf_print_disabled else "warn",
                  "sc4x — [PDF 보호 메인] OFF → 'PDF 프린트' disabled",
                  f"결과: disabled={pdf_print_disabled}", sc=4)
        self._add("pass" if center_text_disabled else "warn",
                  "sc4x — [PDF 보호 메인] OFF → '중앙 워터마크 텍스트' disabled",
                  f"결과: disabled={center_text_disabled}", sc=4)
        self._add("pass" if color_disabled else "warn",
                  "sc4x — [PDF 보호 메인] OFF → '색상 picker' disabled",
                  f"결과: disabled={color_disabled}", sc=4)
        _safe_close_modal(page)

        # 6) 화면 중앙 워터마크 — ON + 텍스트/색상/크기/투명도/기울기 채움 → OFF → 종속 disabled
        # 사용자 보고 2026-06-02: 중앙 워터마크 OFF 시 색상/텍스트 enabled 잔존 = 결함 재현
        _enter_edit_modal(page, SC3L_NAME)
        page.activate_tab("PDF문서 보호 기능 설정")
        page.page.evaluate(
            """() => {
                ['isPdfProtect','isPdfWaterMark','isPdfWaterMarkMain'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el && !el.checked) el.click();
                });
            }"""
        )
        page.page.wait_for_timeout(200)
        # ON 시 종속 다 채움 (사용자 의도: 값 채운 후 OFF)
        page.page.locator(page.SEL_CENTER_WM_TEXT).fill("CenterTest")
        page.page.locator(page.SEL_CENTER_WM_SIZE).fill("12")
        page.page.locator(page.SEL_CENTER_WM_OPACITY).fill("50")
        page.page.locator(page.SEL_CENTER_WM_DEGREE).fill("45")
        page.page.locator(page.SEL_CENTER_WM_COLOR).evaluate("el => { el.value='#ff0000'; el.dispatchEvent(new Event('change',{bubbles:true})); }")
        page.page.wait_for_timeout(100)
        # 중앙 워터마크 OFF
        page.page.evaluate("document.getElementById('isPdfWaterMarkMain').click()")
        page.page.wait_for_timeout(300)
        # 5 종속 disabled 검증
        checks = [
            ("표시 내용", "pdfWaterMarkAddText"),
            ("글자 크기", "pdfWaterMarkAddTextSize"),
            ("불투명도",   "pdfWaterMarkAddTextOpacity"),
            ("기울기",     "pdfWaterMarkAddTextDegree"),
            ("색상 picker", "pdfWaterMarkAddTextColor"),
        ]
        for label, eid in checks:
            disabled = page.page.evaluate(
                f"() => {{ const el = document.getElementById('{eid}'); return el ? el.disabled : null; }}"
            )
            self._add("pass" if disabled else "warn",
                      f"sc4x — [중앙 워터마크 OFF] → '{label}' disabled (기대 True)"
                      if disabled else
                      f"sc4x — [중앙 워터마크 OFF] → '{label}' disabled 안 됨 결함 🔴 (사용자 발견)",
                      f"중앙 워터마크 체크박스 OFF 상태 / '{label}' disabled={disabled} | "
                      f"결함 의미: 메인 OFF 인데 종속 element 사용 가능 (사용자 시각으로도 disabled 안 됨)",
                      sc=4, highlight=page.page.locator(f"#{eid}").first)
        _safe_close_modal(page)

    # ==================================================================
    # sc4o — EDIT 정상 저장 (필드 변경 후 재오픈 일치)
    # ==================================================================
    def test_scenario4o_edit_normal_save_reload_match(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 4o: EDIT 정상 저장 + 재오픈 일치 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        _ensure_sc3l_policy(page)
        _enter_edit_modal(page, SC3L_NAME)

        # 필드 변경
        page.page.locator(page.SEL_CERT_URL).fill("https://sc4o.test/cert")
        page.page.locator(page.SEL_HTML_CONTACT).fill("010-1234-5678")
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=3000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        is_saved = "저장" in msg and "오류" not in msg
        self._add("pass" if is_saved else "fail",
                  "sc4o — EDIT 변경 저장",
                  f"변경: URL+연락처 / msg: {msg!r}", sc=4)

        # 재오픈 일치
        _enter_edit_modal(page, SC3L_NAME)
        reopened = page.page.evaluate(
            """() => ({
                cert_url: document.getElementById('readFileCertificateUrl').value,
                contact: document.getElementById('htmlContactNumber').value,
            })"""
        )
        ok_url = reopened.get("cert_url") == "https://sc4o.test/cert"
        ok_contact = reopened.get("contact") == "010-1234-5678"
        self._add("pass" if ok_url else "fail",
                  "sc4o — EDIT 재오픈 CERT_URL 일치",
                  f"기대: 'https://sc4o.test/cert' / 실제: {reopened.get('cert_url')!r}", sc=4)
        self._add("pass" if ok_contact else "fail",
                  "sc4o — EDIT 재오픈 연락처 일치",
                  f"기대: '010-1234-5678' / 실제: {reopened.get('contact')!r}", sc=4)
        _safe_close_modal(page)
