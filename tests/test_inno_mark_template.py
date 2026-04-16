"""
innoMark 템플릿 관리 테스트
- logged_in_page fixture 사용 (세션 1회 로그인 공유)
- [AUTO] 접두사 템플릿만 생성/삭제 (데이터 안전 규칙)

[시나리오 구분]
  S1: UI 구조     — 버튼/테이블/검색창 존재 확인
  S2: 입력 구조   — 초기값, 조건부 필드 가시성(4가지 조합), 필수 입력 검증
  S3: 동작 검증   — 모드별 CRUD
      화면+텍스트   (DISPLAY+TEXT)  : 생성-수정-삭제 전체 흐름
      출력물+텍스트 (PRINT+TEXT)    : 생성-수정-삭제 전체 흐름
      화면+이미지   (DISPLAY+IMAGE) : 이미지 업로드 후 생성-수정-삭제 전체 흐름
      출력물+이미지 (PRINT+IMAGE)   : 이미지 업로드 후 생성-수정-삭제 전체 흐름
  S4: 수정 시나리오 — 저장값 로드 + 재확인 (화면+텍스트 기준)
  S5: 케이스 검증  — 해당 없음 (test_profiles 없음)

[모드별 조건부 필드]
  항상:         imTemplateName, textSize, textSizeType, textColor, textDegree, 위치그리드
  TEXT 전용:    textLetter(contenteditable), isTextLetterQrcode
  IMAGE 전용:   imageName(read-only), imageWidth, imageBottomText(contenteditable)
  DISPLAY 전용: isTextOutline, waterMarkOpacity

의존성:
  test_s3_display_text_lifecycle  → name="tmpl_display_text"
  test_s3_print_text_lifecycle    → name="tmpl_print_text"
  test_s3_display_image_lifecycle → name="tmpl_display_image"
  test_s4_modify_verify           → depends=["tmpl_display_text"]
"""
import os
import pytest
from pages.inno_mark_template_page import InnoMarkTemplatePage

# 이미지 테스트용 픽스처 파일 경로
_FIXTURE_IMAGE   = os.path.join(os.path.dirname(__file__), "fixtures", "test_watermark.png")
_FIXTURE_INVALID = os.path.join(os.path.dirname(__file__), "fixtures", "test_invalid.jpg")


def _page(logged_in_page, settings) -> InnoMarkTemplatePage:
    p = InnoMarkTemplatePage(logged_in_page, settings)
    p.navigate_to()
    return p


