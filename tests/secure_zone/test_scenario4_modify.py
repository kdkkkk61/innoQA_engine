"""시큐어존 접근제어 정책 — 시나리오 4: 수정(EDIT) — sc3 생성 [AUTO] 재사용(연계).

sc4a — EDIT 모달 진입 + 저장값 로드 확인 ([AUTO]_sac_p3 이름 로드)
sc4b — 이름 수정 + 저장 + 목록 반영 확인

lifecycle: sc3c 가 만든 [AUTO]_sac_p3 를 sc4 가 사용 → sc2/3/4 데이터 유지 원칙.
"""
from pages.secure_zone_access_control_policy_page import SecureZoneAccessControlPolicyPage
from tests.secure_zone._base import SecureZoneACBase

# 마스터 토글 + 하위 종속 (sc3 와 동일 — 수정 모달에서도 동일 id)
_MASTER = "input#isAccessControl"
_DEPS = [
    ("지정 드라이브 숨기기", "input#pickHideDrive"),
    ("지정 드라이브 접근금지", "input#pickDenyDrive"),
    ("지정 드라이브 예외처리", "input#pickExceptDrive"),
    ("명령프롬프트(CMD) 사용", "input#isCmd"),
    ("Regedit 사용", "input#isRegedit"),
    ("MMC, Gpedit 사용", "input#isMmc"),
    ("휴대용 디바이스 — 거부", "input#usbControlDeny"),
    ("휴대용 디바이스 — 읽기", "input#usbControlRead"),
    ("휴대용 디바이스 — 읽기/쓰기", "input#usbControlReadWrite"),
    ("종료 시 접근제어 해제", "input#isShutdownAccessControl"),
]


