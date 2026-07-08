"""pages/secure_zone_template_process_page.py — 시큐어존 템플릿 관리 (프로세스 탭)

공통설정 > SecureZone > 템플릿 관리, 상단 탭 [프로세스] (selectedTab=PROCESS).
타입종속 4중 모달 — 4탭 중 구조 최복잡. 폴더동기화 페이지 미러 + 타입 하드매핑.
yaml: config/scan_hints/secure_zone_template_process*.yaml

[구조 — Chrome 직접조작 실측 2026-07-08, 192.168.13.141 (probe 4타입 생성→확인→삭제)]
- 리스트: 용도/템플릿 이름/프로세스 타입/프로세스·태그 카운트/상태/등록일/수정일
  ★이름 컬럼 = td[1] (td[0]=용도) — sync(td[0]=이름)와 다름.
  타입 필터: 전체/허용·거부·예외처리·실행차단 프로세스 (타입 컬럼 있어 변별 검증 가능).
- 1단계 모달 "시큐어존 프로세스 템플릿 추가/수정": templateName +
  szTemplateType radio 4종(ALLOW/DENY/EXCEPT/BLOCK_PROCESS, 기본 ALLOW) + status(CREATE/DELETE).
- 2단계 L2 div#addDeleteSecureZoneProcess "프로세스 추가/제거": 내부 탭 [개별 프로세스]/[태그]
  + addItemBtn(+)/removeItemBtn(-). 행 선택(tActive) → button#processAddDeleteBtn 로 진입.
- L3 타입종속 (★명명 불일치 — 하드매핑 필수, L3_MAP 참조):
  ALLOW → addModifySecureZoneAllowProcess (isProcessRestart)
  DENY  → addModifySecureZoneDenyProcess  (옵션 없음)
  EXCEPT→ addModifyExceptProcess (isSecureDriveWrite/isTakeoutDriveWrite radio + isProcessRestart)
          ★radio id #ALLOW/#BLOCK 이 두 name 그룹에 중복 → name 조합 셀렉터 필수
  BLOCK → addModifyBlockExecuteProcess (옵션 없음)
  공통: button#szProcessBtn(프로세스 선택/태그 탭에선 '태그 선택' — 같은 L3 재사용,
  picker=globalProcessList 공용) + textarea#description + status(CREATE/DELETE) + 추가/닫기.
- radio 는 evaluate click + checked 검증 후 저장 (probe 에서 .click() 미반영 사례 — 실측 교훈).

[명명/cleanup]
- [AUTO]_sz_proc... = 휘발성. [AUTO_<날짜>]_sz_proc... = 날짜본(영속·연계).
"""
import re

from pages.base_page import BasePage
from pages.shared._overlay import overlay_off
from pages.shared.pickers.process_picker import ProcessPicker


