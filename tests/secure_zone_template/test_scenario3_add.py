"""시큐어존 템플릿(시큐어 드라이브) — 시나리오 3: 동작/CRUD (ADD).

이 탭의 핵심 = **addSecureDriveBtn 서브모달로 시큐어드라이브 항목(N건)을 추가**하는 시스템(사용자 지정 2026-06-23).
완전 생성 필수: 이름 + 시큐어드라이브 항목 ≥1(서브) + 반출드라이브 4필드. 저장 버튼=확인.
보고서엔 _add(detail="입력:X / 결과:Y", repro="단계"). [AUTO] 만 생성, cleanup 은 sc1/sc5 에서만.
※ 모든 카드는 실제 결과로 PASS/WARN/FAIL 동적 판정 — 주석 거동은 작성 시점 관측 참고일 뿐 단정 아님.
"""
from pages.secure_zone_template_page import SecureZoneTemplateSecureDrivePage
from tests.secure_zone_template._base import SecureZoneTemplateBase


class TestSecureZoneTemplateScenario3Add(SecureZoneTemplateBase):
    """시큐어존 템플릿(시큐어 드라이브) — 시나리오 3: ADD."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSecureDrivePage(logged_in_page, settings)
        self._page = page.page
        return page

    # ══ 3a: 빈값 저장 차단 (필수 검증) ════════════════════════════
    def test_scenario3a_required_empty(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3a: 빈값 저장 차단 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()
        msg = page.submit_and_message()
        blocked = ("저장" not in msg) and bool(msg)
        self._add("pass" if blocked else "fail",
                  "sc3a — 필수 빈값 저장 차단",
                  f"입력: 전 필드 빈값 + 확인 / 결과: 경고={msg!r} "
                  + ("(차단됨)" if blocked else "[차단 안 됨 — 빈값 저장 가능하면 결함]"),
                  sc=3, highlight=page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}"),
                  repro="1. 템플릿 추가\n2. 아무것도 안 채우고 '확인'\n3. 필수 경고로 차단되는지 확인")
        page._close_modal_if_open()

    # ══ 3b: 이름 중복 차단 ════════════════════════════════════════
    def test_scenario3b_name_duplicate(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3b: 이름 중복 차단 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_dup"
        page.open_add_modal()
        msg1 = page.create_basic_template(name, sd_letter="Q", to_letter="T")
        page.navigate_to()
        page.open_add_modal()
        # 드라이브 문자만 다르게 → 이름 중복만 격리
        msg2 = page.create_basic_template(name, sd_letter="R", to_letter="U")
        dup = ("이미" in msg2) or ("중복" in msg2)
        self._add("pass" if dup else "fail",
                  "sc3b — 동일 이름 재생성 중복 차단",
                  f"입력: 동일 '{name}' 2회 생성(문자만 변경) / 결과: 1차={msg1!r}, 2차={msg2!r} (기대 '이미/중복')",
                  sc=3, highlight=page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}"),
                  repro=(f"1. '{name}' 생성(1차)\n2. 같은 이름, 드라이브 문자만 변경(2차)\n3. 2차 중복 경고 확인"))
        page._close_modal_if_open()

    # ══ 3c: 정상 생성 (이름+시큐어드라이브+반출) ══════════════════
    def test_scenario3c_create_basic(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3c: 정상 생성 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_basic"
        page.open_add_modal()
        msg = page.create_basic_template(name)
        page.navigate_to()
        exists = name in page.get_template_names()
        ok = ("저장" in msg) and exists
        self._add("pass" if ok else "fail",
                  "sc3c — 정상 생성(이름+시큐어드라이브1+반출) 후 목록 등록",
                  f"입력: '{name}' (시큐어드라이브 1건 + 반출 4필드) / 결과: {msg!r}, 목록존재={exists}",
                  sc=3,
                  repro=("1. 템플릿 추가\n2. 이름 입력\n3. 시큐어드라이브 추가(서브모달)\n"
                         "4. 반출드라이브 입력\n5. 확인\n6. 목록에 등록 확인"))

    # ══ 3d: 시큐어드라이브 서브모달 추가 → 메인 리스트 반영 (핵심) ══
    def test_scenario3d_secure_drive_add(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3d: 시큐어드라이브 항목 추가 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.fill(page.SEL_NAME, f"{page.AUTO_NAME_PREFIX}_sd")
        # WRITE(직접입력) 항목
        page.add_secure_drive("lbl_w", "Q", "C:\\sd_w", "WRITE", "100")
        rows_after_write = page.secure_drive_rows()
        # SYNC(잔여용량 동기화) 항목 추가 (multi-add)
        page.add_secure_drive("lbl_s", "R", "C:\\sd_s", "SYNC")
        rows_after_sync = page.secure_drive_rows()
        added_write = any("lbl_w" in r or "Q" in r for r in rows_after_write)
        added_two = len(rows_after_sync) >= 2
        self._add("pass" if (added_write and added_two) else "fail",
                  "sc3d — 시큐어드라이브 서브모달 추가 → 메인 리스트 반영(WRITE+SYNC 2건)",
                  f"입력: 서브모달로 WRITE 1건+SYNC 1건 추가 / 결과: 1건후={rows_after_write}, "
                  f"2건후 {len(rows_after_sync)}행={rows_after_sync}",
                  sc=3, repro=("1. 템플릿 추가\n2. 시큐어드라이브 추가→WRITE 항목 채우고 추가\n"
                               "3. 다시 추가→SYNC 항목 추가\n4. 메인 리스트에 2건 반영 확인"))
        page._close_modal_if_open()

    # ══ 3e: 반출드라이브 누락 시 저장 차단 ════════════════════════
    def test_scenario3e_takeout_required(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3e: 반출드라이브 필수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.fill(page.SEL_NAME, f"{page.AUTO_NAME_PREFIX}_noto")
        page.add_secure_drive("lbl", "Q", "C:\\sd", "WRITE", "100")
        # 반출드라이브 비운 채 저장 시도
        msg = page.submit_and_message()
        blocked = ("저장" not in msg) and ("반출" in msg or bool(msg))
        self._add("pass" if blocked else "fail",
                  "sc3e — 시큐어드라이브만 있고 반출 빈값 → 저장 차단",
                  f"입력: 이름+시큐어드라이브1, 반출 빈값 + 확인 / 결과: 경고={msg!r} "
                  + ("(차단됨)" if blocked else "[차단 안 됨 — 반출 없이 저장되면 결함]"),
                  sc=3, highlight=page.page.locator(f"{page.SEL_MODAL} {page.SEL_TAKEOUT_PATH}"),
                  repro="1. 추가\n2. 이름+시큐어드라이브만\n3. 반출 빈값으로 확인\n4. 반출 필수 경고 확인")
        page._close_modal_if_open()