class TestSecureZoneAccessControlScenario4Modify(SecureZoneACBase):
    """접근제어 정책 — 시나리오 4: 수정."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneAccessControlPolicyPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario4a_edit_load(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 4a: EDIT 저장값 로드 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()

        target = f"{page.AUTO_NAME_PREFIX}_p3"
        if target not in page.get_policy_names():
            self._add("skip", "sc4a — EDIT 대상 없음",
                      f"'{target}' 미존재 (sc3c 저장 실패 추정)", sc=4)
            return

        page.open_modify_modal(target)
        loaded = page.page.locator(page.SEL_NAME).first.input_value()
        self._add("pass" if loaded == target else "fail",
                  "sc4a — EDIT 모달 저장값(정책 이름) 로드",
                  f"로드={loaded!r} / 기대={target!r}", sc=4,
                  highlight=page.page.locator(page.SEL_NAME))
        page.close_edit_modal()

    def test_scenario4b_modify_name(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 4b: 이름 수정 저장 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()

        target = f"{page.AUTO_NAME_PREFIX}_p3"
        names = page.get_policy_names()
        if target not in names:
            # 이미 sc4b 가 한 번 돌아 이름이 바뀐 경우 등 — skip
            self._add("skip", "sc4b — 수정 대상 없음",
                      f"'{target}' 미존재 (이미 수정됨? 현재: {[n for n in names if n.startswith('[AUTO]')]})",
                      sc=4)
            return

        new_name = f"{page.AUTO_NAME_PREFIX}_p3m"
        page.open_modify_modal(target)
        page.save_policy(new_name)   # 이름 덮어쓰기 + 저장 + 확인 모달 처리

        page.navigate_to()
        after = page.get_policy_names()
        ok = (new_name in after) and (target not in after)
        self._add("pass" if ok else "fail",
                  "sc4b — 이름 수정 저장 + 목록 반영",
                  f"'{target}' → '{new_name}' / 반영={ok} "
                  f"(현재 [AUTO]: {[n for n in after if n.startswith('[AUTO]')]})", sc=4)

    def _modal_field_ids(self, page) -> set:
        sels = (f"{page.SEL_MODAL} input, {page.SEL_MODAL} select, "
                f"{page.SEL_MODAL} textarea")
        ids = set()
        for el in page.page.locator(sels).all():
            i = el.get_attribute("id")
            if i:
                ids.add(i)
        return ids

    def test_scenario4c_add_vs_edit_modal(self, logged_in_page, settings):
        """생성 모달 vs 수정 모달 필드 구성 비교 — '다르게 동작' 현상 검출."""
        print("\n━━ [접근제어 정책] 시나리오 4c: 생성 vs 수정 모달 필드 비교 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()

        page.open_add_modal()
        add_ids = self._modal_field_ids(page)
        page._close_modal_if_open()

        autos = [n for n in page.get_policy_names() if n.startswith("[AUTO]")]
        if not autos:
            self._add("skip", "sc4c — 비교 대상 [AUTO] 정책 없음",
                      "EDIT 모달 열 정책 없음 (sc3 저장 실패?)", sc=4)
            return

        page.open_modify_modal(autos[0])
        edit_ids = self._modal_field_ids(page)
        page.close_edit_modal()

        only_add  = sorted(add_ids - edit_ids)
        only_edit = sorted(edit_ids - add_ids)
        same = not only_add and not only_edit
        self._add("pass" if same else "warn",
                  "sc4c — 생성/수정 모달 필드 구성 일치",
                  f"ADD {len(add_ids)}개 / EDIT {len(edit_ids)}개 / "
                  f"ADD전용={only_add or '없음'} / EDIT전용={only_edit or '없음'} "
                  f"{'(일치)' if same else '(불일치 — 모달 다르게 동작)'}", sc=4)

    # ── sc3 검증을 수정 모달에서도 반복 (수정·생성 모달 동작 차이 검출) ──────
    def _edit_target(self, page) -> str | None:
        """수정 검증용 [AUTO] 정책 1건 확보 (없으면 생성)."""
        autos = [n for n in page.get_policy_names() if n.startswith("[AUTO]")]
        if autos:
            return autos[0]
        name = f"{page.AUTO_NAME_PREFIX}_em"
        page.open_add_modal()
        page.save_policy(name)
        page.navigate_to()
        return name if name in page.get_policy_names() else None

    def test_scenario4d_edit_master_toggle_gating(self, logged_in_page, settings):
        """sc3b 반복 — 수정 모달에서 마스터 토글 gating (OFF→막힘/ON→가능)."""
        print("\n━━ [접근제어 정책] 시나리오 4d: 수정모달 마스터 토글 gating ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        target = self._edit_target(page)
        if not target:
            self._add("skip", "sc4d — 대상 없음", "edit 대상 [AUTO] 없음", sc=4)
            return

        page.open_modify_modal(target)
        master = page.page.locator(_MASTER).first
        if master.is_checked():
            master.evaluate("el => el.click()"); page.page.wait_for_timeout(400)
        for label, sel in _DEPS:
            loc = page.page.locator(sel).first
            disabled = loc.count() > 0 and not loc.is_enabled()
            self._add("pass" if disabled else "fail",
                      f"sc4d — [수정 마스터 OFF] '{label}' 비활성",
                      f"enabled={loc.is_enabled() if loc.count() else '없음'}", sc=4, highlight=loc)
        master.evaluate("el => el.click()"); page.page.wait_for_timeout(400)
        for label, sel in _DEPS:
            loc = page.page.locator(sel).first
            enabled = loc.count() > 0 and loc.is_enabled()
            self._add("pass" if enabled else "fail",
                      f"sc4d — [수정 마스터 ON] '{label}' 활성",
                      f"enabled={loc.is_enabled() if loc.count() else '없음'}", sc=4, highlight=loc)
        page.close_edit_modal()

    def test_scenario4e_edit_required_empty(self, logged_in_page, settings):
        """sc3a 반복 — 수정 모달에서 이름 비우고 저장 → 경고."""
        print("\n━━ [접근제어 정책] 시나리오 4e: 수정모달 필수(이름) 빈값 제출 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        target = self._edit_target(page)
        if not target:
            self._add("skip", "sc4e — 대상 없음", "edit 대상 [AUTO] 없음", sc=4)
            return

        page.open_modify_modal(target)
        nm = page.page.locator(page.SEL_NAME).first
        nm.fill("")
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
        expected = "템플릿 이름을 입력해 주세요."
        self._add("pass" if msg == expected else "fail",
                  "sc4e — 수정모달 이름 빈값 제출 경고 (생성과 동일해야)",
                  f"실제: {msg!r} / 기대: {expected!r}", sc=4,
                  highlight=page.page.locator(page.SEL_NAME))
        page._close_modal_if_open()

    def test_scenario4f_edit_drive_validation(self, logged_in_page, settings):
        """sc3d 반복 — 수정 모달에서 드라이브 필드 한글/긴값 입력 검증."""
        print("\n━━ [접근제어 정책] 시나리오 4f: 수정모달 드라이브 입력 검증 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        target = self._edit_target(page)
        if not target:
            self._add("skip", "sc4f — 대상 없음", "edit 대상 [AUTO] 없음", sc=4)
            return

        page.open_modify_modal(target)
        master = page.page.locator(_MASTER).first
        if not master.is_checked():
            master.evaluate("el => el.click()"); page.page.wait_for_timeout(400)
        bad_val = "C;D;가나다;!@#" + ("가" * 200)
        # 드라이브 3필드 전부 (sc3d 와 동일하게 모든 필드 커버)
        for dlabel, dsel in [("숨기기", "input#pickHideDrive"),
                             ("접근금지", "input#pickDenyDrive"),
                             ("예외처리", "input#pickExceptDrive")]:
            d = page.page.locator(dsel).first
            d.fill(bad_val)
            hangul = any("가" <= ch <= "힣" for ch in d.input_value())
            self._add("warn" if hangul else "pass",
                      f"sc4f — 수정모달 드라이브 '{dlabel}' 클라 필터 (한글)",
                      f"수용 {len(d.input_value())}자 / 한글={hangul} "
                      f"({'필터 없음' if hangul else '필터됨'})", sc=4, highlight=d)
        # 서버 검증 (3필드 채운 채 저장)
        msg = page.submit_and_message()
        saved = ("저장" in msg) or (not msg)
        self._add("warn" if saved else "pass",
                  "sc4f — 수정모달 드라이브 서버 검증",
                  f"결과: {msg or '경고 없음(저장됨)'} "
                  f"({'검증 없음(생성과 동일하면 일관)' if saved else '차단'})", sc=4,
                  highlight=page.page.locator('input#pickHideDrive').first)
        page._close_modal_if_open()

    # ── sc4g (4-3): 위반 입력 통과 후 재오픈 실제값 확인 (표준 책임분리) ──
    # 표준: 1차(경고 떴나) + 2차(재오픈 실제값: 빈값=fail/원본=warn/다른값=fail).
    def test_scenario4g_required_reopen_actual(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 4-3: 이름 빈값 수정 후 재오픈 실제값 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        target = self._edit_target(page)
        if not target:
            self._add("skip", "sc4g — 대상 없음", "edit 대상 [AUTO] 없음", sc=4)
            return

        # 1차 — 이름 비우고 수정 시도 → 경고 떴는가
        page.open_modify_modal(target)
        page.page.locator(page.SEL_NAME).first.fill("")
        page.click_attached(page.SEL_SAVE_BTN)
        page.page.wait_for_timeout(600)
        msg1 = ""
        if page.is_confirm_modal_visible():
            try:
                msg1 = page.get_modal_message()
            except Exception:
                msg1 = ""
            page.click_attached(page.SEL_CONFIRM_BTN)
            page.wait_for_modal_closed()
        warned = msg1 == "템플릿 이름을 입력해 주세요."
        page._close_modal_if_open()

        # 2차 — 재오픈해서 실제 저장값 확인 (데이터 손상 여부)
        if target not in page.get_policy_names():
            self._add("fail", "sc4-3 — 재오픈 실제값: 정책 사라짐 (데이터 손상)",
                      f"1차 경고={warned}({msg1!r}) / '{target}' 목록에서 사라짐", sc=4)
            return
        page.open_modify_modal(target)
        actual = page.page.locator(page.SEL_NAME).first.input_value()
        page.close_edit_modal()
        if actual == target:
            status, detail = "pass", "원본 유지 (검증 작동 → 데이터 무손상)"
        elif actual == "":
            status, detail = "fail", "빈값 저장됨 (데이터 손상)"
        else:
            status, detail = "fail", f"예상 못한 값 저장 (원본={target!r} / 결과={actual!r})"
        self._add(status,
                  "sc4-3 — 이름 빈값 위반 후 재오픈 실제값",
                  f"[1차] 경고={warned}({msg1!r}) / [2차] 실제값={actual!r} → {detail}",
                  sc=4, highlight=page.page.locator(page.SEL_NAME))

    def test_scenario4h_edit_duplicate_name(self, logged_in_page, settings):
        """sc3f 반복(수정판) — 수정 시 기존 다른 정책 이름으로 변경 → 중복 차단."""
        print("\n━━ [접근제어 정책] 시나리오 4h: 수정 시 중복 이름 차단 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()

        # [AUTO] 정책 2건 확보 (없으면 생성)
        autos = [n for n in page.get_policy_names() if n.startswith("[AUTO]")]
        need = [f"{page.AUTO_NAME_PREFIX}_d1", f"{page.AUTO_NAME_PREFIX}_d2"]
        for nm in need:
            if nm not in autos and nm not in page.get_policy_names():
                page.open_add_modal()
                page.save_policy(nm)
                page.navigate_to()
        names = page.get_policy_names()
        target = next((n for n in [need[0]] if n in names), None)
        other = next((n for n in [need[1]] if n in names), None)
        if not target or not other:
            self._add("skip", "sc4h — 비교용 정책 2건 확보 실패",
                      f"target={target} other={other}", sc=4)
            return

        # target 을 other 이름으로 변경 시도 → 중복 경고 (정확 메시지)
        page.open_modify_modal(target)
        page.page.locator(page.SEL_NAME).first.fill(other)
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
        # EDIT 중복 메시지는 ADD("정책 이름이 이미 등록되어 있습니다.")와 다름 — 제품 불일치 (Chrome MCP 실측 2026-06-10)
        expected = "이미 등록된 이름 입니다."
        self._add("pass" if msg == expected else "fail",
                  "sc4h — 수정 시 중복 이름 차단",
                  f"'{target}' → 기존 '{other}' 변경 시도 / 실제: {msg!r} / 기대: {expected!r} "
                  "(ADD 메시지와 다름 — 제품 메시지 불일치)",
                  sc=4, highlight=page.page.locator(page.SEL_NAME))
        page._close_modal_if_open()

    def test_scenario4i_edit_special_char_name(self, logged_in_page, settings):
        """sc3e 반복 — 수정 시 이름을 특수문자로 변경 → 서버 반응 관찰."""
        print("\n━━ [접근제어 정책] 시나리오 4i: 수정모달 특수문자 이름 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        target = self._edit_target(page)
        if not target:
            self._add("skip", "sc4i — 대상 없음", "edit 대상 [AUTO] 없음", sc=4)
            return
        special = f"{page.AUTO_NAME_PREFIX}_scm';!@#$%"   # [AUTO] 유지(cleanup 대상)
        page.open_modify_modal(target)
        page.page.locator(page.SEL_NAME).first.fill(special)
        msg = page.submit_and_message()
        saved = ("저장" in msg) or (not msg)
        self._add("warn" if saved else "pass",
                  "sc4i — 수정 특수문자 이름" + (" 차단 없음(known issue)" if saved else " 서버 차단"),
                  f"입력: {special!r} → 결과: {msg or '경고 없음(저장됨)'}", sc=4,
                  highlight=page.page.locator(page.SEL_NAME))
        page._close_modal_if_open()

    def test_scenario4j_edit_usb_and_checkbox(self, logged_in_page, settings):
        """sc3g 반복 — 수정 모달에서 USB 옵션 순환 + 체크박스 독립 토글."""
        print("\n━━ [접근제어 정책] 시나리오 4j: 수정모달 USB 순환 + 체크박스 독립 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        target = self._edit_target(page)
        if not target:
            self._add("skip", "sc4j — 대상 없음", "edit 대상 [AUTO] 없음", sc=4)
            return
        page.open_modify_modal(target)
        m = page.page.locator(_MASTER).first
        if not m.is_checked():
            m.evaluate("el => el.click()"); page.page.wait_for_timeout(400)
        for label, sel in [("거부", "input#usbControlDeny"),
                           ("읽기", "input#usbControlRead"),
                           ("읽기/쓰기", "input#usbControlReadWrite")]:
            r = page.page.locator(sel).first
            r.evaluate("el => el.click()"); page.page.wait_for_timeout(150)
            self._add("pass" if r.is_checked() else "fail",
                      f"sc4j — 수정 USB 권한 '{label}' 선택",
                      f"checked={r.is_checked()}", sc=4, highlight=r)
        for label, cid in [("CMD", "isCmd"), ("Regedit", "isRegedit"),
                           ("MMC", "isMmc"), ("종료해제", "isShutdownAccessControl")]:
            cb = page.page.locator(f"input#{cid}").first
            b = cb.is_checked()
            cb.evaluate("el => el.click()"); page.page.wait_for_timeout(150)
            a1 = cb.is_checked()
            cb.evaluate("el => el.click()"); page.page.wait_for_timeout(150)
            a2 = cb.is_checked()
            ok = (a1 != b) and (a2 == b)
            self._add("pass" if ok else "fail",
                      f"sc4j — 수정 '{label}' 독립 토글", f"{b}→{a1}→{a2}", sc=4, highlight=cb)
        page.close_edit_modal()   # 저장 안 함 (동작 검증)

    def test_scenario4k_edit_name_maxlength(self, logged_in_page, settings):
        """sc3h 반복 — 수정 모달 이름 maxlength=50 경계값."""
        print("\n━━ [접근제어 정책] 시나리오 4k: 수정모달 이름 maxlength 경계 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        target = self._edit_target(page)
        if not target:
            self._add("skip", "sc4k — 대상 없음", "edit 대상 [AUTO] 없음", sc=4)
            return
        page.open_modify_modal(target)
        nm = page.page.locator(page.SEL_NAME).first
        nm.fill(page.AUTO_NAME_PREFIX + "_" + ("x" * 60))
        accepted = len(nm.input_value())
        self._add("pass" if accepted == 50 else "warn",
                  "sc4k — 수정모달 이름 maxlength=50 경계 (초과 잘림)",
                  f"수용 {accepted}자 (기대 50)", sc=4, highlight=nm)
        page.close_edit_modal()   # 저장 안 함 (이름 망가뜨리지 않음)

    def test_scenario4l_edit_drive_overflow(self, logged_in_page, settings):
        """sc3i 반복 — 수정 모달 드라이브 필드별 대용량(3000자) 저장."""
        print("\n━━ [접근제어 정책] 시나리오 4l: 수정모달 드라이브 대용량(각각) ━━━")
        page = self._new_page(logged_in_page, settings)
        big = "X" * 3000
        for dlabel, dsel in [("숨기기", "input#pickHideDrive"),
                             ("접근금지", "input#pickDenyDrive"),
                             ("예외처리", "input#pickExceptDrive")]:
            page.navigate_to()
            target = self._edit_target(page)
            if not target:
                self._add("skip", f"sc4l — '{dlabel}' 대상 없음", "edit 대상 없음", sc=4)
                return
            page.open_modify_modal(target)
            m = page.page.locator(_MASTER).first
            if not m.is_checked():
                m.evaluate("el => el.click()"); page.page.wait_for_timeout(400)
            d = page.page.locator(dsel).first
            d.fill(big)
            accepted = len(d.input_value())
            msg = page.submit_and_message()
            if "저장" in msg:
                status, detail = "warn", f"수용 {accepted}자 → 저장됨(제한 없음)"
            elif msg:
                status, detail = "warn", f"수용 {accepted}자 → 서버 오류로만 차단: {msg!r}"
            else:
                status, detail = "warn", f"수용 {accepted}자 → 경고 없이 처리"
            self._add(status, f"sc4l — 수정 드라이브 '{dlabel}' 대용량(3000자) overflow",
                      detail, sc=4, highlight=page.page.locator(dsel).first)
            page._close_modal_if_open()

    def test_scenario4m_modify_combo_roundtrip(self, logged_in_page, settings):
        """sc3l 반복 — 수정으로 정상 혼합 조합 저장 → 속성 모달 round-trip."""
        print("\n━━ [접근제어 정책] 시나리오 4m: 수정 혼합 조합 저장 + round-trip ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        target = self._edit_target(page)
        if not target:
            self._add("skip", "sc4m — 대상 없음", "edit 대상 [AUTO] 없음", sc=4)
            return

        page.open_modify_modal(target)
        m = page.page.locator(_MASTER).first
        if not m.is_checked():
            m.evaluate("el => el.click()"); page.page.wait_for_timeout(400)
        page.page.locator("input#pickHideDrive").first.fill("C;D;E")
        for cid, want in [("isCmd", True), ("isRegedit", False),
                          ("isMmc", True), ("isShutdownAccessControl", False)]:
            cb = page.page.locator(f"input#{cid}").first
            if cb.is_checked() != want:
                cb.evaluate("el => el.click()"); page.page.wait_for_timeout(120)
        page.page.locator("input#usbControlRead").first.evaluate("el => el.click()")

        msg = page.submit_and_message()
        self._add("pass" if "저장" in msg else "fail",
                  "sc4m — 수정 혼합 조합 저장", f"msg={msg!r}", sc=4)
        if "저장" not in msg:
            return

        page.open_detail_modal(target)
        detail = page.read_detail_modal()
        text = page.detail_modal_text()
        page.close_detail_modal()
        expected = {"isAccessControl": True, "isCmd": True, "isRegedit": False,
                    "isMmc": True, "isShutdownAccessControl": False, "usb": "읽기"}
        for k, v in expected.items():
            self._add("pass" if detail.get(k) == v else "fail",
                      f"sc4m — 수정 round-trip '{k}' = {v}",
                      f"실제={detail.get(k)} / 기대={v}", sc=4)
        self._add("pass" if "C;D;E" in text else "fail",
                  "sc4m — 수정 round-trip 드라이브 'C;D;E'",
                  f"속성 모달 텍스트 'C;D;E' 포함={'C;D;E' in text}", sc=4)

    def test_scenario4n_edit_modal_title(self, logged_in_page, settings):
        """sc4i(nPouch) 대응 — EDIT 모달 제목이 '수정'이 아니라 '등록'이면 결함.
        Chrome MCP 실측 2026-06-10: add/edit 둘 다 '시큐어존 접근제어 정책 등록' → title 결함."""
        print("\n━━ [접근제어 정책] 시나리오 4n: EDIT 모달 제목 (수정/등록) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        target = self._edit_target(page)
        if not target:
            self._add("skip", "sc4n — 대상 없음", "edit 대상 [AUTO] 없음", sc=4)
            return

        title_sel = f"{page.SEL_MODAL} .modal-title, {page.SEL_MODAL} h3, {page.SEL_MODAL} h4"
        page.open_add_modal()
        add_title = page.page.locator(title_sel).first.inner_text().strip()
        page._close_modal_if_open()

        page.open_modify_modal(target)
        title_loc = page.page.locator(title_sel).first
        edit_title = title_loc.inner_text().strip()

        # EDIT 인데 제목이 '수정' 없이 '등록'이면 결함(사용자 혼란) → WARN
        # 스크린샷은 EDIT 모달이 열린 상태에서 찍어야 제목이 잡힘 → close 전에 _add 호출
        defect = ("수정" not in edit_title) and ("등록" in edit_title)
        self._add("warn" if defect else "pass",
                  "sc4n — EDIT 모달 제목 '수정' 표기",
                  f"add 제목={add_title!r} / edit 제목={edit_title!r} "
                  + ("[결함: 수정 모달인데 '등록' 표기 — 사용자 혼란]" if defect
                     else "(수정 표기 정상)"), sc=4,
                  highlight=title_loc)
        page.close_edit_modal()
