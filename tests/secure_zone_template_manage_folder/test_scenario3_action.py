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
[직접 입력 검증]
sc3i — 설정명 글자수 clamp(30) / sc3j — 설명 오버플로(3000자 서버 처리)
[생성 기반 보강 — 표준 대조로 추가]
sc3k — 저장값 확인(생성 후 재오픈 대조) / sc3l — 이름 특수문자(허용/검사 없음)
sc3m — 복사 충돌(_copy 존재 시 재복사 중복) / sc3n — 멀티 폴더 매핑 추가 / sc3o — 검증 메시지 i18n 전수
sc3s — 경로(원본/대상) 3000자 오버플로(사용자 발견 — raw 서버 오류)
sc3t — 템플릿 이름 글자수 clamp / sc3u — 설정명 특수문자 (전수 대조 보강 2026-07-02)

※ 삭제(리스트 단위)=sc1/sc5, 수정·제거=sc4/sc5 (sc3는 생성 기반). 3d(폴더 제거)는 sc4/sc5 이동 후보.
"""
import re

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
                  "sc3f — 관리자 예약어([/RUN/]/[/DSEC/]) → 비밀번호 인증 게이팅(존재 확인)",
                  f"입력: 관리자 예약어로 추가 / 결과: 차단메시지={msg!r}, 관리자비번 필드 표시={lic_vis}", sc=3,
                  repro="1. 레지변경 폴더 +\n2. 원본/대상에 관리자 예약어([/RUN/])\n3. 추가\n"
                        "4. '관리자 전용 예약어 감지' 차단 + 비밀번호 인증 필드 노출")
        # ★게이팅 '존재'만 자동 확인됨 — 실제 인증/암호화/복호화는 자동화 불가(비번 입력 금지) → 수동 테스트 필요를 명시적으로 남김
        self._add("warn",
                  "sc3f — [수동 확인 필요] 관리자 암호 인증 → 저장 → 설명 암호화 → 재오픈 복호화",
                  "관리자 암호가 필요한 구간이라 자동화 제외(안전규칙: 비밀번호 입력 금지). "
                  "게이팅 '존재'까지만 자동 검증됨 — 실제 인증 통과/암호화/복호화는 담당자가 관리자 암호로 수동 테스트해야 함. "
                  "(자동 pass 아님을 리포트에 남기기 위한 표식)", sc=3, screenshot=False,
                  merge_key="manual_admin_pw_crypto",   # sc4m(수정 컨텍스트) 동일 항목과 결함 카드 묶음
                  repro="1. 관리자 암호로 인증\n2. 저장 후 설명 암호화 확인\n3. 재오픈 → 복호화 버튼 → 암호로 복호화\n(모두 수동)")
        page.close_content_modal()
        page.close_folder_modal()

    # ── list-level ─────────────────────────────────────────────────────
    def test_scenario3g_copy(self, logged_in_page, settings):
        print("\n━━ [특수폴더] sc3g: 복사 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._LINK, "SHORTCUT")
        # 원본에 폴더 매핑 보장(sc3c 산출물 재사용, 없으면 1건 추가) — 복사 완전성 검증용
        page.open_folder_modal(self._LINK)
        if page.folder_item_count() == 0:
            page.open_content_add()
            page.add_folder_mapping("g_map", use_picker=True, src_index=0, tgt_index=1)
        page.close_folder_modal()
        orig_paths = page.template_path_count(self._LINK)
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
        # 복사 완전성 — 복사본이 폴더 매핑(등록된 경로)까지 복제하는가
        copy_paths = page.template_path_count(copy_name)
        same = (copy_paths == orig_paths) and (orig_paths not in (None, "0"))
        self._add("pass" if same else "warn",
                  "sc3g — 복사 완전성: 복사본 등록된 경로 = 원본(매핑까지 복제)",
                  f"입력: 매핑 있는 템플릿 복사 / 결과: 원본 등록경로={orig_paths}, 복사본={copy_paths} "
                  + ("(매핑까지 복제됨)" if same else "[경로 수 불일치 또는 원본 0 — 확인 필요]"), sc=3,
                  repro="1. 폴더 매핑 있는 템플릿 복사\n2. 복사본 '등록된 경로'가 원본과 같은지")

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

    # ── 생성 기반 보강 (표준 대조로 추가) ─────────────────────────────
    def test_scenario3k_saved_value_roundtrip(self, logged_in_page, settings):
        """생성 후 재오픈 시 저장값(설정명/원본/대상) 유지 확인 — 생성 검증(삭제·수정 아님)."""
        print("\n━━ [특수폴더] sc3k: 저장값 확인(생성 후 재오픈 대조) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_save"
        page.ensure_template(tpl, "SHORTCUT")
        page.open_folder_modal(tpl)
        setting = "chk_save"
        page.open_content_add()
        page.add_folder_mapping(setting, use_picker=True, src_index=0, tgt_index=1)  # [/DESKTOP/]→[/MYDOC/]
        page.close_folder_modal()
        # 재오픈 → 저장값 대조
        page.open_folder_modal(tpl)
        vals = " ".join(page.folder_row_values(setting))
        ok = (setting in vals) and ("[/DESKTOP/]" in vals) and ("[/MYDOC/]" in vals)
        self._add("pass" if ok else "fail",
                  "sc3k — 저장값 확인(생성 후 재오픈 대조)",
                  f"입력: {setting}/[/DESKTOP/]→[/MYDOC/] 저장 후 재오픈 / 결과: 행값={vals!r}", sc=3,
                  repro="1. 폴더 매핑 저장\n2. 폴더모달 닫고 재오픈\n3. 설정명/원본/대상 그대로인지")
        page.close_folder_modal()

    def test_scenario3l_special_char_name(self, logged_in_page, settings):
        """이름 특수문자 입력 시 처리 — 실측: 경고 없이 생성(허용, 검사 없음)."""
        print("\n━━ [특수폴더] sc3l: 이름 특수문자 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        sp = "[AUTO]_sz_mf_sp<>!@#"
        if sp in page.get_template_names():
            page.delete_template(sp); page.navigate_to()
        msg = page.create_template(sp, "SHORTCUT")
        page.navigate_to()
        created = sp in page.get_template_names()
        self._add("pass" if created else "warn",
                  "sc3l — 이름 특수문자 입력(생성 시)",
                  f"입력: 이름 '{sp}' / 결과: 경고={msg!r}, 생성={created} "
                  "(실측: 특수문자 허용 — 이름 형식 검사 없음)", sc=3,
                  repro="1. 이름에 특수문자(<>!@#)\n2. 확인\n3. 허용/차단 여부")

    def test_scenario3m_copy_collision(self, logged_in_page, settings):
        """복사본(_copy)이 이미 있는데 재복사 → 실측: 같은 '_copy' 이름 중복 생성(복사는 중복 검사 안 함)."""
        print("\n━━ [특수폴더] sc3m: 복사 충돌(_copy 존재 시 재복사) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._LINK, "SHORTCUT")
        copy_name = self._LINK + "_copy"
        if copy_name not in page.get_template_names():
            page.copy_template(self._LINK); page.navigate_to()
        before = page.get_template_names().count(copy_name)
        page.copy_template(self._LINK)   # _copy 존재 상태 재복사
        page.navigate_to()
        after = page.get_template_names().count(copy_name)
        dup = after > before
        if dup:
            page.search(copy_name)   # 스크린샷에 중복된 _copy 행만 보이게(이슈 위치 명확)
        self._add("warn" if dup else "pass",
                  "sc3m — 복사 충돌(_copy 존재 시 재복사)",
                  f"입력: '{copy_name}' 존재 상태 재복사 / 결과: '{copy_name}' {before}→{after}개 "
                  + ("(중복 생성 — 복사는 중복 검사 안 함, 수동 생성 '이미 등록된 이름' 차단과 불일치)"
                     if dup else "(중복 차단됨)"), sc=3,
                  highlight=(page.page.locator("table tbody") if dup else None),
                  repro="1. 복사본 존재 상태\n2. 원본 재복사\n3. 같은 _copy 이름 중복 생기는지")

    def test_scenario3n_multi_folder(self, logged_in_page, settings):
        """한 템플릿에 폴더 매핑 여러 개 추가 → 등록된 경로 N 증가."""
        print("\n━━ [특수폴더] sc3n: 멀티 폴더 매핑 추가 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_multi"
        page.ensure_template(tpl, "SHORTCUT")
        page.open_folder_modal(tpl)
        before = page.folder_item_count()
        page.open_content_add()
        page.add_folder_mapping("multi_1", use_picker=True, src_index=0, tgt_index=1)
        page.open_content_add()
        page.add_folder_mapping("multi_2", use_picker=True, src_index=2, tgt_index=3)
        after = page.folder_item_count()
        ok = after == before + 2
        self._add("pass" if ok else "fail",
                  "sc3n — 멀티 폴더 매핑 추가 → 등록된 경로 +2",
                  f"입력: 매핑 2건 추가 / 결과: 등록 {before}→{after} (기대 +2)", sc=3,
                  repro="1. 폴더 매핑 2개 추가\n2. 등록된 경로가 2 증가하는지")
        page.close_folder_modal()

    def test_scenario3o_i18n_sweep(self, logged_in_page, settings):
        """생성 검증 메시지 전수 — raw i18n 키(COLUMN.NAME... 류) 노출 없는지. 실측: 깨끗한 한글."""
        print("\n━━ [특수폴더] sc3o: 검증 메시지 i18n 전수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        _KEY = re.compile(r"[A-Z]{2,}[._][A-Z_.]{2,}")   # 미번역 키 패턴(예: COLUMN.NAME.XXX)
        msgs = {}
        page.open_add_modal()
        msgs["1단계 이름 빈값"] = page.submit_and_message()
        page._close_modal_if_open()
        page.ensure_template(self._LINK, "SHORTCUT")
        page.open_folder_modal(self._LINK)
        page.open_content_add()
        msgs["내용 필수 빈값"] = page.content_add_message()
        page.close_content_modal()
        page.close_folder_modal()
        leaks = {k: v for k, v in msgs.items() if _KEY.search(v or "")}
        self._add("warn" if leaks else "pass",
                  "sc3o — 검증 메시지 i18n 키 노출 전수",
                  f"입력: 생성 검증 메시지 수집 / 결과: {msgs} / 키 누출={leaks or '없음'}", sc=3,
                  repro="1. 생성 검증 경고 유발\n2. 메시지에 raw i18n 키(COLUMN.NAME 류) 없는지")

    # ── 감사로 추가 (직접 조작 실측) ───────────────────────────────────
    def test_scenario3p_list_filters(self, logged_in_page, settings):
        """리스트 필터(용도/상태) — select + 검색(돋보기) → 결과 반영. select change 만으론 미적용(실측)."""
        print("\n━━ [특수폴더] sc3p: 리스트 필터(용도/상태) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        # 용도 필터: 바로가기(Link)
        page.filter_by(template_type="바로가기(Link)")
        purposes = set(page.list_column_values(1))
        type_ok = purposes.issubset({"바로가기(Link)"})   # 바로가기만(또는 0건)
        self._add("pass" if type_ok else "fail",
                  "sc3p — 용도 필터(바로가기) → 결과 반영",
                  f"입력: 용도=바로가기 + 검색 / 결과: 용도값={purposes or '없음'} (바로가기만이어야)", sc=3,
                  repro="1. 용도 드롭다운=바로가기\n2. 검색(돋보기)\n3. 바로가기만 표시")
        page.filter_by(template_type="전체")   # 리셋
        # 상태 필터: 활성
        page.filter_by(status="활성")
        statuses = set(page.list_column_values(3))
        status_ok = statuses.issubset({"활성"})
        self._add("pass" if status_ok else "fail",
                  "sc3p — 상태 필터(활성) → 결과 반영",
                  f"입력: 상태=활성 + 검색 / 결과: 상태값={statuses or '없음'} (활성만이어야)", sc=3,
                  repro="1. 상태 드롭다운=활성\n2. 검색(돋보기)\n3. 활성만 표시")
        page.filter_by(status="상태")   # 리셋(기본)

    def test_scenario3q_folder_item_duplicate(self, logged_in_page, settings):
        """폴더 항목 중복(같은 설정명) → '이미 등록된 이름 입니다.' 차단(실측)."""
        print("\n━━ [특수폴더] sc3q: 폴더 항목 중복 차단 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_dup"
        page.ensure_template(tpl, "SHORTCUT")
        page.open_folder_modal(tpl)
        # 기준 항목(dup1) 없으면 추가
        if not page.folder_row_values("dup1"):
            page.open_content_add()
            page.add_folder_mapping("dup1", use_picker=True, src_index=0, tgt_index=1)
        # 같은 설정명으로 재추가 → 차단?
        page.open_content_add()
        msg = page.add_folder_mapping("dup1", use_picker=True, src_index=0, tgt_index=1)
        blocked = "이미 등록된 이름" in msg
        self._add("pass" if blocked else "warn",
                  "sc3q — 폴더 항목 중복(같은 설정명) → 차단",
                  f"입력: 같은 설정명 'dup1' 재추가 / 결과: 경고={msg!r} (기대 '이미 등록된 이름 입니다.')", sc=3,
                  repro="1. 폴더 항목 추가(dup1)\n2. 같은 설정명 dup1 재추가\n3. 중복 차단 경고")
        page.close_content_modal()
        page.close_folder_modal()

    def test_scenario3r_example_import(self, logged_in_page, settings):
        """엑셀 대량 Example(다운로드)/Import(업로드) — 존재 확인 + 실제 동작은 [수동 확인 필요](자동화 경계)."""
        print("\n━━ [특수폴더] sc3r: Example/Import(엑셀 대량) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._LINK, "SHORTCUT")
        page.open_folder_modal(self._LINK)
        fm = page.SEL_FOLDER_MODAL
        ex = page.page.locator(f"{fm} button", has_text="Example").count() > 0
        im = page.page.locator(f"{fm} button", has_text="Import").count() > 0
        self._add("pass" if (ex and im) else "skip",
                  "sc3r — Example/Import 버튼 존재(엑셀 대량 export/import)",
                  f"결과: Example={ex}, Import={im}", sc=3,
                  repro="1. 폴더 추가/제거 모달\n2. Example/Import 버튼 존재")
        self._add("warn",
                  "sc3r — [수동 확인 필요] Example 다운로드 / Import 업로드 실제 동작",
                  "엑셀 예제 다운로드·대량 가져오기는 파일 다운로드/업로드라 자동화 제외(안전규칙). "
                  "존재만 자동 확인 — 실제 다운로드 내용·Import 반영은 담당자 수동 테스트 필요.", sc=3, screenshot=False,
                  repro="1. Example 클릭 → 예제 파일 다운로드 확인(수동)\n2. Import → 엑셀 업로드 → 폴더 반영 확인(수동)")
        page.close_folder_modal()

    def test_scenario3s_path_overflow(self, logged_in_page, settings):
        """경로 3000자 오버플로 — 원본/대상위치 **요소별 개별 판정·카드**(이슈 귀속 정확화, 사용자 지시 2026-07-02).
        결과가 완전히 같으면 merge_key 로 결함 카드 1장으로 묶임(sc4o 동일 결과와도 묶임).
        실측(직접조작 2026-07-02): raw '서버에서 오류' 노출 — 설명(sc3j)과 달리 경로는 길이 가드 없음."""
        print("\n━━ [특수폴더] sc3s: 경로 오버플로 3000자(요소별) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_povf"
        page.ensure_template(tpl, "SHORTCUT")
        page.open_folder_modal(tpl)
        big = "A" * 3000
        cases = [("원본위치", "povf_src", dict(source=big, target="[/MYDOC/]")),
                 ("대상위치", "povf_tgt", dict(source="[/DESKTOP/]", target=big))]
        for elem, setting, kw in cases:
            page.open_content_add()
            msg = page.add_folder_mapping(setting, use_picker=False, **kw)
            committed = bool(page.folder_row_values(setting))
            if ("입력해" in msg) or ("초과" in msg):
                st, note = "pass", "명확한 경고로 차단(데이터 안전)"
            elif "서버" in msg:
                st, note = "warn", "raw 서버 오류 노출 — 클라 길이 가드 부재"
            else:
                st, note = "warn", "차단 없이 저장됨 — 확인 필요" if committed else "경고 없음·미커밋 — 확인 필요"
            sel = page.SEL_C_SOURCE if elem == "원본위치" else page.SEL_C_TARGET
            self._add(st, f"sc3s — {elem} 3000자 오버플로 → 처리",
                      f"입력: {elem}에 3000자 + 추가 / 결과: 경고={msg!r}, 커밋={committed} / {note}", sc=3,
                      highlight=page.page.locator(sel),
                      merge_key=f"path_ovf::{elem}::{st}::{note}",   # 같은 요소 + 같은 결과만 묶임(생성/수정 간)
                      repro=f"1. 폴더 내용 추가\n2. {elem}에 3000자\n3. 추가\n4. 경고 종류 확인(서버 오류면 검증 부재)")
            page.close_content_modal()
        page.close_folder_modal()

    def test_scenario3t_template_name_clamp(self, logged_in_page, settings):
        """템플릿 이름(1단계) 글자수 clamp — 설정명(sc3i)만 있고 이름은 빠져 있던 것 보강(전수 대조 2026-07-02).
        스캔힌트 실측 기대 maxlength=30. 저장 안 함(타이핑 수용량만 확인)."""
        print("\n━━ [특수폴더] sc3t: 템플릿 이름 글자수 clamp(생성 모달) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        accepted = page.type_real(f"{page.SEL_MODAL} {page.SEL_NAME}", "A" * 35)
        self._add("pass" if accepted == 30 else "warn",
                  "sc3t — 템플릿 이름 글자수 clamp(생성 모달)",
                  f"입력: 이름에 35자 실타이핑 / 결과: 실제 수용 {accepted}자 (기대 30 clamp — 설정명 sc3i 와 동일)", sc=3,
                  highlight=page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}"),
                  repro="1. 템플릿 추가 모달 이름에 35자 실타이핑\n2. 30자에서 잘리는지")
        page._close_modal_if_open()

    def test_scenario3u_content_name_special_char(self, logged_in_page, settings):
        """설정명(내용 모달) 특수문자 — 템플릿 이름(sc3l)만 있고 설정명은 빠져 있던 것 보강."""
        print("\n━━ [특수폴더] sc3u: 설정명 특수문자(생성) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_spn"
        page.ensure_template(tpl, "SHORTCUT")
        page.open_folder_modal(tpl)
        sp = "sp_item<>!@#"
        if not page.folder_row_values(sp):
            page.open_content_add()
            msg = page.add_folder_mapping(sp, use_picker=True, src_index=0, tgt_index=1)
        else:
            msg = "(기존 존재)"
        created = bool(page.folder_row_values(sp))
        self._add("pass" if created else "warn",
                  "sc3u — 설정명 특수문자 입력(생성)",
                  f"입력: 설정명 '{sp}' / 결과: 경고={msg!r}, 생성={created} "
                  "(템플릿 이름 sc3l 과 동일하게 특수문자 허용 기대)", sc=3,
                  highlight=page.page.locator(f"{page.SEL_FOLDER_MODAL} tbody tr", has_text="sp_item"),
                  repro="1. 폴더 내용 추가 설정명에 특수문자(<>!@#)\n2. 추가\n3. 허용/차단 여부")
        page.close_folder_modal()
