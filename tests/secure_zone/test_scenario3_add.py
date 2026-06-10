"""시큐어존 접근제어 정책 — 시나리오 3: 동작 검증 + CRUD(추가/삭제).

  sc3a — 필수(정책 이름) 빈값 제출 → 경고 ("템플릿 이름을 입력해 주세요.")
  sc3b — 마스터 토글(접근제어 사용) gating: OFF→하위 disabled / ON→enabled / OFF→disabled
  sc3c — [AUTO] 정책 정상 추가 + 목록 확인
  sc3d — 지정 드라이브 3필드 입력 검증 (한글/특수문자 클라필터 + 서버검증)
  sc3e — 특수문자 정책 이름 제출 → 서버 반응 관찰
  sc3f — 중복 이름 등록 차단 ("정책 이름이 이미 등록되어 있습니다.")
  sc3g — USB 옵션 순환 + 체크박스(CMD/Regedit/MMC/종료해제) 독립 토글
  sc3h — 이름 maxlength=50 경계값 (초과 입력 잘림)
  sc3i — 입력 필드별 대용량(3000자) 저장 — 이름+드라이브3 각각 격리 (overflow)

긴값/특수문자/드라이브는 yaml-guide 원칙(추측 금지)대로 서버 실제 반응을 관찰해 기록:
  서버 차단(경고)=pass(정상 방어) / 서버 저장=warn(제한 없음, known issue 가능)

※ 버튼 커버리지:
  - 추가(addItem)=sc3 / 수정(modifyItem)=sc4 / 삭제(removeItem)=cleanup 상시 사용 + sc5c 가 "삭제 후 [AUTO] 0건" 검증 / 버튼 존재=sc1a
  - 정책 할당/회수(addRemoveItemUserBtn)=에이전트(별도 영역) 기능 — 별도 작업
  - 검색/필터 영역=추후 확장 (필터 가능 검색 vs 불가 구분)
"""
from pages.secure_zone_access_control_policy_page import SecureZoneAccessControlPolicyPage
from tests.secure_zone._base import SecureZoneACBase


# 마스터 토글 + 하위 종속 컨트롤 (Chrome MCP 실측 2026-06-09)
_MASTER = "input#isAccessControl"
_DEPS = [
    ("지정 드라이브 숨기기",        "input#pickHideDrive"),
    ("지정 드라이브 접근금지",      "input#pickDenyDrive"),
    ("지정 드라이브 예외처리",      "input#pickExceptDrive"),
    ("명령프롬프트(CMD) 사용",      "input#isCmd"),
    ("Regedit 사용",               "input#isRegedit"),
    ("MMC, Gpedit 사용",           "input#isMmc"),
    ("휴대용 디바이스 — 거부",      "input#usbControlDeny"),
    ("휴대용 디바이스 — 읽기",      "input#usbControlRead"),
    ("휴대용 디바이스 — 읽기/쓰기", "input#usbControlReadWrite"),
    ("종료 시 접근제어 해제",       "input#isShutdownAccessControl"),
]


class TestSecureZoneAccessControlScenario3Add(SecureZoneACBase):
    """접근제어 정책 — 시나리오 3: 동작 + ADD."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneAccessControlPolicyPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _submit_and_message(self, page) -> str:
        """저장 클릭 → 확인/경고 모달 메시지 반환 + dismiss. 모달 없으면 ''."""
        page.click_attached(page.SEL_SAVE_BTN)
        page.page.wait_for_timeout(600)
        msg = ""
        if page.is_confirm_modal_visible():
            try:
                msg = page.get_modal_message()
            except Exception:
                msg = ""
            page.click_attached(page.SEL_CONFIRM_BTN)
            page.wait_for_modal_closed()
        return msg

    def _set_master(self, page, on: bool) -> None:
        loc = page.page.locator(_MASTER).first
        if loc.is_checked() != on:
            loc.evaluate("el => el.click()")
            page.page.wait_for_timeout(400)

    # ── sc3a: 필수 빈값 제출 ──────────────────────────────────────
    def test_scenario3a_required_empty(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 3a: 필수 빈값 제출 경고 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)   # sc1 미작성 — 여기서 clean slate 보장

        page.open_add_modal()
        msg = self._submit_and_message(page)
        expected = "템플릿 이름을 입력해 주세요."
        self._add("pass" if msg == expected else "fail",
                  "sc3a — 필수(정책 이름) 빈값 제출 경고",
                  f"실제: {msg!r} / 기대: {expected!r}", sc=3,
                  highlight=page.page.locator(page.SEL_NAME))
        page._close_modal_if_open()

    # ── sc3b: 마스터 토글 gating ─────────────────────────────────
    def test_scenario3b_master_toggle_gating(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 3b: 마스터 토글 gating (OFF→막힘/ON→가능) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()

        # ① OFF 상태 → 하위 전부 disabled
        self._set_master(page, on=False)
        for label, sel in _DEPS:
            loc = page.page.locator(sel).first
            disabled = (loc.count() > 0) and (not loc.is_enabled())
            self._add("pass" if disabled else "fail",
                      f"sc3b — [마스터 OFF] '{label}' 비활성",
                      f"결과: enabled={loc.is_enabled() if loc.count() else '요소없음'}",
                      sc=3, highlight=loc)

        # ② ON 상태 → 하위 전부 enabled
        self._set_master(page, on=True)
        for label, sel in _DEPS:
            loc = page.page.locator(sel).first
            enabled = (loc.count() > 0) and loc.is_enabled()
            self._add("pass" if enabled else "fail",
                      f"sc3b — [마스터 ON] '{label}' 활성",
                      f"결과: enabled={loc.is_enabled() if loc.count() else '요소없음'}",
                      sc=3, highlight=loc)

        # ③ 다시 OFF → 하위 전부 disabled (복구 검증)
        self._set_master(page, on=False)
        for label, sel in _DEPS:
            loc = page.page.locator(sel).first
            disabled = (loc.count() > 0) and (not loc.is_enabled())
            self._add("pass" if disabled else "fail",
                      f"sc3b — [마스터 ON→OFF] '{label}' 재비활성",
                      f"결과: enabled={loc.is_enabled() if loc.count() else '요소없음'}",
                      sc=3, highlight=loc)

        page._close_modal_if_open()

    # ── sc3c: [AUTO] 정책 정상 추가 ──────────────────────────────
    def test_scenario3c_add_auto_policy(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 3c: [AUTO] 정책 추가 + 목록 확인 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()

        name = f"{page.AUTO_NAME_PREFIX}_p3"
        page.open_add_modal()
        page.save_policy(name)

        page.navigate_to()
        exists = name in page.get_policy_names()
        self._add("pass" if exists else "fail",
                  "sc3c — [AUTO] 정책 추가 후 목록 확인",
                  f"'{name}' 목록 존재={exists}", sc=3)

    # ── sc3d: 지정 드라이브 입력 검증 (드라이브 문자 외 임의 문자열·긴값) ──
    # Chrome MCP 실측 2026-06-09: pickHideDrive 는 클라 필터 없음 + 서버 검증 없음
    #   → "abc123;:D!@#XYZ" 그대로 저장됨 확인. 드라이브 문자/형식/길이 검증 부재.
    def test_scenario3d_drive_input_validation(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 3d: 지정 드라이브 입력 검증 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()

        name = f"{page.AUTO_NAME_PREFIX}_drv"
        page.fill(page.SEL_NAME, name)
        self._set_master(page, on=True)
        # 정상 포맷은 'C;D;E'(세미콜론)·'A-Z'(범위)·'S,W'(쉼표). 여기에 한글·특수문자·긴 길이 혼합 →
        # 드라이브 문자가 아닌 입력을 막아야 정상(막으면 pass / 안 막으면 잠재 결함 warn).
        bad_val = "C;D;가나다;!@#ABCXYZ" + ("가" * 200)   # 한글 + 비드라이브 + 긴 길이

        # ① 클라 입력 필터 여부 — 드라이브 3필드 전부 (규칙5: 모든 필드 커버)
        drive_fields = [("숨기기", "input#pickHideDrive"),
                        ("접근금지", "input#pickDenyDrive"),
                        ("예외처리", "input#pickExceptDrive")]
        for dlabel, dsel in drive_fields:
            d = page.page.locator(dsel).first
            d.fill(bad_val)
            hangul = any("가" <= ch <= "힣" for ch in d.input_value())
            self._add("warn" if hangul else "pass",
                      f"sc3d — 지정 드라이브 '{dlabel}' 클라 필터 (한글/특수문자)",
                      f"입력 {len(bad_val)}자 → 수용 {len(d.input_value())}자 / 한글={hangul} "
                      f"({'필터 없음' if hangul else '필터됨'})", sc=3, highlight=d)

        # ② 서버 검증 여부 (3필드 모두 채운 채 저장)
        drv = page.page.locator("input#pickHideDrive").first
        accepted_len = len(drv.input_value())
        msg = self._submit_and_message(page)
        saved = ("저장" in msg) or (not msg)
        if saved:
            self._add("warn",
                      "sc3d — 지정 드라이브 서버 검증 없음 (한글·임의 문자열 저장)",
                      f"입력 {accepted_len}자(한글 포함) → 결과: {msg or '경고 없음(저장됨)'} "
                      "[잠재 결함: 드라이브 문자/형식 검증 부재 — 방식차이 가능, 사람 판단]", sc=3, highlight=drv)
        else:
            self._add("pass", "sc3d — 지정 드라이브 서버 검증 정상 (드라이브 문자 외 차단)",
                      f"입력 {accepted_len}자 → 경고: {msg!r}", sc=3, highlight=drv)
        # 생성된 [AUTO] 는 유지 — cleanup 은 sc5c 에서만 (lifecycle 규칙)
        page._close_modal_if_open()

    # ── sc3e: 특수문자 — 정책 이름 ───────────────────────────────
    def test_scenario3e_special_char_name(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 3e: 특수문자 정책 이름 제출 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()

        # HTML < > 금지 (inner_text 파싱/cleanup 이슈) — yaml-guide 준수
        special_name = f"{page.AUTO_NAME_PREFIX}_sc';!@#$%"
        page.fill(page.SEL_NAME, special_name)
        msg = self._submit_and_message(page)
        saved = ("저장" in msg) or (not msg)
        if saved:
            self._add("warn", "sc3e — 특수문자 이름 차단 없음 (known issue 가능)",
                      f"입력: {special_name!r} → 결과: {msg or '경고 없음(저장됨 추정)'}", sc=3,
                      highlight=page.page.locator(page.SEL_NAME))
        else:
            self._add("pass", "sc3e — 특수문자 이름 서버 차단",
                      f"입력: {special_name!r} → 경고: {msg!r}", sc=3,
                      highlight=page.page.locator(page.SEL_NAME))
        # 생성된 [AUTO] 는 유지 — cleanup 은 sc5c 에서만 (lifecycle 규칙)
        page._close_modal_if_open()

    # ── sc3f: 비정상 — 중복 이름 등록 차단 (표준 비정상 케이스) ────
    # Chrome MCP 실측 2026-06-10: 중복 이름 → "정책 이름이 이미 등록되어 있습니다."
    def test_scenario3f_duplicate_name(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 3f: 중복 이름 등록 차단 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()

        name = f"{page.AUTO_NAME_PREFIX}_dup"
        # 기준 정책 확보 (없으면 생성)
        if name not in page.get_policy_names():
            page.open_add_modal()
            page.save_policy(name)
            page.navigate_to()

        # 같은 이름 재등록 → 중복 경고 (정확 메시지 비교 — 표준 규칙4)
        page.open_add_modal()
        page.fill(page.SEL_NAME, name)
        msg = self._submit_and_message(page)
        expected = "정책 이름이 이미 등록되어 있습니다."
        self._add("pass" if msg == expected else "fail",
                  "sc3f — 중복 이름 등록 차단",
                  f"입력: 기존 '{name}' 재등록 / 실제: {msg!r} / 기대: {expected!r}", sc=3,
                  highlight=page.page.locator(page.SEL_NAME))
        page._close_modal_if_open()

    # ── sc3g: USB 옵션 순환 + 체크박스 독립 토글 (모든 필드 커버 — 규칙5) ──
    def test_scenario3g_usb_cycle_and_checkbox_independent(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 3g: USB 옵션 순환 + 체크박스 독립 토글 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        self._set_master(page, on=True)

        # USB radio 3옵션 순환 클릭 → 각 선택 확인
        for label, sel in [("거부", "input#usbControlDeny"),
                           ("읽기", "input#usbControlRead"),
                           ("읽기/쓰기", "input#usbControlReadWrite")]:
            r = page.page.locator(sel).first
            r.evaluate("el => el.click()")
            page.page.wait_for_timeout(150)
            self._add("pass" if r.is_checked() else "fail",
                      f"sc3g — USB 권한 '{label}' 선택",
                      f"클릭 후 checked={r.is_checked()}", sc=3, highlight=r)

        # 체크박스 독립 토글 (ON→OFF→복구) — 각자 독립 동작
        for label, cid in [("CMD", "isCmd"), ("Regedit", "isRegedit"),
                           ("MMC", "isMmc"), ("종료해제", "isShutdownAccessControl")]:
            cb = page.page.locator(f"input#{cid}").first
            before = cb.is_checked()
            cb.evaluate("el => el.click()"); page.page.wait_for_timeout(150)
            after1 = cb.is_checked()
            cb.evaluate("el => el.click()"); page.page.wait_for_timeout(150)
            after2 = cb.is_checked()
            ok = (after1 != before) and (after2 == before)
            self._add("pass" if ok else "fail",
                      f"sc3g — '{label}' 독립 토글 (ON/OFF 복구)",
                      f"{before}→{after1}→{after2}", sc=3, highlight=cb)
        page._close_modal_if_open()

    # ── sc3h: 정책 이름 maxlength=50 경계값 (51자 → 잘림) ──────────
    def test_scenario3h_name_maxlength_boundary(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 3h: 이름 maxlength=50 경계값 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()

        long_name = "[AUTO]_sac_" + ("x" * 50)   # 61자 (50 초과)
        nm = page.page.locator(page.SEL_NAME).first
        nm.fill(long_name)
        accepted = len(nm.input_value())
        self._add("pass" if accepted == 50 else "warn",
                  "sc3h — 이름 maxlength=50 경계 (초과 입력 잘림)",
                  f"입력 {len(long_name)}자 → 수용 {accepted}자 (기대 50)", sc=3,
                  highlight=nm)
        page._close_modal_if_open()

    # ── sc3i: 대용량(3000자) 저장 시도 — 입력 가능 필드 '각각' 따로 (overflow 버그 확인) ──
    # 한 번에 여러 필드 넣으면 어디서 터지는지 모름 → 필드별 1건씩 격리 테스트.
    # 이름(maxlength=50 캡)부터 드라이브 3필드(maxlength 없음)까지 전부.
    def test_scenario3i_overflow_per_field(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 3i: 입력 필드별 대용량(3000자) 저장 (각각) ━━━")
        page = self._new_page(logged_in_page, settings)
        big = "X" * 3000

        # (라벨, selector, 마스터 ON 필요, 이름필드인가)
        targets = [
            ("정책 이름",          page.SEL_NAME,          False, True),
            ("드라이브 숨기기",    "input#pickHideDrive",  True,  False),
            ("드라이브 접근금지",  "input#pickDenyDrive",  True,  False),
            ("드라이브 예외처리",  "input#pickExceptDrive", True, False),
        ]
        for i, (label, sel, need_master, is_name) in enumerate(targets):
            page.navigate_to()
            page.open_add_modal()
            if is_name:
                # 이름 자체에 대용량 → [AUTO] 접두사 유지(cleanup 대상!) + maxlength=50 캡 확인.
                # 순수 'X'*3000 은 잘린 'XXX..' 가 [AUTO] 미시작 → cleanup 누락(데이터 안전 위반).
                page.page.locator(sel).first.fill(page.AUTO_NAME_PREFIX + "_ovn_" + big)
            else:
                page.fill(page.SEL_NAME, f"{page.AUTO_NAME_PREFIX}_ov{i}")
                if need_master:
                    self._set_master(page, on=True)
                page.page.locator(sel).first.fill(big)
            accepted = len(page.page.locator(sel).first.input_value())

            msg = self._submit_and_message(page)
            if "저장" in msg:
                status, detail = ("pass" if is_name and accepted <= 50 else "warn"), \
                    (f"수용 {accepted}자 → 저장됨" +
                     (" (maxlength 캡 정상)" if is_name and accepted <= 50
                      else " — 길이 제한 없음(서버 한도 의존)"))
            elif msg:
                status, detail = "warn", f"수용 {accepted}자 → 서버 오류로만 차단(클라 가드 부재): {msg!r}"
            else:
                status, detail = "warn", f"수용 {accepted}자 → 경고 없이 처리(저장 추정)"
            self._add(status,
                      f"sc3i — '{label}' 대용량(3000자) 저장 (overflow)",
                      detail, sc=3, highlight=page.page.locator(sel).first)
            page._close_modal_if_open()

    # ── sc3k: master ON + 하위 전부 빈값 저장 — 필수 검증 여부 ────────
    # Chrome MCP 실측 2026-06-10: master ON + 빈값 → "저장 하였습니다" (하위 필수 아님).
    def test_scenario3k_master_on_empty_save(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 3k: master ON + 하위 빈값 저장 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()

        name = f"{page.AUTO_NAME_PREFIX}_mon"
        page.fill(page.SEL_NAME, name)
        self._set_master(page, on=True)   # 드라이브/체크박스 전부 빈/off 유지
        msg = self._submit_and_message(page)
        saved = ("저장" in msg) or (not msg)
        # 하위는 필수 아님 → 빈값으로 저장되는 게 정상 동작 (결함 아님)
        self._add("pass" if saved else "warn",
                  "sc3k — master ON + 하위 빈값 저장 (하위 필수 아님 → 정상)",
                  f"입력: master ON, 하위 전부 빈/off → 결과: {msg or '경고없음(저장)'} "
                  "(하위 비필수 — 빈 정책 허용은 정상)", sc=3,
                  highlight=page.page.locator(_MASTER).first)
        page._close_modal_if_open()

    # ── sc3m: master OFF 인데 하위 항목 수정되면 결함 (gating 우회 능동 검증) ──
    # sc3b 는 disabled 속성만 확인 — 여기선 실제 클릭/입력 시도 → 변경되면 FAIL.
    def test_scenario3m_off_gating_no_bypass(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 3m: master OFF 하위 수정 차단 (능동) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        self._set_master(page, on=False)   # master OFF

        # ① 체크박스 클릭 시도 → 상태 안 바뀌어야 (바뀌면 gating 우회 결함)
        for label, cid in [("CMD", "isCmd"), ("Regedit", "isRegedit"),
                           ("MMC", "isMmc"), ("종료해제", "isShutdownAccessControl")]:
            cb = page.page.locator(f"input#{cid}").first
            before = cb.is_checked()
            try:
                cb.evaluate("el => el.click()")
                page.page.wait_for_timeout(120)
            except Exception:
                pass
            after = cb.is_checked()
            self._add("pass" if after == before else "fail",
                      f"sc3m — [master OFF] '{label}' 변경 차단",
                      f"{before}→{after} (변경되면 gating 우회 결함)", sc=3, highlight=cb)

        # ② 드라이브 입력 시도 → 값 안 들어가야 (disabled)
        for label, dsel in [("숨기기", "input#pickHideDrive"),
                            ("접근금지", "input#pickDenyDrive"),
                            ("예외처리", "input#pickExceptDrive")]:
            drv = page.page.locator(dsel).first
            try:
                drv.fill("C", timeout=1500)
            except Exception:
                pass   # disabled → fill 실패가 정상
            val = drv.input_value()
            self._add("pass" if val == "" else "fail",
                      f"sc3m — [master OFF] 드라이브 '{label}' 입력 차단",
                      f"입력값={val!r} (값 들어가면 gating 우회 결함)", sc=3, highlight=drv)
        page._close_modal_if_open()

    # ── sc3l: 정상 혼합 조합 저장 → 속성 모달 round-trip (개별 필드 persist) ──
    # positive 케이스 — 각 필드가 설정한 값 그대로 저장/표시되는지 (on/off 혼합).
    def test_scenario3l_normal_combo_roundtrip(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 3l: 정상 혼합 조합 저장 + round-trip ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()

        name = f"{page.AUTO_NAME_PREFIX}_rt"
        page.fill(page.SEL_NAME, name)
        self._set_master(page, on=True)
        page.page.locator("input#pickHideDrive").first.fill("C;D;E")
        # 혼합: CMD ON / Regedit OFF / MMC ON / 종료해제 OFF
        for cid, want in [("isCmd", True), ("isRegedit", False),
                          ("isMmc", True), ("isShutdownAccessControl", False)]:
            cb = page.page.locator(f"input#{cid}").first
            if cb.is_checked() != want:
                cb.evaluate("el => el.click()"); page.page.wait_for_timeout(120)
        page.page.locator("input#usbControlRead").first.evaluate("el => el.click()")  # USB 읽기

        msg = self._submit_and_message(page)
        self._add("pass" if "저장" in msg else "fail",
                  "sc3l — 정상 혼합 조합 저장", f"msg={msg!r}", sc=3)
        if "저장" not in msg:
            return

        # 속성 모달 round-trip — 각 필드 설정값 그대로인지
        page.open_detail_modal(name)
        detail = page.read_detail_modal()
        text = page.detail_modal_text()
        page.close_detail_modal()
        print(f"[sc3l] 속성 모달: {detail}")
        expected = {"isAccessControl": True, "isCmd": True, "isRegedit": False,
                    "isMmc": True, "isShutdownAccessControl": False, "usb": "읽기"}
        for k, v in expected.items():
            self._add("pass" if detail.get(k) == v else "fail",
                      f"sc3l — round-trip '{k}' = {v}",
                      f"실제={detail.get(k)} / 기대={v}", sc=3)
        self._add("pass" if "C;D;E" in text else "fail",
                  "sc3l — round-trip 드라이브 'C;D;E'",
                  f"속성 모달 텍스트 'C;D;E' 포함={'C;D;E' in text}", sc=3)
