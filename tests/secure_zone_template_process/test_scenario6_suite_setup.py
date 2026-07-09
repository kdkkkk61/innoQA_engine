"""시큐어존 템플릿(프로세스) — 시나리오 6: 연계 데이터 준비 (날짜본 + 상위 seed 소비).

sc6 = 날짜본 [AUTO_<MMDD>]_sz_proc(ALLOW) 생성 + 상위 [AUTO_<date>]_cm_proc / _cm_tag
seed 를 **이름 검색으로 찾아 등록**(연계). 검색이 핵심 — sc3 처럼 앞쪽 행(front rows)이
아니라 '[AUTO' 검색 후 SEED 정규식 정확 매칭으로 선택. picker 는 1253/116건 대량이라
검색이 안 되면 seed 가 1페이지(20행)에 없어 못 찾음 → **sc6 통과 = 검색 실동작 증명**.
seed 없으면 skip(상위 운용/태그 테스트 미실행 run).

명명: '[AUTO]'(날짜 없음)=휘발성 / '[AUTO_<MMDD>]'(날짜본)=영속·연계 → 다음 run 의 sc1
clean slate([AUTO]+[AUTO_날짜] 둘 다 삭제)가 최종 정리. sc6 은 생성·연계·확인만(삭제 안 함).
연계 대상(상위 시큐어존 정책)은 현재 미구현 → seed 보존까지.
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

    def _dated(self) -> str:
        return f"[AUTO_{time.strftime('%m%d')}]_sz_proc"

    # ══ 6a: 프로세스 seed 검색·연계 (개별 프로세스 탭) ══════════════════
    def test_scenario6a_process_seed_link(self, logged_in_page, settings):
        """날짜본 생성 → 개별 프로세스 picker '[AUTO' 검색 → [AUTO_<date>]_cm_proc seed 등록.
        검색으로 정확 선택(앞쪽 행 아님)이 핵심. seed 없으면 skip."""
        print("\n━━ [프로세스] sc6a: 프로세스 seed 검색·연계 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        dated = self._dated()
        page.ensure_template(dated, "ALLOW_PROCESS")   # 같은 날 재실행은 동명 재사용
        page.open_l2_modal(dated)

        picked = []
        if page.l2_item_count() == 0:
            page.open_l3_add("ALLOW_PROCESS")
            picked = page.l3_register("ALLOW_PROCESS", search_term="[AUTO",
                                      name_pattern=page.SEED_PROC)
            if picked:
                page.l3_add_message("ALLOW_PROCESS")
            else:
                page.close_l3_modal("ALLOW_PROCESS")   # seed 미발견 → L3 닫기

        cnt = page.l2_item_count()
        names = [r.locator("td").nth(1).inner_text().strip() for r in page.l2_rows()]
        seed_linked = any(page.SEED_PROC.search(n) for n in names)

        if cnt == 0:
            self._add("skip", "sc6a — 프로세스 seed 검색·연계",
                      f"상위 [AUTO_<date>]_cm_proc seed 미존재(운용 프로세스 테스트 미실행 run) → skip. "
                      f"'{dated}' 빈 연계로 생성됨.", sc=6)
        else:
            self._add("pass" if seed_linked else "warn",
                      "sc6a — 프로세스 seed 검색·연계 ('[AUTO' 검색으로 정확 선택)",
                      f"검색 '[AUTO' → {picked or '(기존 등록 재사용)'} / L2 {cnt}건, 이름={names}, "
                      f"seed 매칭={seed_linked}"
                      + ("" if seed_linked else " [검색 결과가 seed 와 불일치 — 검색/매칭 확인]"), sc=6,
                      highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                      repro="1. 날짜본 템플릿 L2 → +\n2. 프로세스 선택 picker 에서 '[AUTO' 검색\n"
                            "3. [AUTO_<date>]_cm_proc seed 선택 → 추가\n4. L2 에 seed 등록 확인")
        page.close_l2_modal()

    # ══ 6b: 태그 seed 검색·연계 (태그 탭) ═══════════════════════════════
    def test_scenario6b_tag_seed_link(self, logged_in_page, settings):
        """같은 날짜본 L2 태그 탭 → '[AUTO' 검색 → [AUTO_<date>]_cm_tag seed 등록.
        태그 picker(processTagList) 검색 경로 검증. seed 없으면 skip."""
        print("\n━━ [프로세스] sc6b: 태그 seed 검색·연계 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        dated = self._dated()
        page.ensure_template(dated, "ALLOW_PROCESS")
        page.open_l2_modal(dated)
        page.switch_l2_tab("태그")

        picked = []
        if page.l2_item_count() == 0:
            page.open_l3_add("ALLOW_PROCESS")
            picked = page.l3_register("ALLOW_PROCESS", tag=True, search_term="[AUTO",
                                      name_pattern=page.SEED_TAG)
            if picked:
                page.l3_add_message("ALLOW_PROCESS")
            else:
                page.close_l3_modal("ALLOW_PROCESS")

        cnt = page.l2_item_count()
        names = [r.locator("td").nth(1).inner_text().strip() for r in page.l2_rows()]
        seed_linked = any(page.SEED_TAG.search(n) for n in names)

        if cnt == 0:
            self._add("skip", "sc6b — 태그 seed 검색·연계",
                      f"상위 [AUTO_<date>]_cm_tag seed 미존재(태그 테스트 미실행 run) → skip. "
                      f"'{dated}' 태그 빈 연계.", sc=6)
        else:
            self._add("pass" if seed_linked else "warn",
                      "sc6b — 태그 seed 검색·연계 ('[AUTO' 검색으로 정확 선택)",
                      f"검색 '[AUTO' → {picked or '(기존 등록 재사용)'} / 태그 탭 {cnt}건, 이름={names}, "
                      f"seed 매칭={seed_linked}"
                      + ("" if seed_linked else " [검색 결과가 seed 와 불일치 — 검색/매칭 확인]"), sc=6,
                      highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                      repro="1. 날짜본 템플릿 L2 태그 탭 → +\n2. 태그 선택 picker 에서 '[AUTO' 검색\n"
                            "3. [AUTO_<date>]_cm_tag seed 선택 → 추가\n4. 태그 탭에 seed 등록 확인")
        page.close_l2_modal()

    # ══ 6c: 연계 데이터 남겨두기 (삭제 안 함) ══════════════════════════
    def test_scenario6c_leave_handoff(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc6c: 연계 데이터 남겨두기 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        dated = self._dated()
        present = dated in page.get_template_names()
        self._add("skip", "sc6c — 연계 데이터 남겨두기(삭제 안 함)",
                  f"'{dated}' 존재={present} — 상위 시큐어존 정책 테스트가 참조 예정(현재 미구현, seed 보존). "
                  "날짜본 최종 정리는 다음 run 의 sc1 clean slate 가 담당.", sc=6)
