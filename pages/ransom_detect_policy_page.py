from pages.base_page import BasePage


class RansomDetectPolicyPage(BasePage):
    # ------------------------------------------------------------------
    # Selectors
    # ------------------------------------------------------------------

    # 메뉴 네비게이션
    # 매니저 페이지 좌측 아이콘 nav (세션 유효성 확인: 로그인 상태면 항상 존재)
    SEL_LEFT_NAV          = "ul.leftNavList"
    # App Setting 아이콘 (클릭 시 App Setting 서브메뉴 패널 토글)
    SEL_APP_SETTING_MENU  = "a[data-menuid='managerAppSetting']"
    # App Setting 서브메뉴 패널 (열림 여부 확인용)
    SEL_APP_SETTING_PANEL = "ul.managerAppSettingList"
    # RansomCruncher 아코디언 섹션 헤더 (클릭 시 하위 메뉴 펼침)
    SEL_RC_SECTION_HEADER = "a.managerRansomCruncher"
    # 탐지정책 메뉴 링크
    SEL_RC_DETECT_POLICY  = "a[data-menuid='managerRansomCruncherDetectPolicy']"

    # 목록
    SEL_TABLE_ROW         = "table tbody tr"
    SEL_TABLE_ROW_ACTIVE  = "table tbody tr.tActive"   # 선택된 행 (단일 선택 하이라이트)
    SEL_CHECKBOX          = "input[type='checkbox']"

    # 버튼 (목록 페이지)
    SEL_ADD_BTN           = "button#addItemBtn"
    SEL_USER_BTN          = "button#addRemoveItemUserBtn"
    SEL_MODIFY_BTN        = "button#modifyItemBtn"
    SEL_COPY_BTN          = "button#copyItemBtn"
    SEL_DELETE_BTN        = "button#removeItemBtn"

    # 모달 - 정책 추가/수정 모달 컨테이너
    # Bootstrap 3: 열릴 때 .in 클래스 추가 → visible 체크 불가, attached+.in 으로 판단
    SEL_ADD_MODAL         = "div#addItemModal.in"
    SEL_MODAL             = "div.modal-body"
    SEL_POLICY_NAME       = "input#rcDetectPolicyName"
    SEL_EXTENSION_INPUT   = "input#protectExtension"
    SEL_EXTENSION_ADD_BTN = "button#extensionAttachBtn"
    SEL_EXTENSION_LIST    = "div#protectExtensionList"

    # 모달 - 하단 버튼
    SEL_REGISTER_BTN      = "button[add-btn]"
    SEL_SAVE_BTN          = "button[modify-btn]"
    SEL_CLOSE_BTN         = "button[data-dismiss='modal'], .btn:has-text('닫기')"

    # 확인 모달 (등록/수정/삭제 후 공통)
    SEL_CONFIRM_MODAL        = "div#__globalMessageModal"
    SEL_CONFIRM_MODAL_OPENED = "div#__globalMessageModal.in"   # Bootstrap 3: .in = 열린 상태
    SEL_CONFIRM_BTN          = "div#__globalMessageModal button:has-text('확인')"  # 텍스트 '확인' 버튼. ×(close)·취소(btn-default) 제외
    SEL_MODAL_BODY_TEXT      = "div.modal-body-text"           # 모달 본문 메시지 텍스트

    # 모달 - 토글 (ON/OFF 체크박스)
    SEL_TOGGLE_EXCEPT_DETECT  = "input#isExceptDetect"
    SEL_TOGGLE_ROLLBACK_USE   = "input#isRollbackUse"
    SEL_TOGGLE_BLOCK_PROCESS  = "input#isBlockProcessIsolation"
    SEL_TOGGLE_EXCEPT_PERIOD  = "input#isExceptProcessCollectPeriod"
    SEL_TOGGLE_POLICY_UPDATE  = "input#isPolicyUpdateIntervalMinute"
    SEL_TOGGLE_AUTH_PASSWORD  = "input#isAuthorizationPassword"

    # 토글 종속 필드
    SEL_FIELD_FILE_PATH_EXCEPT    = "input#isFilePathExcept"
    SEL_FIELD_PROCESS_PATH_EXCEPT = "input#isProcessPathExcept"
    SEL_FIELD_DIGITAL_SIGN_EXCEPT = "input#isDigitalSignExcept"
    SEL_FIELD_ROLLBACK_MAX_SIZE   = "input#rollbackFileMaxSize"
    SEL_FIELD_ROLLBACK_WAIT_MIN   = "input#blockRollbackWaitMinute"
    SEL_FIELD_REMOVE_ISOLATED     = "input#isRemoveIsolatedProcess"
    SEL_FIELD_EXCEPT_PERIOD       = "input#exceptProcessCollectPeriod"
    SEL_FIELD_POLICY_UPDATE_MIN   = "input#policyUpdateIntervalMinute"
    SEL_FIELD_AUTH_PASSWORD       = "input#authorizationPassword"

    # ------------------------------------------------------------------
    # 타임아웃 상수
    # ------------------------------------------------------------------
    _TIMEOUT_TABLE = 5000   # 테이블 XHR 완료 대기
    _TIMEOUT_MODAL = 3000   # 모달 응답 대기
    _TIMEOUT_STALE = 1000   # 잔여 모달 빠른 확인

    # 탐지정책 목록 pageSize=100 해시 URL (CRUD 후 pageSize 리셋 복원용)
    _HASH_PAGE_SIZE_100 = (
        "#!/managerRansomCruncherDetectPolicy"
        "?pageNo=1&pageSize=100&searchText=&startIndex=0&sortIndex=0&sortOrder=0"
    )

    # ------------------------------------------------------------------
    # 네비게이션
    # ------------------------------------------------------------------
    def navigate_to(self) -> None:
        """
        탐지정책 페이지로 이동.
        0. 정책추가/수정 모달이 열려 있으면 닫기
        1. 확인/세션만료 모달이 열려 있으면 닫기 (이전 테스트 잔여 or 서버 세션 충돌)
        2. 정책추가 버튼이 보이고 URL에 RansomCruncher가 포함되면 이미 탐지정책 페이지 → 즉시 반환
        3. manager/main.html 루트로 강제 이동 (이동 후 세션만료 모달 재확인)
        4. leftNavList 가 없으면 세션 만료로 판단하여 즉시 오류 발생
           (30초 타임아웃 낭비 방지 + 명확한 메시지 제공)
        5. App Setting 패널 열기 → RansomCruncher 아코디언 펼치기 → 탐지정책 메뉴 클릭
        """
        # 이전 테스트 잔여 정책추가/수정 모달 닫기
        self._close_modal_if_open()
        # 확인/세션만료 모달이 열려 있으면 닫기 (1초 타임아웃, 없으면 즉시 통과)
        self._dismiss_stale_confirm_modal()

        # 이미 탐지정책 페이지 + pageSize=100이면 즉시 반환
        # URL 로 페이지를 구분한다: button#addItemBtn 은 다른 관리 페이지(사용자 관리 등)에도 존재하므로
        # URL 에 탐지정책 fragment 가 없으면 같은 버튼이 보여도 조기 반환하지 않는다.
        if (self.is_visible(self.SEL_ADD_BTN)
                and "RansomCruncher" in self.page.url
                and "pageSize=100" in self.page.url):
            return

        # 이미 매니저 메인 페이지에 있으면 goto 생략 (전체 재로드 시 서버 단일세션 충돌 방지)
        # logged_in_page fixture 는 manager/main.html#!/ 에서 출발하므로 goto 불필요
        if "manager/main.html" not in self.page.url:
            host = self.base_url.split("/#!/")[0].rstrip("/")
            self.page.goto(f"{host}/manager/main.html")
            # goto 후 세션만료 모달 재확인
            self._dismiss_stale_confirm_modal()

        # 세션 만료 조기 감지: leftNavList 가 보이지 않으면 세션 만료로 판단
        # goto 직후 SPA가 초기화 중일 수 있으므로 최대 5초 대기 후 판단
        # (30초 기본 타임아웃 대신 5초로 낮춰 빠르게 실패)
        try:
            self.page.locator(self.SEL_LEFT_NAV).first.wait_for(
                state="visible", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass  # visible 아니면 아래 RuntimeError에서 처리
        if not self.is_visible(self.SEL_LEFT_NAV):
            raise RuntimeError(
                "매니저 페이지 UI 없음 — 세션 만료 또는 접근 권한 없음.\n"
                "이전 테스트 실행이 로그아웃 없이 종료된 경우 발생합니다.\n"
                "pytest를 재실행해 주세요."
            )

        # App Setting 패널이 닫혀 있으면 App Setting 아이콘 클릭해 열기
        if not self.is_visible(self.SEL_APP_SETTING_PANEL):
            self.click(self.SEL_APP_SETTING_MENU)
            self.wait_for(self.SEL_APP_SETTING_PANEL)

        # RansomCruncher 하위 메뉴가 접혀 있으면 아코디언 헤더 클릭해 펼치기
        if not self.is_visible(self.SEL_RC_DETECT_POLICY):
            self.click(self.SEL_RC_SECTION_HEADER)
            self.wait_for(self.SEL_RC_DETECT_POLICY)

        self.click(self.SEL_RC_DETECT_POLICY)
        self.wait_for(self.SEL_ADD_BTN)
        # pageSize=100으로 확장: 정렬 순서에 관계없이 [AUTO] 항목 포함 전체 목록 조회
        # SPA hash 변경이므로 페이지 전체 재로드 없이 목록만 갱신됨
        self.page.evaluate(f"window.location.hash = '{self._HASH_PAGE_SIZE_100}';")
        self.wait_for(self.SEL_ADD_BTN)
        # hash 변경 후 ADD_BTN은 즉시 보이지만 테이블 XHR이 완료될 때까지 대기
        # 빈 테이블(정책 없음)이면 timeout 후 통과
        try:
            self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass  # 정책 0건이면 정상 통과

    # ------------------------------------------------------------------
    # 목록 조회
    # ------------------------------------------------------------------
    def get_policy_names(self) -> list[str]:
        """현재 목록의 정책 이름 리스트 반환 (첫 번째 열 기준)"""
        names = []
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = row.locator("td").all()
            if tds:
                name = tds[0].inner_text().strip()
                if name:
                    names.append(name)
        return names

    def is_policy_exists(self, policy_name: str) -> bool:
        """목록에 해당 이름의 정책이 존재하는지 확인"""
        return policy_name in self.get_policy_names()

    # ------------------------------------------------------------------
    # 행 선택
    # ------------------------------------------------------------------
    def click_policy_row(self, policy_name: str) -> None:
        """
        정책 이름으로 행 클릭 (단일 선택).
        오버레이는 사람 클릭 차단용이므로 자동화 클릭 시에만 일시 비활성화한다.
        pointer-events를 none으로 전환 → Playwright 네이티브 click() → 즉시 복원.
        행 선택 성공 여부는 tr.tActive 클래스 부착으로 판단한다.
        실패 시 최대 3회 재시도. 3회 모두 실패하면 Exception 발생.
        """
        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=policy_name).first
        for attempt in range(3):
            # 오버레이 일시 비활성화 (사람 클릭 차단 해제) → 클릭 → 즉시 복원
            self._toggle_overlay(False)
            try:
                row.click()
            finally:
                self._toggle_overlay(True)
            try:
                self.page.locator(self.SEL_TABLE_ROW_ACTIVE).filter(
                    has_text=policy_name
                ).first.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
                return  # tr.tActive 확인 → 행 선택 성공
            except Exception:
                print(f"\n[click_policy_row] tActive 미확인 ({attempt+1}회), 재시도...")
        raise Exception(f"행 선택 실패 (3회 재시도): {policy_name}")

    def check_policy_row(self, policy_name: str) -> None:
        """
        정책 이름 행의 체크박스 체크.
        [AUTO] 접두사 정책만 허용 — 이 규칙은 어떤 경우에도 우회하지 않는다.
        jQuery는 document 레벨에서 click 이벤트 위임으로 처리하므로
        click_policy_row()와 동일하게 오버레이 pointer-events 일시 비활성화 후
        Playwright 네이티브 click()을 사용해야 jQuery 핸들러가 트리거된다.
        이미 체크된 상태이면 재클릭(토글) 방지를 위해 즉시 반환한다.
        """
        if not policy_name.startswith("[AUTO]"):
            raise Exception("테스트 생성 정책([AUTO] 접두사)만 조작 가능합니다")
        checkbox = (
            self.page.locator(self.SEL_TABLE_ROW)
            .filter(has_text=policy_name)
            .first.locator(self.SEL_CHECKBOX)
            .first
        )
        # 이미 체크된 상태이면 재클릭 방지 (클릭 시 토글되어 해제될 수 있음)
        if checkbox.is_checked():
            return
        # 오버레이 일시 비활성화 → 네이티브 클릭 → 즉시 복원
        # dispatchEvent(click/change)는 jQuery document 위임 핸들러를 트리거하지 않음
        # Playwright 네이티브 click()만이 실제 브라우저 이벤트를 생성해 jQuery를 깨움
        self._toggle_overlay(False)
        try:
            checkbox.click()
        finally:
            self._toggle_overlay(True)
        # 클릭 후 체크 상태 검증: DOM이 checked=true여야 Angular/jQuery도 반영된 것
        if not checkbox.is_checked():
            raise Exception(f"체크박스 클릭 후 미체크 상태: {policy_name}")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def add_policy(self, name: str, extensions: list[str]) -> str:
        """
        정책 추가.
        중복 이름 오류 시 이름 뒤에 숫자(_2, _3, ...)를 붙여 재시도한다.
        실패 시 navigate_to() 후 1회 재시도한다.
        반환값: 실제 생성된 정책 이름 (중복 시 suffix 포함)
        """
        actual_name = [name]  # list로 감싸 내부 함수에서 수정 가능

        def _attempt():
            self.click(self.SEL_ADD_BTN)
            # Bootstrap 3: visible 체크 불가 → .in 클래스 부착(attached) 확인
            self.wait_for(self.SEL_ADD_MODAL, state="attached")
            # maxlength 초과 → 재시도 없이 즉시 ValueError
            self._validate_name_length(actual_name[0], self.SEL_POLICY_NAME)
            self.fill(self.SEL_POLICY_NAME, actual_name[0])
            for ext in extensions:
                self.fill(self.SEL_EXTENSION_INPUT, ext)
                self.click(self.SEL_EXTENSION_ADD_BTN)
            self.click(self.SEL_REGISTER_BTN)
            # 등록 결과 모달 처리 (중복이면 suffix 붙여 재시도, 최대 9회)
            for suffix in range(2, 11):
                try:
                    self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                        state="attached", timeout=self._TIMEOUT_MODAL
                    )
                except Exception:
                    break  # 모달 없음 → 등록 완료
                msg = self.get_modal_message()
                self.click_attached(self.SEL_CONFIRM_BTN)
                self.wait_for_modal_closed()
                if "이미 등록되어 있습니다" not in msg:
                    break  # 성공 모달("저장 하였습니다" 등) → 종료
                # 중복 이름 → suffix 붙여 재시도
                actual_name[0] = f"{name}_{suffix}"
                loc = self.page.locator(self.SEL_POLICY_NAME).first
                loc.evaluate("el => { el.value = ''; }")
                loc.fill(actual_name[0])
                loc.evaluate("el => el.dispatchEvent(new Event('input', {bubbles: true}))")
                loc.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))")
                self.click(self.SEL_REGISTER_BTN)
            self.wait_for(self.SEL_ADD_BTN)

        try:
            _attempt()
        except ValueError:
            raise  # maxlength 초과는 재시도 없이 즉시 실패
        except Exception as e:
            print(f"\n[add_policy] 1차 실패: {e}\nnavigate_to() 후 재시도...")
            self.navigate_to()
            actual_name[0] = name  # 재시도 시 이름 초기화
            _attempt()

        return actual_name[0]

    def modify_policy(self, policy_name: str, new_name: str) -> None:
        """
        정책 수정.
        행 선택 실패 시 navigate_to() 후 1회 재시도한다.
        이름 길이 초과(maxlength)는 재시도 없이 즉시 ValueError 발생.
        """
        # maxlength 사전 검증: 모달을 열기 전에 미리 차단
        # (fill()은 maxlength를 준수해 자동 잘림 → 다른 이름으로 저장되는 버그 방지)
        # 실제 maxlength는 모달을 열어야 알 수 있으므로 여기서는 알려진 20자 한계를 기준으로 함
        # 모달 안에서 정확한 maxlength를 읽어 재검증하므로 중복 방어가 된다
        def _attempt():
            self.click_policy_row(policy_name)
            self.click(self.SEL_MODIFY_BTN)
            # 수정 버튼 클릭 후 에러 모달 조기 감지 ("선택된 항목이 없습니다" 등)
            # click_policy_row에서 이미 수정 버튼 enabled 확인 → 3000ms면 충분
            self._fail_if_modal(self._TIMEOUT_MODAL)
            # Bootstrap 3: visible 체크 불가 → .in 클래스 부착(attached) 확인
            self.wait_for(self.SEL_ADD_MODAL, state="attached")
            # JS로 값 초기화 → fill() → input/change 이벤트 강제 발생
            # (프레임워크 바인딩이 fill()만으로 갱신되지 않는 경우 대응)
            loc = self.page.locator(self.SEL_POLICY_NAME).first
            # maxlength 초과 → 재시도 없이 즉시 ValueError (fill이 자동 잘라버림 방지)
            self._validate_name_length(new_name, self.SEL_POLICY_NAME)
            loc.evaluate("el => { el.value = ''; }")
            loc.fill(new_name)
            loc.evaluate("el => el.dispatchEvent(new Event('input',  {bubbles: true}))")
            loc.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))")
            # fill 후 실제 입력값 검증 (maxlength 외 다른 이유로도 잘릴 수 있음)
            actual = loc.input_value()
            if actual != new_name:
                raise ValueError(
                    f"이름 입력 후 값 불일치 — 입력 차단 또는 잘림 의심\n"
                    f"  입력: {new_name!r} ({len(new_name)}자)\n"
                    f"  실제: {actual!r} ({len(actual)}자)"
                )
            # button[modify-btn] 은 Bootstrap 3 모달 내부에서 Playwright visible 체크 실패
            # → click_attached() 로 attached 확인 후 JS 직접 클릭
            self.click_attached(self.SEL_SAVE_BTN)
            self._dismiss_modal()
            # 저장 후 수정 모달이 닫혔는지 확인
            # 중복 이름 등으로 저장 실패 시: 확인 모달은 닫히지만 수정 모달은 열린 채로 남음
            if self.page.locator(self.SEL_ADD_MODAL).count() > 0:
                self.click(self.SEL_CLOSE_BTN)
                raise Exception("수정 저장 실패: 저장 후 수정 모달이 닫히지 않음 (중복 이름?)")
            self.wait_for(self.SEL_ADD_BTN)
            # CRUD 후 SPA가 pageSize를 기본값(20)으로 리셋할 수 있음 → 복원
            self._restore_page_size()
        try:
            _attempt()
        except ValueError:
            raise  # maxlength 초과·입력 차단은 재시도 없이 즉시 실패
        except Exception as e:
            print(f"\n[modify_policy] 1차 실패: {e}\nnavigate_to() 후 재시도...")
            self.navigate_to()
            _attempt()

    def copy_policy(self, policy_name: str) -> None:
        """
        정책 복사.
        실패 시 navigate_to() 후 1회 재시도한다.
        [AUTO] 접두사 정책만 허용 — 이 규칙은 어떤 경우에도 우회하지 않는다.
        """
        if not policy_name.startswith("[AUTO]"):
            raise Exception("테스트 생성 정책([AUTO] 접두사)만 조작 가능합니다")
        def _attempt():
            self.check_policy_row(policy_name)
            self.click(self.SEL_COPY_BTN)
            if not self.is_confirm_modal_visible():
                raise Exception("복사 버튼 클릭 후 모달이 나타나지 않음")
            msg = self.get_modal_message()
            print(f"\n[copy_policy] 모달 메시지: {msg!r}")
            if "하시겠습니까" not in msg:
                self.take_screenshot("copy_error_modal")
                self.click_attached(self.SEL_CONFIRM_BTN)
                self.wait_for_modal_closed()
                raise Exception(f"복사 중 에러 모달: {msg!r}")
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
            self.wait_for(self.SEL_ADD_BTN)
            # 복사 후 SPA 테이블 XHR 완료 대기 (ADD_BTN보다 테이블 갱신이 늦을 수 있음)
            try:
                self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                    state="attached", timeout=self._TIMEOUT_TABLE
                )
            except Exception:
                pass
            # CRUD 후 SPA가 pageSize를 기본값(20)으로 리셋할 수 있음 → 복원
            self._restore_page_size()
        try:
            _attempt()
        except Exception as e:
            print(f"\n[copy_policy] 1차 실패: {e}\nnavigate_to() 후 재시도...")
            self.navigate_to()
            _attempt()

    def delete_all_auto_policies(self) -> None:
        """
        목록에서 [AUTO] 접두사 정책을 모두 삭제한다.
        [AUTO] 접두사 안전 규칙에 따라 실수 삭제 방지.
        복사본 등 [AUTO] 접두사가 없는 정책은 건드리지 않는다.
        """
        auto_names = [n for n in self.get_policy_names() if n.startswith("[AUTO]")]
        for name in auto_names:
            self.delete_policy(name)

    def delete_policy(self, policy_name: str) -> None:
        """
        정책 삭제.
        실패 시 navigate_to() 후 1회 재시도한다.
        [AUTO] 접두사 정책만 허용 — 이 규칙은 어떤 경우에도 우회하지 않는다.
        """
        if not policy_name.startswith("[AUTO]"):
            raise Exception("테스트 생성 정책([AUTO] 접두사)만 조작 가능합니다")
        def _attempt():
            self.check_policy_row(policy_name)
            self.click(self.SEL_DELETE_BTN)
            if not self.is_confirm_modal_visible():
                raise Exception("삭제 버튼 클릭 후 모달이 나타나지 않음")
            msg = self.get_modal_message()
            print(f"\n[delete_policy] 모달 메시지: {msg!r}")
            if "하시겠습니까" not in msg:
                # "선택된 항목이 없습니다" 등 에러 모달 → 체크박스 선택 실패로 판단
                self.take_screenshot("delete_error_modal")
                self.click_attached(self.SEL_CONFIRM_BTN)
                self.wait_for_modal_closed()
                raise Exception(f"삭제 중 에러 모달 (체크박스 선택 실패 의심): {msg!r}")
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
            self.wait_for(self.SEL_ADD_BTN)
            # CRUD 후 SPA가 pageSize를 기본값(20)으로 리셋할 수 있음 → 복원
            self._restore_page_size()
        try:
            _attempt()
        except Exception as e:
            print(f"\n[delete_policy] 1차 실패: {e}\nnavigate_to() 후 재시도...")
            self.navigate_to()
            _attempt()

    # ------------------------------------------------------------------
    # 입력 검증 테스트용 헬퍼
    # ------------------------------------------------------------------
    def open_add_modal(self) -> None:
        """
        정책추가 버튼 클릭 → 모달 열림 대기.
        div#addItemModal 컨테이너 + button[add-btn] visible 확인 후 반환.
        모달이 열리지 않으면 Exception 발생.
        """
        self.click(self.SEL_ADD_BTN)
        try:
            # Bootstrap 3: visible 체크 불가 → .in 클래스 부착(attached) 확인
            self.wait_for(self.SEL_ADD_MODAL, state="attached")
        except Exception as e:
            raise Exception(f"정책 추가 모달이 열리지 않음: {e}") from e

    def open_modify_modal(self, policy_name: str) -> None:
        """
        정책 행 선택 → 수정 버튼 클릭 → 모달 열림 대기.
        저장하지 않고 모달만 연다 (UIScanner 스캔 전용).
        모달이 열리지 않으면 Exception 발생.
        """
        self.click_policy_row(policy_name)
        self.click(self.SEL_MODIFY_BTN)
        self._fail_if_modal(self._TIMEOUT_MODAL)
        try:
            self.wait_for(self.SEL_ADD_MODAL, state="attached")
        except Exception as e:
            raise Exception(f"정책 수정 모달이 열리지 않음: {e}") from e

    def close_modal(self) -> None:
        """모달 닫기 버튼 클릭 → 목록 페이지 복귀 대기"""
        self.click(self.SEL_CLOSE_BTN)
        self.wait_for(self.SEL_ADD_BTN)

    def get_name_input_value(self) -> str:
        """정책 이름 입력란의 현재 값 반환"""
        return self.page.locator(self.SEL_POLICY_NAME).first.input_value()

    def is_register_btn_disabled(self) -> bool:
        """등록 버튼이 비활성화(disabled) 상태인지 반환"""
        return self.page.locator(self.SEL_REGISTER_BTN).first.is_disabled()

    def try_register(self) -> None:
        """등록 버튼 클릭 시도 (활성/비활성 무관하게 JS 클릭)"""
        self.page.locator(self.SEL_REGISTER_BTN).first.evaluate("el => el.click()")

    def add_extension(self, ext: str) -> None:
        """확장자 입력 후 추가 버튼 클릭"""
        self.fill(self.SEL_EXTENSION_INPUT, ext)
        self.click(self.SEL_EXTENSION_ADD_BTN)

    def get_extension_list_text(self) -> str:
        """확장자 목록 영역의 텍스트 반환"""
        return self.page.locator(self.SEL_EXTENSION_LIST).first.inner_text().strip()

    def get_modal_message(self) -> str:
        """에러/확인 모달의 본문 메시지 텍스트 반환 (div.modal-body-text)"""
        return self.page.locator(self.SEL_MODAL_BODY_TEXT).first.inner_text().strip()

    def is_confirm_modal_visible(self) -> bool:
        """확인 모달(#__globalMessageModal)이 열려 있는지 반환"""
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
            return True
        except Exception:
            return False

    def wait_for_modal_closed(self) -> None:
        """
        확인 모달의 .in 클래스가 제거될 때까지 대기 (최대 5초).
        SEL_CONFIRM_MODAL_OPENED(div#__globalMessageModal.in)가 더 이상
        DOM에 매칭되지 않으면 detached 상태가 된다.
        """
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    def is_modal_closed(self) -> bool:
        """확인 모달이 닫혀 있는지 즉시 확인 (대기 없음)"""
        return self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).count() == 0

    def dismiss_confirm_modal(self) -> None:
        """열린 확인 모달을 닫는다"""
        self.click_attached(self.SEL_CONFIRM_BTN)

    def set_toggle(self, selector: str, *, on: bool) -> None:
        """
        토글(체크박스)을 지정 상태로 설정한다.
        이미 원하는 상태이면 클릭하지 않는다.
        오버레이로 인해 JS evaluate로 클릭한다.
        """
        is_checked = self.page.locator(selector).first.is_checked()
        if is_checked != on:
            self.page.locator(selector).first.evaluate("el => el.click()")

    def is_input_enabled(self, selector: str) -> bool:
        """입력 요소가 활성화(not disabled) 상태인지 반환"""
        return not self.page.locator(selector).first.is_disabled()

    # ------------------------------------------------------------------
    # 내부 유틸 - 입력 검증
    # ------------------------------------------------------------------
    def _validate_name_length(self, name: str, selector: str) -> None:
        """
        입력란의 maxlength 속성을 읽어 이름 길이를 검증한다.
        초과 시 ValueError 발생 (fill()이 자동으로 잘라버리는 것을 방지).
        """
        loc = self.page.locator(selector).first
        maxlen = loc.get_attribute("maxlength")
        if maxlen and len(name) > int(maxlen):
            raise ValueError(
                f"이름이 maxlength({maxlen}자)를 초과: {name!r} ({len(name)}자)"
            )

    # ------------------------------------------------------------------
    # 내부 유틸 - pageSize 복원
    # ------------------------------------------------------------------
    def _restore_page_size(self) -> None:
        """
        CRUD 작업 후 SPA가 URL pageSize를 기본값(20)으로 리셋할 수 있다.
        pageSize=100 이 URL에 없으면 해시를 재설정해 목록을 100개 표시로 복원한다.
        [AUTO] 정책 탐지 / is_policy_exists 정확도 보장에 필수.
        """
        if "pageSize=100" in self.page.url:
            return
        self.page.evaluate(f"window.location.hash = '{self._HASH_PAGE_SIZE_100}';")
        self.wait_for(self.SEL_ADD_BTN)
        try:
            self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass  # 정책 0건이면 정상 통과

    # ------------------------------------------------------------------
    # 내부 유틸 - 모달 처리
    # ------------------------------------------------------------------
    def _dismiss_modal(self) -> None:
        """
        정상 흐름의 확인 모달 처리.
        모달 감지(최대 5초) → 확인 버튼 클릭 → 닫힘 대기.
        스크린샷 없음. 모달이 뜨지 않아도 정상 처리.
        사용: add_policy, modify_policy 완료 모달 등
        """
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE
            )
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        except Exception:
            pass

    def _close_modal_if_open(self) -> None:
        """
        정책 추가/수정 모달(div#addItemModal)이 열려 있으면 닫는다.
        이전 테스트가 실패하고 모달을 닫지 못한 경우의 잔여 상태를 정리한다.
        모달이 열려 있지 않으면 아무 동작 없이 반환한다.
        """
        try:
            # Bootstrap 3 모달은 is_visible() 실패 → .in 클래스 존재 여부(count)로 판단
            if self.page.locator(self.SEL_ADD_MODAL).count() > 0:
                self.click(self.SEL_CLOSE_BTN)
                self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass

    def _dismiss_stale_confirm_modal(self) -> None:
        """
        navigate_to() 호출 시 열려 있을 수 있는 확인/세션만료 모달을 닫는다.
        정상 상황에서는 모달이 없으므로 1초 타임아웃으로 빠르게 통과한다.
        세션 만료 알림("로그인 정보가 만료되었거나, 접근권한이 없습니다.") 모달도
        div#__globalMessageModal.in 으로 동일하게 처리한다.
        """
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_STALE
            )
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        except Exception:
            pass

    def _fail_if_modal(self, timeout: int = _TIMEOUT_TABLE) -> None:
        """
        예상치 못한 모달이 나타나면 스크린샷 저장 후 Exception 발생.
        정상 상황(모달 없음)이면 아무 동작 없이 반환.
        사용: click_policy_row() 직후 에러 모달 조기 감지
        """
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=timeout
            )
        except Exception:
            return  # 모달 없음 → 정상
        msg = self.get_modal_message()
        self.take_screenshot("unexpected_modal")
        self.click_attached(self.SEL_CONFIRM_BTN)
        self.wait_for_modal_closed()
        raise Exception(f"예상치 못한 모달 발생: {msg!r}")

    # ------------------------------------------------------------------
    # Universal Scanner 표준 인터페이스 구현
    # ------------------------------------------------------------------

    # AUTO_NAME_PREFIX: maxlength=20 제약 대응 (10자 → _p1/_p2 추가 시 최대 13자)
    AUTO_NAME_PREFIX = "[AUTO]_det"

    def save_policy(self, name: str) -> None:
        """Phase 1/2 완료 후 정책 저장 (이름 + 확장자 필수)."""
        self.fill(self.SEL_POLICY_NAME, name)
        if self.page.locator("i.extentionDeleteBtn").count() == 0:
            self.fill(self.SEL_EXTENSION_INPUT, "txt")
            self.click(self.SEL_EXTENSION_ADD_BTN)
            self.page.wait_for_timeout(300)
        self.click(self.SEL_REGISTER_BTN)
        self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.click_attached(self.SEL_CONFIRM_BTN)
        self.wait_for_modal_closed()
        self.wait_for(self.SEL_ADD_BTN)

    def close_edit_modal(self) -> None:
        """Phase 3 EDIT 모달 닫기 — known_bug로 이미 닫혔을 수 있으므로 조건부."""
        try:
            if self.page.locator(self.SEL_ADD_MODAL).count() > 0:
                self.close_modal()
            else:
                self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass

    def get_verify_values(self, saved_name: str) -> dict:
        """Phase 3: EDIT 모달 로드 후 정책 이름 필드 값 확인."""
        return {"input#rcDetectPolicyName": saved_name}
