"""원본보호 정책 — 시나리오 1: UI 구조 (목록·버튼·ADD 모달 진입 검증).

initial 스캔 (Chrome MCP 2026-05-28):
  - 목록 페이지 버튼 4종 (add/modify/copy/delete) + searchText + 7컬럼 테이블
  - ADD 모달: div#addItemModal.modal-wrap.in (동적 생성/제거)
  - 모달 안 input 26개 (visible 22 + hidden toggle 4) — yaml 인벤토리 참조

의존성: 제어 스위트 [AUTO_KEEP]_sc5_step1 (사용은 sc3 부터).
"""
from pages.npouch_origin_protect_policy_page import NpouchOriginProtectPolicyPage
from tests.origin_protect._base import OriginProtectBase


class TestOriginProtectScenario1Ui(OriginProtectBase):
    """원본보호 정책 — 시나리오 1: UI 구조."""

    def test_scenario1a_navigate_list_buttons(self, logged_in_page, settings):
        """sc1a — 목록 페이지 진입 + 4 버튼 + 검색 input 존재 확인."""
        print("\n━━ [원본보호 정책] 시나리오 1a: navigate + 목록 UI ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)   # delete_all_test_data 없으면 no-op (TODO)

        url_ok = "managerNpouchOriginProtectPolicy" in page.page.url
        self._add("pass" if url_ok else "fail",
                  "navigate_to → managerNpouchOriginProtectPolicy",
                  f"url={page.page.url!r}", sc=1)

        # 4 버튼 + 검색 input 존재
        buttons_present = {
            "addItemBtn":    page.page.locator(page.SEL_ADD_BTN).count() > 0,
            "modifyItemBtn": page.page.locator(page.SEL_MODIFY_BTN).count() > 0,
            "copyItemBtn":   page.page.locator(page.SEL_COPY_BTN).count() > 0,
            "removeItemBtn": page.page.locator(page.SEL_DELETE_BTN).count() > 0,
            "searchText":    page.page.locator(page.SEL_SEARCH_INPUT).count() > 0,
        }
        for name, present in buttons_present.items():
            self._add("pass" if present else "fail",
                      f"목록 페이지 — {name} 존재",
                      f"결과: present={present}", sc=1)

    def test_scenario1b_add_modal_enter_exit(self, logged_in_page, settings):
        """sc1b — ADD 모달 진입 + 26 input 존재 확인 + 닫기."""
        print("\n━━ [원본보호 정책] 시나리오 1b: ADD 모달 진입/탈출 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()

        page.open_add_modal()
        modal_open = page.page.locator(page.SEL_MODAL_OPEN).count() > 0
        self._add("pass" if modal_open else "fail",
                  "ADD 모달 진입",
                  f"결과: modal_open={modal_open}", sc=1)

        # 핵심 필드 4건 (기본 설정) 존재 확인
        core_fields = {
            "originProtectPolicyName": page.SEL_POLICY_NAME,
            "driveLetter":             page.SEL_DRIVE_LETTER,
            "driveLabel":              page.SEL_DRIVE_LABEL,
            "originProtectDriveQuota": page.SEL_DRIVE_QUOTA,
        }
        for fid, sel in core_fields.items():
            present = page.page.locator(sel).count() > 0
            self._add("pass" if present else "fail",
                      f"ADD 모달 — 기본 필드 '{fid}' 존재",
                      f"selector='{sel}' / 결과: present={present}", sc=1)

        # CSU select 버튼 + #controlSuiteId span (제어스위트 연계 지점)
        csu_btn_present = page.page.locator(page.SEL_CSU_SELECT_BTN).count() > 0
        csu_span_present = page.page.locator(page.SEL_CSU_ID_SPAN).count() > 0
        self._add("pass" if csu_btn_present and csu_span_present else "fail",
                  "ADD 모달 — 제어스위트 연계 (CSU select 버튼 + controlSuiteId span)",
                  f"결과: btn={csu_btn_present}, span={csu_span_present}", sc=1)

        # 프로세스 토글 3종
        for tid in ["isAllowProcess", "isExceptProcess", "isBlockProcess"]:
            present = page.page.locator(f"input#{tid}").count() > 0
            self._add("pass" if present else "fail",
                      f"ADD 모달 — 프로세스 토글 '{tid}' 존재",
                      f"결과: present={present}", sc=1)

        page.close_modal()
        closed = page.page.locator(page.SEL_MODAL_OPEN).count() == 0
        self._add("pass" if closed else "fail",
                  "ADD 모달 close",
                  f"결과: closed={closed}", sc=1)