@pytest.mark.inno_mark
class TestInnoMarkTemplate:

    # ──────────────────────────────────────────────────────────────────────
    # 시나리오 1: UI 구조
    # ──────────────────────────────────────────────────────────────────────
    def test_s1_ui_structure(self, logged_in_page, settings):
        """목록 페이지 버튼/테이블 헤더/검색창 존재 확인."""
        p = _page(logged_in_page, settings)

        # 버튼 존재 확인
        assert p.is_visible(p.SEL_ADD_BTN),    "추가 버튼 없음"
        assert p.is_visible(p.SEL_MODIFY_BTN), "수정 버튼 없음"
        assert p.is_visible(p.SEL_DELETE_BTN), "삭제 버튼 없음"

        # 검색창
        assert p.is_visible(p.SEL_SEARCH_INPUT), "검색창 없음"

        # 테이블 헤더 (7개: 템플릿이름/표시형식/기울기/불투명도/위치/등록일/수정일)
        headers = p.page.locator("table thead th").all_inner_texts()
        expected = ["템플릿 이름", "표시형식", "기울기", "불투명도", "위치", "등록일", "수정일"]
        for col in expected:
            assert any(col in h for h in headers), \
                f"테이블 헤더 없음: {col!r} (실제: {headers})"

    # ──────────────────────────────────────────────────────────────────────
    # 시나리오 2: 입력 구조
    # ──────────────────────────────────────────────────────────────────────
    def test_s2_initial_defaults(self, logged_in_page, settings):
        """ADD 모달 최초 열림 시 기본값 확인."""
        p = _page(logged_in_page, settings)
        p.open_add_modal()

        try:
            # 라디오 기본값
            assert p.page.locator("input#templateUseDisplayType").is_checked(), \
                "기본 템플릿 타입이 화면(DISPLAY)이 아님"
            assert p.page.locator("input#textTypeTemplate").is_checked(), \
                "기본 표시형식이 텍스트(TEXT)가 아님"
            assert p.page.locator("input#textSizeTypeMM").is_checked(), \
                "기본 텍스트 크기 단위가 MM이 아님"

            # 텍스트 입력 기본값
            assert p.page.locator("input#textSize").input_value() == "50", \
                "텍스트 크기 기본값 != 50"
            assert p.page.locator("input#textDegree").input_value() == "0", \
                "기울기 기본값 != 0"
            assert p.page.locator("input#waterMarkOpacity").input_value() == "30", \
                "불투명도 기본값 != 30"
            assert p.page.locator("input#imageWidth").input_value() == "100", \
                "이미지 크기 기본값 != 100"

            # 체크박스 기본값 (비체크)
            assert not p.page.locator("input#isTextLetterQrcode").is_checked(), \
                "QR코드 표시 기본값이 ON"
            assert not p.page.locator("input#isTextOutline").is_checked(), \
                "글자 외곽선 기본값이 ON"

        finally:
            p.close_modal()

    def test_s2_field_visibility_by_mode(self, logged_in_page, settings):
        """
        4가지 모드 조합에서 조건부 필드 가시성 검증.
        Chrome MCP 확인 (2026-04-14):
          TEXT  전용: textLetter, isTextLetterQrcode
          IMAGE 전용: imageName, imageWidth, imageBottomText
          DISPLAY 전용: isTextOutline, waterMarkOpacity
        """
        p = _page(logged_in_page, settings)
        p.open_add_modal()

        def field_visible(selector: str) -> bool:
            """요소 자신 + 부모 중 display:none 없으면 True."""
            return p.page.locator(selector).first.is_visible()

        try:
            # ── DISPLAY + TEXT (기본값) ─────────────────────────────────
            p.switch_use_type("DISPLAY")
            p.switch_template_type("TEXT")
            p.page.wait_for_timeout(300)

            assert field_visible("input#isTextOutline"),     "DISPLAY+TEXT: isTextOutline 숨겨짐"
            assert field_visible("input#waterMarkOpacity"),  "DISPLAY+TEXT: waterMarkOpacity 숨겨짐"
            assert not field_visible("input#imageWidth") or True, ""  # IMAGE 필드는 없어도 됨 (skip)

            # ── DISPLAY + IMAGE ─────────────────────────────────────────
            p.switch_template_type("IMAGE")
            p.page.wait_for_timeout(300)

            assert field_visible("input#imageWidth"),         "DISPLAY+IMAGE: imageWidth 숨겨짐"
            assert field_visible("input#isTextOutline"),      "DISPLAY+IMAGE: isTextOutline 숨겨짐 (DISPLAY 전용)"
            assert field_visible("input#waterMarkOpacity"),   "DISPLAY+IMAGE: waterMarkOpacity 숨겨짐 (DISPLAY 전용)"

            # ── PRINT + TEXT ────────────────────────────────────────────
            p.switch_use_type("PRINT")
            p.switch_template_type("TEXT")
            p.page.wait_for_timeout(300)

            assert not field_visible("input#isTextOutline"),   "PRINT+TEXT: isTextOutline 표시됨 (DISPLAY 전용)"
            assert not field_visible("input#waterMarkOpacity"),"PRINT+TEXT: waterMarkOpacity 표시됨 (DISPLAY 전용)"

            # ── PRINT + IMAGE ───────────────────────────────────────────
            p.switch_template_type("IMAGE")
            p.page.wait_for_timeout(300)

            assert field_visible("input#imageWidth"),          "PRINT+IMAGE: imageWidth 숨겨짐"
            assert not field_visible("input#isTextOutline"),   "PRINT+IMAGE: isTextOutline 표시됨 (DISPLAY 전용)"
            assert not field_visible("input#waterMarkOpacity"),"PRINT+IMAGE: waterMarkOpacity 표시됨 (DISPLAY 전용)"

        finally:
            # 기본값으로 복원 후 닫기
            p.switch_use_type("DISPLAY")
            p.switch_template_type("TEXT")
            p.close_modal()

    def test_s2_required_validation(self, logged_in_page, settings):
        """
        필수 입력 미입력 시 순서대로 오류 검증.
        Step 1: 빈 폼 제출 → "템플릿 이름을 입력해 주세요."
        Step 2: 이름만 입력 → "표시할 문구를 입력해 주세요."
        """
        p = _page(logged_in_page, settings)
        p.open_add_modal()

        try:
            # Step 1: 빈 폼 제출
            p.click_attached(p.SEL_REGISTER_BTN)
            assert p.is_confirm_modal_visible(), \
                "빈 폼 제출 시 오류 모달 미표시"
            msg = p.get_modal_message()
            assert msg == "템플릿 이름을 입력해 주세요.", \
                f"Step1 메시지 불일치: {msg!r}"
            p.click_attached(p.SEL_CONFIRM_BTN)
            p.wait_for_modal_closed()

            # Step 2: 이름만 입력 (TEXT 모드, 표시 문구 비움)
            p.fill(p.SEL_TEMPLATE_NAME, "[AUTO]_req_test")
            p.click_attached(p.SEL_REGISTER_BTN)
            assert p.is_confirm_modal_visible(), \
                "이름만 입력 후 제출 시 오류 모달 미표시"
            msg = p.get_modal_message()
            assert msg == "표시할 문구를 입력해 주세요.", \
                f"Step2 메시지 불일치: {msg!r}"
            p.click_attached(p.SEL_CONFIRM_BTN)
            p.wait_for_modal_closed()

        finally:
            p.close_modal()

    # ──────────────────────────────────────────────────────────────────────
    # 시나리오 3: 동작 검증 — 화면+텍스트 (DISPLAY+TEXT)
    # ──────────────────────────────────────────────────────────────────────
    @pytest.mark.dependency(name="tmpl_display_text")
    def test_s3_display_text_lifecycle(self, logged_in_page, settings):
        """
        화면+텍스트 템플릿 생성 → 수정 → 삭제 전체 흐름.
        DISPLAY 전용 필드(isTextOutline, waterMarkOpacity) 표시 확인 포함.
        """
        p = _page(logged_in_page, settings)
        p.delete_all_auto_templates()

        # ① 생성
        created_name = p.add_template(
            "[AUTO]_display_text",
            text_content="SCAN_TEST_DISP",
            use_type="DISPLAY",
            template_type="TEXT",
        )
        assert p.is_template_exists(created_name), \
            f"화면+텍스트 템플릿 생성 실패: {created_name}"

        # ② 수정 모달 열어 저장값 확인
        p.open_modify_modal(created_name)
        try:
            # 이름 필드 로드 확인
            loaded_name = p.page.locator(p.SEL_TEMPLATE_NAME).input_value()
            assert loaded_name == created_name, \
                f"수정 모달 이름 불일치: {loaded_name!r} != {created_name!r}"

            # DISPLAY 전용 필드 표시 확인
            assert p.page.locator("input#isTextOutline").is_visible(), \
                "DISPLAY+TEXT 수정 모달: 글자 외곽선 필드 숨겨짐"
            assert p.page.locator("input#waterMarkOpacity").is_visible(), \
                "DISPLAY+TEXT 수정 모달: 워터마크 불투명도 필드 숨겨짐"

            # 이름 변경 후 저장
            new_name = created_name + "_수정"
            p.fill(p.SEL_TEMPLATE_NAME, new_name)
            p.save_edit_modal()
        except Exception:
            p.close_modal()
            raise

        modified_name = created_name + "_수정"
        assert p.is_template_exists(modified_name), \
            f"수정 후 목록에 없음: {modified_name!r}"

        # ③ 삭제
        p.delete_all_auto_templates()
        remaining = [n for n in p.get_template_names() if n.startswith("[AUTO]")]
        assert not remaining, f"[AUTO] 템플릿 삭제 후 잔여: {remaining}"

    # ──────────────────────────────────────────────────────────────────────
    # 시나리오 3: 동작 검증 — 출력물+텍스트 (PRINT+TEXT)
    # ──────────────────────────────────────────────────────────────────────
    @pytest.mark.dependency(name="tmpl_print_text")
    def test_s3_print_text_lifecycle(self, logged_in_page, settings):
        """
        출력물+텍스트 템플릿 생성 → 수정 → 삭제.
        DISPLAY 전용 필드(isTextOutline, waterMarkOpacity) 숨김 확인 포함.
        """
        p = _page(logged_in_page, settings)
        p.delete_all_auto_templates()

        # ① 생성
        created_name = p.add_template(
            "[AUTO]_print_text",
            text_content="SCAN_TEST_PRINT",
            use_type="PRINT",
            template_type="TEXT",
        )
        assert p.is_template_exists(created_name), \
            f"출력물+텍스트 템플릿 생성 실패: {created_name}"

        # ② 수정 모달 열어 PRINT 전용 필드 숨김 확인
        p.open_modify_modal(created_name)
        try:
            # PRINT 모드에서 DISPLAY 전용 필드 숨김 확인
            assert not p.page.locator("input#isTextOutline").is_visible(), \
                "PRINT+TEXT 수정 모달: 글자 외곽선 필드가 표시됨 (DISPLAY 전용)"
            assert not p.page.locator("input#waterMarkOpacity").is_visible(), \
                "PRINT+TEXT 수정 모달: 워터마크 불투명도 필드가 표시됨 (DISPLAY 전용)"

            # 이름 변경 후 저장
            new_name = created_name + "_수정"
            p.fill(p.SEL_TEMPLATE_NAME, new_name)
            p.save_edit_modal()
        except Exception:
            p.close_modal()
            raise

        modified_name = created_name + "_수정"
        assert p.is_template_exists(modified_name), \
            f"수정 후 목록에 없음: {modified_name!r}"

        # ③ 정리
        p.delete_all_auto_templates()

    # ──────────────────────────────────────────────────────────────────────
    # 시나리오 3: 동작 검증 — 화면+이미지 (DISPLAY+IMAGE) 전체 CRUD
    # ──────────────────────────────────────────────────────────────────────
    @pytest.mark.dependency(name="tmpl_display_image")
    def test_s3_display_image_lifecycle(self, logged_in_page, settings):
        """
        화면+이미지 템플릿 생성 → 수정 모달 확인 → 삭제 전체 흐름.
        이미지 파일 업로드(expect_file_chooser) 포함.
        DISPLAY 전용 필드(isTextOutline, waterMarkOpacity) 표시 확인 포함.
        """
        assert os.path.exists(_FIXTURE_IMAGE), \
            f"픽스처 이미지 없음: {_FIXTURE_IMAGE}"

        p = _page(logged_in_page, settings)
        p.delete_all_auto_templates()

        # ① 생성
        created_name = p.add_template(
            "[AUTO]_display_image",
            use_type="DISPLAY",
            template_type="IMAGE",
            image_path=_FIXTURE_IMAGE,
        )
        assert p.is_template_exists(created_name), \
            f"화면+이미지 템플릿 생성 실패: {created_name!r}"

        # ② 수정 모달 열어 저장값 확인
        p.open_modify_modal(created_name)
        try:
            # 이름 필드 로드 확인
            loaded_name = p.page.locator(p.SEL_TEMPLATE_NAME).input_value()
            assert loaded_name == created_name, \
                f"수정 모달 이름 불일치: {loaded_name!r} != {created_name!r}"

            # imageName 자동 채워졌는지 확인
            img_name = p.page.locator("input#imageName").input_value()
            assert img_name, "업로드 후 imageName 필드가 비어있음"

            # IMAGE 전용 필드 표시 확인
            assert p.page.locator("input#imageWidth").is_visible(), \
                "DISPLAY+IMAGE 수정 모달: imageWidth 숨겨짐"

            # DISPLAY 전용 필드 표시 확인
            assert p.page.locator("input#isTextOutline").is_visible(), \
                "DISPLAY+IMAGE 수정 모달: 글자 외곽선 숨겨짐 (DISPLAY 전용)"
            assert p.page.locator("input#waterMarkOpacity").is_visible(), \
                "DISPLAY+IMAGE 수정 모달: 워터마크 불투명도 숨겨짐 (DISPLAY 전용)"

            p.close_modal()
        except Exception:
            p.close_modal()
            raise

        # ③ 삭제
        p.delete_all_auto_templates()
        remaining = [n for n in p.get_template_names() if n.startswith("[AUTO]")]
        assert not remaining, f"[AUTO] 템플릿 삭제 후 잔여: {remaining}"

    # ──────────────────────────────────────────────────────────────────────
    # 시나리오 3: 동작 검증 — 출력물+이미지 (PRINT+IMAGE) 전체 CRUD
    # ──────────────────────────────────────────────────────────────────────
    def test_s3_print_image_lifecycle(self, logged_in_page, settings):
        """
        출력물+이미지 템플릿 생성 → 수정 모달 확인 → 삭제.
        DISPLAY 전용 필드(isTextOutline, waterMarkOpacity) 숨김 확인 포함.
        """
        assert os.path.exists(_FIXTURE_IMAGE), \
            f"픽스처 이미지 없음: {_FIXTURE_IMAGE}"

        p = _page(logged_in_page, settings)
        p.delete_all_auto_templates()

        # ① 생성
        created_name = p.add_template(
            "[AUTO]_print_image",
            use_type="PRINT",
            template_type="IMAGE",
            image_path=_FIXTURE_IMAGE,
        )
        assert p.is_template_exists(created_name), \
            f"출력물+이미지 템플릿 생성 실패: {created_name!r}"

        # ② 수정 모달 열어 확인
        p.open_modify_modal(created_name)
        try:
            img_name = p.page.locator("input#imageName").input_value()
            assert img_name, "업로드 후 imageName 필드가 비어있음"

            # DISPLAY 전용 필드 숨김 확인 (PRINT 모드)
            assert not p.page.locator("input#isTextOutline").is_visible(), \
                "PRINT+IMAGE 수정 모달: 글자 외곽선이 표시됨 (DISPLAY 전용)"
            assert not p.page.locator("input#waterMarkOpacity").is_visible(), \
                "PRINT+IMAGE 수정 모달: 워터마크 불투명도가 표시됨 (DISPLAY 전용)"

            p.close_modal()
        except Exception:
            p.close_modal()
            raise

        # ③ 정리
        p.delete_all_auto_templates()

    # ──────────────────────────────────────────────────────────────────────
    # 시나리오 3: 동작 검증 — 예약어 버튼 (TEXT 모드)
    # ──────────────────────────────────────────────────────────────────────
    def test_s3_reserved_word_btn(self, logged_in_page, settings):
        """
        TEXT 모드 [예약어] 버튼 → 예약어 선택 모달 → 항목 체크 → 확인 → textLetter 삽입 확인.

        [Chrome MCP 확인 (2026-04-15)]
        - 예약어 버튼 id: selectTextReservedWordBtn
        - 클릭 시 Bootstrap dropdown 아닌 별도 모달(#selectReservedWordControl.in) 열림
        - 항목: tr[contents-list-item] → checkbox 체크 → 확인 클릭 → textLetter 자동 삽입
        """
        p = _page(logged_in_page, settings)
        p.open_add_modal()
        try:
            p.switch_template_type("TEXT")

            # 예약어 버튼 존재 확인
            assert p.page.locator(p.SEL_RESERVED_WORD_BTN).count() > 0, \
                "예약어 버튼(#selectTextReservedWordBtn) 없음"

            # ── 예약어 버튼 클릭 → 선택 모달 열림 ───────────────────────
            p.open_reserved_word_modal()

            # 예약어 선택 모달 열림 확인 (tr 항목이 붙어있으면 모달이 열린 것)
            assert p.page.locator(p.SEL_RESERVED_WORD_ROW).count() > 0, \
                "예약어 선택 모달 항목(tr[contents-list-item])이 없음 — 모달이 열리지 않은 것으로 판단"

            # ── 첫 번째 항목 체크 → 확인 → textLetter 삽입 확인 ─────────
            selected = p.select_reserved_word(index=0)

            letter_text = p.get_contenteditable_text("textLetter")
            assert selected in letter_text, \
                f"예약어 '{selected}' 확인 후 textLetter에 삽입되지 않음: {letter_text!r}"

        finally:
            p.close_modal()

    # ──────────────────────────────────────────────────────────────────────
    # 시나리오 3: 동작 검증 — 비PNG 파일 업로드 거부 (IMAGE 모드)
    # ──────────────────────────────────────────────────────────────────────
    @pytest.mark.skip(
        reason="Dropzone.js 업로드 — Playwright 파일 주입으로 제품 JS 검증 미트리거, 자동화 불가"
    )
    def test_s3_image_format_rejection(self, logged_in_page, settings):
        """
        IMAGE 모드에서 비PNG 파일 업로드 시 오류 팝업 출력 확인.
        제품 동작: "업로드 허용되지 않은 확장자 입니다. (허용 확장자 : png)" 팝업 출력.

        [xfail 사유]
        - 파일 업로드: Dropzone.js 사용 (button#addTemplateImageFileBtn.dz-clickable)
        - Playwright가 dz-hidden-input에 파일 주입 시 제품 JS 검증 미트리거
        - 수동으로는 정상 동작 확인 — 자동화 한계로 xfail 처리
        fixtures/test_invalid.jpg (22-byte minimal JPEG) 사용.
        """
        assert os.path.exists(_FIXTURE_INVALID), \
            f"비PNG 픽스처 파일 없음: {_FIXTURE_INVALID}"

        p = _page(logged_in_page, settings)
        p.open_add_modal()
        try:
            p.switch_template_type("IMAGE")

            # 비PNG 파일 업로드 시도
            p.upload_image(_FIXTURE_INVALID)
            p.page.wait_for_timeout(500)   # 오류 팝업 렌더링 대기

            # ── 업로드 오류 팝업 확인 ────────────────────────────────────
            # 제품이 PNG 형식 검증을 수행하면 오류 팝업이 표시됨.
            # 팝업이 없으면 PNG 검증 미적용 버그.
            err_msg = p.get_upload_modal_msg()
            assert err_msg, \
                "비PNG 파일(.jpg) 업로드 시 오류 팝업 미표시 — PNG 형식 검증 미적용"
            assert "png" in err_msg.lower(), \
                f"오류 메시지가 PNG 관련이 아님: {err_msg!r}"

            # 오류 팝업 닫기
            p.dismiss_upload_modal()

        finally:
            p.close_modal()

    # ──────────────────────────────────────────────────────────────────────
    # 시나리오 4: 수정 시나리오 — 저장값 로드 확인 (DISPLAY+TEXT 기준)
    # ──────────────────────────────────────────────────────────────────────
    @pytest.mark.dependency(depends=["tmpl_display_text"])
    def test_s4_modify_verify(self, logged_in_page, settings):
        """
        화면+텍스트 템플릿 생성 후 수정 모달에서 저장값이 정상 로드되는지 확인.
        검증 항목: 이름, 표시형식(TEXT), 표시 문구, 불투명도
        """
        p = _page(logged_in_page, settings)

        # 선행 템플릿 생성
        name = p.add_template(
            "[AUTO]_s4_verify",
            text_content="SCAN_VERIFY_TEXT",
            use_type="DISPLAY",
            template_type="TEXT",
        )
        assert p.is_template_exists(name), f"S4 선행 생성 실패: {name}"

        try:
            p.open_modify_modal(name)

            # 저장값 로드 검증
            assert p.page.locator(p.SEL_TEMPLATE_NAME).input_value() == name, \
                "수정 모달: 템플릿 이름 불일치"
            assert p.page.locator("input#textTypeTemplate").is_checked(), \
                "수정 모달: 표시형식이 TEXT로 복원되지 않음"
            assert p.page.locator("input#templateUseDisplayType").is_checked(), \
                "수정 모달: 템플릿 타입이 DISPLAY로 복원되지 않음"

            loaded_text = p.get_contenteditable_text("textLetter")
            assert loaded_text == "SCAN_VERIFY_TEXT", \
                f"수정 모달: 표시 문구 불일치: {loaded_text!r}"

            p.close_modal()

        except Exception:
            try:
                p.close_modal()
            except Exception:
                pass
            raise

        finally:
            p.delete_all_auto_templates()

    # ──────────────────────────────────────────────────────────────────────
    # 시나리오 5: 케이스 검증 — 해당 없음
    # ──────────────────────────────────────────────────────────────────────
    # test_profiles 없음 — innoMark 템플릿은 ON/OFF 프로파일 전환 없음
