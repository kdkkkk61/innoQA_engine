"""시큐어존 템플릿(특수폴더) — 시나리오 6: 연계 데이터 준비 (날짜본 2종).

sc6 = 다음 테스트(상위 시큐어존 정책)가 참조할 데이터를 만들어 '삭제하지 않고 남긴다'(표준 정의).
사용자 지시(2026-07-02): 특수폴더는 **바로가기 + 레지스트리 둘 다** 날짜본 생성.
  → [AUTO_<MMDD>]_sz_mf_link(SHORTCUT) / [AUTO_<MMDD>]_sz_mf_reg(MODIFY_REGIST), 각 매핑 1건 포함(실사용 가능 seed).

명명: '[AUTO]'(날짜 없음)=휘발성→sc5d 가 삭제 / '[AUTO_<MMDD>]'(날짜본)=영속·연계→보존
  (startswith('[AUTO]') 가 '[AUTO_'는 불일치 → 자동 제외). cleanup 은 sc5d 책임 — sc6 은 생성·확인만(표준).
연계 대상(상위 시큐어존 정책 테스트)은 현재 미구현 → 날짜본 seed 생성·보존까지
  (속성 모달 '사용처'가 정책 참조를 표시하므로, 정책 테스트 작성 시 이 날짜본을 picker 로 선택).
"""
import time

from pages.secure_zone_template_manage_folder_page import SecureZoneTemplateManageFolderPage
from tests.secure_zone_template_manage_folder._base import SecureZoneTemplateManageFolderBase


class TestSecureZoneTemplateManageFolderScenario6SuiteSetup(SecureZoneTemplateManageFolderBase):
    """시큐어존 템플릿(특수폴더) — 시나리오 6: 연계 데이터 준비."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateManageFolderPage(logged_in_page, settings)
        self._page = page.page
        return page

    # ══ 6a: 연계 날짜본 2종(바로가기/레지스트리) 생성 — 삭제하지 않고 남김 ════
    def test_scenario6a_dated_handoff(self, logged_in_page, settings):
        """[AUTO_<MMDD>] 날짜본 2종 + 각 매핑 1건 생성(없을 때만) → 존재·용도·매핑 확인 → 남김."""
        print("\n━━ [특수폴더] 시나리오 6a: 연계 날짜본 2종(바로가기/레지스트리) 생성 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        date = time.strftime("%m%d")                       # 예: 0702
        made = []
        for label, suffix, tpl_type, purpose_kw in (
                ("바로가기", "link", "SHORTCUT", "바로가기"),
                ("레지스트리", "reg", "MODIFY_REGIST", "레지스트")):
            dated = f"[AUTO_{date}]_sz_mf_{suffix}"
            page.ensure_template(dated, tpl_type)          # 같은 날 재실행은 동명 재사용(없을 때만 생성)
            page.open_folder_modal(dated)
            if page.folder_item_count() == 0:
                page.open_content_add()
                page.add_folder_mapping(f"{suffix}_suite", use_picker=True, src_index=0, tgt_index=1)
            n = page.folder_item_count()
            page.close_folder_modal()
            present = dated in page.get_template_names()
            purpose = ""
            try:
                purpose = page._row_locator(dated).locator("td").nth(1).inner_text().strip()
            except Exception:
                pass
            ok = present and (n >= 1) and (purpose_kw in purpose)
            self._add("pass" if ok else "fail",
                      f"sc6a — 연계 날짜본({label}) 생성 + 매핑 1건",
                      f"결과: '{dated}' 존재={present}, 용도={purpose!r}(기대 {purpose_kw}), 매핑={n}건 "
                      + ("(연계 seed 준비됨)" if ok else "[생성/용도/매핑 확인 필요]"), sc=6,
                      repro=f"1. [AUTO_MMDD]_sz_mf_{suffix} 생성({label})\n2. 폴더 매핑 1건 추가\n"
                            "3. 리스트 존재·용도·등록된 경로 확인")
            made.append(dated)
        # 삭제하지 않고 남김 — 표준 표식(cleanup 은 sc5d/다음 run sc1 책임)
        self._add("skip", "sc6a — 연계 데이터 남겨두기(삭제 안 함)",
                  f"{made} — 상위 시큐어존 정책 테스트가 참조 예정(현재 미구현, seed 보존). "
                  "휘발성 [AUTO] 정리는 sc5d, 날짜본 최종 정리는 다음 run 의 sc1 시작이 담당.", sc=6)
