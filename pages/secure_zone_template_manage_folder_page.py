"""pages/secure_zone_template_manage_folder_page.py — 시큐어존 템플릿 관리 (특수폴더 탭)

공통설정 > SecureZone > 템플릿 관리, 상단 탭 [특수폴더] (selectedTab=MANAGE_FOLDER).
시큐어 드라이브 탭과 동일 list_page + 2단계(행 선택 → 폴더 추가/제거 → 용도별 내용 모달).
yaml: config/scan_hints/secure_zone_template_manage_folder.yaml

[구조 — Chrome MCP 직접조작 실측 2026-06-30, 192.168.13.141 v11.1.0.172]
- 1단계 모달 addModifySecureZoneManageFolderTemplate: 이름 + 용도(SHORTCUT/MODIFY_REGIST) + 상태(CREATE=활성/DELETE=비활성)
- 2단계: 행 선택(tActive) → folderAddDeleteBtn → addDeleteSecureZoneManageFolder(폴더 목록, +/- /Example/Import)
  → + → 용도별 내용 모달(SHORTCUT=addModifySecureZoneShortcut / MODIFY_REGIST=addModifySecureZoneModifyRegist)
- 내용 모달 공통: 설정명(manageFolderName) / 원본·대상위치(folderSourcePath/folderTargetPath, contenteditable div) / 설명(description) / 상태
  + 원본/대상 옆 '특수폴더' picker(예약어 selectReservedWordControl, 일반 예약어 11)
- 모달 = div#id.in (실제 class 'modal-wrap in'), 닫으면 DOM 에서 제거(동적).
- ★관리자 전용 예약어([/RUN/]·[/DSEC/] 등) 입력 시 비밀번호 인증 게이팅 — 인증/암호화/복호화는 테스트 제외(user-driven).

[명명/cleanup — 날짜본 통일]
- [AUTO]_sz_mf... = 휘발성(cleanup 대상). [AUTO_<날짜>]_sz_mf... = 날짜본(영속·연계, delete_all_auto 보존).
"""
import re

from pages.base_page import BasePage
from pages.shared._overlay import overlay_off


