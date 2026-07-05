"""
pages/npouch_tag_page.py — nPouch 태그 관리 페이지

공통설정 > 자원 관리 > 태그 관리
scan_mode: list_page
모달: div#addItemModal.modal-wrap.in  (동적 생성/제거 방식)
"""
import re

from pages.base_page import BasePage


class NpouchTagPage(BasePage):

    # 날짜본([AUTO_<MMDD>]) 매칭 — cleanup/가드 판별용 (2026-07-03 날짜본 전환)
    _AUTO_DATED = re.compile(r"^\[AUTO_(\d{4,8})\]")

    # ── 네비게이션 ────────────────────────────────────────────────
    SEL_SYS_MGMT_ICON   = "a[data-menuid='managerSystemManagement']"
    SEL_SYS_MGMT_LIST   = "ul.managerSystemManagementList"
    SEL_RESOURCE_HEADER = "a.managerResource"
    SEL_MENU_ITEM       = "a[data-menuid='managerGlobalProcessTag']"

    # ── 목록 버튼 ─────────────────────────────────────────────────
    SEL_ADD_BTN    = "button#addItemBtn"
    SEL_MODIFY_BTN = "button#modifyItemBtn"
    SEL_DELETE_BTN = "button#removeItemBtn"
    SEL_TABLE_ROW  = "table tbody tr"
    SEL_CHECKBOX   = "input[type='checkbox']"

    # ── 모달 ─────────────────────────────────────────────────────
    SEL_MODAL      = "div#addItemModal"
    SEL_MODAL_OPEN = "div#addItemModal.in"
    SEL_TAG_NAME   = "input#tagName"
    SEL_DESCRIPTION = "textarea#description"
    SEL_SUBMIT_BTN = "div#addItemModal button.btn-primary"
    SEL_CANCEL_BTN = "div#addItemModal button.btn-default"

    # ── 수정 모달 내 프로세스 관리 (+/-) ─────────────────────────
    SEL_TAG_ADD_PROC_BTN     = "div#addItemModal button#addItemBtn"    # + 버튼
    SEL_TAG_REMOVE_PROC_BTN  = "div#addItemModal button#removeItemBtn" # - 버튼
    SEL_PROC_TABLE_ROW       = "div#addItemModal table tbody tr"       # 등록된 프로세스 목록
    SEL_PROC_TABLE_CHECKBOX  = "div#addItemModal table tbody input[type='checkbox']"

    # ── 프로세스 선택 서브모달 (#globalProcessList) ──────────────
    SEL_PROC_MODAL        = "div#globalProcessList"
    SEL_PROC_MODAL_OPEN   = "div#globalProcessList.in"
    SEL_PROC_LIST_ROW     = "div#globalProcessList table tbody tr"
    SEL_PROC_LIST_CB      = "input[name='selectProcess']"
    SEL_PROC_LIST_ALL_CB  = "input#mainListHeaderCheckBox"
    SEL_PROC_LIST_CONFIRM = "div#globalProcessList button.btn-primary"
    # 프로세스 명 검색 — origin_protect 패턴 (id 변경 대응, fallback 다중)
    # 사용자 보고 2026-06-03: 옛 id 'searchNameText' DOM 에 없음 (제품 UI 변경)
    SEL_PROC_LIST_SEARCH  = (
        "div#globalProcessList input#searchText, "
        "div#globalProcessList input#searchNameText, "
        "div#globalProcessList input[type='search'], "
        "div#globalProcessList input[placeholder]"
    )
    # 검색 실행 버튼 — input 옆 돋보기. AngularJS — ng-model 만 update 시 적용 안 됨, 명시 클릭 필요
    SEL_PROC_LIST_SEARCH_BTN = (
        "div#globalProcessList button[ng-click*='search'], "
        "div#globalProcessList button.btn-search, "
        "div#globalProcessList i.fa-search, "
        "div#globalProcessList span.glyphicon-search"
    )

    # ── 확인 모달 (전역) ─────────────────────────────────────────
    SEL_CONFIRM_MODAL = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN   = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_MSG     = "#__globalMessageModal .modal-body"

    _TIMEOUT_TABLE = 5_000
    _TIMEOUT_MODAL = 5_000
    _TIMEOUT_STALE = 1_000

    _HASH_PAGE_SIZE = (
        "#!/managerGlobalProcessTag"
        "?pageNo=1&pageSize=100&searchText="
    )

    # ── 네비게이션 ────────────────────────────────────────────────

    def navigate_to(self) -> None:
        """태그 관리 페이지로 이동."""
        self._dismiss_stale_confirm_modal()
        self._close_modal_if_open()

        if ("GlobalProcessTag" in self.page.url
                and "pageSize=100" in self.page.url
                and self.is_visible(self.SEL_ADD_BTN)):
            return

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

    def _row_by_name(self, name: str):
        """이름 셀(td[0]) 정확 일치 행 반환(없으면 None) — 접두사 이름 충돌 방지.
        filter(has_text=) 부분 일치가 '[AUTO]_cm_tag' 로 '[AUTO]_cm_tag_sc1_detail' 행을
        잡는 오탐 발생(리포트 2026-07-03) → 전 행 조회를 정확 일치로 통일."""
        for r in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = r.locator("td").all()
            if tds and tds[0].inner_text().strip() == name:
                return r
        return None

    def get_item_names(self) -> list[str]:
        """현재 목록의 태그 이름 리스트 반환."""
        names = []
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = row.locator("td").all()
            # 실제 데이터 행은 최소 2열 이상 (1열짜리는 "검색된 내용이 없습니다." colspan 행)
            if len(tds) >= 2:
                name = tds[0].inner_text().strip()
                if name:
                    names.append(name)
        return names

    # ── CRUD ──────────────────────────────────────────────────────

    def add_item(self, name: str) -> None:
        """태그 추가. [AUTO]_ / [AUTO_KEEP]_ / [AUTO_<날짜>]_ 접두사 필수."""
        if not (name.startswith("[AUTO]_") or name.startswith("[AUTO_KEEP]_")
                or self._AUTO_DATED.match(name)):
            raise Exception("테스트 항목([AUTO]_/[AUTO_KEEP]_/[AUTO_<날짜>]_ 접두사)만 생성 가능합니다")

        self.open_add_modal()
        self.fill(self.SEL_TAG_NAME, name)
        self.click_attached(self.SEL_SUBMIT_BTN)
        self._handle_confirm_modal()
        self.wait_for(self.SEL_ADD_BTN)
        # 추가 후 행 노출 — [AUTO 계열은 공용 필터 유지(개별 이름 재검색 왕복 제거)
        if name.startswith("[AUTO"):
            self.ensure_auto_filter()
        else:
            self.search_item(name)

    def register_first_process(self, name: str) -> str:
        """이름으로 태그를 찾아 첫 번째 프로세스를 등록하고 저장. 등록된 프로세스 이름 반환."""
        self.open_modify_modal(name)
        self.open_process_list_modal()
        proc_name = self.select_first_process_in_modal()
        self.confirm_process_selection()
        self.click_attached(self.SEL_SUBMIT_BTN)
        self._handle_confirm_modal()
        self.wait_for(self.SEL_ADD_BTN)
        return proc_name

    def add_item_with_process(self, name: str) -> str:
        """태그 추가 후 첫 번째 프로세스 등록. [AUTO] 접두사 필수. 등록된 프로세스 이름 반환."""
        self.add_item(name)
        return self.register_first_process(name)

    def add_item_with_desc(self, name: str, desc: str) -> None:
        """태그 추가 (이름 + 설명). [AUTO]_ / [AUTO_KEEP]_ / [AUTO_<날짜>]_ 접두사 필수."""
        if not (name.startswith("[AUTO]_") or name.startswith("[AUTO_KEEP]_")
                or self._AUTO_DATED.match(name)):
            raise Exception("테스트 항목([AUTO]_/[AUTO_KEEP]_/[AUTO_<날짜>]_ 접두사)만 생성 가능합니다")

        self.open_add_modal()
        self.fill(self.SEL_TAG_NAME, name)
        self.page.locator(self.SEL_DESCRIPTION).first.evaluate(
            "(el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); }",
            desc
        )
        self.page.wait_for_timeout(150)
        self.click_attached(self.SEL_SUBMIT_BTN)
        self._handle_confirm_modal()
        self.wait_for(self.SEL_ADD_BTN)
        if name.startswith("[AUTO"):
            self.ensure_auto_filter()
        else:
            self.search_item(name)

    def delete_all_auto_items(self) -> None:
        """[AUTO]_ 접두사 태그 일괄 삭제 — [AUTO_KEEP]_* 는 보존.
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
        """clean slate — [AUTO]_ 휘발성 + [AUTO_KEEP]_ 레거시 + 날짜본([AUTO_<MMDD>], 오늘 포함) 전부 삭제.
        용도: 시나리오 시작(세션 1회) — 이전 세션 잔존 정리 (운용 프로세스와 동일 범위, 2026-07-03).
        참조 잠금 차단 시 사용처 제거 → 재삭제(강제 삭제), 실패 시에만 [AUTO]_DELME_ rename.
        """
        self.search_item("[AUTO")
        while True:
            names = [
                n for n in self.get_item_names()
                if (n.startswith("[AUTO]_") or n.startswith("[AUTO_KEEP]_")
                    or self._AUTO_DATED.match(n))
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
        """태그 삭제. [AUTO] 접두사 필수.
        _skip_search=True: 검색 단계 생략 (bulk cleanup 에서 사용).
        """
        if not (name.startswith("[AUTO]_") or name.startswith("[AUTO_KEEP]_")
                or self._AUTO_DATED.match(name)):
            raise Exception("테스트 항목([AUTO]_/[AUTO_KEEP]_/[AUTO_<날짜>]_ 접두사)만 삭제 가능합니다")

        if not _skip_search:
            # 행 노출 — [AUTO 계열은 공용 필터 유지(개별 이름 재검색 왕복 제거)
            if name.startswith("[AUTO"):
                self.ensure_auto_filter()
            else:
                self.search_item(name)
            self.page.wait_for_timeout(300)

        row = self._row_by_name(name)   # 정확 일치 — 접두사 이름 충돌 방지(2026-07-03)
        if row is None:
            raise Exception(f"행 없음(정확 일치): {name}")
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
        """수정 모달에서 태그 이름 변경 후 저장. cleanup 차단 시 [AUTO]_DELME_ 마킹용."""
        self.open_modify_modal(old_name)
        self.page.locator(self.SEL_TAG_NAME).first.fill(new_name)
        self.page.wait_for_timeout(150)
        self.click_attached(self.SEL_SUBMIT_BTN)
        self._handle_confirm_modal()
        self.wait_for(self.SEL_ADD_BTN)

    # ── 속성(태그 속성) 모달 — sc1/sc5/사용처 (직접조작 실측 2026-07-03) ──
    # 행 가운데(프로세스 카운트 셀) 더블클릭으로 열림. 구성: 태그 이름/설명 텍스트 +
    # 등록 프로세스 테이블(tbody#globalProcessTbBd: 프로세스명/서명/SHA2/설명) + '※ 사용처 확인'.
    SEL_DETAIL_MODAL = "div#detailGlobalTag.in"

    def open_detail_modal(self, name: str) -> None:
        """행 td[1] 합성 더블클릭 → '태그 속성'(읽기전용). 이름 대조 방어(운용 프로세스와 동일)."""
        row = None
        for r in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = r.locator("td").all()
            if tds and tds[0].inner_text().strip() == name:
                row = r
                break
        if row is None:
            raise Exception(f"행 없음: {name}")
        cell = row.locator("td").nth(1)
        det = self.page.locator(self.SEL_DETAIL_MODAL)
        for _ in range(3):
            cell.evaluate(
                "el => ['mousedown','mouseup','click','mousedown','mouseup','click','dblclick']"
                ".forEach(t => el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})))"
            )
            try:
                det.wait_for(state="attached", timeout=3000)
            except Exception:
                continue
            self.page.wait_for_timeout(300)
            if name in self.detail_modal_text():
                return
            self.close_detail_modal()
        raise Exception(f"속성 모달 열기 실패: {name}")

    def detail_modal_text(self) -> str:
        try:
            return self.page.locator("div#detailGlobalTag").first.inner_text().strip()
        except Exception:
            return ""

    def close_detail_modal(self) -> None:
        try:
            btn = self.page.locator("div#detailGlobalTag button", has_text="닫기").first
            btn.evaluate("el => el.click()")
            self.page.locator(self.SEL_DETAIL_MODAL).wait_for(
                state="detached", timeout=self._TIMEOUT_MODAL)
        except Exception:
            pass
        self.page.wait_for_timeout(200)

    def detail_registered_process_names(self) -> list[str]:
        """속성 모달 등록 프로세스 테이블(tbody#globalProcessTbBd)의 프로세스명 목록."""
        names = []
        for r in self.page.locator("div#detailGlobalTag tbody#globalProcessTbBd tr").all():
            tds = r.locator("td").all()
            if len(tds) >= 2:
                t = tds[1].inner_text().strip()
                if t:
                    names.append(t)
        return names

    def remove_all_usages(self, name: str) -> int:
        """속성 모달 '※사용처 확인'의 참조 chip(×) 전부 제거 — 참조 잠금 해제.
        운용 프로세스와 동일 chip 구조(usage-list-body / i.extentionDeleteBtn). 반환: 제거 수."""
        self.open_detail_modal(name)
        removed = 0
        try:
            for _ in range(20):
                chips = self.page.locator("div#detailGlobalTag i.extentionDeleteBtn")
                if chips.count() == 0:
                    break
                chips.first.evaluate("el => el.click()")
                self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                    state="attached", timeout=self._TIMEOUT_MODAL)
                self.click_attached(self.SEL_CONFIRM_BTN)
                self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                    state="detached", timeout=self._TIMEOUT_MODAL)
                self.page.wait_for_timeout(400)
                removed += 1
        finally:
            self.close_detail_modal()
        return removed

    # ── Import 업로드 모달 (직접조작 실측 2026-07-03: 네이티브 대화상자 아님) ──
    # importFileBtn 클릭 → div#addTagUpload 모달(input#addFile[type=file] + 파일추가/등록/취소)
    SEL_UPLOAD_MODAL = "div#addTagUpload.in"
    SEL_UPLOAD_FILE  = "div#addTagUpload input#addFile"

    def open_import_modal(self) -> None:
        self.page.locator("button#importFileBtn").first.evaluate("el => el.click()")
        self.page.locator(self.SEL_UPLOAD_MODAL).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL)
        self.page.wait_for_timeout(200)

    def upload_import_file(self, file_path: str) -> str:
        """열린 업로드 모달에 파일 지정 → '등록' 클릭 → 응답 모달 메시지 반환."""
        self.page.locator(self.SEL_UPLOAD_FILE).first.set_input_files(file_path)
        self.page.wait_for_timeout(300)
        btn = self.page.locator("div#addTagUpload button.btn-primary").first
        btn.evaluate("el => el.click()")
        self.page.wait_for_timeout(1000)
        msg = ""
        if self.is_confirm_modal_visible():
            msg = self.get_modal_message()
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_confirm_modal_closed()
        self.close_import_modal()
        return msg

    def close_import_modal(self) -> None:
        try:
            if self.page.locator(self.SEL_UPLOAD_MODAL).count() > 0:
                cancel = self.page.locator("div#addTagUpload button", has_text="취소").first
                cancel.evaluate("el => el.click()")
                self.page.locator(self.SEL_UPLOAD_MODAL).wait_for(
                    state="detached", timeout=self._TIMEOUT_MODAL)
        except Exception:
            pass
        self.page.wait_for_timeout(200)

    def ensure_auto_filter(self) -> None:
        """리스트를 '[AUTO' 프리픽스 검색 상태로 유지 — 이미 걸려 있으면 재검색 생략(운용 프로세스와 동일)."""
        try:
            cur = self.page.locator("input#searchText").first.input_value().strip()
        except Exception:
            cur = ""
        if cur != "[AUTO":
            self.search_item("[AUTO")

    def _delete_checked_row(self, name: str) -> str:
        """행 체크 → 삭제 → 1단계 confirm → 2단계 서버 응답 메시지 반환('' = 차단 없음)."""
        row = self._row_by_name(name)   # 정확 일치 — 접두사 이름 충돌 방지(2026-07-03)
        if row is None:
            raise Exception(f"행 없음(정확 일치): {name}")
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
        self.click_attached(self.SEL_CONFIRM_BTN)
        self.page.wait_for_timeout(700)
        msg2 = ""
        if self.page.locator(self.SEL_CONFIRM_MODAL).count() > 0:
            msg2 = self.page.locator(self.SEL_MODAL_MSG).first.inner_text().strip()
        return msg2

    def _delete_or_rename(self, name: str) -> str:
        """삭제 시도 → 참조 잠금 차단 시 사용처 참조 제거 후 재삭제(강제 삭제, 운용 프로세스 미러 2026-07-03).
        그래도 실패하면 [AUTO]_DELME_ rename (최후 fallback).
        반환: 'deleted' | 'force_deleted' | 'renamed'. cleanup 루프에서 검색 1회 후 호출 (_skip_search 전제).
        """
        msg2 = self._delete_checked_row(name)
        if ("할당" in msg2) or ("사용" in msg2) or ("참조" in msg2):
            self.click_attached(self.SEL_CONFIRM_BTN)
            try:
                self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                    state="detached", timeout=self._TIMEOUT_TABLE
                )
            except Exception:
                pass
            # 강제 삭제: 사용처 참조 전부 제거 후 재시도
            try:
                self.remove_all_usages(name)
                msg_retry = self._delete_checked_row(name)
                if not (("할당" in msg_retry) or ("사용" in msg_retry) or ("참조" in msg_retry)):
                    if msg_retry:
                        self.click_attached(self.SEL_CONFIRM_BTN)
                    self.wait_for(self.SEL_ADD_BTN)
                    return "force_deleted"
                self.click_attached(self.SEL_CONFIRM_BTN)
            except Exception:
                pass
            base = re.sub(r"^\[AUTO(_\d{4,8}|_KEEP)?\]_", "", name)
            self.rename_item(name, f"[AUTO]_DELME_{base}")
            return "renamed"
        if msg2:
            self.click_attached(self.SEL_CONFIRM_BTN)
        try:
            self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass
        return "deleted"

    def open_modify_modal(self, name: str) -> None:
        """행 선택 → 수정 버튼 클릭 → 모달 열림 대기."""
        # 행 노출 — [AUTO 계열은 공용 필터 유지(개별 이름 재검색 왕복 제거)
        if name.startswith("[AUTO"):
            self.ensure_auto_filter()
        else:
            self.search_item(name)
        self.page.wait_for_timeout(300)

        row = self._row_by_name(name)   # 정확 일치 — 접두사 이름 충돌 방지(2026-07-03)
        if row is None:
            raise Exception(f"행 없음(정확 일치): {name}")
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
        """수정 모달에서 description 변경 후 저장."""
        desc_loc = self.page.locator(self.SEL_DESCRIPTION).first
        desc_val = desc_loc.evaluate("el => el.value") or ""
        new_desc = "scan_mod_tag" if not desc_val else (desc_val + "_m")
        self.page.locator(self.SEL_DESCRIPTION).first.fill(new_desc)
        self.page.wait_for_timeout(150)
        self.click_attached(self.SEL_SUBMIT_BTN)
        self._handle_confirm_modal()
        self.wait_for(self.SEL_ADD_BTN)
        return {self.SEL_TAG_NAME: None}

    def get_verify_values(self, saved_name: str) -> dict:
        return {"input#tagName": saved_name}

    # ── 테스트 헬퍼 (public) ──────────────────────────────────────

    def open_add_modal(self) -> None:
        """추가 버튼 클릭 → 모달 열림 대기."""
        self.click(self.SEL_ADD_BTN)
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.page.wait_for_timeout(200)

    def close_modal(self) -> None:
        """취소 버튼으로 모달 닫기."""
        try:
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

    # ── 프로세스 등록/해제 (수정 모달 내) ────────────────────────

    def open_process_list_modal(self) -> None:
        """수정 모달 내 + 버튼 클릭 → 프로세스 선택 서브모달 열림 대기."""
        self.click_attached(self.SEL_TAG_ADD_PROC_BTN)
        self.page.locator(self.SEL_PROC_MODAL_OPEN).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.page.wait_for_timeout(300)

    def select_first_process_in_modal(self) -> str:
        """프로세스 선택 모달에서 첫 번째 프로세스 체크박스 선택 → 이름 반환."""
        rows = self.page.locator(self.SEL_PROC_LIST_ROW).all()
        if not rows:
            raise Exception("프로세스 선택 모달에 프로세스 없음")
        first_row = rows[0]
        proc_name = first_row.locator("td").nth(1).inner_text().strip()
        cb = first_row.locator("input[type='checkbox']").first
        self._toggle_overlay(False)
        try:
            cb.click()
        finally:
            self._toggle_overlay(True)
        return proc_name

    def select_process_by_name(self, name: str) -> str:
        """프로세스 선택 모달에서 이름으로 검색 후 정확히 일치하는 행 체크박스 선택.
        매칭 실패 시 모달 dismiss 후 raise.

        구현 주의사항:
          1. 검색어는 "[AUTO" 단축 — AUTO + AUTO_KEEP 둘 다 substring 매칭
          2. el.value + input 이벤트만으론 검색 실행 X (AngularJS ng-model 만 update)
             → 검색 버튼 클릭 또는 Enter keypress 필요
          3. fallback 첫 행 무조건 선택 금지 — 잘못된 프로세스 선택 방지
        """
        try:
            # 1. 검색어 입력 — "[AUTO" 단축 (사용자 권장 2026-06-04)
            search_input = self.page.locator(self.SEL_PROC_LIST_SEARCH)
            if search_input.count() > 0:
                search_input.first.evaluate(
                    "(el, v) => { el.value = v;"
                    " el.dispatchEvent(new Event('input',{bubbles:true}));"
                    " el.dispatchEvent(new Event('change',{bubbles:true})); }",
                    "[AUTO"
                )
                # 2. 검색 실행 — Enter keypress (AngularJS ng-submit/ng-keypress 호환)
                try:
                    search_input.first.press("Enter")
                except Exception:
                    pass
                # 3. 검색 버튼 클릭 시도 (Enter 미지원 케이스 대비)
                try:
                    btn = self.page.locator(self.SEL_PROC_LIST_SEARCH_BTN)
                    if btn.count() > 0:
                        btn.first.evaluate("el => el.click()")
                except Exception:
                    pass
                # 4. 결과 적용 대기 — 1252건 → 검색 결과로 줄어들 때까지
                try:
                    self.page.locator(self.SEL_PROC_LIST_ROW).filter(
                        has_text=name
                    ).first.wait_for(state="visible", timeout=3000)
                except Exception:
                    self.page.wait_for_timeout(1500)

            rows = self.page.locator(self.SEL_PROC_LIST_ROW).all()
            if not rows:
                raise Exception(
                    f"프로세스 선택 모달 빈 결과 (검색어: '[AUTO' / 찾는 name: {name!r})"
                )

            # 5. 이름 정확 일치 행 매칭 (fallback 없음)
            for row in rows:
                tds = row.locator("td").all()
                if len(tds) >= 2:
                    row_name = tds[1].inner_text().strip()
                    if row_name == name:
                        cb = row.locator("input[type='checkbox']").first
                        self._toggle_overlay(False)
                        try:
                            cb.click()
                        finally:
                            self._toggle_overlay(True)
                        return row_name

            # 6. 매칭 실패 — 진단 정보 + 모달 dismiss 후 raise
            visible_names = [
                row.locator("td").nth(1).inner_text().strip()
                for row in rows[:5]
            ]
            raise Exception(
                f"프로세스 정확 일치 매칭 실패: name={name!r} "
                f"(검색어 '[AUTO' / 결과 {len(rows)}건 / 상위 5건: {visible_names})"
            )
        except Exception:
            # 모달 dismiss — 후속 navigate 가능하도록
            try:
                close_btn = self.page.locator(
                    "div#globalProcessList button[data-dismiss='modal'], "
                    "div#globalProcessList button.close, "
                    "div#globalProcessList .modal-header button"
                )
                if close_btn.count() > 0:
                    close_btn.first.evaluate("el => el.click()")
                    self.page.wait_for_timeout(300)
            except Exception:
                pass
            raise

    def select_different_process_in_modal(self, exclude_name: str) -> str:
        """프로세스 선택 모달에서 프로세스 선택. 우선순위:
        1) [AUTO] 프로세스 검색 → 있으면 선택
        2) [AUTO] 없으면 exclude_name 이 아닌 첫 번째 프로세스 선택
        3) fallback: 첫 번째 항목 (중복 dedup 가능)
        선택된 프로세스 이름 반환."""

        def _click_row(row) -> str:
            proc_name = row.locator("td").nth(1).inner_text().strip()
            cb = row.locator("input[type='checkbox']").first
            self._toggle_overlay(False)
            try:
                cb.click()
            finally:
                self._toggle_overlay(True)
            return proc_name

        def _search_modal(keyword: str) -> None:
            """검색어 입력 + 검색 실행 (Enter + 버튼 클릭) + 결과 적용 대기."""
            try:
                si = self.page.locator(self.SEL_PROC_LIST_SEARCH)
                if si.count() > 0:
                    si.first.evaluate(
                        "(el, v) => { el.value = v;"
                        " el.dispatchEvent(new Event('input',{bubbles:true}));"
                        " el.dispatchEvent(new Event('change',{bubbles:true})); }",
                        keyword
                    )
                    # 검색 실행 — Enter
                    try:
                        si.first.press("Enter")
                    except Exception:
                        pass
                    # 검색 버튼 클릭 (fallback)
                    try:
                        btn = self.page.locator(self.SEL_PROC_LIST_SEARCH_BTN)
                        if btn.count() > 0:
                            btn.first.evaluate("el => el.click()")
                    except Exception:
                        pass
                    self.page.wait_for_timeout(800)
            except Exception:
                pass

        # 1순위: "[AUTO" 검색 (AUTO + AUTO_KEEP 둘 다 매칭)
        _search_modal("[AUTO")
        rows = self.page.locator(self.SEL_PROC_LIST_ROW).all()
        for row in rows:
            tds = row.locator("td").all()
            if len(tds) >= 2 and tds[1].inner_text().strip().startswith("[AUTO]_"):
                return _click_row(row)

        # 2순위: 검색 초기화 후 exclude_name 이 아닌 프로세스
        _search_modal("")
        rows = self.page.locator(self.SEL_PROC_LIST_ROW).all()
        if not rows:
            raise Exception("프로세스 선택 모달에 프로세스 없음")
        for row in rows:
            tds = row.locator("td").all()
            if len(tds) >= 2 and tds[1].inner_text().strip() != exclude_name:
                return _click_row(row)

        # fallback: 첫 번째 항목
        return _click_row(rows[0])

    def confirm_process_selection(self) -> None:
        """프로세스 선택 모달 확인 버튼 클릭 → 모달 닫힘 대기."""
        self.click_attached(self.SEL_PROC_LIST_CONFIRM)
        self.page.locator(self.SEL_PROC_MODAL_OPEN).wait_for(
            state="detached", timeout=self._TIMEOUT_TABLE
        )
        self.page.wait_for_timeout(200)

    def get_registered_process_names(self) -> list[str]:
        """수정 모달 내 등록된 프로세스 이름 목록 반환."""
        names = []
        for row in self.page.locator(self.SEL_PROC_TABLE_ROW).all():
            tds = row.locator("td").all()
            if len(tds) >= 2:
                name = tds[1].inner_text().strip()
                if name:
                    names.append(name)
        return names

    def remove_first_registered_process(self) -> None:
        """수정 모달 내 첫 번째 등록 프로세스 선택 → - 버튼 클릭."""
        rows = self.page.locator(self.SEL_PROC_TABLE_ROW).all()
        if not rows:
            raise Exception("등록된 프로세스 없음")
        cb = rows[0].locator("input[type='checkbox']").first
        self._toggle_overlay(False)
        try:
            cb.click()
        finally:
            self._toggle_overlay(True)
        self.page.wait_for_timeout(100)
        self.click_attached(self.SEL_TAG_REMOVE_PROC_BTN)
        self.page.wait_for_timeout(300)

    def get_process_count_in_list(self, tag_name: str) -> int:
        """목록 페이지에서 태그의 프로세스 카운트 컬럼 값 반환."""
        self.search_item(tag_name)
        self.page.wait_for_timeout(300)
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = row.locator("td").all()
            if len(tds) >= 2 and tds[0].inner_text().strip() == tag_name:
                try:
                    return int(tds[1].inner_text().strip())
                except ValueError:
                    return 0
        return -1  # 태그 없음

    def search_item(self, keyword: str) -> None:
        """키워드로 검색 실행."""
        search = self.page.locator("input#searchText").first
        search.fill(keyword)
        self.page.locator("button#searchBtn").first.evaluate("el => el.click()")
        self.page.wait_for_timeout(600)

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
