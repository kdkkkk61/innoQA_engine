"""
pages/npouch_operation_process_page.py — nPouch 운용 프로세스 페이지

공통설정 > 자원 관리 > 운용 프로세스
scan_mode: list_page
모달: div#addCommonProcess.modal-wrap.in  (Bootstrap 3 방식 아님 — 동적 생성/제거)
"""
from pages.base_page import BasePage


class NpouchOperationProcessPage(BasePage):

    # ── 네비게이션 ────────────────────────────────────────────────
    SEL_SYS_MGMT_ICON   = "a[data-menuid='managerSystemManagement']"
    SEL_SYS_MGMT_LIST   = "ul.managerSystemManagementList"
    SEL_RESOURCE_HEADER = "a.managerResource"
    SEL_MENU_ITEM       = "a[data-menuid='managerGlobalCommonProcess']"

    # ── 목록 버튼 ─────────────────────────────────────────────────
    SEL_ADD_BTN    = "button#addItemBtn"
    SEL_MODIFY_BTN = "button#modifyItemBtn"
    SEL_DELETE_BTN = "button#removeItemBtn"
    SEL_TABLE_ROW  = "table tbody tr"
    SEL_CHECKBOX   = "input[type='checkbox']"

    # ── 모달 (동적 생성/제거 방식) ────────────────────────────────
    SEL_MODAL        = "div#addCommonProcess"
    SEL_MODAL_OPEN   = "div#addCommonProcess.in"
    SEL_PROCESS_NAME = "input#processName"
    SEL_SIGN         = "input#sign"
    SEL_SHA2         = "textarea#sha2"
    SEL_EXEC_PATH    = "textarea#processExecutePath"
    SEL_DESCRIPTION  = "textarea#description"
    SEL_SUBMIT_BTN   = "div#addCommonProcess button.btn-primary"
    SEL_CANCEL_BTN   = "div#addCommonProcess button.btn-default"

    # ── 확인 모달 (전역 공통) ─────────────────────────────────────
    SEL_CONFIRM_MODAL  = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN    = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_MSG      = "#__globalMessageModal .modal-body"

    _TIMEOUT_TABLE = 5_000
    _TIMEOUT_MODAL = 5_000
    _TIMEOUT_STALE = 1_000

    _HASH_PAGE_SIZE = (
        "#!/managerGlobalCommonProcess"
        "?pageNo=1&pageSize=100&searchOption=processName&searchText="
    )

    # ── 네비게이션 ────────────────────────────────────────────────

    def navigate_to(self) -> None:
        """운용 프로세스 페이지로 이동."""
        self._dismiss_stale_confirm_modal()
        self._close_modal_if_open()
        # 이전 페이지(태그 등)에서 닫히지 않고 남은 모달 backdrop 제거.
        # cross-page 진입 시 잔여 'modal-backdrop in'이 좌측 메뉴 클릭을 가로채
        # 30초 타임아웃을 유발(실측 2026-06-17 sc6). url이 이미 main.html이면 리로드를
        # 건너뛰는 경로(아래 64행)라 backdrop이 그대로 남는 문제를 막는다.
        try:
            self.page.evaluate(
                "() => { document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());"
                " document.body.classList.remove('modal-open');"
                " document.body.style.removeProperty('padding-right'); }"
            )
        except Exception:
            pass

        if ("GlobalCommonProcess" in self.page.url
                and "pageSize=100" in self.page.url
                and self.is_visible(self.SEL_ADD_BTN)):
            return

        # 매니저 main.html 로드 (세션 유지 + 메뉴 초기화)
        if "manager/main.html" not in self.page.url:
            self.page.goto(f"{self.host_origin}/manager/main.html")
            self._dismiss_stale_confirm_modal()

        try:
            self.page.locator(self.SEL_SYS_MGMT_LIST).wait_for(
                state="visible", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

        if not self.is_visible(self.SEL_SYS_MGMT_LIST):
            self.click(self.SEL_SYS_MGMT_ICON)
            self.wait_for(self.SEL_SYS_MGMT_LIST)

        # 자원 관리 섹션 펼치기 (이미 보이면 스킵)
        if not self.is_visible(self.SEL_MENU_ITEM):
            try:
                self.page.locator(self.SEL_RESOURCE_HEADER).first.evaluate("el => el.click()")
                self.page.wait_for_timeout(300)
            except Exception:
                pass

        self.click(self.SEL_MENU_ITEM)
        self.wait_for(self.SEL_ADD_BTN)
        self.page.evaluate(f"window.location.hash = '{self._HASH_PAGE_SIZE}';")
        self.wait_for(self.SEL_ADD_BTN)
        try:
            self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    # ── 목록 조회 ─────────────────────────────────────────────────

    def get_item_names(self) -> list[str]:
        """현재 목록의 프로세스 이름 리스트 반환.
        td가 2개 미만인 행(빈 목록 안내 메시지 등)은 제외."""
        names = []
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = row.locator("td").all()
            if len(tds) >= 2:
                name = tds[0].inner_text().strip()
                if name:
                    names.append(name)
        return names

    # ── CRUD ──────────────────────────────────────────────────────

    def add_item(self, name: str, sha2: str = "", sign: str = "",
                 exec_path: str = "", description: str = "") -> None:
        """운용 프로세스 추가. [AUTO]_ 또는 [AUTO_KEEP]_ 접두사 필수."""
        if not (name.startswith("[AUTO]_") or name.startswith("[AUTO_KEEP]_")):
            raise Exception("테스트 항목([AUTO]_ 또는 [AUTO_KEEP]_ 접두사)만 생성 가능합니다")

        self.open_add_modal()

        self.fill(self.SEL_PROCESS_NAME, name)
        if sign:
            self.fill(self.SEL_SIGN, sign)
        if sha2:
            sha2_loc = self.page.locator(self.SEL_SHA2).first
            sha2_loc.evaluate(
                "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles:true})); }",
                sha2
            )
            self.page.wait_for_timeout(150)
        if exec_path:
            self.page.locator(self.SEL_EXEC_PATH).first.fill(exec_path)
            self.page.wait_for_timeout(100)
        if description:
            self.page.locator(self.SEL_DESCRIPTION).first.fill(description)
            self.page.wait_for_timeout(100)

        self.click_attached(self.SEL_SUBMIT_BTN)
        self._handle_confirm_modal()
        self.wait_for(self.SEL_ADD_BTN)
        # 추가 후 검색으로 항목 찾기 (알파벳순 정렬 시 목록 밖에 있을 수 있음)
        self.search_item(name)

    def delete_all_auto_items(self) -> None:
        """[AUTO]_ 접두사만 일괄 삭제 — [AUTO_KEEP]_* 는 보존.
        용도: 시나리오 5 마무리 — KEEP 잔존 + AUTO 정리.
        참조 잠금 차단 시 [AUTO]_DELME_ rename (제외 대상이라 무한루프 안 됨).
        """
        self.search_item("[AUTO")
        while True:
            names = [
                n for n in self.get_item_names()
                if n.startswith("[AUTO]_") and not n.startswith("[AUTO]_DELME_")
            ]
            if not names:
                break
            try:
                self._delete_or_rename(names[0])
            except Exception:
                break
        self._restore_page_size()

    def cleanup_with_keep(self) -> None:
        """[AUTO]_ + [AUTO_KEEP]_ 일괄 삭제 — clean slate.
        용도: 시나리오 1 시작 전 — 이전 세션 잔존 정리.
        참조 잠금 차단 시 [AUTO]_DELME_ rename (테스터 수동 정리, 무한루프 방지 제외).
        """
        self.search_item("[AUTO")
        while True:
            names = [
                n for n in self.get_item_names()
                if (n.startswith("[AUTO]_") or n.startswith("[AUTO_KEEP]_"))
                and not n.startswith("[AUTO]_DELME_")
            ]
            if not names:
                break
            try:
                self._delete_or_rename(names[0])
            except Exception:
                break
        self._restore_page_size()

    def delete_item(self, name: str, _skip_search: bool = False) -> None:
        """항목 삭제. [AUTO]_ 또는 [AUTO_KEEP]_ 접두사 필수.
        _skip_search=True: 검색 단계 생략 (bulk cleanup 에서 사용).
        """
        if not (name.startswith("[AUTO]_") or name.startswith("[AUTO_KEEP]_")):
            raise Exception("테스트 항목([AUTO]_ 또는 [AUTO_KEEP]_ 접두사)만 삭제 가능합니다")

        if not _skip_search:
            # 검색으로 행 노출
            self.search_item(name)
            self.page.wait_for_timeout(300)

        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=name).first
        checkbox = row.locator(self.SEL_CHECKBOX).first
        if not checkbox.is_checked():
            self._toggle_overlay(False)
            try:
                checkbox.click()
            finally:
                self._toggle_overlay(True)

        self.click(self.SEL_DELETE_BTN)
        self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        msg = self.page.locator(self.SEL_MODAL_MSG).first.inner_text().strip()
        if "하시겠습니까" not in msg:
            self.click_attached(self.SEL_CONFIRM_BTN)
            raise Exception(f"삭제 에러 모달: {msg!r}")
        self.click_attached(self.SEL_CONFIRM_BTN)
        self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
            state="detached", timeout=self._TIMEOUT_TABLE
        )
        self.wait_for(self.SEL_ADD_BTN)
        try:
            row.wait_for(state="detached", timeout=self._TIMEOUT_TABLE)
        except Exception:
            pass

    def rename_item(self, old_name: str, new_name: str) -> None:
        """수정 모달에서 이름 변경 후 저장. cleanup 차단 시 [AUTO]_DELME_ 마킹용."""
        self.open_modify_modal(old_name)
        self.page.locator(self.SEL_PROCESS_NAME).first.fill(new_name)
        self.page.wait_for_timeout(150)
        self.click_attached(self.SEL_SUBMIT_BTN)
        self._handle_confirm_modal()
        self.wait_for(self.SEL_ADD_BTN)

    def _delete_or_rename(self, name: str) -> str:
        """삭제 시도 → 참조 잠금 차단 시 [AUTO]_DELME_ 로 rename (테스터 수동 정리용).
        반환: 'deleted' | 'renamed'. _skip_search 전제 (cleanup 루프에서 검색 1회 후 호출).

        제품 2단계 동작 (Chrome 검증 2026-06-04):
          1) 삭제 → "삭제 하시겠습니까?" confirm → 확인
          2) 서버 검증 → 참조 시 "할당 되어 있습니다" 차단 (확인만) / 미참조 시 삭제 완료
        """
        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=name).first
        checkbox = row.locator(self.SEL_CHECKBOX).first
        if not checkbox.is_checked():
            self._toggle_overlay(False)
            try:
                checkbox.click()
            finally:
                self._toggle_overlay(True)

        self.click(self.SEL_DELETE_BTN)
        # 1단계: "삭제 하시겠습니까?" → 확인 클릭
        self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.click_attached(self.SEL_CONFIRM_BTN)
        self.page.wait_for_timeout(700)
        # 2단계: 서버 응답 — 차단 모달 있으면 참조 잠금 → rename
        if self.page.locator(self.SEL_CONFIRM_MODAL).count() > 0:
            msg2 = self.page.locator(self.SEL_MODAL_MSG).first.inner_text().strip()
            if ("할당" in msg2) or ("사용" in msg2) or ("참조" in msg2):
                self.click_attached(self.SEL_CONFIRM_BTN)
                try:
                    self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                        state="detached", timeout=self._TIMEOUT_TABLE
                    )
                except Exception:
                    pass
                base = name.replace("[AUTO_KEEP]_", "").replace("[AUTO]_", "")
                self.rename_item(name, f"[AUTO]_DELME_{base}")
                return "renamed"
            # 그 외 응답 모달 (성공 등) → dismiss
            self.click_attached(self.SEL_CONFIRM_BTN)
        try:
            self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass
        return "deleted"

    def open_modify_modal(self, name: str) -> None:
        """행 선택 → 수정 버튼 클릭 → 모달 열림 대기."""
        # 검색으로 행 노출
        self.search_item(name)
        self.page.wait_for_timeout(300)

        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=name).first
        self._toggle_overlay(False)
        self.page.wait_for_timeout(80)
        try:
            row.click(force=True, timeout=3000)
        finally:
            self._toggle_overlay(True)
        self.page.wait_for_timeout(300)
        self.click(self.SEL_MODIFY_BTN)
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.page.wait_for_timeout(200)

    def fill_modify_and_save(self) -> dict:
        """수정 모달에서 description 마지막 자리 변경 후 저장."""
        desc_loc = self.page.locator(self.SEL_DESCRIPTION).first
        desc_val = desc_loc.evaluate("el => el.value") or ""
        new_desc = desc_val[:-1] + ("1" if not desc_val or desc_val[-1] != "1" else "0") if desc_val else "scan_mod"
        self.page.locator(self.SEL_DESCRIPTION).first.fill(new_desc)
        self.page.wait_for_timeout(150)
        self.click_attached(self.SEL_SUBMIT_BTN)
        self._handle_confirm_modal()
        self.wait_for(self.SEL_ADD_BTN)
        return {self.SEL_PROCESS_NAME: None}  # 이름 유지 확인용

    def get_verify_values(self, saved_name: str) -> dict:
        return {"input#processName": saved_name}

    # ── 테스트 헬퍼 (public) ──────────────────────────────────────

    def open_add_modal(self) -> None:
        """추가 버튼 클릭 → 모달 열림 대기."""
        self.click(self.SEL_ADD_BTN)
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.page.wait_for_timeout(200)

    def close_modal(self) -> None:
        """취소 버튼으로 모달 닫기. 이미 닫혀있으면 즉시 반환."""
        try:
            if self.page.locator(self.SEL_MODAL_OPEN).count() == 0:
                return
            self.click_attached(self.SEL_CANCEL_BTN)
            self.page.locator(self.SEL_MODAL_OPEN).wait_for(
                state="detached", timeout=self._TIMEOUT_MODAL
            )
        except Exception:
            pass

    def try_submit(self) -> None:
        """제출 버튼 클릭 (결과 처리 없음 — 검증용)."""
        self.click_attached(self.SEL_SUBMIT_BTN)
        self.page.wait_for_timeout(400)

    def is_confirm_modal_visible(self) -> bool:
        """전역 확인 모달 표시 여부."""
        return self.page.locator(self.SEL_CONFIRM_MODAL).count() > 0

    def get_modal_message(self) -> str:
        """전역 확인 모달 메시지 텍스트."""
        try:
            return self.page.locator(self.SEL_MODAL_MSG).first.inner_text().strip()
        except Exception:
            return ""

    def dismiss_confirm_modal(self) -> None:
        """전역 확인 모달 닫기."""
        self.click_attached(self.SEL_CONFIRM_BTN)

    def wait_for_confirm_modal_closed(self) -> None:
        """전역 확인 모달이 사라질 때까지 대기."""
        self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
            state="detached", timeout=self._TIMEOUT_TABLE
        )

    # 검색 컬럼 드롭다운: 라벨은 빌드마다 다름('프로세스명' vs '프로세스 이름') → value 로 선택.
    # value 는 안정적(Chrome 직접 확인 2026-06-17: processName/sign/description).
    _SEARCH_OPTION_VALUE = {
        "프로세스 이름": "processName", "프로세스명": "processName", "이름": "processName",
        "서명": "sign", "설명": "description",
    }

    def _select_search_option(self, value: str) -> None:
        """검색 컬럼 드롭다운을 value 로 선택 (라벨 빌드차 흡수)."""
        try:
            self.page.locator("select#searchOption").first.select_option(value=value)
            self.page.wait_for_timeout(100)
        except Exception:
            pass

    def _do_search(self, keyword: str) -> None:
        """검색창 입력 + 검색 버튼 (드롭다운 미변경)."""
        search = self.page.locator("input#searchText").first
        search.fill(keyword)
        self.page.locator("button#searchBtn").first.evaluate("el => el.click()")
        self.page.wait_for_timeout(600)

    def search_item(self, keyword: str) -> None:
        """이름(프로세스명) 컬럼으로 검색. 드롭다운 상태가 이전 검색(설명 등)에서
        물려지지 않도록 매번 processName 명시 선택 (URL 해시 의존 제거)."""
        self._select_search_option("processName")
        self._do_search(keyword)

    def search_item_with_option(self, keyword: str, option_label: str) -> None:
        """검색 옵션 변경 후 검색. option_label: '프로세스 이름'/'프로세스명' | '서명' | '설명'.
        라벨이 빌드마다 달라 value 로 변환해 선택."""
        value = self._SEARCH_OPTION_VALUE.get(option_label, "processName")
        self._select_search_option(value)
        self._do_search(keyword)

    def get_modal_title(self) -> str:
        """현재 열린 모달의 타이틀 텍스트."""
        try:
            return self.page.locator(
                f"{self.SEL_MODAL} .modal-title, {self.SEL_MODAL} .modal-header h4"
            ).first.inner_text().strip()
        except Exception:
            return ""

    def get_field_value(self, selector: str) -> str:
        """필드 value 속성 반환."""
        try:
            return self.page.locator(selector).first.evaluate("el => el.value")
        except Exception:
            return ""

    # ── 내부 유틸 ─────────────────────────────────────────────────

    def _restore_page_size(self) -> None:
        if "pageSize=100" in self.page.url:
            return
        self.page.evaluate(f"window.location.hash = '{self._HASH_PAGE_SIZE}';")
        self.wait_for(self.SEL_ADD_BTN)
        try:
            self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    def _close_modal_if_open(self) -> None:
        try:
            if self.page.locator(self.SEL_MODAL_OPEN).count() > 0:
                self.click_attached(self.SEL_CANCEL_BTN)
                self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass

    def _dismiss_stale_confirm_modal(self) -> None:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="attached", timeout=self._TIMEOUT_STALE
            )
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    def _handle_confirm_modal(self) -> None:
        """추가/수정 후 나타나는 확인 모달 처리."""
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass
