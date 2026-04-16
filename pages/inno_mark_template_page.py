"""
pages/inno_mark_template_page.py — innoMark 템플릿 관리 페이지 조작

모달 ID: div#addInnoMarkTemplateControl (class: modal-wrap in)

[조건부 가시성 — Chrome MCP 확인 (2026-04-14)]
  항상 표시:
    input#imTemplateName, input#textSize, radio textSizeType,
    input#textColor, input#textDegree, table#splitScreenLocationType

  imTemplateType=TEXT 일 때만 표시 (div#displayTextType):
    div#textLetter (contenteditable, 필수), input#isTextLetterQrcode

  imTemplateType=IMAGE 일 때만 표시 (div#displayImageType):
    input#imageName (read-only), input#imageWidth, div#imageBottomText (contenteditable)

  imTemplateUseType=DISPLAY 일 때만 표시:
    input#isTextOutline (div#displayTextOutline)
    input#waterMarkOpacity (div#displayWaterMarkOpacity)

버튼:
  - 확인(ADD): div#addInnoMarkTemplateControl button.btn-primary.btn-sm:has-text("확인")
  - 수정(EDIT): div#addInnoMarkTemplateControl button.btn-primary.btn-sm:has-text("수정")
  - 닫기: div#addInnoMarkTemplateControl button.btn-default.btn-sm
"""
from pages.base_page import BasePage