class SecureZoneTemplateProcessPage(BasePage):
    """시큐어존 템플릿 — 프로세스 탭 (타입종속 4중 모달)."""

    PAGE_ID = "secure_zone_template_process"
    AUTO_NAME_PREFIX = "[AUTO]_sz_proc"

    SEL_LEFT_NAV = "ul.leftNavList"

    # ── 목록 ──
    SEL_ADD_BTN            = "button#addItemBtn"
    SEL_MODIFY_BTN         = "button#modifyItemBtn"
    SEL_DELETE_BTN         = "button#removeItemBtn"
    SEL_COPY_BTN           = "button#copyItemBtn"
    SEL_PROC_ADD_DEL_BTN   = "button#processAddDeleteBtn"   # 프로세스 탭 전용 2단계 진입
    SEL_TABLE_ROW          = "table tbody tr"
    SEL_TABLE_ROW_ACTIVE   = "table tbody tr.tActive"
    SEL_CHECKBOX           = "input[type='checkbox']"
    SEL_SEARCH             = "input#searchText"
    SEL_FILTER_TYPE        = "select#szTemplateType"
    SEL_FILTER_STATUS      = "select#status"
    SEL_SEARCH_ICON        = ".fa-search"
    NAME_COL = 1   # ★이름 컬럼 인덱스 (td[0]=용도)

    # ── 1단계 모달 ──
    SEL_MODAL         = "div#addModifySecureZoneProcessTemplate.in"
    SEL_NAME          = "input#templateName"
    SEL_STATUS_CREATE = "div#addModifySecureZoneProcessTemplate.in input#CREATE"
    SEL_STATUS_DELETE = "div#addModifySecureZoneProcessTemplate.in input#DELETE"
    SEL_SAVE_ADD      = "div#addModifySecureZoneProcessTemplate.in button[addbtn]"
    SEL_SAVE_MODIFY   = "div#addModifySecureZoneProcessTemplate.in button[modifybtn]"
    SEL_SAVE_BTN      = "div#addModifySecureZoneProcessTemplate.in button:has-text('확인')"
    SEL_CLOSE_BTN     = ("div#addModifySecureZoneProcessTemplate.in button:has-text('닫기'), "
                         "div#addModifySecureZoneProcessTemplate.in button[data-dismiss='modal']")

    # 타입 radio (1단계) — 하드매핑 + 한국어 라벨
    TYPES = ["ALLOW_PROCESS", "DENY_PROCESS", "EXCEPT_PROCESS", "BLOCK_PROCESS"]
    TYPE_KO = {"ALLOW_PROCESS": "허용 프로세스", "DENY_PROCESS": "거부 프로세스",
               "EXCEPT_PROCESS": "예외처리 프로세스", "BLOCK_PROCESS": "실행차단 프로세스"}

    # ── 2단계 L2 모달 ──
    SEL_L2_MODAL    = "div#addDeleteSecureZoneProcess.in"
    SEL_L2_ADD_ITEM = "div#addDeleteSecureZoneProcess.in button#addItemBtn"     # +
    SEL_L2_DEL_ITEM = "div#addDeleteSecureZoneProcess.in button#removeItemBtn"  # -

    # ── L3 타입종속 하드매핑 (실측 2026-07-08 — 명명 불일치 주의) ──
    L3_MAP = {
        "ALLOW_PROCESS":  "addModifySecureZoneAllowProcess",
        "DENY_PROCESS":   "addModifySecureZoneDenyProcess",
        "EXCEPT_PROCESS": "addModifyExceptProcess",
        "BLOCK_PROCESS":  "addModifyBlockExecuteProcess",
    }
    # 타입별 전용 옵션 셀렉터(L3 스코프 내) — sc1 매핑 대조/EXCEPT 검증용
    L3_OPTIONS = {
        "ALLOW_PROCESS":  {"프로세스 재시작": "input#isProcessRestart"},
        "DENY_PROCESS":   {},
        "EXCEPT_PROCESS": {"프로세스 재시작": "input#isProcessRestart",
                           "시큐어드라이브 접근(허용)": "input[name='isSecureDriveWrite']#ALLOW",
                           "시큐어드라이브 접근(차단)": "input[name='isSecureDriveWrite']#BLOCK",
                           "반출드라이브 쓰기(허용)": "input[name='isTakeoutDriveWrite']#ALLOW",
                           "반출드라이브 쓰기(차단)": "input[name='isTakeoutDriveWrite']#BLOCK"},
        "BLOCK_PROCESS":  {},
    }
    SEL_L3_ANY = ", ".join(f"div#{mid}.in" for mid in L3_MAP.values())
    SEL_L3_DESC = "textarea#description"
    SEL_L3_PICK = "button#szProcessBtn"   # '프로세스 선택' / 태그 탭 '태그 선택'

    # ── 속성(상세정보 보기) — SD/특수폴더/폴더동기화와 모달 id 공유 ──
    SEL_DETAIL_MODAL = "div#detailSecureZoneTemplate.in"

    # ── 확인/경고 모달 ──
    SEL_CONFIRM_MODAL_OPENED = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN          = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_BODY_TEXT      = "div.modal-body-text"

    _TIMEOUT_TABLE = 5000
    _TIMEOUT_MODAL = 3000
    _TIMEOUT_STALE = 1000

    _AUTO_ANY = re.compile(r"^\[AUTO(_\d{4,8})?\]")

    _HASH_PROCESS = (
        "#!/managerSecureZoneTemplate"
        "?pageNo=1&pageSize=100&searchText=&selectedTab=PROCESS"
        "&szTemplateType=&status=&startIndex=0&sortIndex=0&sortOrder=0"
    )

    def __init__(self, page, settings):
        super().__init__(page, settings)
        self.picker = ProcessPicker(page)   # szProcessBtn → globalProcessList 공용 picker

    # ──────────────────────────────────────────────────────────────
    # 네비게이션 (탭 전환은 전체 goto — reloadOnSearch=false)
    # ──────────────────────────────────────────────────────────────
    def navigate_to_clean(self) -> None:
        """F5 + navigate — AngularJS 모달 상태 누적 정리(저널 리셋용, sync 동일 패턴)."""
        try:
            self.page.reload(wait_until="domcontentloaded", timeout=15000)
            self.page.wait_for_timeout(500)
        except Exception:
            pass
        self.navigate_to()

    def navigate_to(self) -> None:
        self._close_all_modals()
        self._dismiss_stale_confirm_modal()
        if (self.is_visible(self.SEL_ADD_BTN)
                and "managerSecureZoneTemplate" in self.page.url
                and "selectedTab=PROCESS" in self.page.url
                and "pageSize=100" in self.page.url):
            return
        self.page.goto(f"{self.host_origin}/manager/main.html{self._HASH_PROCESS}")
        self._dismiss_stale_confirm_modal()
        try:
            self.page.locator(self.SEL_LEFT_NAV).first.wait_for(
                state="visible", timeout=self._TIMEOUT_TABLE)
        except Exception:
            pass
        if not self.is_visible(self.SEL_LEFT_NAV):
            raise RuntimeError(
                "매니저 페이지 UI 없음 — 세션 만료 또는 접근 권한 없음.\npytest를 재실행해 주세요.")
        self.wait_for(self.SEL_ADD_BTN)
        try:
            self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE)
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # 목록 / 행 (★이름=td[1])
    # ──────────────────────────────────────────────────────────────
    def get_template_names(self) -> list[str]:
        names = []
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = row.locator("td")
            if tds.count() > self.NAME_COL:
                t = tds.nth(self.NAME_COL).inner_text().strip()
                if t and "없습니다" not in t:
                    names.append(t)
        return names

    def _row_locator(self, name: str):
        """이름 정확 일치(td[NAME_COL]) 행 — 부분 일치 오탐 방지."""
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = row.locator("td")
            if tds.count() > self.NAME_COL and tds.nth(self.NAME_COL).inner_text().strip() == name:
                return row
        return self.page.locator(self.SEL_TABLE_ROW).filter(has_text=name).first

    def row_type_text(self, name: str) -> str:
        """행의 '프로세스 타입' 컬럼 텍스트(td[2])."""
        try:
            return self._row_locator(name).locator("td").nth(2).inner_text().strip()
        except Exception:
            return ""

    def select_row(self, name: str) -> None:
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 조작 가능합니다")
        with overlay_off(self.page):
            self._row_locator(name).click(force=True)
        self.page.wait_for_timeout(200)

    def check_row(self, name: str) -> None:
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 조작 가능합니다")
        cb = self._row_locator(name).locator(self.SEL_CHECKBOX).first
        if cb.is_checked():
            return
        self._toggle_overlay(False)
        try:
            cb.click()
        finally:
            self._toggle_overlay(True)
        if not cb.is_checked():
            raise Exception(f"체크박스 클릭 후 미체크: {name}")

    # ──────────────────────────────────────────────────────────────
    # 삭제 / cleanup (검색-우선)
    # ──────────────────────────────────────────────────────────────
    def _delete_matching(self, pred) -> None:
        for name in [n for n in self.get_template_names() if pred(n)]:
            self.delete_template(name)

    def delete_all_test_data(self) -> None:
        try:
            self.search("[AUTO")
            self._delete_matching(lambda n: self._AUTO_ANY.match(n))
        finally:
            self.search("")
        self._delete_matching(lambda n: self._AUTO_ANY.match(n))

    def delete_all_auto(self) -> None:
        try:
            self.search("[AUTO]")
            self._delete_matching(lambda n: n.startswith("[AUTO]"))
        finally:
            self.search("")
        self._delete_matching(lambda n: n.startswith("[AUTO]"))

    def delete_template(self, name: str) -> None:
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 조작 가능합니다")

        def _attempt():
            self.check_row(name)
            self.click(self.SEL_DELETE_BTN)
            if not self.is_confirm_modal_visible():
                raise Exception("삭제 버튼 클릭 후 모달 없음")
            msg = self.get_modal_message()
            if "하시겠습니까" not in msg:
                self.click_attached(self.SEL_CONFIRM_BTN)
                self.wait_for_modal_closed()
                raise Exception(f"삭제 중 에러 모달: {msg!r}")
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
            self.wait_for(self.SEL_ADD_BTN)

        try:
            _attempt()
        except Exception as e:
            print(f"\n[delete_template] 1차 실패: {e}\nnavigate_to() 후 재시도...")
            self.navigate_to()
            _attempt()

    # ──────────────────────────────────────────────────────────────
    # 1단계 모달
    # ──────────────────────────────────────────────────────────────
    def open_add_modal(self) -> None:
        self.click(self.SEL_ADD_BTN)
        self.wait_for(self.SEL_MODAL, state="attached")

    def close_modal(self) -> None:
        self.click(self.SEL_CLOSE_BTN)
        self.wait_for(self.SEL_ADD_BTN)

    def _close_modal_if_open(self) -> None:
        try:
            if self.page.locator(self.SEL_MODAL).count() > 0:
                self.click(self.SEL_CLOSE_BTN)
                self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass

    def open_modify_modal(self, name: str) -> None:
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 조작 가능합니다")
        self.select_row(name)
        self.click(self.SEL_MODIFY_BTN)
        self.wait_for(self.SEL_MODAL, state="attached")

    def select_type(self, ttype: str) -> None:
        """1단계 타입 radio 선택 — evaluate click + checked 검증(probe 미반영 사례 교훈)."""
        loc = self.page.locator(f"{self.SEL_MODAL} input#{ttype}").first
        loc.evaluate("el => el.click()")
        self.page.wait_for_timeout(150)
        if not loc.is_checked():
            loc.evaluate("el => { el.checked = true; el.dispatchEvent(new Event('change',{bubbles:true})); }")

    def create_template(self, name: str, ttype: str = "ALLOW_PROCESS") -> str:
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 생성 가능합니다")
        self.open_add_modal()
        self.fill(f"{self.SEL_MODAL} {self.SEL_NAME}", name)
        if ttype != "ALLOW_PROCESS":
            self.select_type(ttype)
        return self.submit_and_message()

    def ensure_template(self, name: str, ttype: str = "ALLOW_PROCESS") -> None:
        if name not in self.get_template_names():
            self.create_template(name, ttype)
            self.navigate_to()

    # ──────────────────────────────────────────────────────────────
    # 2단계 L2 / L3 (타입종속)
    # ──────────────────────────────────────────────────────────────
    def open_l2_modal(self, name: str) -> None:
        """행 선택(tActive) → 프로세스 추가/제거(L2)."""
        self.select_row(name)
        self.click(self.SEL_PROC_ADD_DEL_BTN)
        self.wait_for(self.SEL_L2_MODAL, state="attached")

    def close_l2_modal(self) -> None:
        for _ in range(4):
            modals = self.page.locator(self.SEL_L2_MODAL)
            if modals.count() == 0:
                return
            top = modals.last
            try:
                with overlay_off(self.page):
                    top.locator("button", has_text="닫기").first.click(force=True, timeout=2000)
            except Exception:
                try:
                    top.evaluate("el => el.classList.remove('in')")
                except Exception:
                    pass
            self.page.wait_for_timeout(300)

    def switch_l2_tab(self, tab_label: str) -> None:
        """L2 내부 탭 전환 — '개별 프로세스' | '태그'."""
        self.page.locator(self.SEL_L2_MODAL).last.locator(
            "li a", has_text=tab_label).first.evaluate("el => el.click()")
        self.page.wait_for_timeout(400)

    def open_l3_add(self, ttype: str) -> None:
        """L2 '+' → 타입종속 L3 모달 (하드매핑 id 로 대기)."""
        self.page.locator(self.SEL_L2_ADD_ITEM).last.evaluate("el => el.click()")
        self.wait_for(f"div#{self.L3_MAP[ttype]}.in", state="attached")

    def l3_scope(self, ttype: str):
        return self.page.locator(f"div#{self.L3_MAP[ttype]}.in")

    def close_l3_modal(self, ttype: str) -> None:
        try:
            with overlay_off(self.page):
                self.l3_scope(ttype).locator("button", has_text="닫기").first.click(
                    force=True, timeout=2000)
            self.page.locator(f"div#{self.L3_MAP[ttype]}.in").wait_for(
                state="detached", timeout=self._TIMEOUT_MODAL)
        except Exception:
            pass

    def l3_pick_first(self, ttype: str, mode: str = "single") -> str:
        """L3 '프로세스 선택'(태그 탭 '태그 선택') → 공용 picker 첫 행 선택+확인."""
        self.l3_scope(ttype).locator(self.SEL_L3_PICK).first.evaluate("el => el.click()")
        self.picker.wait_open()
        return self.picker.select_first_and_confirm(mode=mode)

    def l3_add_message(self, ttype: str) -> str:
        """L3 '추가' 클릭 → 경고 메시지 반환+dismiss(''=커밋). 알림 캡처가 필요한 흐름은
        테스트에서 클릭/대기/dismiss 를 분리(저널 행위)해서 사용."""
        with overlay_off(self.page):
            self.l3_scope(ttype).locator("button", has_text="추가").first.click(force=True)
        self.page.wait_for_timeout(500)
        msg = ""
        if self.is_confirm_modal_visible():
            try:
                msg = self.get_modal_message()
            except Exception:
                msg = ""
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        return msg

    def l2_item_count(self) -> int:
        """L2 현재 탭의 등록 행 수(체크박스 있는 tr)."""
        modals = self.page.locator(self.SEL_L2_MODAL)
        if modals.count() == 0:
            return 0
        return modals.last.locator("tbody tr:has(input[type='checkbox'])").count()

    def l2_remove_item(self, index: int = 0) -> str:
        row = self.page.locator(
            f"{self.SEL_L2_MODAL} tbody tr:has(input[type='checkbox'])").nth(index)
        row.locator("input[type='checkbox']").first.evaluate("el => el.click()")
        self.page.locator(self.SEL_L2_DEL_ITEM).first.evaluate("el => el.click()")
        msg = ""
        if self.is_confirm_modal_visible():
            msg = self.get_modal_message()
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        return msg

    # ── 복사 / 검색 / 필터 ──────────────────────────────────────────
    def copy_template(self, name: str) -> str:
        self.check_row(name)
        self.click(self.SEL_COPY_BTN)
        msg = ""
        if self.is_confirm_modal_visible():
            msg = self.get_modal_message()
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
            self.wait_for(self.SEL_ADD_BTN)
        return msg

    def search(self, term: str) -> None:
        self.fill(self.SEL_SEARCH, term)
        self.page.locator(self.SEL_SEARCH).first.press("Enter")
        self.page.wait_for_timeout(700)

    def filter_by(self, template_type: str = None, status: str = None) -> None:
        def _set(sel, label):
            self.page.locator(sel).evaluate(
                "(el,v)=>{const o=[...el.options].find(x=>x.textContent.trim()===v); "
                "if(o){el.value=o.value; el.dispatchEvent(new Event('change',{bubbles:true}));}}", label)
        if template_type is not None:
            _set(self.SEL_FILTER_TYPE, template_type)
        if status is not None:
            _set(self.SEL_FILTER_STATUS, status)
        self.page.locator(self.SEL_SEARCH_ICON).first.evaluate("el => (el.closest('button,a')||el).click()")
        self.page.wait_for_timeout(900)

    def list_type_values(self) -> list[str]:
        """리스트 각 행의 '프로세스 타입'(td[2]) 텍스트 — 필터 변별 검증용."""
        vals = []
        for r in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = r.locator("td")
            if tds.count() > 2:
                t = tds.nth(2).inner_text().strip()
                if t:
                    vals.append(t)
        return vals

    # ── 속성 모달 (sc5) ────────────────────────────────────────────
    def open_detail_modal(self, name: str) -> None:
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 조작 가능합니다")
        cell = self._row_locator(name).locator("td").nth(2)
        det = self.page.locator(self.SEL_DETAIL_MODAL)
        for _ in range(3):
            cell.evaluate(
                "el => ['mousedown','mouseup','click','mousedown','mouseup','click','dblclick']"
                ".forEach(t => el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})))"
            )
            try:
                det.wait_for(state="attached", timeout=4000)
                self.page.wait_for_timeout(400)
                if name in det.first.inner_text():
                    return
                self.close_detail_modal()
            except Exception:
                self.page.wait_for_timeout(300)
        raise Exception(f"속성 모달이 열리지 않음(3회 재시도 실패): {name}")

    def detail_modal_text(self) -> str:
        return self.page.locator(self.SEL_DETAIL_MODAL).first.inner_text()

    def close_detail_modal(self) -> None:
        try:
            self.page.locator(f"{self.SEL_DETAIL_MODAL} button", has_text="닫기").first.evaluate(
                "el => el.click()")
            self.page.locator(self.SEL_DETAIL_MODAL).wait_for(
                state="detached", timeout=self._TIMEOUT_MODAL)
        except Exception:
            pass

    # ── 헬퍼 ───────────────────────────────────────────────────────
    def column_headers(self) -> list[str]:
        return [h.inner_text().strip()
                for h in self.page.locator("table thead th").all()
                if h.inner_text().strip()]

    def field_present(self, selector: str) -> bool:
        return self.page.locator(selector).count() > 0

    def type_real(self, selector: str, text: str) -> int:
        loc = self.page.locator(selector).first
        with overlay_off(self.page):
            loc.click(force=True)
        loc.fill("")
        loc.press_sequentially(text, delay=2)
        self.page.wait_for_timeout(150)
        return len(loc.input_value())

    def _click_save(self) -> None:
        for sel in (self.SEL_SAVE_MODIFY, self.SEL_SAVE_ADD):
            loc = self.page.locator(sel).first
            try:
                if loc.count() > 0 and loc.is_visible():
                    loc.evaluate("el => el.click()")
                    return
            except Exception:
                pass
        self.page.locator(self.SEL_SAVE_BTN).first.evaluate("el => el.click()")

    def submit_and_message(self) -> str:
        self._click_save()
        self.page.wait_for_timeout(600)
        msg = ""
        if self.is_confirm_modal_visible():
            try:
                msg = self.get_modal_message()
            except Exception:
                msg = ""
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        if (self.page.locator(self.SEL_ADD_BTN).count() > 0
                and self.page.locator(self.SEL_MODAL).count() == 0):
            self.wait_for(self.SEL_ADD_BTN)
        return msg

    def _close_all_modals(self) -> None:
        for _ in range(6):
            modals = self.page.locator(".modal-wrap.in, .modal.in")
            if modals.count() == 0:
                return
            top = modals.last
            clicked = False
            for label in ("닫기", "취소", "확인"):
                btn = top.locator(f"button:has-text('{label}')")
                if btn.count() > 0:
                    try:
                        with overlay_off(self.page):
                            btn.first.click(force=True, timeout=2000)
                        clicked = True
                        break
                    except Exception:
                        pass
            if not clicked:
                try:
                    top.evaluate("el => el.classList.remove('in')")
                except Exception:
                    pass
            self.page.wait_for_timeout(300)

    def get_modal_message(self) -> str:
        return self.page.locator(self.SEL_MODAL_BODY_TEXT).first.inner_text().strip()

    def is_confirm_modal_visible(self) -> bool:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL)
            return True
        except Exception:
            return False

    def wait_for_modal_closed(self) -> None:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE)
        except Exception:
            pass

    def _dismiss_stale_confirm_modal(self) -> None:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_STALE)
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        except Exception:
            pass
