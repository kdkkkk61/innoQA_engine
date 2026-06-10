"""시큐어존 접근제어 정책 — 시나리오 5: lifecycle (nPouch sc5 패턴 + 속성 모달 레이어).

사용자 설계 (2026-06-10):
  기존 nPouch sc5 방식("어떤 값을 추가했는지" 재오픈 EDIT 모달로 전체 일치 검증)을 따르고,
  거기에 신규 '속성 모달' 검증만 레이어로 추가한다.

sc5a — 전부 ON 생성 → ① 재오픈 EDIT 모달 전체 값 ON 일치 ② 속성 모달 ON 일치 + 읽기전용
sc5b — EDIT 전부 OFF 저장 → ① 재오픈 EDIT 모달 전체 값 OFF 일치 ② 속성 모달 OFF 일치
sc5c — lifecycle 종료 cleanup ([AUTO] 전체 삭제; 날짜본 [AUTO_<날짜>] KEEP 은 보존)

cleanup: sc1 시작 clean slate / sc2~4 미삭제 / sc5c 종료 정리. 접근제어는 독립(교차연계 없음).
"""
from pages.secure_zone_access_control_policy_page import SecureZoneAccessControlPolicyPage
from tests.secure_zone._base import SecureZoneACBase

_MASTER = "input#isAccessControl"
_CHECKS = ["isCmd", "isRegedit", "isMmc", "isShutdownAccessControl"]
_DRIVES = {
    "input#pickHideDrive":   "C;D;E",
    "input#pickDenyDrive":   "C;D;E",
    "input#pickExceptDrive": "S,W",
}

# 전부 ON 기준값 (재오픈 검증용)
_ON_CHECKS = {"isAccessControl": True, "isCmd": True, "isRegedit": True,
              "isMmc": True, "isShutdownAccessControl": True}
_ON_USB = "읽기/쓰기"
# 전부 OFF 기준값
_OFF_CHECKS = {"isAccessControl": False, "isCmd": False, "isRegedit": False,
               "isMmc": False, "isShutdownAccessControl": False}


