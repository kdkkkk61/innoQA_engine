"""시큐어존 템플릿(특수폴더) — 시나리오 3: 동작 (빡빡, 생성 흐름 중심).

sc3 = "바로가기를 생성해보며 이슈 잡고, 레지변경을 생성해보며 이슈 잡는다" — 용도별 흐름 따로.
각 단계가 '이 행동을 하면 이렇게 된다' 시나리오. 메시지는 직접조작 수집값(2026-06-30) == 비교.
관리자 예약어 게이팅은 '존재(차단 메시지+인증필드)'까지만 — 비번 인증/암호화/복호화는 user-driven(제외).

[바로가기 생성 흐름]
sc3a — 바로가기 템플릿 생성(정상) → 리스트 등장 + 용도=바로가기(Link)
sc3b — 같은 이름 또 생성 → '이미 등록된 이름 입니다.' 차단
sc3c — 폴더 매핑 추가(예약어 picker 로 원본/대상) → 커밋 + 등록된 경로 +1
sc3d — 폴더 매핑 추가 후 제거(-) → 확인 '선택한 항목을 삭제 하시겠습니까?' → 등록 -1
[레지변경 생성 흐름]
sc3e — 레지변경 템플릿 생성(정상) → 용도=레지스트변경
sc3f — ★레지변경 폴더에 관리자 예약어([/RUN/]/[/DSEC/]) → 추가 → 비밀번호 인증 게이팅(관리자 기능 존재)
[list-level]
sc3g — 복사 → '선택한 항목을 복사 하시겠습니까?' → '<이름>_copy' 생성
sc3h — 검색 → 이름으로 필터
"""
from pages.secure_zone_template_manage_folder_page import SecureZoneTemplateManageFolderPage
from tests.secure_zone_template_manage_folder._base import SecureZoneTemplateManageFolderBase


