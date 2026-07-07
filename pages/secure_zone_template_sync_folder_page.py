"""pages/secure_zone_template_sync_folder_page.py — 시큐어존 템플릿 관리 (폴더동기화 탭)

공통설정 > SecureZone > 템플릿 관리, 상단 탭 [폴더동기화] (selectedTab=SYNC_FOLDER).
특수폴더(manage_folder) 탭과 동일 list_page + 2단계(행 선택 → 폴더 추가/제거 → 내용 모달).
yaml: config/scan_hints/secure_zone_template_sync_folder.yaml

[구조 — Chrome 직접조작 실측 2026-07-07, 192.168.13.141]
- 1단계 모달 addModifySecureZoneSyncFolderTemplate "시큐어존 폴더동기화 템플릿 추가/수정":
  templateName + szTemplateType=SYNC_FOLDER(단일, 용도 분기 없음) + status(CREATE=활성/INACTIVE=비활성)
- 2단계: 행 선택(tActive) → syncFolderAddDeleteBtn → addDeleteSecureZoneSyncFolder(폴더 목록, +/-)
  → + → 내용 모달 addModifySecureZoneSyncFolder "폴더동기화 폴더 추가/수정" (4탭 중 최다 필드)
- 내용 모달: syncFolderName / sourcePath·destinationPath(contenteditable div, '특수폴더' picker)
  / 확장자 포함·제외(isExtensionInclude radio + extensionIncludes textarea + isExtensionIncludeHeaderCheck)
  / syncFolderScheduleType(NONE/MINUTES/DAYS/WEEKS) — 조건부 필드 트리거
  / executeHour·executeMinute·minutes·days·checkSun~checkSat(요일)
  / isOriginRemoveSchedule·isRealTime·isOriginRemoveRealtime·isRemoveFolder·isStartAutoSchedule
  / fileLimitSize / description / status(CREATE/DELETE)
- syncFolderScheduleType 조건부 노출(실측): NONE=없음 / MINUTES=minutes / DAYS=executeHour·Minute+days
  / WEEKS=executeHour·Minute+checkSun~Sat. isRealTime 등·fileLimitSize·description 은 항상 노출.
- 원본/대상 '특수폴더' picker = selectReservedWordControl(예약어), specialFolderBtn.
- 관리자 예약어 인증/암호화/복호화는 테스트 제외(user-driven).

[명명/cleanup — 날짜본 통일]
- [AUTO]_sz_sync... = 휘발성(cleanup 대상). [AUTO_<날짜>]_sz_sync... = 날짜본(영속·연계, delete_all_auto 보존).
"""
import re

from pages.base_page import BasePage
from pages.shared._overlay import overlay_off