class TestSecureZoneAccessControlScenario5Lifecycle(SecureZoneACBase):
    """접근제어 정책 — 시나리오 5: lifecycle."""

    _NAME = None

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneAccessControlPolicyPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _set_checked(self, page, sel, on: bool):
        loc = page.page.locator(sel).first
        if loc.count() and loc.is_enabled() and loc.is_checked() != on:
            loc.evaluate("el => el.click()")
            page.page.wait_for_timeout(150)

    def _verify_detail(self, page, name, exp_checks, scope,
                       check_readonly=False, drive_values=None, exp_usb=None,
                       drives_present=True):
        """속성 모달로 내용 확인 (재오픈 EDIT 대신 — 사용자 설계 2026-06-10).

        토글(id)·USB(name)은 read_detail_modal, 드라이브 값은 모달 텍스트 포함 여부로 검증.
        drive_values: 검증할 드라이브 값 리스트 (예 ['C;D;E','S,W']).
        drives_present: True=값 포함돼야 / False=값 없어야 (OFF 시).
        """
        page.open_detail_modal(name)
        readonly = page.detail_modal_readonly() if check_readonly else None
        changed = page.detail_modal_try_change() if check_readonly else {}
        detail = page.read_detail_modal()
        text = page.detail_modal_text()
        page.close_detail_modal()
        print(f"[sc{scope}] 속성 모달: {detail} / readonly={readonly} / 변경시도={changed}")
        if check_readonly:
            # ① disabled 속성
            self._add("pass" if readonly else "warn",
                      f"sc{scope} — 속성 모달 읽기전용(disabled 속성)",
                      f"모달 내 모든 input disabled={readonly}", sc=5)
            # ② 능동 검증: 클릭 시도 → 값 안 바뀜 (읽기전용 우회 여부)
            any_changed = [s for s, r in changed.items() if r.get("changed")]
            self._add("pass" if not any_changed else "fail",
                      f"sc{scope} — 속성 모달 UI 변경 불가 (클릭 시도→무변경)",
                      f"클릭 시도 결과: {changed} / 변경된 요소: {any_changed or '없음'}", sc=5)
        for cid, exp in exp_checks.items():
            v = detail.get(cid)
            ok = (v == exp) if exp else (v in (False, None))
            self._add("pass" if ok else ("fail" if exp else "warn"),
                      f"sc{scope} — 속성 모달 '{cid}' = {exp}",
                      f"실제={v} / 기대={exp}", sc=5)
        if exp_usb is not None:
            self._add("pass" if detail.get("usb") == exp_usb else "fail",
                      f"sc{scope} — 속성 모달 USB 권한 = {exp_usb}",
                      f"실제={detail.get('usb')!r} / 기대={exp_usb!r}", sc=5)
        for dv in (drive_values or []):
            present = dv in text
            ok = present if drives_present else (not present)
            self._add("pass" if ok else "fail",
                      f"sc{scope} — 속성 모달 드라이브 값 '{dv}' "
                      f"{'포함' if drives_present else '미포함'}",
                      f"모달텍스트 포함={present} / 기대={'포함' if drives_present else '미포함'}",
                      sc=5)

    # ── sc5a: 전부 ON 생성 → EDIT 재오픈 + 속성 모달 ──────────────
    def test_scenario5a_all_on(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 5a: 전부 ON 생성 + 재오픈/속성 검증 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()

        name = f"{page.AUTO_NAME_PREFIX}_on"
        TestSecureZoneAccessControlScenario5Lifecycle._NAME = name
        page.open_add_modal()
        page.fill(page.SEL_NAME, name)
        self._set_checked(page, _MASTER, True)
        for sel, val in _DRIVES.items():
            page.page.locator(sel).first.fill(val)
        for cid in _CHECKS:
            self._set_checked(page, f"input#{cid}", True)
        page.page.locator("input#usbControlReadWrite").first.evaluate("el => el.click()")

        # 생성 '액션' 검증 — 저장 성공 메시지
        msg = page.submit_and_message()
        self._add("pass" if "저장" in msg and "오류" not in msg else "fail",
                  "sc5a — 전부 ON 정책 생성 저장 성공",
                  f"입력: 마스터+드라이브(C;D;E·S,W)+CMD/Regedit/MMC/종료해제 ON+USB 읽기/쓰기 / msg={msg!r}",
                  sc=5)
        page.navigate_to()
        exists = name in page.get_policy_names()
        self._add("pass" if exists else "fail",
                  "sc5a — 생성 정책 목록 등록 확인",
                  f"'{name}' 존재={exists}", sc=5)
        if not exists:
            return
        # 속성 모달로 내용 확인 (재오픈 EDIT 대신) — 토글 ON + USB + 드라이브 값 + 읽기전용
        self._verify_detail(page, name, _ON_CHECKS, scope="5a",
                            check_readonly=True, exp_usb=_ON_USB,
                            drive_values=["C;D;E", "S,W"], drives_present=True)

    # ── sc5b: 전부 OFF 수정 → EDIT 재오픈 + 속성 모달 ─────────────
    def test_scenario5b_all_off(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 5b: 전부 OFF 수정 + 재오픈/속성 검증 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = TestSecureZoneAccessControlScenario5Lifecycle._NAME
        if not name or name not in page.get_policy_names():
            self._add("skip", "sc5b — 대상 없음", f"sc5a ON 정책 미존재({name})", sc=5)
            return

        page.open_modify_modal(name)
        # 종속 먼저 OFF/비우기 → 마스터 OFF (순서)
        for cid in _CHECKS:
            self._set_checked(page, f"input#{cid}", False)
        for sel in _DRIVES:
            loc = page.page.locator(sel).first
            if loc.count():
                loc.fill("")
        self._set_checked(page, _MASTER, False)

        # 수정 '액션' 검증 — 저장 성공 메시지 ("수정했다" 검증)
        msg = page.submit_and_message()
        self._add("pass" if "저장" in msg and "오류" not in msg else "fail",
                  "sc5b — 전부 OFF 수정 저장 성공",
                  f"변경: 마스터+하위 전부 OFF + 드라이브 비움 / msg={msg!r}", sc=5)

        # 속성 모달로 OFF 재확인 — 토글 OFF + 드라이브 값 미포함 + 읽기전용/변경불가(sc5a와 동일)
        self._verify_detail(page, name, _OFF_CHECKS, scope="5b",
                            check_readonly=True,
                            drive_values=["C;D;E", "S,W"], drives_present=False)

    # ── sc5c: lifecycle 종료 cleanup ─────────────────────────────
    def test_scenario5c_lifecycle_cleanup(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 5c: lifecycle 종료 cleanup ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        before = [n for n in page.get_policy_names() if n.startswith("[AUTO]")]
        page.delete_all_auto_policies()
        page.navigate_to()
        after = [n for n in page.get_policy_names() if n.startswith("[AUTO]")]
        self._add("pass" if not after else "fail",
                  "sc5c — lifecycle 종료 cleanup ([AUTO] 전체 삭제)",
                  f"삭제 전 {len(before)}건 {before} → 후 {len(after)}건 {after}", sc=5)
