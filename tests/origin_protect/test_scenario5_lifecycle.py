"""원본보호 정책 — 시나리오 5 — 한 정책 lifecycle (5a/5b/5c).

제어스위트 sc5 패턴 동일:
  - 5a: [AUTO_KEEP]_sc5_origin_protect 정책 ADD (전체 필드) + 재오픈 일치
  - 5b: 5a 정책 EDIT (필드 변경) + 재오픈 일치
  - 5c: 5b 변경값 재오픈 일치 + cleanup ([AUTO]_ 만 정리, [AUTO_KEEP]_ 보존)
       → [AUTO_KEEP]_sc5_origin_protect 정책은 sc6 / 다음 페이지 연계용 보존

사용자 설계 (2026-05-29):
  - sc1 시작: AUTO + AUTO_KEEP 둘 다 cleanup (clean slate)
  - sc2/3/4: cleanup 없음 (이전 정책 재사용)
  - sc5: AUTO 만 정리, AUTO_KEEP 보존 (lifecycle 종료 + 다음 연계)
"""
from pages.npouch_origin_protect_policy_page import NpouchOriginProtectPolicyPage
from tests.origin_protect._base import OriginProtectBase
from tests.origin_protect.test_scenario3_add import _csu_select_first, _save_click
from tests.origin_protect.test_scenario4_modify import _enter_edit_modal, _safe_close_modal