class SecureZoneTemplateSyncFolderPage(BasePage):
    """시큐어존 템플릿 — 폴더동기화 탭 (특수폴더 페이지 미러)."""

    PAGE_ID = "secure_zone_template_sync_folder"
    AUTO_NAME_PREFIX = "[AUTO]_sz_sync"

    SEL_LEFT_NAV = "ul.leftNavList"

    # ── 목록 ──
    SEL_ADD_BTN            = "button#addItemBtn"
    SEL_MODIFY_BTN         = "button#modifyItemBtn"
    SEL_DELETE_BTN         = "button#removeItemBtn"
    SEL_COPY_BTN           = "button#copyItemBtn"
    SEL_FOLDER_ADD_DEL_BTN = "button#syncFolderAddDeleteBtn"   # 폴더동기화 탭 전용 2단계 진입
    SEL_TABLE_ROW          = "table tbody tr"
    SEL_TABLE_ROW_ACTIVE   = "table tbody tr.tActive"
    SEL_CHECKBOX           = "input[type='checkbox']"
    SEL_SEARCH             = "input#searchText"
    SEL_FILTER_TYPE        = "select#szTemplateType"    # 전체/폴더 동기화
    SEL_FILTER_STATUS      = "select#status"            # 상태/활성/비활성
    SEL_SEARCH_ICON        = ".fa-search"

    # ── 1단계 모달 ──
    SEL_MODAL         = "div#addModifySecureZoneSyncFolderTemplate.in"
    SEL_NAME          = "input#templateName"
    SEL_STATUS_CREATE = "div#addModifySecureZoneSyncFolderTemplate.in input#CREATE"
    SEL_STATUS_INACTIVE = "div#addModifySecureZoneSyncFolderTemplate.in input#INACTIVE"
    SEL_SAVE_ADD      = "div#addModifySecureZoneSyncFolderTemplate.in button[addbtn]"
    SEL_SAVE_MODIFY   = "div#addModifySecureZoneSyncFolderTemplate.in button[modifybtn]"
    SEL_SAVE_BTN      = "div#addModifySecureZoneSyncFolderTemplate.in button:has-text('확인')"
    SEL_CLOSE_BTN     = ("div#addModifySecureZoneSyncFolderTemplate.in button:has-text('닫기'), "
                         "div#addModifySecureZoneSyncFolderTemplate.in button[data-dismiss='modal']")

    # ── 2단계 폴더 모달 ──
    SEL_FOLDER_MODAL    = "div#addDeleteSecureZoneSyncFolder.in"
    SEL_FOLDER_ADD_ITEM = "div#addDeleteSecureZoneSyncFolder.in button#addItemBtn"     # +
    SEL_FOLDER_DEL_ITEM = "div#addDeleteSecureZoneSyncFolder.in button#removeItemBtn"  # -
    SEL_FOLDER_CLOSE    = "div#addDeleteSecureZoneSyncFolder.in button:has-text('닫기')"

    # ── 내용 모달 (단일) ──
    SEL_CONTENT       = "div#addModifySecureZoneSyncFolder.in"
    SEL_C_NAME        = "input#syncFolderName"
    SEL_C_SOURCE      = "div#sourcePath"          # contenteditable div
    SEL_C_TARGET      = "div#destinationPath"     # contenteditable div
    SEL_C_EXT_INCLUDE = "input[name='isExtensionInclude']"   # radio ×2 (포함/제외)
    SEL_C_EXT_LIST    = "textarea#extensionIncludes"
    SEL_C_EXT_HEADER  = "input#isExtensionIncludeHeaderCheck"
    SEL_C_SCHEDULE    = "select#syncFolderScheduleType"      # NONE/MINUTES/DAYS/WEEKS
    SEL_C_EXEC_HOUR   = "select#executeHour"
    SEL_C_EXEC_MIN    = "select#executeMinute"
    SEL_C_MINUTES     = "input#minutes"
    SEL_C_DAYS        = "input#days"
    SEL_C_FILE_LIMIT  = "input#fileLimitSize"
    SEL_C_DESC        = "textarea#description"
    SEL_C_REALTIME    = "input#isRealTime"
    SEL_C_REMOVE_FOLDER   = "input#isRemoveFolder"
    SEL_C_START_AUTO      = "input#isStartAutoSchedule"
    SEL_C_ORIGIN_RM_SCHED = "input#isOriginRemoveSchedule"
    SEL_C_ORIGIN_RM_REAL  = "input#isOriginRemoveRealtime"
    SEL_C_STATUS_CREATE   = "div#addModifySecureZoneSyncFolder.in input#CREATE"
    SEL_C_STATUS_DELETE   = "div#addModifySecureZoneSyncFolder.in input#DELETE"
    SEL_C_WEEKDAYS = ["input#checkSun", "input#checkMon", "input#checkTue", "input#checkWed",
                      "input#checkThu", "input#checkFri", "input#checkSat"]

    # 스케줄 타입별 노출 필드(실측 2026-07-07) — sc2 조건부 검증용
    SCHEDULE_VISIBLE = {
        "NONE":    [],
        "MINUTES": [SEL_C_MINUTES],
        "DAYS":    [SEL_C_EXEC_HOUR, SEL_C_EXEC_MIN, SEL_C_DAYS],
        "WEEKS":   [SEL_C_EXEC_HOUR, SEL_C_EXEC_MIN] + SEL_C_WEEKDAYS,
    }
    SCHEDULE_HIDDEN_ALL = ([SEL_C_MINUTES, SEL_C_DAYS, SEL_C_EXEC_HOUR, SEL_C_EXEC_MIN] + SEL_C_WEEKDAYS)

    # 리포트 표시용 한국어 라벨 (DOM 값은 영어라 불변 — 표시만 한국어 통일)
    SCHEDULE_KO = {"NONE": "없음", "MINUTES": "매분", "DAYS": "매일", "WEEKS": "매주"}
    FIELD_KO = {
        SEL_C_EXEC_HOUR: "실행 시각(시)", SEL_C_EXEC_MIN: "실행 시각(분)",
        SEL_C_MINUTES: "분 주기", SEL_C_DAYS: "일 주기",
        "input#checkSun": "요일:일", "input#checkMon": "요일:월", "input#checkTue": "요일:화",
        "input#checkWed": "요일:수", "input#checkThu": "요일:목",
        "input#checkFri": "요일:금", "input#checkSat": "요일:토",
    }

    def sched_ko(self, value: str) -> str:
        """스케줄 타입 영어 값 → 한국어 라벨 (리포트 표시용)."""
        return self.SCHEDULE_KO.get(value, value)

    def fields_ko(self, selectors) -> list:
        """셀렉터 목록 → 한국어 필드명 목록 (리포트 표시용)."""
        return [self.FIELD_KO.get(s, s) for s in selectors]

    # ── 예약어 picker (특수폴더 버튼) ──
    SEL_PICKER_MODAL    = "div#selectReservedWordControl.in"
    SEL_PICKER_CHECKBOX = "div#selectReservedWordControl.in input[name='selectReservedWord']"
    SEL_PICKER_CONFIRM  = "div#selectReservedWordControl.in button:has-text('확인')"

    # ── 속성(상세정보 보기) 모달 — sc5 (SD/특수폴더와 동일 모달 id 재사용) ──
    SEL_DETAIL_MODAL      = "div#detailSecureZoneTemplate.in"
    SEL_ITEM_DETAIL_MODAL = "div#viewDetailItemModal.in"

    # ── 확인/경고 모달 ──
    SEL_CONFIRM_MODAL_OPENED = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN          = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_BODY_TEXT      = "div.modal-body-text"

    _TIMEOUT_TABLE = 5000
    _TIMEOUT_MODAL = 3000
    _TIMEOUT_STALE = 1000

    _AUTO_ANY = re.compile(r"^\[AUTO(_\d{4,8})?\]")

    _HASH_SYNC_FOLDER = (
        "#!/managerSecureZoneTemplate"
        "?pageNo=1&pageSize=100&searchText=&selectedTab=SYNC_FOLDER"
        "&szTemplateType=&status=&startIndex=0&sortIndex=0&sortOrder=0"
    )

    # ──────────────────────────────────────────────────────────────
    # 네비게이션 (특수폴더와 동일 — hash-set 만으론 탭 미전환, 전체 goto)
    # ──────────────────────────────────────────────────────────────
    def navigate_to(self) -> None:
        self._close_all_modals()
        self._dismiss_stale_confirm_modal()

        if (self.is_visible(self.SEL_ADD_BTN)
                and "managerSecureZoneTemplate" in self.page.url
                and "selectedTab=SYNC_FOLDER" in self.page.url
                and "pageSize=100" in self.page.url):
            return

        self.page.goto(f"{self.host_origin}/manager/main.html{self._HASH_SYNC_FOLDER}")
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
    # 삭제 / cleanup
    # ──────────────────────────────────────────────────────────────
    def _delete_matching(self, pred) -> None:
        for name in [n for n in self.get_template_names() if pred(n)]:
            self.delete_template(name)

    def delete_all_test_data(self) -> None:
        """[AUTO] + [AUTO_<날짜>] 둘 다 삭제 — sc1 시작 clean slate. '[AUTO' 검색 후 삭제 + 잔여 fallback."""
        try:
            self.search("[AUTO")
            self._delete_matching(lambda n: self._AUTO_ANY.match(n))
        finally:
            self.search("")
        self._delete_matching(lambda n: self._AUTO_ANY.match(n))

    def delete_all_auto(self) -> None:
        """[AUTO] (날짜 없음) 만 삭제, [AUTO_<날짜>] 보존 — sc5/sc6."""
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

    def open_modify_modal(self, name: str) -> None:
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 조작 가능합니다")
        self.select_row(name)
        self.click(self.SEL_MODIFY_BTN)
        self.wait_for(self.SEL_MODAL, state="attached")

    def create_template(self, name: str) -> str:
        """1단계 템플릿 생성 — 이름 입력 → '확인'(폴더동기화는 용도 분기 없음). 반환=메시지."""
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 생성 가능합니다")
        self.open_add_modal()
        self.fill(f"{self.SEL_MODAL} {self.SEL_NAME}", name)
        return self.submit_and_message()

    def ensure_template(self, name: str) -> None:
        if name not in self.get_template_names():
            self.create_template(name)
            self.navigate_to()

    # ──────────────────────────────────────────────────────────────
    # 2단계 폴더 모달 / 내용 모달
    # ──────────────────────────────────────────────────────────────
    def open_folder_modal(self, name: str) -> None:
        self.select_row(name)
        self.click(self.SEL_FOLDER_ADD_DEL_BTN)
        self.wait_for(self.SEL_FOLDER_MODAL, state="attached")

    def close_folder_modal(self) -> None:
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
        """폴더 모달 '+' → 내용 모달(addModifySecureZoneSyncFolder)."""
        self.page.locator(self.SEL_FOLDER_ADD_ITEM).last.evaluate("el => el.click()")
        self.wait_for(self.SEL_CONTENT, state="attached")

    def close_content_modal(self) -> None:
        try:
            with overlay_off(self.page):
                self.page.locator(self.SEL_CONTENT).locator("button", has_text="닫기").first.click(
                    force=True, timeout=2000)
            self.page.locator(self.SEL_CONTENT).wait_for(state="detached", timeout=self._TIMEOUT_MODAL)
        except Exception:
            pass

    def set_content_path(self, selector: str, value: str) -> None:
        """원본/대상위치(contenteditable div) 값 설정 — textContent + Angular 바인딩 이벤트."""
        self.page.locator(selector).first.evaluate(
            "(el,v)=>{el.focus(); el.textContent=v; "
            "['input','keyup','change','blur'].forEach(t=>el.dispatchEvent(new Event(t,{bubbles:true})));}",
            value)

    def pick_path(self, which: str, index: int = 0) -> None:
        """원본/대상위치를 예약어 picker 로 채움. which='source'(첫 특수폴더)|'target'(둘째)."""
        btn = self.page.locator(self.SEL_CONTENT).locator(
            "button", has_text="특수폴더").nth(0 if which == "source" else 1)
        btn.evaluate("el => el.click()")
        self.wait_for(self.SEL_PICKER_MODAL, state="attached")
        self.page.locator(f"{self.SEL_PICKER_MODAL} tbody tr").nth(index).locator(
            "input[type='checkbox']").first.evaluate("el => el.click()")
        self.page.locator(self.SEL_PICKER_CONFIRM).first.evaluate("el => el.click()")
        self.page.locator(self.SEL_PICKER_MODAL).wait_for(state="detached", timeout=self._TIMEOUT_MODAL)

    # ── 스케줄 조건부 (실측 2026-07-07) ──────────────────────────────
    def set_schedule_type(self, value: str) -> None:
        """syncFolderScheduleType 설정(NONE/MINUTES/DAYS/WEEKS) + change 이벤트로 조건부 필드 재렌더."""
        self.page.locator(self.SEL_C_SCHEDULE).first.evaluate(
            "(el,v)=>{el.value=v; el.dispatchEvent(new Event('change',{bubbles:true}));}", value)
        self.page.wait_for_timeout(300)

    def field_visible(self, selector: str) -> bool:
        """내용 모달 안 필드가 실제 노출(display/visibility)인지 — 조건부 검증용."""
        loc = self.page.locator(selector).first
        try:
            if loc.count() == 0:
                return False
            return loc.is_visible()
        except Exception:
            return False

    def add_folder_mapping(self, setting_name: str, use_picker: bool = True,
                           src_index: int = 0, tgt_index: int = 1,
                           schedule: str = "NONE", description: str = None) -> str:
        """내용 모달에서 폴더동기화 매핑 입력 → '추가'. 반환=경고('' 성공)."""
        self.fill(self.SEL_C_NAME, setting_name)
        if use_picker:
            self.pick_path("source", src_index)
            self.pick_path("target", tgt_index)
        if schedule and schedule != "NONE":
            self.set_schedule_type(schedule)
        if description is not None:
            self.fill(self.SEL_C_DESC, description)
        return self.content_add_message()

    def content_add_message(self) -> str:
        """내용 모달 '추가' 클릭 → 경고 반환 + dismiss. 성공이면 ''(커밋 후 닫힘)."""
        with overlay_off(self.page):
            self.page.locator(self.SEL_CONTENT).locator("button", has_text="추가").first.click(force=True)
        self.page.wait_for_timeout(500)
        return self._dismiss_and_message()

    def content_save_message(self) -> str:
        """내용 모달 저장('수정'|'추가' 존재하는 것) → 경고 반환 + dismiss. sc4 수정용."""
        loc = self.page.locator(self.SEL_CONTENT)
        btn = loc.locator("button", has_text="수정")
        if btn.count() == 0:
            btn = loc.locator("button", has_text="추가")
        with overlay_off(self.page):
            btn.first.click(force=True)
        self.page.wait_for_timeout(500)
        return self._dismiss_and_message()

    def _dismiss_and_message(self) -> str:
        msg = ""
        if self.is_confirm_modal_visible():
            try:
                msg = self.get_modal_message()
            except Exception:
                msg = ""
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        return msg

    def open_folder_item_edit(self, setting_name: str) -> None:
        """폴더모달에서 '설정명' 링크(a) 클릭 → 내용 모달(로드값 + 저장='수정')."""
        modals = self.page.locator(self.SEL_FOLDER_MODAL)
        if modals.count() == 0:
            raise Exception("폴더 모달이 열려있지 않음")
        row = modals.last.locator("tbody tr", has_text=setting_name).first
        row.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
        row.locator("a").first.evaluate("el => el.click()")
        self.wait_for(self.SEL_CONTENT, state="attached")

    def type_real(self, selector: str, text: str) -> int:
        """실제 per-key 타이핑 → 수용 길이 반환 (maxlength clamp 검증)."""
        loc = self.page.locator(selector).first
        with overlay_off(self.page):
            loc.click(force=True)
        loc.fill("")
        loc.press_sequentially(text, delay=2)
        self.page.wait_for_timeout(150)
        return len(loc.input_value())

    def folder_item_count(self) -> int:
        modals = self.page.locator(self.SEL_FOLDER_MODAL)
        if modals.count() == 0:
            return 0
        return modals.last.locator("tbody tr:has(input[type='checkbox'])").count()

    def folder_row_values(self, setting_name: str) -> list[str]:
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
        row = self.page.locator(f"{self.SEL_FOLDER_MODAL} tbody tr:has(input[type='checkbox'])").nth(index)
        row.locator("input[type='checkbox']").first.evaluate("el => el.click()")
        self.page.locator(self.SEL_FOLDER_DEL_ITEM).first.evaluate("el => el.click()")
        msg = ""
        if self.is_confirm_modal_visible():
            msg = self.get_modal_message()
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        return msg

    # ── 복사 / 검색 / 필터 (list-level) ──────────────────────────────
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

    def list_column_values(self, col_index: int) -> list[str]:
        vals = []
        for r in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = r.locator("td")
            if tds.count() > col_index:
                t = tds.nth(col_index).inner_text().strip()
                if t:
                    vals.append(t)
        return vals

    # ──────────────────────────────────────────────────────────────
    # 속성(상세정보 보기) 모달 — sc5
    # ──────────────────────────────────────────────────────────────
    def open_detail_modal(self, name: str) -> None:
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 조작 가능합니다")
        cell = self._row_locator(name).locator("td").nth(1)
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
