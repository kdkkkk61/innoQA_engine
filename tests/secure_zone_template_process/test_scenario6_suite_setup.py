"""시큐어존 템플릿(프로세스) — 시나리오 6: 연계 데이터 준비 (날짜본).

sc6 = 다음 테스트(상위 시큐어존 정책)가 참조할 데이터를 만들어 '삭제하지 않고 남긴다'(표준).
날짜본 [AUTO_<MMDD>]_sz_proc(ALLOW) + 프로세스 1건 + 태그 1건 등록.

등록 대상 선정(사용자 지시 2026-07-09): **당일 정확한 seed 를 먼저** —
picker 에서 [AUTO_<오늘>]_cm_proc / _cm_tag 를 **정확 검색**해 있으면 그걸 등록(연계),
없으면(상위 운용/태그 테스트를 안 돌린 run) **맨 앞 행** fallback. 프로세스·태그 둘 다.
※ 이전 날짜 seed([AUTO_0706] 등)는 다른 날 산출물이라 쓰지 않는다 — 당일 것만 정확 매칭.

sc6 은 생성·보존만 — 검색 필터/옵션 등 동작 검증은 sc3(sc3o 등) 담당.
명명: '[AUTO]'=휘발성 / '[AUTO_<MMDD>]'=영속·연계 → 다음 run sc1 clean slate 가 최종 정리.
"""
import re
import time

from pages.secure_zone_template_process_page import SecureZoneTemplateProcessPage
from tests.secure_zone_template_process._base import SecureZoneTemplateProcessBase


class TestSecureZoneTemplateProcessScenario6SuiteSetup(SecureZoneTemplateProcessBase):
    """시큐어존 템플릿(프로세스) — 시나리오 6: 연계 데이터 준비."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _register_seed_or_front(self, page, seed_name: str, *, tag: bool) -> tuple[list, str]:
        """당일 정확 seed 검색 → 있으면 등록 / 없으면 맨 앞 행 fallback(검색 리셋 "").
        반환: (등록 이름 리스트, 'seed'|'front')."""
        page.open_l3_add("ALLOW_PROCESS")
        picked = page.l3_register("ALLOW_PROCESS", tag=tag, search_term=seed_name,
                                  name_pattern=re.compile(re.escape(seed_name)))
        how = "seed"
        if not picked:   # 당일 seed 없음(상위 테스트 미실행 run) → 맨 앞 행
            picked = page.l3_register("ALLOW_PROCESS", tag=tag, count=1, search_term="")
            how = "front"
        if picked:
            page.l3_add_message("ALLOW_PROCESS")
        else:
            page.close_l3_modal("ALLOW_PROCESS")
        return picked, how

    # ══ 6a: 연계 날짜본 생성(프로세스 1건 + 태그 1건) — 삭제하지 않고 남김 ════
    def test_scenario6a_dated_handoff(self, logged_in_page, settings):
        """[AUTO_<MMDD>]_sz_proc 생성 → 프로세스/태그 각 1건(당일 seed 정확 검색, 없으면 맨 앞) → 남김."""
        print("\n━━ [프로세스] 시나리오 6a: 연계 날짜본 생성 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        date = time.strftime("%m%d")
        dated = f"[AUTO_{date}]_sz_proc"
        page.ensure_template(dated, "ALLOW_PROCESS")   # 같은 날 재실행은 동명 재사용
        page.open_l2_modal(dated)

        # 개별 프로세스: 당일 [AUTO_<오늘>]_cm_proc 정확 검색 → 없으면 맨 앞
        proc_picked, proc_how = ([], "기존")
        if page.l2_item_count() == 0:
            proc_picked, proc_how = self._register_seed_or_front(
                page, f"[AUTO_{date}]_cm_proc", tag=False)
        n_proc = page.l2_item_count()

        # 태그: 당일 [AUTO_<오늘>]_cm_tag 정확 검색 → 없으면 맨 앞
        page.switch_l2_tab("태그")
        tag_picked, tag_how = ([], "기존")
        if page.l2_item_count() == 0:
            tag_picked, tag_how = self._register_seed_or_front(
                page, f"[AUTO_{date}]_cm_tag", tag=True)
        n_tag = page.l2_item_count()
        page.close_l2_modal()

        present = dated in page.get_template_names()
        ok = present and n_proc >= 1 and n_tag >= 1
        self._add("pass" if ok else "fail",
                  "sc6a — 연계 날짜본 생성 + 프로세스/태그 각 1건 (당일 seed 우선)",
                  f"결과: '{dated}' 존재={present}, 프로세스={n_proc}건({proc_how}"
                  + (f": {proc_picked}" if proc_picked else "") + f"), 태그={n_tag}건({tag_how}"
                  + (f": {tag_picked}" if tag_picked else "") + ") "
                  + ("(연계 seed 준비됨)" if ok else "[생성/등록 확인 필요]"), sc=6,
                  highlight=(page._row_locator(dated) if present else None),
                  repro=f"1. {dated} 생성\n2. picker 에서 [AUTO_{date}]_cm_proc 정확 검색"
                        "(없으면 맨 앞 행)\n3. 태그 탭도 [AUTO_{date}]_cm_tag 동일 순서\n4. 존재·등록 확인")

        # 삭제하지 않고 남김 — 표준 표식(cleanup 은 다음 run sc1 clean slate 책임)
        self._add("skip", "sc6a — 연계 데이터 남겨두기(삭제 안 함)",
                  f"'{dated}' — 상위 시큐어존 정책 테스트가 참조 예정(현재 미구현, seed 보존). "
                  "날짜본 최종 정리는 다음 run 의 sc1 clean slate 가 담당.", sc=6)
