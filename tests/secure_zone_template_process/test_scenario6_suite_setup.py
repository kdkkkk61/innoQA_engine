"""시큐어존 템플릿(프로세스) — 시나리오 6: 연계 데이터 준비 (날짜본).

sc6 = 다음 테스트(상위 시큐어존 정책)가 참조할 데이터를 만들어 '삭제하지 않고 남긴다'(표준).
날짜본 [AUTO_<MMDD>]_sz_proc(ALLOW) + 실사용 가능하도록 프로세스 1건 등록.
sc6 은 **생성·보존만** — 검색 동작/옵션/저장값 등 검증은 생성(sc3)·수정(sc4) 담당.

명명: '[AUTO]'(날짜 없음)=휘발성 / '[AUTO_<MMDD>]'(날짜본)=영속·연계 → 다음 run 의 sc1
clean slate([AUTO]+[AUTO_날짜] 둘 다 삭제)가 최종 정리. 연계 대상(상위 정책)은 현재 미구현.
"""
import time

from pages.secure_zone_template_process_page import SecureZoneTemplateProcessPage
from tests.secure_zone_template_process._base import SecureZoneTemplateProcessBase


class TestSecureZoneTemplateProcessScenario6SuiteSetup(SecureZoneTemplateProcessBase):
    """시큐어존 템플릿(프로세스) — 시나리오 6: 연계 데이터 준비."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    # ══ 6a: 연계 날짜본 생성(프로세스 1건 포함) — 삭제하지 않고 남김 ════
    def test_scenario6a_dated_handoff(self, logged_in_page, settings):
        """[AUTO_<MMDD>]_sz_proc + 프로세스 1건 생성(없을 때만) → 존재·등록 확인 → 남김."""
        print("\n━━ [프로세스] 시나리오 6a: 연계 날짜본 생성 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        date = time.strftime("%m%d")
        dated = f"[AUTO_{date}]_sz_proc"
        page.ensure_template(dated, "ALLOW_PROCESS")   # 같은 날 재실행은 동명 재사용
        page.open_l2_modal(dated)
        if page.l2_item_count() == 0:
            page.open_l3_add("ALLOW_PROCESS")
            page.l3_register("ALLOW_PROCESS", count=1)   # 앞쪽 행(front) — 생성용
            page.l3_add_message("ALLOW_PROCESS")
        n = page.l2_item_count()
        page.close_l2_modal()
        present = dated in page.get_template_names()
        ok = present and n >= 1
        self._add("pass" if ok else "fail",
                  "sc6a — 연계 날짜본 생성 + 프로세스 1건",
                  f"결과: '{dated}' 존재={present}, 등록={n}건 "
                  + ("(연계 seed 준비됨)" if ok else "[생성/등록 확인 필요]"), sc=6,
                  highlight=(page._row_locator(dated) if present else None),
                  repro=f"1. {dated} 생성\n2. 프로세스 1건 등록\n3. 존재·등록 확인")

        # 삭제하지 않고 남김 — 표준 표식(cleanup 은 다음 run sc1 clean slate 책임)
        self._add("skip", "sc6a — 연계 데이터 남겨두기(삭제 안 함)",
                  f"'{dated}' — 상위 시큐어존 정책 테스트가 참조 예정(현재 미구현, seed 보존). "
                  "날짜본 최종 정리는 다음 run 의 sc1 clean slate 가 담당.", sc=6)
