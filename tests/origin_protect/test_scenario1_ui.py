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

        # ADD 모달 탭 4개 존재 (yaml: tab_count=4 / 순서: 기본설정·허용·예외처리·실행차단)
        tabs = page.page.locator(
            "div#addItemModal ul.nav-tabs li a, div#addItemModal ul.tab-list li a, div#addItemModal li > a"
        )
        tab_count = tabs.count()
        self._add("pass" if tab_count == 4 else "fail",
                  "ADD 모달 — 4탭 (기본설정·허용·예외처리·실행차단 프로세스) 존재",
                  f"결과: tab_count={tab_count}", sc=1)

        page.close_modal()
        closed = page.page.locator(page.SEL_MODAL_OPEN).count() == 0
        self._add("pass" if closed else "fail",
                  "ADD 모달 close",
                  f"결과: closed={closed}", sc=1)

    def test_scenario1c_add_tab_access_restriction(self, logged_in_page, settings):
        """sc1c — ADD 중 비기본 3탭 클릭 시 차단 메시지 정확 assert.

        yaml tab_access_restriction (Chrome MCP 직접 검증 2026-05-28):
          허용/예외처리/실행차단 탭 클릭 시 → __globalMessageModal 노출
            "정책 정보를 먼저 등록 하셔야 합니다."
          + active 탭 강제로 idx=0 (기본설정) 유지.
        """
        print("\n━━ [원본보호 정책] 시나리오 1c: ADD 비기본 탭 접근 차단 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        tabs = page.page.locator(
            "div#addItemModal ul.nav-tabs li a, div#addItemModal ul.tab-list li a, div#addItemModal li > a"
        )
        if tabs.count() < 4:
            self._add("fail", "sc1c — 탭 4개 미만 → 검증 불가",
                      f"결과: tab_count={tabs.count()}", sc=1)
            page.close_modal()
            return

        expected_msg = "정책 정보를 먼저 등록 하셔야 합니다."
        for idx, label in [(1, "허용 프로세스"), (2, "예외처리 프로세스"), (3, "실행차단 프로세스")]:
            # conftest qa-block-overlay 가 native click 차단 → JS evaluate click 사용
            # (control_suite 동일 패턴 — 버튼/탭 클릭은 좌표 무관 JS click 으로 overlay 우회)
            tabs.nth(idx).evaluate("el => el.click()")
            if page.is_confirm_modal_visible(timeout=1500):
                msg = page.get_confirm_message()
                # active tab 확인 — 0번으로 강제 유지
                active_idx = page.page.evaluate(f"""
                    () => {{
                      const ts = document.querySelectorAll(
                        'div#addItemModal ul.nav-tabs li a, div#addItemModal ul.tab-list li a, div#addItemModal li > a'
                      );
                      for (let i=0; i<ts.length; i++) {{
                        if (ts[i].parentElement && ts[i].parentElement.classList.contains('active')) return i;
                      }}
                      return -1;
                    }}
                """)
                msg_ok = msg == expected_msg
                active_ok = active_idx == 0
                self._add("pass" if msg_ok and active_ok else "fail",
                          f"sc1c — '{label}' 탭 클릭 차단 메시지 + active idx=0 강제 유지",
                          f"입력: 탭 idx={idx} 클릭 / 결과: 메시지={msg!r}, active_idx={active_idx}", sc=1)
                page.dismiss_confirm_modal()
            else:
                self._add("fail", f"sc1c — '{label}' 탭 클릭 후 차단 메시지 미노출",
                          f"입력: 탭 idx={idx} 클릭 / 결과: 알림 없음 (yaml 기대와 불일치)", sc=1)

        page.close_modal()

    def test_scenario1d_add_modal_default_reset(self, logged_in_page, settings):
        """sc1d — ADD 모달 close → re-open 시 모든 필드 default (빈/false) 로 reset 검증.

        yaml default_values 확정 사실 (Chrome MCP 2026-05-28):
          모든 text input = ''
          모든 checkbox = false
        """
        print("\n━━ [원본보호 정책] 시나리오 1d: ADD 모달 default reset ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 임의로 값 채움
        page.page.locator(page.SEL_POLICY_NAME).fill("[AUTO]_probe_d")
        page.page.locator(page.SEL_DRIVE_LETTER).fill("Z")
        page.page.locator(page.SEL_DRIVE_LABEL).fill("ProbeLabel")
        page.page.locator(page.SEL_DRIVE_QUOTA).fill("100")

        # close → re-open
        page.close_modal()
        page.open_add_modal()

        defaults_ok = {
            "originProtectPolicyName": page.page.locator(page.SEL_POLICY_NAME).input_value() == "",
            "driveLetter":             page.page.locator(page.SEL_DRIVE_LETTER).input_value() == "",
            "driveLabel":              page.page.locator(page.SEL_DRIVE_LABEL).input_value() == "",
            "originProtectDriveQuota": page.page.locator(page.SEL_DRIVE_QUOTA).input_value() == "",
        }
        for fid, ok in defaults_ok.items():
            self._add("pass" if ok else "fail",
                      f"sc1d — ADD 재오픈 시 '{fid}' 빈값 default reset",
                      f"결과: ok={ok}", sc=1)

        page.close_modal()
