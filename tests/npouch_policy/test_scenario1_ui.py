"""nPouch 엔파우치 정책 — 시나리오 1: UI 구조 (origin_protect 패턴 그대로).

Chrome MCP 사실 (2026-06-01):
  - list 컬럼 6개 + list 버튼 6 (정책추가/통합정책/수정/복사/공인IP/삭제) + 검색
  - ADD 모달: div#addItemModal.in
  - 탭 2개 (정책 정보 / PDF문서 보호 기능 설정)
  - 모달 input 51개

의존성: 원본보호 정책 [AUTO_KEEP]_sc5_origin_protect (sc3 부터 활용).
"""
from pages.npouch_policy_page import NpouchPolicyPage
from tests.npouch_policy._base import NpouchPolicyBase


class TestNpouchPolicyScenario1Ui(NpouchPolicyBase):
    """엔파우치 정책 — 시나리오 1: UI 구조."""

    def test_scenario1a_navigate_list_buttons(self, logged_in_page, settings):
        """sc1a — 목록 페이지 진입 + 6 버튼 + 검색 input 존재."""
        print("\n━━ [엔파우치 정책] 시나리오 1a: navigate + 목록 UI ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        url_ok = "managerNpouchPolicy" in page.page.url
        self._add("pass" if url_ok else "fail",
                  "navigate_to → managerNpouchPolicy",
                  f"url={page.page.url!r}", sc=1)

        elements = {
            "정책추가":                       page.SEL_ADD_BTN,
            "수정":                           page.SEL_MODIFY_BTN,
            "정책복사":                       page.SEL_COPY_BTN,
            "삭제":                           page.SEL_DELETE_BTN,
            "통합정책 추가/삭제":             page.SEL_INTEGRATED_BTN,
            "엔파우치 열람 가능 공인IP 설정": page.SEL_PUBLIC_IP_BTN,
            "검색":                           page.SEL_SEARCH_INPUT,
        }
        for label, sel in elements.items():
            present = page.page.locator(sel).count() > 0
            # 없으면 fail(높음버그) 아니라 skip — 빌드별 삭제는 sc0 '변경사항(삭제)'가 보고.
            self._add("pass" if present else "skip",
                      f"목록 페이지 — '{label}' 존재",
                      f"결과: present={present}"
                      + ("" if present else " (이 빌드 미존재 — sc0 변경사항 참조)"), sc=1)

    def test_scenario1b_add_modal_enter_exit(self, logged_in_page, settings):
        """sc1b — ADD 모달 진입 + 핵심 필드 + 2탭 존재 + close."""
        print("\n━━ [엔파우치 정책] 시나리오 1b: ADD 모달 진입/탈출 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()

        page.open_add_modal()
        modal_open = page.page.locator(page.SEL_MODAL_OPEN).count() > 0
        self._add("pass" if modal_open else "fail",
                  "ADD 모달 진입",
                  f"결과: modal_open={modal_open}", sc=1)

        # 정책 정보 탭 핵심 필드
        core_fields = {
            "정책 이름":                  page.SEL_POLICY_NAME,
            "열람 파일 인증 서버 URL":    page.SEL_CERT_URL,
            "SSL 인증서 유효성 검사 토글": page.SEL_VALIDATE_SSL,
            "열람횟수 설정 토글":         page.SEL_MAX_READ_COUNT_TOGGLE,
            "열람 유효기간 토글":         page.SEL_MAX_READ_DAY_TOGGLE,
            "열기암호 사용 토글":         page.SEL_PW_TOGGLE,
            "원본보호 정책 적용 체크박스": page.SEL_ORIGIN_PROTECT,
            "원본보호 정책 선택 버튼":    page.SEL_ORIGIN_PROTECT_BTN,
            "확장자 필터기능 토글":       page.SEL_EXT_FILTER,
        }
        for label, sel in core_fields.items():
            present = page.page.locator(sel).count() > 0
            # 없으면 fail(높음버그) 아니라 skip — 빌드별 삭제는 sc0 '변경사항(삭제)'가 보고.
            self._add("pass" if present else "skip",
                      f"ADD 모달 — '{label}' 필드 존재",
                      f"selector='{sel}' / 결과: present={present}"
                      + ("" if present else " (이 빌드 미존재 — sc0 변경사항 참조)"), sc=1)

        # 탭 2개 존재
        tabs = page.page.locator(
            "div#addItemModal.in ul.nav-tabs li a, div#addItemModal.in ul.tab-list li a, div#addItemModal.in li > a"
        )
        tab_count = tabs.count()
        self._add("pass" if tab_count >= 2 else "fail",
                  "ADD 모달 — 2탭 (정책 정보 + PDF문서 보호 기능 설정) 존재",
                  f"결과: tab_count={tab_count}", sc=1)

        page.close_modal()
        closed = page.page.locator(page.SEL_MODAL_OPEN).count() == 0
        self._add("pass" if closed else "fail",
                  "ADD 모달 close",
                  f"결과: closed={closed}", sc=1)

    def test_scenario1c_pdf_tab_access(self, logged_in_page, settings):
        """sc1c — ADD 중 PDF 탭 진입 — 차단 없이 정상 진입 (origin_protect 와 다른 동작).

        origin_protect: 비기본 탭 클릭 시 '정책 정보 먼저 등록' 차단
        nPouch 정책:    PDF 탭 자유 진입 가능 (정보 수집 시 확인됨)
        """
        print("\n━━ [엔파우치 정책] 시나리오 1c: PDF 탭 진입 자유 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # PDF 탭 클릭
        page.activate_tab("PDF문서 보호 기능 설정")

        # 차단 메시지 없어야 정상
        blocked = page.is_confirm_modal_visible(timeout=1000)
        if blocked:
            try:
                page.dismiss_confirm_modal()
            except Exception:
                pass
        self._add("pass" if not blocked else "fail",
                  "sc1c — PDF 탭 자유 진입 (차단 메시지 없음)",
                  f"결과: blocked={blocked} (기대 False — PDF 탭 자유 접근)", sc=1)

        # PDF 탭 핵심 필드 (color picker + 워터마크 위치 grid) 존재
        color_present = page.page.locator(page.SEL_CENTER_WM_COLOR).count() > 0
        grid_cells    = page.page.locator(
            "table#tempTable td[data-split-location]"
        ).count()
        self._add("pass" if color_present else "fail",
                  "sc1c — PDF 탭 색상 picker 존재",
                  f"selector={page.SEL_CENTER_WM_COLOR!r} / 결과: present={color_present}", sc=1)
        self._add("pass" if grid_cells == 9 else "fail",
                  "sc1c — PDF 탭 워터마크 위치 3x3 grid (9 cell)",
                  f"결과: cell={grid_cells} (기대 9)", sc=1)

        page.close_modal()

    def test_scenario1d_add_modal_default_reset(self, logged_in_page, settings):
        """sc1d — ADD close → re-open 시 default reset 확인 (정책 이름).

        nPouch 정책의 일부 토글은 default ON (열람횟수/유효기간/열기암호 등)
        → 빈값 reset 검증은 text 필드 (정책 이름/URL) 만 적용.
        """
        print("\n━━ [엔파우치 정책] 시나리오 1d: ADD 모달 default reset ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 임의로 값 채움
        page.page.locator(page.SEL_POLICY_NAME).fill("[AUTO]_probe_d")
        page.page.locator(page.SEL_CERT_URL).fill("https://probe.test/cert")

        page.close_modal()
        page.open_add_modal()

        defaults_ok = {
            "정책 이름":               page.page.locator(page.SEL_POLICY_NAME).input_value() == "",
            "열람 파일 인증 서버 URL": page.page.locator(page.SEL_CERT_URL).input_value() == "",
        }
        for label, ok in defaults_ok.items():
            self._add("pass" if ok else "fail",
                      f"sc1d — ADD 재오픈 시 '{label}' 빈값 default reset",
                      f"결과: ok={ok}", sc=1)

        page.close_modal()