class InnoMarkTemplatePage(BasePage):
    # ------------------------------------------------------------------
    # Selectors
    # ------------------------------------------------------------------

    # 메뉴 네비게이션
    SEL_LEFT_NAV           = "ul.leftNavList"
    SEL_APP_SETTING_MENU   = "a[data-menuid='managerAppSetting']"
    SEL_APP_SETTING_PANEL  = "ul.managerAppSettingList"
    SEL_IM_SECTION_HEADER  = "a.managerInnoMark"
    SEL_IM_TEMPLATE_MENU   = "a[data-menuid='managerInnoMarkTemplate']"

    # 목록
    SEL_TABLE_ROW          = "table tbody tr"
    SEL_TABLE_ROW_ACTIVE   = "table tbody tr.tActive"
    SEL_CHECKBOX           = "input[type='checkbox']"

    # 버튼 (목록 페이지)
    SEL_ADD_BTN            = "button#addItemBtn"
    SEL_MODIFY_BTN         = "button#modifyItemBtn"
    SEL_DELETE_BTN         = "button#removeItemBtn"
    SEL_SEARCH_INPUT       = "input#searchText"

    # 모달 컨테이너
    SEL_ADD_MODAL          = "div#addInnoMarkTemplateControl.in"

    # 모달 내부 — 기본 필드 (.in 범위 한정으로 중복 DOM 간섭 방지)
    SEL_TEMPLATE_NAME      = "div#addInnoMarkTemplateControl.in input#imTemplateName"

    # 모달 하단 버튼 — .in 범위로 한정 (동일 ID 모달 중복 DOM 간섭 방지)
    SEL_REGISTER_BTN       = "div#addInnoMarkTemplateControl.in button.btn-primary.btn-sm:has-text('확인')"
    SEL_SAVE_BTN           = "div#addInnoMarkTemplateControl.in button.btn-primary.btn-sm:has-text('수정')"
    SEL_CLOSE_BTN          = "div#addInnoMarkTemplateControl.in button.btn-default.btn-sm"

    # 예약어 버튼 (TEXT 모드 전용 — .in 스코프로 숨겨진 복사본 오작동 방지)
    SEL_RESERVED_WORD_BTN    = "div#addInnoMarkTemplateControl.in button#selectTextReservedWordBtn"

    # 예약어 선택 모달 (예약어 버튼 클릭 시 열리는 별도 모달)
    # [주의] Playwright 환경에서 Bootstrap .in 클래스 애니메이션이 적용 안 될 수 있음
    # → .in 없이 ID만으로 스코프, 컨텐츠(tr) 존재 여부로 열림 판단
    SEL_RESERVED_WORD_MODAL        = "div#selectReservedWordControl"
    SEL_RESERVED_WORD_ROW          = "div#selectReservedWordControl tr[contents-list-item]"
    SEL_RESERVED_WORD_NAME         = "span[name='reservedWordName']"
    SEL_RESERVED_WORD_CONFIRM_BTN  = "div#selectReservedWordControl button.btn-primary"

    # 확인 모달 (공통)
    SEL_CONFIRM_MODAL        = "div#__globalMessageModal"
    SEL_CONFIRM_MODAL_OPENED = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN          = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_BODY_TEXT      = "div.modal-body-text"

    # ------------------------------------------------------------------
    # 타임아웃 상수
    # ------------------------------------------------------------------
    _TIMEOUT_TABLE = 5000
    _TIMEOUT_MODAL = 3000
    _TIMEOUT_STALE = 1000

    _HASH_PAGE_SIZE_100 = (
        "#!/managerInnoMarkTemplate"
        "?pageNo=1&pageSize=100&searchText=&startIndex=0&sortIndex=0&sortOrder=0"
    )

    # ------------------------------------------------------------------
    # 네비게이션
    # ------------------------------------------------------------------
    def navigate_to(self) -> None:
        """
        innoMark 템플릿 관리 페이지로 이동.
        1. 잔여 모달 닫기
        2. 이미 템플릿 페이지 + pageSize=100이면 즉시 반환
        3. 매니저 루트로 goto
        4. App Setting → innoMark 섹션 → 템플릿 관리 순서로 클릭
        """
        self._close_modal_if_open()
        self._dismiss_stale_confirm_modal()

        if (self.is_visible(self.SEL_ADD_BTN)
                and "InnoMarkTemplate" in self.page.url
                and "pageSize=100" in self.page.url):
            return

        if "manager/main.html" not in self.page.url:
            self.page.goto(f"{self.host_origin}/manager/main.html")
            self._dismiss_stale_confirm_modal()

        try:
            self.page.locator(self.SEL_LEFT_NAV).first.wait_for(
                state="visible", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass
        if not self.is_visible(self.SEL_LEFT_NAV):
            raise RuntimeError(
                "매니저 페이지 UI 없음 — 세션 만료 또는 접근 권한 없음.\n"
                "pytest를 재실행해 주세요."
            )

        if not self.is_visible(self.SEL_APP_SETTING_PANEL):
            self.click(self.SEL_APP_SETTING_MENU)
            self.wait_for(self.SEL_APP_SETTING_PANEL)

        if not self.is_visible(self.SEL_IM_TEMPLATE_MENU):
            self.click(self.SEL_IM_SECTION_HEADER)
            self.wait_for(self.SEL_IM_TEMPLATE_MENU)

        self.click(self.SEL_IM_TEMPLATE_MENU)
        self.wait_for(self.SEL_ADD_BTN)
        self.page.evaluate(f"window.location.hash = '{self._HASH_PAGE_SIZE_100}';")
        self.wait_for(self.SEL_ADD_BTN)
        try:
            self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 목록 조회
    # ------------------------------------------------------------------
    def get_template_names(self) -> list[str]:
        """현재 목록의 템플릿 이름 리스트 반환"""
        names = []
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = row.locator("td").all()
            if tds:
                name = tds[0].inner_text().strip()
                if name:
                    names.append(name)
        return names

    def is_template_exists(self, name: str) -> bool:
        return name in self.get_template_names()

    # ------------------------------------------------------------------
    # 행 선택
    # ------------------------------------------------------------------
    def click_template_row(self, template_name: str) -> None:
        """
        템플릿 이름으로 행 클릭 (tActive 확인).
        오버레이 일시 비활성화 + force=True 클릭.
        """
        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=template_name).first
        for attempt in range(3):
            self._toggle_overlay(False)
            self.page.wait_for_timeout(80)
            try:
                row.click(force=True, timeout=3000)
            finally:
                self._toggle_overlay(True)
            try:
                self.page.locator(self.SEL_TABLE_ROW_ACTIVE).filter(
                    has_text=template_name
                ).first.wait_for(state="attached", timeout=5000)
                return
            except Exception:
                print(f"\n[click_template_row] tActive 미확인 ({attempt+1}회), 재시도...")
        raise Exception(f"행 선택 실패 (3회 재시도): {template_name}")

    def check_template_row(self, template_name: str) -> None:
        """
        템플릿 이름 행의 체크박스 체크.
        [AUTO] 접두사 템플릿만 허용.
        jQuery document 위임 핸들러 트리거를 위해
        _toggle_overlay(False) + Playwright 네이티브 click() 조합 필수.
        dispatchEvent / el.click() (JS) 로는 jQuery 핸들러가 트리거되지 않음.
        """
        if not template_name.startswith("[AUTO]"):
            raise Exception("테스트 생성 템플릿([AUTO] 접두사)만 조작 가능합니다")
        checkbox = (
            self.page.locator(self.SEL_TABLE_ROW)
            .filter(has_text=template_name)
            .first.locator(self.SEL_CHECKBOX)
            .first
        )
        if checkbox.is_checked():
            return
        # 오버레이 일시 비활성화 → 네이티브 클릭 → 즉시 복원
        self._toggle_overlay(False)
        try:
            checkbox.click()
        finally:
            self._toggle_overlay(True)
        if not checkbox.is_checked():
            raise Exception(f"체크박스 클릭 후 미체크 상태: {template_name}")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def add_template(
        self,
        name: str,
        text_content: str = "SCAN_TEST",
        use_type: str = "DISPLAY",
        template_type: str = "TEXT",
        image_path: str | None = None,
    ) -> str:
        """
        템플릿 추가. 이름 + 모드 + 표시 문구(TEXT) / 이미지 파일(IMAGE) 입력 후 등록.
        중복 이름 시 suffix(_2, _3, ...) 붙여 재시도.

        Args:
            name          : 템플릿 이름 ([AUTO] 접두사 필수)
            text_content  : TEXT 모드 표시 문구 (기본: "SCAN_TEST")
            use_type      : "DISPLAY"(화면, 기본) | "PRINT"(출력물)
            template_type : "TEXT"(기본) | "IMAGE"
            image_path    : IMAGE 모드 업로드 파일 경로 (None이면 이미지 미업로드)

        Returns:
            실제 생성된 템플릿 이름
        """
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 생성 템플릿([AUTO] 접두사)만 생성 가능합니다")

        actual_name = [name]

        def _attempt():
            self.click(self.SEL_ADD_BTN)
            self.wait_for(self.SEL_ADD_MODAL, state="attached")

            # 모드 설정
            self.switch_use_type(use_type)
            self.switch_template_type(template_type)

            self.fill(self.SEL_TEMPLATE_NAME, actual_name[0])

            if template_type == "TEXT":
                # 표시할 문구 (contenteditable div) — JS innerText 직접 설정
                self._set_contenteditable("textLetter", text_content)
            elif template_type == "IMAGE" and image_path:
                # 이미지 파일 업로드 — 파일등록 버튼 → OS 파일선택 다이얼로그
                self.upload_image(image_path)

            self.click_attached(self.SEL_REGISTER_BTN)
            for suffix in range(2, 11):
                try:
                    self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                        state="attached", timeout=self._TIMEOUT_MODAL
                    )
                except Exception:
                    break
                msg = self.get_modal_message()
                self.click_attached(self.SEL_CONFIRM_BTN)
                self.wait_for_modal_closed()
                if "이미 등록되어 있습니다" not in msg:
                    break
                actual_name[0] = f"{name}_{suffix}"
                loc = self.page.locator(self.SEL_TEMPLATE_NAME).first
                loc.evaluate("el => { el.value = ''; }")
                loc.fill(actual_name[0])
                loc.evaluate("el => el.dispatchEvent(new Event('input', {bubbles: true}))")
                self.click_attached(self.SEL_REGISTER_BTN)
            self.wait_for(self.SEL_ADD_BTN)

        try:
            _attempt()
        except Exception as e:
            print(f"\n[add_template] 1차 실패: {e}\nnavigate_to() 후 재시도...")
            self.navigate_to()
            actual_name[0] = name
            _attempt()

        return actual_name[0]

    def delete_all_auto_templates(self) -> None:
        """[AUTO] 접두사 템플릿을 모두 삭제 시도한다."""
        auto_names = [n for n in self.get_template_names() if n.startswith("[AUTO]")]
        for name in auto_names:
            try:
                self.delete_template(name)
            except Exception as e:
                print(f"\n[delete_all_auto_templates] {name!r} 삭제 실패: {e}")

    def delete_template(self, template_name: str) -> None:
        """템플릿 삭제. [AUTO] 접두사 템플릿만 허용."""
        if not template_name.startswith("[AUTO]"):
            raise Exception("테스트 생성 템플릿([AUTO] 접두사)만 조작 가능합니다")

        def _attempt():
            self.check_template_row(template_name)
            self.click(self.SEL_DELETE_BTN)
            if not self.is_confirm_modal_visible():
                raise Exception("삭제 버튼 클릭 후 모달이 나타나지 않음")
            msg = self.get_modal_message()
            if "하시겠습니까" not in msg:
                self.take_screenshot("delete_error_modal")
                self.click_attached(self.SEL_CONFIRM_BTN)
                self.wait_for_modal_closed()
                raise Exception(f"삭제 중 에러 모달: {msg!r}")
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
            self.wait_for(self.SEL_ADD_BTN)
            self._restore_page_size()

        try:
            _attempt()
        except Exception as e:
            print(f"\n[delete_template] 1차 실패: {e}\nnavigate_to() 후 재시도...")
            self.navigate_to()
            _attempt()

    def try_delete_template_expect_blocked(self, template_name: str) -> str:
        """
        정책에 할당된 템플릿 삭제 시도 → 차단 메시지 반환.
        삭제가 의도적으로 차단되는지 검증할 때 사용.
        반환값: 경고 모달 메시지 텍스트
        """
        self.check_template_row(template_name)
        self.click(self.SEL_DELETE_BTN)
        if not self.is_confirm_modal_visible():
            raise Exception("삭제 버튼 클릭 후 모달이 나타나지 않음")
        msg = self.get_modal_message()
        self.click_attached(self.SEL_CONFIRM_BTN)
        self.wait_for_modal_closed()
        return msg

    # ------------------------------------------------------------------
    # UIScanner 스캔용 헬퍼
    # ------------------------------------------------------------------
    def open_add_modal(self) -> None:
        """템플릿 추가 버튼 클릭 → 모달 열림 대기"""
        self.click(self.SEL_ADD_BTN)
        try:
            self.wait_for(self.SEL_ADD_MODAL, state="attached")
        except Exception as e:
            raise Exception(f"템플릿 추가 모달이 열리지 않음: {e}") from e

    def open_modify_modal(self, template_name: str) -> None:
        """템플릿 행 선택 → 수정 버튼 클릭 → 모달 열림 대기"""
        self.click_template_row(template_name)
        self.click(self.SEL_MODIFY_BTN)
        self._fail_if_modal(self._TIMEOUT_MODAL)
        try:
            self.wait_for(self.SEL_ADD_MODAL, state="attached")
        except Exception as e:
            raise Exception(f"템플릿 수정 모달이 열리지 않음: {e}") from e

    def close_modal(self) -> None:
        """모달 닫기 버튼 클릭 → 목록 복귀 대기"""
        self.click_attached(self.SEL_CLOSE_BTN)
        self.wait_for(self.SEL_ADD_BTN)

    # ------------------------------------------------------------------
    # 모달 유틸
    # ------------------------------------------------------------------
    def get_modal_message(self) -> str:
        return self.page.locator(self.SEL_MODAL_BODY_TEXT).first.inner_text().strip()

    def is_confirm_modal_visible(self) -> bool:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
            return True
        except Exception:
            return False

    def wait_for_modal_closed(self) -> None:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 모드 전환 헬퍼 (조건부 필드 가시성 제어)
    # ------------------------------------------------------------------
    # 화면/출력물, 텍스트/이미지 라디오는 input 자체가 display:none 이고
    # 실제 클릭 대상은 <label for="..."> 요소임 (Chrome MCP 확인 2026-04-14).
    # label.evaluate("el => el.click()") → AngularJS ng-model 정상 트리거 확인.
    # 열린 모달(.in) 내부의 label만 선택해 중복 DOM 간섭 방지.
    # ------------------------------------------------------------------

    # 모달 내부 label 셀렉터 (열린 모달 범위 한정)
    _MODAL_OPEN = "div#addInnoMarkTemplateControl.in"

    def switch_use_type(self, use_type: str) -> None:
        """
        템플릿 타입(화면/출력물) 전환.
        use_type: "DISPLAY" | "PRINT"
        DISPLAY 전용 필드: isTextOutline, waterMarkOpacity
        """
        label_for = {
            "DISPLAY": "templateUseDisplayType",
            "PRINT":   "templateUsePrintType",
        }.get(use_type)
        if not label_for:
            raise ValueError(f"알 수 없는 use_type: {use_type!r} (DISPLAY|PRINT)")

        # 이미 선택된 경우 스킵
        radio_loc = self.page.locator(f"{self._MODAL_OPEN} input#{label_for}").first
        if radio_loc.count() > 0 and radio_loc.is_checked():
            return

        label_loc = self.page.locator(f"{self._MODAL_OPEN} label[for='{label_for}']").first
        if label_loc.count() > 0:
            label_loc.evaluate("el => el.click()")
            self.page.wait_for_timeout(250)

    def switch_template_type(self, template_type: str) -> None:
        """
        표시형식(텍스트/이미지) 전환.
        template_type: "TEXT" | "IMAGE"
        TEXT  전용 필드: textLetter (contenteditable), isTextLetterQrcode
        IMAGE 전용 필드: imageName (read-only), imageWidth, imageBottomText (contenteditable)
        """
        label_for = {
            "TEXT":  "textTypeTemplate",
            "IMAGE": "imageTypeTemplate",
        }.get(template_type)
        if not label_for:
            raise ValueError(f"알 수 없는 template_type: {template_type!r} (TEXT|IMAGE)")

        radio_loc = self.page.locator(f"{self._MODAL_OPEN} input#{label_for}").first
        if radio_loc.count() > 0 and radio_loc.is_checked():
            return

        label_loc = self.page.locator(f"{self._MODAL_OPEN} label[for='{label_for}']").first
        if label_loc.count() > 0:
            label_loc.evaluate("el => el.click()")
            self.page.wait_for_timeout(250)

    def get_current_use_type(self) -> str:
        """현재 모달의 템플릿 타입 반환: 'DISPLAY' | 'PRINT'"""
        loc = self.page.locator(f"{self._MODAL_OPEN} input#templateUsePrintType").first
        if loc.count() > 0 and loc.is_checked():
            return "PRINT"
        return "DISPLAY"

    def get_current_template_type(self) -> str:
        """현재 모달의 표시형식 반환: 'TEXT' | 'IMAGE'"""
        loc = self.page.locator(f"{self._MODAL_OPEN} input#imageTypeTemplate").first
        if loc.count() > 0 and loc.is_checked():
            return "IMAGE"
        return "TEXT"

    # ------------------------------------------------------------------
    # 예약어 선택 헬퍼
    # ------------------------------------------------------------------
    def open_reserved_word_modal(self) -> None:
        """
        TEXT 모드 [예약어] 버튼 클릭 → 예약어 선택 모달(#selectReservedWordControl) 열기.

        [Chrome MCP 확인 (2026-04-15)]
        - 버튼 id: selectTextReservedWordBtn (Bootstrap dropdown 아님)
        - 클릭 시 별도 모달 #selectReservedWordControl 이 열림
        - 항목: tr[contents-list-item] → checkbox + span[name=reservedWordName]
        - 확인 버튼 클릭 시 선택한 예약어가 textLetter에 삽입됨

        [클릭 전략 — Chrome MCP로 원인 확정 (2026-04-16)]
        예약어 버튼 �핸들러가 window.getSelection().getRangeAt(0)으로
        textLetter contenteditable의 현재 커서 위치를 읽어 예약어를 삽입함.
        textLetter에 포커스/커서가 없으면 getRangeAt(0)에서 IndexSizeError 발생
        → 모달이 열리지 않음 (JS 에러로 핸들러가 중단).

        해결: 버튼 클릭 전에 textLetter에 focus() + Selection range 설정.
        이후 evaluate(btn.click())으로 버튼 클릭 → 모달 정상 열림.
        """
        # 1) textLetter에 포커스 + 커서를 끝에 위치 (getRangeAt(0) 에러 방지)
        self.page.evaluate("""
            var el = document.getElementById('textLetter');
            if (el) {
                el.focus();
                var range = document.createRange();
                var sel = window.getSelection();
                range.selectNodeContents(el);
                range.collapse(false);
                sel.removeAllRanges();
                sel.addRange(range);
            }
        """)
        self.page.wait_for_timeout(80)

        # 2) 예약어 버튼 클릭 (evaluate로 JS 직접 호출)
        self.page.evaluate(
            "document.querySelector('#addInnoMarkTemplateControl.in [name=\"addReservedWordBtn\"]').click()"
        )

        # 3) 모달 컨텐츠(tr 항목) DOM 등록 대기
        self.page.wait_for_selector(
            self.SEL_RESERVED_WORD_ROW, state="attached", timeout=5000
        )

    def select_reserved_word(self, index: int = 0) -> str:
        """
        예약어 선택 모달에서 index번째 항목 체크 → 확인 클릭 → 선택된 예약어명 반환.
        open_reserved_word_modal() 호출 후 사용.
        """
        rows = self.page.locator(self.SEL_RESERVED_WORD_ROW).all()
        assert rows, "예약어 선택 모달에 항목이 없음"
        row = rows[index]
        item_text = row.locator(self.SEL_RESERVED_WORD_NAME).first.inner_text().strip()
        row.locator("input[type='checkbox']").first.evaluate("el => el.click()")
        self.page.wait_for_timeout(200)
        self.page.locator(self.SEL_RESERVED_WORD_CONFIRM_BTN).first.evaluate("el => el.click()")
        self.page.wait_for_timeout(400)
        return item_text

    # ------------------------------------------------------------------
    # 이미지 업로드 헬퍼
    # ------------------------------------------------------------------
    def upload_image(self, image_path: str) -> None:
        """
        IMAGE 모드에서 파일등록 버튼을 클릭해 OS 파일 선택 다이얼로그를 열고 파일 설정.

        [방식] 파일등록 버튼 클릭 → expect_file_chooser() 인터셉트 → set_files()
        - 제품의 정상 파일 등록 흐름(버튼 클릭 → OS 다이얼로그 → 선택)을 그대로 재현.
        - Playwright가 OS 다이얼로그를 인터셉트해 자동으로 파일 지정.
        - 이후 제품 JS 검증 실행 (PNG 외 파일이면 오류 팝업 출력).
        - 오버레이는 native click이 필요하므로 _toggle_overlay(False) 사용.

        흐름:
          1. _toggle_overlay(False) — 오버레이 포인터 이벤트 해제
          2. expect_file_chooser 컨텍스트 안에서 파일등록 버튼 click(force=True)
          3. OS 다이얼로그 인터셉트 → set_files(image_path)
          4. 1.5초 대기 (제품 JS 검증 + imageName 채움 or 오류 팝업 렌더링)
        """
        btn_sel = f"{self._MODAL_OPEN} button#addTemplateImageFileBtn"
        self._toggle_overlay(False)
        try:
            with self.page.expect_file_chooser(timeout=5000) as fc_info:
                self.page.locator(btn_sel).first.click(force=True, timeout=3000)
            fc_info.value.set_files(str(image_path))
            self.page.wait_for_timeout(1500)   # 제품 JS 검증 + 팝업 렌더링 대기
        except Exception as e:
            self._on_error("upload_image", e)
            raise
        finally:
            self._toggle_overlay(True)

    # ------------------------------------------------------------------
    # contenteditable 헬퍼
    # ------------------------------------------------------------------
    def _set_contenteditable(self, element_id: str, text: str) -> None:
        """contenteditable div에 텍스트를 설정한다 (JS innerText 직접 주입)."""
        self.page.evaluate(
            f"""
            var el = document.getElementById('{element_id}');
            if (el) {{
                el.innerText = {repr(text)};
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                el.dispatchEvent(new Event('blur', {{bubbles: true}}));
            }}
            """
        )

    def get_contenteditable_text(self, element_id: str) -> str:
        """contenteditable div의 현재 innerText 반환."""
        try:
            return self.page.evaluate(
                f"var el = document.getElementById('{element_id}'); el ? el.innerText.trim() : ''"
            )
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # 내부 유틸
    # ------------------------------------------------------------------
    def _restore_page_size(self) -> None:
        if "pageSize=100" in self.page.url:
            return
        self.page.evaluate(f"window.location.hash = '{self._HASH_PAGE_SIZE_100}';")
        self.wait_for(self.SEL_ADD_BTN)
        try:
            self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 업로드 검증 팝업 처리 (__globalMessageModal 外 별도 팝업 대응)
    # ------------------------------------------------------------------

    def get_upload_modal_msg(self) -> str:
        """
        파일 업로드 직후 표시되는 형식 오류 팝업의 메시지 반환.
        addInnoMarkTemplateControl 내부 요소는 제외하고 전역 모달을 검색.
        팝업 없으면 "" 반환.
        """
        try:
            self.page.wait_for_timeout(300)
            return self.page.evaluate("""
                () => {
                    for (const sel of ['.modal-body-text', '.modal-body']) {
                        const els = document.querySelectorAll(sel);
                        for (const el of els) {
                            if (el.closest('#addInnoMarkTemplateControl')) continue;
                            const text = el.innerText.trim();
                            if (text) return text;
                        }
                    }
                    return '';
                }
            """)
        except Exception:
            return ""

    def dismiss_upload_modal(self) -> None:
        """
        업로드 오류 팝업의 확인 버튼 클릭.
        addInnoMarkTemplateControl 외부의 visible '확인' 버튼을 찾아 JS click.
        """
        try:
            self.page.evaluate("""
                () => {
                    const candidates = Array.from(document.querySelectorAll('button'))
                        .filter(b => {
                            if (b.closest('#addInnoMarkTemplateControl')) return false;
                            const text = b.textContent.trim();
                            const style = window.getComputedStyle(b);
                            return text === '\ud655\uc778' && style.display !== 'none';
                        });
                    if (candidates.length > 0) {
                        candidates[candidates.length - 1].click();
                    }
                }
            """)
            self.page.wait_for_timeout(400)
        except Exception:
            pass

    def _close_modal_if_open(self) -> None:
        try:
            if self.page.locator(self.SEL_ADD_MODAL).count() > 0:
                self.click_attached(self.SEL_CLOSE_BTN)
                self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass

    def _dismiss_stale_confirm_modal(self) -> None:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_STALE
            )
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        except Exception:
            pass

    def _fail_if_modal(self, timeout: int = _TIMEOUT_TABLE) -> None:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=timeout
            )
        except Exception:
            return
        msg = self.get_modal_message()
        self.take_screenshot("unexpected_modal")
        self.click_attached(self.SEL_CONFIRM_BTN)
        self.wait_for_modal_closed()
        raise Exception(f"예상치 못한 모달 발생: {msg!r}")

    # ------------------------------------------------------------------
    # Universal Scanner 표준 인터페이스 구현
    # ------------------------------------------------------------------

    AUTO_NAME_PREFIX = "[AUTO]_im_tmpl"

    # qa_runner.py 호환 alias ─────────────────────────────────────────
    # run_3phase_scan 은 모든 PageClass에 대해 아래 메서드를 호출한다.
    # InnoMarkTemplatePage는 "template" 명칭을 쓰므로 alias 로 연결.

    def delete_all_auto_policies(self) -> None:
        """qa_runner 호환 — delete_all_auto_templates() 위임."""
        self.delete_all_auto_templates()

    def get_policy_names(self) -> list[str]:
        """qa_runner _append_list_check 호환 — get_template_names() 위임."""
        return self.get_template_names()

    def save_policy(self, name: str) -> None:
        """
        Phase 1/2 완료 후 템플릿 저장.
        현재 모달의 표시형식(TEXT/IMAGE)을 자동 감지하여 필수 필드 처리.
        - TEXT 모드: textLetter 비어있으면 기본값 채움
        - IMAGE 모드: 파일 없이도 저장 시도 (필수 검증 테스트 목적)
        """
        self.fill(self.SEL_TEMPLATE_NAME, name)

        template_type = self.get_current_template_type()
        if template_type == "TEXT":
            # 표시할 문구가 비어있으면 기본값 채움 (필수 필드)
            current_text = self.get_contenteditable_text("textLetter")
            if not current_text:
                self._set_contenteditable("textLetter", "SCAN_TEST")

        self.click_attached(self.SEL_REGISTER_BTN)
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        except Exception:
            pass
        self.wait_for(self.SEL_ADD_BTN)

    def close_edit_modal(self) -> None:
        """Phase 3 EDIT 모달 닫기."""
        try:
            if self.page.locator(self.SEL_ADD_MODAL).count() > 0:
                self.close_modal()
            else:
                self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass

    def save_edit_modal(self) -> None:
        """Phase 4: 수정 모달에서 변경 내용 저장."""
        self.click_attached(self.SEL_SAVE_BTN)
        self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.click_attached(self.SEL_CONFIRM_BTN)
        self.wait_for_modal_closed()
        self.wait_for(self.SEL_ADD_BTN)

    def get_verify_values(self, saved_name: str) -> dict:
        """
        Phase 3: EDIT 모달 로드 후 저장값 검증.
        템플릿 이름 필드 + 현재 모드에 따른 필드 반환.
        """
        result = {"input#imTemplateName": saved_name}

        template_type = self.get_current_template_type()
        if template_type == "TEXT":
            text_val = self.get_contenteditable_text("textLetter")
            if text_val:
                result["div#textLetter"] = text_val
        elif template_type == "IMAGE":
            img_name = self.page.locator("input#imageName").first.input_value()
            if img_name:
                result["input#imageName"] = img_name
            img_width = self.page.locator("input#imageWidth").first.input_value()
            if img_width:
                result["input#imageWidth"] = img_width

        return result
