"""시큐어존 템플릿(시큐어 드라이브) — 시나리오 6: 연계 데이터 준비 + lifecycle cleanup.

sc6 = 다음 테스트(상위 시큐어존 정책)가 참조할 데이터를 만들어 '삭제하지 않고 남긴다'(표준 정의).
  → [AUTO_<MMDD>] 날짜본 템플릿(시큐어드라이브 2건) 생성 → 휘발성 [AUTO] 전부 정리 → 날짜본만 남김.
명명: '[AUTO]'(날짜 없음)=휘발성→delete_all_auto 삭제 / '[AUTO_<MMDD>]'(날짜본)=영속·연계→보존
  (startswith('[AUTO]') 가 '[AUTO_'는 불일치 → 자동 제외).
★날짜 기반 이유: 고정명은 다른 날 테스트 시 이전 본이 아직 등록/연계돼 있으면 '이미 등록된 이름' 충돌.
  날짜로 두면 날마다 이름이 달라(0628 vs 0629) 이전 본 생존해도 안 겹침. 같은 날 재실행은 동명 재사용(없을 때만 생성).

연계 대상(상위 시큐어존 정책 테스트)은 현재 미구현 → 날짜본 seed 생성·보존까지만(정책 페이지 작성 시 거기서 참조).
"""
import time

from pages.secure_zone_template_page import SecureZoneTemplateSecureDrivePage
from tests.secure_zone_template._base import SecureZoneTemplateBase


class TestSecureZoneTemplateScenario6SuiteSetup(SecureZoneTemplateBase):
    """시큐어존 템플릿(시큐어 드라이브) — 시나리오 6: 연계 데이터 준비."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSecureDrivePage(logged_in_page, settings)
        self._page = page.page
        return page

    # ══ 6a: 연계 준비 — [AUTO_날짜] 날짜본 생성 → [AUTO] 전부 정리(날짜본만 남김) ════
    def test_scenario6a_dated_handoff_and_cleanup(self, logged_in_page, settings):
        """sc6 연계용 [AUTO_<MMDD>] 날짜본 템플릿(시큐어드라이브 2건) 생성 후, 휘발성 [AUTO] 전부 삭제하고 날짜본은 남김."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 6a: 연계 날짜본 생성 + [AUTO] 정리 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        date = time.strftime("%m%d")                       # 예: 0629
        dated = f"[AUTO_{date}]_sztpl_sd"
        # ① 날짜본 생성(없으면) — 시큐어드라이브 2건 + 반출
        if dated not in page.get_template_names():
            page.open_add_modal()
            page.create_basic_template(dated, sd_letter="K", to_letter="L", to_path="C:\\dated_to", two_drives=True)
            page.navigate_to()
        dated_created = dated in page.get_template_names()
        # ② 휘발성 [AUTO] 전부 삭제(날짜본=[AUTO_날짜]는 보존)
        before = [n for n in page.get_template_names() if n.startswith("[AUTO]")]
        page.delete_all_auto()
        page.navigate_to()
        after_vol = [n for n in page.get_template_names() if n.startswith("[AUTO]")]
        dated_present = dated in page.get_template_names()
        kept_dated = [n for n in page.get_template_names()
                      if page._AUTO_ANY.match(n) and not n.startswith("[AUTO]")]
        ok = dated_created and (len(after_vol) == 0) and dated_present
        self._add("pass" if ok else "fail",
                  "sc6a — 연계 [AUTO_날짜] 날짜본 생성 + [AUTO] 전부 정리(날짜본 남김)",
                  f"결과: 날짜본 '{dated}' 생성={dated_created}/보존={dated_present}, "
                  f"휘발성 [AUTO] {len(before)}건 → {len(after_vol)}건, [AUTO_날짜] 보존 {len(kept_dated)}건 "
                  + ("(날짜본만 남고 [AUTO] 정리)" if ok else "[날짜본 미보존 또는 [AUTO] 잔존]"), sc=6,
                  repro="1. [AUTO_MMDD] 날짜본 템플릿 생성(시큐어드라이브 2건)\n"
                        "2. delete_all_auto → [AUTO] 전부 삭제\n3. 날짜본([AUTO_날짜])만 남는지 확인(다음 정책 테스트가 참조)")