class TestSecureZoneTemplateManageFolderScenario3Action(SecureZoneTemplateManageFolderBase):
    """시큐어존 템플릿(특수폴더) — 시나리오 3: 동작."""

    _LINK = "[AUTO]_sz_mf_link"     # 바로가기 흐름
    _REG  = "[AUTO]_sz_mf_reg"      # 레지변경 흐름

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateManageFolderPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _purpose(self, page, name):
        try:
            return page._row_locator(name).locator("td").nth(1).inner_text().strip()
        except Exception:
            return ""

    # ── 바로가기 생성 흐름 ─────────────────────────────────────────────
    def test_scenario3a_create_shortcut(self, logged_in_page, settings):
        print("\n━━ [특수폴더] sc3a: 바로가기 템플릿 생성(정상) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        if self._LINK in page.get_template_names():
            page.delete_template(self._LINK)
            page.navigate_to()
        page.create_template(self._LINK, "SHORTCUT")
        page.navigate_to()
        created = self._LINK in page.get_template_names()
        purpose = self._purpose(page, self._LINK)
        self._add("pass" if created and ("바로가기" in purpose) else "fail",
                  "sc3a — 바로가기 템플릿 생성 → 리스트 등장 + 용도",
                  f"입력: 이름+바로가기 저장 / 결과: 생성={created}, 용도={purpose!r}(기대 바로가기)", sc=3,
                  repro="1. 템플릿 추가\n2. 이름+바로가기\n3. 확인\n4. 리스트 등장·용도 확인")

    def test_scenario3b_duplicate_name(self, logged_in_page, settings):
        print("\n━━ [특수폴더] sc3b: 이름 중복 차단 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._LINK, "SHORTCUT")
        page.open_add_modal()
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", self._LINK)
        msg = page.submit_and_message()
        self._add("pass" if "이미 등록된 이름" in msg else "fail",
                  "sc3b — 같은 이름 또 생성 → 중복 차단",
                  f"입력: 기존 이름 재생성 / 결과: 경고={msg!r} (기대 '이미 등록된 이름 입니다.')", sc=3,
                  repro="1. 기존 이름으로 추가\n2. 확인\n3. 중복 경고")
        page._close_modal_if_open()

    def test_scenario3c_folder_add_via_picker(self, logged_in_page, settings):
        print("\n━━ [특수폴더] sc3c: 폴더 매핑 추가(예약어 picker) → 등록 반영 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._LINK, "SHORTCUT")
        page.open_folder_modal(self._LINK)
        before = page.folder_item_count()
        page.open_content_add()
        msg = page.add_folder_mapping("mapping_pick", use_picker=True, src_index=0, tgt_index=1)
        after = page.folder_item_count()
        ok = (msg.strip() == "") and (after == before + 1)
        self._add("pass" if ok else "fail",
                  "sc3c — 폴더 매핑 추가(예약어 picker 원본/대상) → 등록된 경로 +1",
                  f"입력: picker 로 원본([/DESKTOP/])·대상([/MYDOC/]) 선택 후 추가 / "
                  f"결과: 경고={msg!r}, 등록 {before}→{after}", sc=3,
                  repro="1. 폴더 추가/제거 +\n2. 특수폴더 picker 로 원본·대상 예약어\n3. 추가\n4. 등록된 경로 증가")
        page.close_folder_modal()

    def test_scenario3d_folder_remove(self, logged_in_page, settings):
        print("\n━━ [특수폴더] sc3d: 폴더 매핑 추가 후 제거(-) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        rm_tpl = "[AUTO]_sz_mf_rm"
        page.ensure_template(rm_tpl, "SHORTCUT")
        page.open_folder_modal(rm_tpl)
        # 제거할 항목 1개 보장
        page.open_content_add()
        page.add_folder_mapping("mapping_rm", use_picker=True, src_index=0, tgt_index=1)
        before = page.folder_item_count()
        msg = page.remove_folder_item(0)
        after = page.folder_item_count()
        ok = ("삭제 하시겠습니까" in msg) and (after == before - 1)
        self._add("pass" if ok else "fail",
                  "sc3d — 폴더 항목 제거(-) → 확인 → 등록된 경로 -1",
                  f"입력: 항목 선택 + 제거 / 결과: 확인메시지={msg!r}, 등록 {before}→{after}", sc=3,
                  repro="1. 폴더 항목 체크\n2. - 버튼\n3. '선택한 항목을 삭제 하시겠습니까?' 확인\n4. 등록 감소")
        page.close_folder_modal()

    # ── 레지변경 생성 흐름 ─────────────────────────────────────────────
    def test_scenario3e_create_regist(self, logged_in_page, settings):
        print("\n━━ [특수폴더] sc3e: 레지변경 템플릿 생성(정상) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        if self._REG in page.get_template_names():
            page.delete_template(self._REG)
            page.navigate_to()
        page.create_template(self._REG, "MODIFY_REGIST")
        page.navigate_to()
        created = self._REG in page.get_template_names()
        purpose = self._purpose(page, self._REG)
        self._add("pass" if created and ("레지스트" in purpose) else "fail",
                  "sc3e — 레지변경 템플릿 생성 → 리스트 등장 + 용도",
                  f"입력: 이름+레지변경 저장 / 결과: 생성={created}, 용도={purpose!r}(기대 레지스트변경)", sc=3,
                  repro="1. 템플릿 추가\n2. 이름+레지스트리 변경\n3. 확인\n4. 용도 확인")

    def test_scenario3f_admin_reserved_word_gating(self, logged_in_page, settings):
        """★레지변경 고유 — 관리자 예약어 입력 시 비밀번호 인증 게이팅(관리자 기능 존재).
        비번 입력/암호화/복호화는 user-driven(제외) — 여기선 차단 메시지 + licensePwd 노출까지."""
        print("\n━━ [특수폴더] sc3f: 레지변경 관리자 예약어 게이팅 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._REG, "MODIFY_REGIST")
        page.open_folder_modal(self._REG)
        page.open_content_add()
        # 관리자 예약어는 일반 picker 에 없음 → 직접 입력(contenteditable)
        msg = page.add_folder_mapping("mapping_admin", source="[/RUN/]", target="[/DSEC/]", use_picker=False)
        gated = "관리자 전용 예약어가 감지되었습니다" in msg
        lic_vis = (page.field_present(page.SEL_C_LICENSE_PW)
                   and page.page.locator(page.SEL_C_LICENSE_PW).first.is_visible())
        self._add("pass" if gated and lic_vis else "fail",
                  "sc3f — 관리자 예약어([/RUN/]/[/DSEC/]) → 비밀번호 인증 게이팅(관리자 기능 존재)",
                  f"입력: 관리자 예약어로 추가 / 결과: 차단메시지={msg!r}, 관리자비번 필드 표시={lic_vis} "
                  "(비번 인증·암호화·복호화는 user-driven 제외)", sc=3,
                  repro="1. 레지변경 폴더 +\n2. 원본/대상에 관리자 예약어([/RUN/])\n3. 추가\n"
                        "4. '관리자 전용 예약어 감지' 차단 + 비밀번호 인증 필드 노출")
        page.close_content_modal()
        page.close_folder_modal()

    # ── list-level ─────────────────────────────────────────────────────
    def test_scenario3g_copy(self, logged_in_page, settings):
        print("\n━━ [특수폴더] sc3g: 복사 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._LINK, "SHORTCUT")
        copy_name = self._LINK + "_copy"
        if copy_name in page.get_template_names():
            page.delete_template(copy_name)
            page.navigate_to()
        msg = page.copy_template(self._LINK)
        page.navigate_to()
        copied = copy_name in page.get_template_names()
        self._add("pass" if ("복사 하시겠습니까" in msg) and copied else "fail",
                  "sc3g — 복사 → '<이름>_copy' 생성",
                  f"입력: 템플릿 복사 / 결과: 확인메시지={msg!r}, '{copy_name}' 생성={copied}", sc=3,
                  repro="1. 템플릿 체크\n2. 복사\n3. '선택한 항목을 복사 하시겠습니까?' 확인\n4. _copy 생성")

    # ── 직접 입력 검증 (글자수 clamp / 오버플로) ──────────────────────
    def test_scenario3i_content_name_clamp(self, logged_in_page, settings):
        """설정명 maxlength=30 → 경계+1(35자) 실타이핑 → 실제 30에서 clamp 되나 (fill 금지, 실타이핑)."""
        print("\n━━ [특수폴더] sc3i: 설정명 글자수 clamp(maxlength 30) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._LINK, "SHORTCUT")
        page.open_folder_modal(self._LINK)
        page.open_content_add()
        accepted = page.type_real(page.SEL_C_NAME, "A" * 35)
        self._add("pass" if accepted == 30 else "warn",
                  "sc3i — 설정명 글자수 clamp(maxlength 30)",
                  f"입력: 35자 실타이핑 / 결과: 실제 수용 {accepted}자 (기대 30 clamp)", sc=3,
                  repro="1. 내용 모달 설정명에 35자 실타이핑\n2. 30자에서 잘리는지")
        page.close_content_modal()
        page.close_folder_modal()

    def test_scenario3j_description_overflow(self, logged_in_page, settings):
        """설명(maxlength=null) 3000자 → '추가' → 서버 처리(오류/절단/저장). 실측: 오류 없이 3000자 저장."""
        print("\n━━ [특수폴더] sc3j: 설명 오버플로(3000자) 서버 처리 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        ovf_tpl = "[AUTO]_sz_mf_ovf"
        page.ensure_template(ovf_tpl, "SHORTCUT")
        page.open_folder_modal(ovf_tpl)
        before = page.folder_item_count()
        page.open_content_add()
        big = "A" * 3000
        msg = page.add_folder_mapping("mapping_ovf", use_picker=True, src_index=0, tgt_index=1, description=big)
        after = page.folder_item_count()
        committed = after == before + 1
        # 오류 없이 저장(커밋)됐는지 — 서버 제한 없음 확인
        self._add("pass" if (msg.strip() == "" and committed) else "warn",
                  "sc3j — 설명 3000자 오버플로 → 서버 처리",
                  f"입력: 설명 3000자 + 추가 / 결과: 경고={msg!r}, 커밋={committed}(등록 {before}→{after}) "
                  "(실측: 서버 제한/절단 없이 저장)", sc=3,
                  repro="1. 설명에 3000자\n2. 추가\n3. 서버오류/절단 없이 저장되는지")
        page.close_folder_modal()

    def test_scenario3h_search(self, logged_in_page, settings):
        print("\n━━ [특수폴더] sc3h: 검색(이름 필터) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._LINK, "SHORTCUT")
        page.search(self._LINK)
        names = page.get_template_names()
        ok = (self._LINK in names) and all(self._LINK in n for n in names)
        self._add("pass" if ok else "warn",
                  "sc3h — 이름 검색 → 해당 템플릿만 필터",
                  f"입력: 검색 '{self._LINK}' / 결과: {len(names)}건 {names[:5]}", sc=3,
                  repro="1. 검색창에 이름\n2. Enter\n3. 해당 이름만 표시")