class SecureZoneTemplateManageFolderPage(BasePage):
    """시큐어존 템플릿 — 특수폴더 탭 (방식 B)."""

    PAGE_ID = "secure_zone_template_manage_folder"
    AUTO_NAME_PREFIX = "[AUTO]_sz_mf"

    # ── 네비게이션 (전체 goto — 탭 전환 위해 fresh boot, hash-set 은 reloadOnSearch=false 로 탭 미전환) ──
    SEL_LEFT_NAV = "ul.leftNavList"

    # ── 목록 ──
    SEL_ADD_BTN            = "button#addItemBtn"
    SEL_MODIFY_BTN         = "button#modifyItemBtn"
    SEL_DELETE_BTN         = "button#removeItemBtn"
    SEL_COPY_BTN           = "button#copyItemBtn"
    SEL_FOLDER_ADD_DEL_BTN = "button#folderAddDeleteBtn"   # 특수폴더 탭 전용 2단계 진입
    SEL_TABLE_ROW          = "table tbody tr"
    SEL_TABLE_ROW_ACTIVE   = "table tbody tr.tActive"
    SEL_CHECKBOX           = "input[type='checkbox']"
    SEL_SEARCH             = "input#searchText"

    # ── 1단계 모달 ──
    SEL_MODAL         = "div#addModifySecureZoneManageFolderTemplate.in"
    SEL_NAME          = "input#templateName"
    SEL_TYPE_SHORTCUT = "div#addModifySecureZoneManageFolderTemplate.in input#SHORTCUT"
    SEL_TYPE_REGIST   = "div#addModifySecureZoneManageFolderTemplate.in input#MODIFY_REGIST"
    SEL_STATUS_CREATE = "div#addModifySecureZoneManageFolderTemplate.in input#CREATE"
    SEL_STATUS_DELETE = "div#addModifySecureZoneManageFolderTemplate.in input#DELETE"
    SEL_SAVE_BTN      = "div#addModifySecureZoneManageFolderTemplate.in button:has-text('확인')"
    # 저장: 추가='확인'(addbtn) / 수정='수정'(modifybtn) — 같은 모달 id, 모드별 표시 토글
    SEL_SAVE_ADD      = "div#addModifySecureZoneManageFolderTemplate.in button[addbtn]"
    SEL_SAVE_MODIFY   = "div#addModifySecureZoneManageFolderTemplate.in button[modifybtn]"
    SEL_CLOSE_BTN     = ("div#addModifySecureZoneManageFolderTemplate.in button:has-text('닫기'), "
                         "div#addModifySecureZoneManageFolderTemplate.in button[data-dismiss='modal']")

    # ── 2단계 폴더 모달 ──
    SEL_FOLDER_MODAL    = "div#addDeleteSecureZoneManageFolder.in"
    SEL_FOLDER_ADD_ITEM = "div#addDeleteSecureZoneManageFolder.in button#addItemBtn"     # +
    SEL_FOLDER_DEL_ITEM = "div#addDeleteSecureZoneManageFolder.in button#removeItemBtn"  # -
    SEL_FOLDER_CLOSE    = "div#addDeleteSecureZoneManageFolder.in button:has-text('닫기')"

    # ── 내용 모달 (용도별) ──
    SEL_CONTENT_SHORTCUT = "div#addModifySecureZoneShortcut.in"
    SEL_CONTENT_REGIST   = "div#addModifySecureZoneModifyRegist.in"
    SEL_CONTENT_ANY      = "div#addModifySecureZoneShortcut.in, div#addModifySecureZoneModifyRegist.in"
    SEL_C_NAME    = "input#manageFolderName"
    SEL_C_SOURCE  = "div#folderSourcePath"      # contenteditable div
    SEL_C_TARGET  = "div#folderTargetPath"      # contenteditable div
    SEL_C_DESC    = "textarea#description"
    # 레지스트리(MODIFY_REGIST) 전용 — 바로가기엔 없음. 기본 숨김(관리자 예약어/암호화 시 노출). 존재(count)로 구조 차이 확인.
    SEL_C_DESC_RUN    = "div#addModifySecureZoneModifyRegist.in textarea#descriptionRun"
    SEL_C_RUN_PW      = "div#addModifySecureZoneModifyRegist.in input#runPassword"
    SEL_C_LICENSE_PW  = "div#addModifySecureZoneModifyRegist.in input#licensePwd"

    # ── 예약어 picker (특수폴더 버튼) ──
    SEL_PICKER_MODAL    = "div#selectReservedWordControl.in"
    SEL_PICKER_CHECKBOX = "div#selectReservedWordControl.in input[name='selectReservedWord']"
    SEL_PICKER_CONFIRM  = "div#selectReservedWordControl.in button:has-text('확인')"

    # ── 확인/경고 모달 ──
    SEL_CONFIRM_MODAL_OPENED = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN          = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_BODY_TEXT      = "div.modal-body-text"

    _TIMEOUT_TABLE = 5000
    _TIMEOUT_MODAL = 3000
    _TIMEOUT_STALE = 1000

    _AUTO_ANY = re.compile(r"^\[AUTO(_\d{4,8})?\]")

    _HASH_MANAGE_FOLDER = (
        "#!/managerSecureZoneTemplate"
        "?pageNo=1&pageSize=100&searchText=&selectedTab=MANAGE_FOLDER"
        "&szTemplateType=&status=&startIndex=0&sortIndex=0&sortOrder=0"
    )

    # ──────────────────────────────────────────────────────────────
    # 네비게이션
    # ──────────────────────────────────────────────────────────────
    def navigate_to(self) -> None:
        """템플릿 관리 > 특수폴더 탭 (selectedTab=MANAGE_FOLDER, pageSize=100).

        ⚠️ hash-set 만으론 탭 전환 안 됨 — AngularJS reloadOnSearch=false 라 쿼리(selectedTab)만 바뀌면
        컨트롤러를 재로드하지 않아 뷰가 직전 탭(기본 SECURE_DRIVE)에 머문다(URL 은 MANAGE_FOLDER).
        그러면 #addItemBtn 이 시큐어드라이브 모달을 열어 manage folder 모달 대기가 타임아웃(실측 2026-06-30).
        → 전체 goto 로 fresh boot 하면 selectedTab=MANAGE_FOLDER + pageSize=100 이 한 번에 resolve 되어 탭이 정확히 잡힌다."""
        self._close_all_modals()
        self._dismiss_stale_confirm_modal()

        if (self.is_visible(self.SEL_ADD_BTN)
                and "managerSecureZoneTemplate" in self.page.url
                and "selectedTab=MANAGE_FOLDER" in self.page.url
                and "pageSize=100" in self.page.url):
            return

        self.page.goto(f"{self.host_origin}/manager/main.html{self._HASH_MANAGE_FOLDER}")
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
    # 목록 / 행
    # ──────────────────────────────────────────────────────────────
    def get_template_names(self) -> list[str]:
        names = []
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            dn = row.get_attribute("data-name")
            if dn:
                names.append(dn)
                continue
            texts = [td.inner_text().strip() for td in row.locator("td").all()]
            name = next((t for t in texts if t), "")
            if name:
                names.append(name)
        return names

    def _row_locator(self, name: str, active: bool = False):
        sel = self.SEL_TABLE_ROW_ACTIVE if active else self.SEL_TABLE_ROW
        safe = name.replace("\\", "\\\\").replace('"', '\\"')
        exact = self.page.locator(f'{sel}[data-name="{safe}"]')
        try:
            if exact.count() > 0:
                return exact.first
        except Exception:
            pass
        return self.page.locator(sel).filter(has_text=name).first

    def select_row(self, name: str) -> None:
        """행 활성화(tActive) — 실제 클릭(force) 필요(el.click()은 tActive 미반응)."""
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
    # 삭제 / cleanup (방식 B 라이프사이클)
    # ──────────────────────────────────────────────────────────────
    def delete_all_test_data(self) -> None:
        """[AUTO] + [AUTO_<날짜>] 둘 다 삭제 — sc1 시작 clean slate."""
        for name in [n for n in self.get_template_names() if self._AUTO_ANY.match(n)]:
            self.delete_template(name)

    def delete_all_auto(self) -> None:
        """[AUTO] (날짜 없음) 만 삭제, [AUTO_<날짜>] 날짜본 보존 — sc5/sc6."""
        for name in [n for n in self.get_template_names() if n.startswith("[AUTO]")]:
            self.delete_template(name)

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
    # 1단계 모달 열기/닫기
    # ──────────────────────────────────────────────────────────────
    def open_add_modal(self) -> None:
        self.click(self.SEL_ADD_BTN)
        try:
            self.wait_for(self.SEL_MODAL, state="attached")
        except Exception as e:
            raise Exception(f"템플릿 추가 모달이 열리지 않음: {e}") from e

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

    def select_template_type(self, ttype: str) -> None:
        """1단계 용도 라디오 선택 — 'SHORTCUT'(바로가기) / 'MODIFY_REGIST'(레지스트리)."""
        sel = self.SEL_TYPE_REGIST if ttype == "MODIFY_REGIST" else self.SEL_TYPE_SHORTCUT
        with overlay_off(self.page):
            self.page.locator(sel).first.click(force=True)

    def create_template(self, name: str, ttype: str = "SHORTCUT") -> str:
        """1단계 템플릿 생성 — 이름+용도 → '확인'. 반환=메시지(성공/경고)."""
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 생성 가능합니다")
        self.open_add_modal()
        self.fill(f"{self.SEL_MODAL} {self.SEL_NAME}", name)
        if ttype == "MODIFY_REGIST":
            self.select_template_type("MODIFY_REGIST")
        return self.submit_and_message()

    def ensure_template(self, name: str, ttype: str = "SHORTCUT") -> None:
        if name not in self.get_template_names():
            self.create_template(name, ttype)
            self.navigate_to()

    # ──────────────────────────────────────────────────────────────
    # 2단계 폴더 모달 / 용도별 내용 모달
    # ──────────────────────────────────────────────────────────────
    def open_folder_modal(self, name: str) -> None:
        """행 선택(tActive) → 폴더 추가/제거 → 특수폴더 추가/제거 모달."""
        self.select_row(name)
        self.click(self.SEL_FOLDER_ADD_DEL_BTN)
        self.wait_for(self.SEL_FOLDER_MODAL, state="attached")

    def close_folder_modal(self) -> None:
        """폴더 모달 전부 닫기(루프) — 스테일 모달 누적 방지.
        하나만 닫으면 div#addDeleteSecureZoneManageFolder.in 이 남아 재오픈 시 2개 공존 → 읽기가 엉뚱한 모달을 봄(실측 2026-07-01)."""
        for _ in range(4):
            modals = self.page.locator(self.SEL_FOLDER_MODAL)
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

    def open_content_add(self) -> None:
        """폴더 모달 '+' → 용도별 내용 모달(SHORTCUT/REGIST). 최상단(현재) 폴더 모달의 + JS 직접 클릭."""
        self.page.locator(self.SEL_FOLDER_ADD_ITEM).last.evaluate("el => el.click()")
        self.wait_for(self.SEL_CONTENT_ANY, state="attached")

    def content_modal_id(self) -> str:
        """현재 열린 내용 모달 종류 반환: 'SHORTCUT' / 'MODIFY_REGIST' / ''."""
        if self.page.locator(self.SEL_CONTENT_SHORTCUT).count() > 0:
            return "SHORTCUT"
        if self.page.locator(self.SEL_CONTENT_REGIST).count() > 0:
            return "MODIFY_REGIST"
        return ""

    def set_content_path(self, selector: str, value: str) -> None:
        """원본/대상위치(contenteditable div) 값 설정 — textContent + Angular 바인딩 이벤트."""
        self.page.locator(selector).first.evaluate(
            "(el,v)=>{el.focus(); el.textContent=v; "
            "['input','keyup','change','blur'].forEach(t=>el.dispatchEvent(new Event(t,{bubbles:true})));}",
            value)

    def _content_loc(self):
        """현재 열린 내용 모달(SHORTCUT/REGIST) locator — 콤마 union '>>' 대신 안전 분기."""
        sc = self.page.locator(self.SEL_CONTENT_SHORTCUT)
        if sc.count() > 0:
            return sc.first
        return self.page.locator(self.SEL_CONTENT_REGIST).first

    def _content_btn(self, text: str):
        return self._content_loc().locator("button", has_text=text).first

    def close_content_modal(self) -> None:
        try:
            with overlay_off(self.page):
                self._content_btn("닫기").click(force=True, timeout=2000)
            self.page.locator(self.SEL_CONTENT_ANY).wait_for(state="detached", timeout=self._TIMEOUT_MODAL)
        except Exception:
            pass

    def content_add_message(self) -> str:
        """내용 모달 '추가' 클릭 → 경고 메시지 반환 + dismiss. 성공이면 ''(커밋 후 모달 닫힘)."""
        with overlay_off(self.page):
            self._content_btn("추가").click(force=True)
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

    # ── 예약어 picker / 폴더 매핑 추가·제거 (sc3 동작) ──────────────────
    def pick_path(self, which: str, index: int = 0) -> None:
        """원본/대상위치를 예약어 picker 로 채움. which='source'(첫 특수폴더)|'target'(둘째). index=예약어 행."""
        btn = self._content_loc().locator("button", has_text="특수폴더").nth(0 if which == "source" else 1)
        btn.evaluate("el => el.click()")
        self.wait_for(self.SEL_PICKER_MODAL, state="attached")
        self.page.locator(f"{self.SEL_PICKER_MODAL} tbody tr").nth(index).locator(
            "input[type='checkbox']").first.evaluate("el => el.click()")
        self.page.locator(self.SEL_PICKER_CONFIRM).first.evaluate("el => el.click()")
        self.page.locator(self.SEL_PICKER_MODAL).wait_for(state="detached", timeout=self._TIMEOUT_MODAL)

    def add_folder_mapping(self, setting_name: str, source: str = None, target: str = None,
                           use_picker: bool = True, src_index: int = 0, tgt_index: int = 1,
                           description: str = None) -> str:
        """내용 모달에서 폴더 매핑 입력 → '추가'. 반환=경고('' 성공=커밋).
        use_picker: 예약어 picker 로 원본/대상 채움 / False 면 source·target 문자열 직접(contenteditable).
        description: 설명(maxlength 없음) — 오버플로 검증 등에 사용."""
        self.fill(self.SEL_C_NAME, setting_name)
        if use_picker:
            self.pick_path("source", src_index)
            self.pick_path("target", tgt_index)
        else:
            self.set_content_path(self.SEL_C_SOURCE, source)
            self.set_content_path(self.SEL_C_TARGET, target)
        if description is not None:
            self.fill(self.SEL_C_DESC, description)   # 설명은 maxlength 없음 → fill 무방
        return self.content_add_message()

    def type_real(self, selector: str, text: str) -> int:
        """실제 per-key 타이핑(press_sequentially) → 실제 수용 길이 반환 (maxlength clamp 검증).
        ⚠️ fill() 은 maxlength 무시(value 직접 설정)라 clamp 검증 불가 → press_sequentially. overlay OFF + force click 후 타이핑."""
        loc = self.page.locator(selector).first
        with overlay_off(self.page):
            loc.click(force=True)
        loc.fill("")
        loc.press_sequentially(text, delay=2)
        self.page.wait_for_timeout(150)
        return len(loc.input_value())

    def folder_item_count(self) -> int:
        """폴더 모달에 커밋된 항목 수(데이터 행 = 체크박스 있는 tr). 최상단(현재) 모달 기준."""
        modals = self.page.locator(self.SEL_FOLDER_MODAL)
        if modals.count() == 0:
            return 0
        return modals.last.locator("tbody tr:has(input[type='checkbox'])").count()

    def folder_row_values(self, setting_name: str) -> list[str]:
        """폴더 모달에서 설정명으로 행 찾아 셀 텍스트 목록 반환(저장값 대조용). 없으면 [].
        최상단(현재) 모달로 스코프 + 재오픈 시 행 async 로딩 대기(스테일 모달·타이밍 둘 다 대응)."""
        modals = self.page.locator(self.SEL_FOLDER_MODAL)
        if modals.count() == 0:
            return []
        row = modals.last.locator("tbody tr", has_text=setting_name).first
        try:
            row.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
        except Exception:
            return []
        return [c.inner_text().strip() for c in row.locator("td").all() if c.inner_text().strip()]

    def remove_folder_item(self, index: int = 0) -> str:
        """폴더 항목 선택(체크) + '-' → 확인 모달 메시지 반환 + 확인(제거)."""
        row = self.page.locator(f"{self.SEL_FOLDER_MODAL} tbody tr:has(input[type='checkbox'])").nth(index)
        row.locator("input[type='checkbox']").first.evaluate("el => el.click()")
        self.page.locator(self.SEL_FOLDER_DEL_ITEM).first.evaluate("el => el.click()")
        msg = ""
        if self.is_confirm_modal_visible():
            msg = self.get_modal_message()
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        return msg

    # ── 복사 / 검색 (list-level, sc3) ──────────────────────────────────
    def copy_template(self, name: str) -> str:
        """템플릿 선택(체크) + '복사' → 확인 모달 메시지 반환 + 확인. 결과는 '<name>_copy'."""
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
        """이름 검색 — input#searchText 입력 + Enter."""
        self.fill(self.SEL_SEARCH, term)
        self.page.locator(self.SEL_SEARCH).first.press("Enter")
        self.page.wait_for_timeout(700)

    # ──────────────────────────────────────────────────────────────
    # 헬퍼
    # ──────────────────────────────────────────────────────────────
    def column_headers(self) -> list[str]:
        return [h.inner_text().strip()
                for h in self.page.locator("table thead th").all()
                if h.inner_text().strip()]

    def field_present(self, selector: str) -> bool:
        return self.page.locator(selector).count() > 0

    def _click_save(self) -> None:
        """1단계 저장 — 추가='확인'(addbtn) / 수정='수정'(modifybtn) 중 visible 한 것 JS 직접 클릭."""
        for sel in (self.SEL_SAVE_MODIFY, self.SEL_SAVE_ADD):
            loc = self.page.locator(sel).first
            try:
                if loc.count() > 0 and loc.is_visible():
                    loc.evaluate("el => el.click()")
                    return
            except Exception:
                pass
        self.page.locator(self.SEL_SAVE_BTN).first.evaluate("el => el.click()")  # fallback

    def submit_and_message(self) -> str:
        """1단계 '확인'(저장) → 확인/경고 모달 메시지 반환 + dismiss. 성공 시 목록 복귀."""
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
