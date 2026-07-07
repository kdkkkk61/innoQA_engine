"""시큐어존 템플릿(폴더동기화) — 시나리오 6: 연계 데이터 준비 (날짜본).

sc6 = 다음 테스트(상위 시큐어존 정책)가 참조할 데이터를 만들어 '삭제하지 않고 남긴다'(표준).
폴더동기화는 단일 타입 → 날짜본 1종: [AUTO_<MMDD>]_sz_sync + 실사용 가능 매핑 1건
(원본/대상 picker + 스케줄 매주·월 — 스케줄 포함 seed 여야 정책 참조 시 실동작 검증 가능).

명명: '[AUTO]'(날짜 없음)=휘발성→sc5d 삭제 / '[AUTO_<MMDD>]'(날짜본)=영속·연계→보존.
cleanup 은 sc5d/다음 run sc1 책임 — sc6 은 생성·확인만.
연계 대상(상위 시큐어존 정책 테스트)은 현재 미구현 → seed 생성·보존까지
(속성 모달 '사용처'가 정책 참조를 표시 — 정책 테스트 작성 시 이 날짜본을 picker 로 선택).
"""
import time

from pages.secure_zone_template_sync_folder_page import SecureZoneTemplateSyncFolderPage
from tests.secure_zone_template_sync_folder._base import SecureZoneTemplateSyncFolderBase


class TestSecureZoneTemplateSyncFolderScenario6SuiteSetup(SecureZoneTemplateSyncFolderBase):
    """시큐어존 템플릿(폴더동기화) — 시나리오 6: 연계 데이터 준비."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSyncFolderPage(logged_in_page, settings)
        self._page = page.page
        return page

    # ══ 6a: 연계 날짜본 생성(스케줄 포함 매핑 seed) — 삭제하지 않고 남김 ════
    def test_scenario6a_dated_handoff(self, logged_in_page, settings):
        """[AUTO_<MMDD>]_sz_sync + 매핑 1건(매주·월) 생성(없을 때만) → 존재·매핑·속성 확인 → 남김."""
        print("\n━━ [폴더동기화] 시나리오 6a: 연계 날짜본 생성 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        date = time.strftime("%m%d")
        dated = f"[AUTO_{date}]_sz_sync"
        page.ensure_template(dated)          # 같은 날 재실행은 동명 재사용(없을 때만 생성)
        page.open_folder_modal(dated)
        if page.folder_item_count() == 0:
            page.open_content_add()
            page.fill(page.SEL_C_NAME, "sync_suite_seed")
            page.pick_path("source", 0)
            page.pick_path("target", 1)
            page.set_schedule_type("WEEKS")
            page.page.locator("input#checkMon").first.evaluate(
                "el => { if (!el.checked) el.click(); }")
            page.content_add_message()
        n = page.folder_item_count()
        page.close_folder_modal()
        present = dated in page.get_template_names()
        ok = present and n >= 1
        self._add("pass" if ok else "fail",
                  "sc6a — 연계 날짜본 생성 + 스케줄 포함 매핑 1건",
                  f"결과: '{dated}' 존재={present}, 매핑={n}건(매주·월 seed) "
                  + ("(연계 seed 준비됨)" if ok else "[생성/매핑 확인 필요]"), sc=6,
                  repro=f"1. {dated} 생성\n2. 매핑 1건(스케줄 매주·월) 추가\n3. 존재·등록 확인")

        # 속성 모달로 seed 상태 확인(사용처 섹션 존재 — 정책 연계 시 여기에 정책명 표시 예정)
        try:
            page.open_detail_modal(dated)
            dtext = page.detail_modal_text()
            item_shown = "sync_suite_seed" in dtext
            page.close_detail_modal()
            self._add("pass" if item_shown else "warn",
                      "sc6a — 날짜본 속성 모달: seed 항목 표시",
                      f"결과: 'sync_suite_seed' 표시={item_shown}", sc=6)
        except Exception as e:
            self._add("warn", "sc6a — 날짜본 속성 모달 확인", f"예외: {e!r}", sc=6)

        # 삭제하지 않고 남김 — 표준 표식(cleanup 은 sc5d/다음 run sc1 책임)
        self._add("skip", "sc6a — 연계 데이터 남겨두기(삭제 안 함)",
                  f"'{dated}' — 상위 시큐어존 정책 테스트가 참조 예정(현재 미구현, seed 보존). "
                  "휘발성 [AUTO] 정리는 sc5d, 날짜본 최종 정리는 다음 run 의 sc1 시작이 담당.", sc=6)