class TestOriginProtectScenario5Lifecycle(OriginProtectBase):
    """원본보호 정책 — sc5: 한 정책 lifecycle (5a → 5b → 5c)."""

    LIFECYCLE_NAME = "[AUTO_KEEP]_sc5_origin_protect"

    # ==================================================================
    # sc5a — lifecycle ADD: 전체 필드 채움 + 재오픈 일치
    # ==================================================================
    def test_scenario5a_lifecycle_add(self, logged_in_page, settings):
        """sc5a — 종합 ADD (필수+선택 + 워터마크) → 재오픈 일치 검증.

        cleanup 정책 (사용자 설계):
          - sc1 시작 cleanup 으로 list 비어있음
          - 5a 는 [AUTO_KEEP]_ 정책 1건 생성 (5b/5c 에서 공유)
          - 5a 끝에 cleanup 안 함 (5b 에 정책 전달)
        """
        print("\n━━ [원본보호 정책] 시나리오 5a: lifecycle ADD ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        NAME = self.LIFECYCLE_NAME
        # 방어적 idempotent — 이미 존재하면 skip (이전 run 잔존)
        if page.is_policy_exists(NAME):
            self._add("skip", "sc5a — 이미 존재 (이전 run 잔존)",
                      f"입력: {NAME} / 결과: list 에 이미 존재 — sc5b 가 그대로 사용", sc=5)
            return

        # ADD 모달 — 전체 필드 채우기
        page.open_add_modal()
        page.page.locator(page.SEL_POLICY_NAME).fill(NAME)
        page.page.locator(page.SEL_DRIVE_LETTER).fill("S")
        page.page.locator(page.SEL_DRIVE_LABEL).fill("LifecycleLabel")
        page.page.locator(page.SEL_DRIVE_QUOTA).fill("500")
        _csu_select_first(page)

        # 워터마크 PC + TIME 체크 → 자동 토큰
        page.page.locator(page.SEL_SCREEN_WM_PC_INFO).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(300)
        page.page.locator(page.SEL_SCREEN_WM_TIME).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(300)

        # 투명도/각도
        for sel, val in [
            (page.SEL_SCREEN_WM_OPACITY, "50"),
            (page.SEL_SCREEN_WM_DEGREE, "45"),
        ]:
            loc = page.page.locator(sel)
            loc.fill(val)
            page.page.wait_for_timeout(100)

        # 저장
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        is_success = "저장" in msg and "오류" not in msg
        self._add("pass" if is_success else "fail",
                  "sc5a — lifecycle ADD 정상 저장",
                  f"입력: {NAME} (S, LifecycleLabel, 500, CSU 첫행, 워터마크 토큰+투명도+각도) / msg={msg!r}",
                  sc=5)

        # 재오픈 일치 검증 — list 등록 + EDIT 진입 + 저장값 확인
        page.navigate_to()
        page.page.wait_for_timeout(800)
        exists = page.is_policy_exists(NAME)
        self._add("pass" if exists else "fail",
                  "sc5a — lifecycle 정책 list 등록 확인",
                  f"입력: '{NAME}' / 결과: exists={exists}", sc=5)
        if not exists:
            return

        _enter_edit_modal(page, NAME)
        loaded = page.page.evaluate(
            """() => ({
                name: document.getElementById('originProtectPolicyName').value,
                letter: document.getElementById('driveLetter').value,
                label: document.getElementById('driveLabel').value,
                quota: document.getElementById('originProtectDriveQuota').value,
                wm_pc: document.getElementById('isScreenWaterMarkPcInfo').checked,
                wm_time: document.getElementById('isScreenWaterMarkCurrentTime').checked,
                wm_op: document.getElementById('screenWaterMarkOpacity').value,
                wm_dg: document.getElementById('screenWaterMarkDegree').value,
            })"""
        )
        expected = {
            "name": NAME, "letter": "S", "label": "LifecycleLabel", "quota": "500",
            "wm_pc": True, "wm_time": True, "wm_op": "50", "wm_dg": "45",
        }
        for k, v in expected.items():
            ok = loaded.get(k) == v
            self._add("pass" if ok else "fail",
                      f"sc5a — 재오픈 [{k}] 저장값 일치",
                      f"기대: {v!r} / 실제: {loaded.get(k)!r}", sc=5)
        _safe_close_modal(page)
        # cleanup 안 함 — 5b 가 그대로 사용

    # ==================================================================
    # sc5b — lifecycle modify: 5a 정책 EDIT (필드 변경) + 재오픈 일치
    # ==================================================================
    def test_scenario5b_lifecycle_modify(self, logged_in_page, settings):
        """sc5b — 5a 정책 EDIT, driveLabel/Quota/투명도 변경 + 재오픈 일치."""
        print("\n━━ [원본보호 정책] 시나리오 5b: lifecycle modify ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        NAME = self.LIFECYCLE_NAME
        if not page.is_policy_exists(NAME):
            self._add("skip", "sc5b — 5a 정책 부재 (5a 미실행)",
                      f"입력: {NAME} / sc5a 먼저 실행 필요", sc=5)
            return

        _enter_edit_modal(page, NAME)
        # 필드 변경: Label, Quota, 투명도, 각도
        page.page.locator(page.SEL_DRIVE_LABEL).fill("Modified5bLabel")
        page.page.locator(page.SEL_DRIVE_QUOTA).fill("800")
        page.page.locator(page.SEL_SCREEN_WM_OPACITY).fill("80")
        page.page.locator(page.SEL_SCREEN_WM_DEGREE).fill("180")

        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        is_success = "저장" in msg and "오류" not in msg
        self._add("pass" if is_success else "fail",
                  "sc5b — lifecycle modify 저장",
                  f"변경: Label='Modified5bLabel', Quota='800', Opacity='80', Degree='180' / msg={msg!r}",
                  sc=5)

        # 재오픈 일치 검증
        page.navigate_to()
        page.page.wait_for_timeout(800)
        _enter_edit_modal(page, NAME)
        loaded = page.page.evaluate(
            """() => ({
                label: document.getElementById('driveLabel').value,
                quota: document.getElementById('originProtectDriveQuota').value,
                wm_op: document.getElementById('screenWaterMarkOpacity').value,
                wm_dg: document.getElementById('screenWaterMarkDegree').value,
            })"""
        )
        expected = {"label": "Modified5bLabel", "quota": "800", "wm_op": "80", "wm_dg": "180"}
        for k, v in expected.items():
            ok = loaded.get(k) == v
            self._add("pass" if ok else "fail",
                      f"sc5b — 재오픈 [{k}] 변경값 일치",
                      f"기대: {v!r} / 실제: {loaded.get(k)!r}", sc=5)
        _safe_close_modal(page)
        # cleanup 안 함 — 5c 가 검증 + cleanup

    # ==================================================================
    # sc5c — lifecycle verify + cleanup: 5b 변경값 재오픈 일치 + AUTO 정리 (KEEP 보존)
    # ==================================================================
    def test_scenario5c_lifecycle_verify_and_cleanup(self, logged_in_page, settings):
        """sc5c — 5b 변경값 한 번 더 재오픈 일치 확인 + AUTO 만 cleanup.

        사용자 설계 (2026-05-29):
          - sc5 cleanup = AUTO 만 정리, AUTO_KEEP 은 보존 (sc6 / 다음 페이지 연계용)
          - delete_all_auto_policies() 사용 — [AUTO]_ 만 삭제, [AUTO_KEEP]_ 보존
        """
        print("\n━━ [원본보호 정책] 시나리오 5c: lifecycle verify + cleanup ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        NAME = self.LIFECYCLE_NAME
        if not page.is_policy_exists(NAME):
            self._add("skip", "sc5c — 5a/5b 정책 부재", "", sc=5)
            return

        # 1) 5b 변경값 재오픈 일치 한 번 더
        _enter_edit_modal(page, NAME)
        loaded = page.page.evaluate(
            """() => ({
                label: document.getElementById('driveLabel').value,
                quota: document.getElementById('originProtectDriveQuota').value,
            })"""
        )
        ok_label = loaded.get("label") == "Modified5bLabel"
        ok_quota = loaded.get("quota") == "800"
        self._add("pass" if ok_label and ok_quota else "fail",
                  "sc5c — 5b 변경값 재오픈 일치 (Label + Quota)",
                  f"기대: Modified5bLabel / 800 / 실제: {loaded.get('label')!r} / {loaded.get('quota')!r}",
                  sc=5)
        _safe_close_modal(page)

        # 2) cleanup — AUTO 만 정리, AUTO_KEEP 보존
        page.navigate_to()
        page.page.wait_for_timeout(500)
        before_names = page.get_policy_names()
        before_auto = [n for n in before_names if n.startswith("[AUTO]") and not n.startswith("[AUTO_KEEP]")]
        before_keep = [n for n in before_names if n.startswith("[AUTO_KEEP]")]

        deleted = page.delete_all_auto_policies()

        page.navigate_to()
        page.page.wait_for_timeout(500)
        after_names = page.get_policy_names()
        after_auto = [n for n in after_names if n.startswith("[AUTO]") and not n.startswith("[AUTO_KEEP]")]
        after_keep = [n for n in after_names if n.startswith("[AUTO_KEEP]")]

        auto_cleared = len(after_auto) == 0
        keep_preserved = (NAME in after_keep)

        self._add("pass" if auto_cleared else "fail",
                  "sc5c — cleanup: [AUTO]_ 정책 전부 삭제",
                  f"before AUTO: {len(before_auto)}건 / deleted={deleted} / after AUTO: {len(after_auto)}건 "
                  f"(잔여: {after_auto if after_auto else '없음'})",
                  sc=5)

        self._add("pass" if keep_preserved else "fail",
                  "sc5c — cleanup: [AUTO_KEEP]_ 정책 보존 (sc6 / 다음 연계용)",
                  f"before KEEP: {before_keep} / after KEEP: {after_keep} "
                  f"(lifecycle 정책 {NAME} 보존 여부={keep_preserved})",
                  sc=5)
