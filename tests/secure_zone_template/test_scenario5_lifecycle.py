"""시큐어존 템플릿(시큐어 드라이브) — 시나리오 5: 케이스 검증(lifecycle) + 속성 모달 표시.

구조(시큐어존 정책 sc5 동일, 속성-확인 법칙): 케이스별 연속 흐름
  ① 채워 저장 → ② 수정 모달 재오픈해 '진짜 저장값' round-trip 검증 → ③ 속성(상세) 모달로 '표시' 검증.
역할 구분: 수정 모달=저장됐나(손실=fail) / 속성 모달=읽기전용 + 수정모달값과 같게 표시되나(불일치=warn=속성 표시 버그, 데이터는 안전).

- 5a 케이스A(전체 채움, 시큐어드라이브 2건): 옵션(ECM·반출숨김·예외드라이브) 포함 → 저장→수정확인→속성확인
- 5b 케이스B(필수만, 선택 비움): 선택 빈값 유지(예외드라이브 '없음' 등)
- 5c 경고용량 단위 불일치(버그): 입력 GB ↔ 속성>sd상세 표시 MB
  (날짜본 생성 + [AUTO] cleanup 연계 준비는 sc6 = test_scenario6_suite_setup.py 로 분리)

직접조작 수집(2026-06-29): 속성 모달=detailSecureZoneTemplate(행 더블클릭, 읽기전용), input은 체크박스 2개,
나머지(이름·반출·시큐어드라이브 항목·예외드라이브)는 텍스트 표시 + '사용처'(연계 정책명) 표시.
"""
from pages.secure_zone_template_page import SecureZoneTemplateSecureDrivePage
from tests.secure_zone_template._base import SecureZoneTemplateBase


class TestSecureZoneTemplateScenario5Lifecycle(SecureZoneTemplateBase):
    """시큐어존 템플릿(시큐어 드라이브) — 시나리오 5: 케이스 검증 + 속성 표시."""

    _CASE_A = "[AUTO]_sztpl_sd_sc5a"
    _CASE_B = "[AUTO]_sztpl_sd_sc5b"

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSecureDrivePage(logged_in_page, settings)
        self._page = page.page
        return page

    def _ensure(self, page, name, sd_letter, to_letter, to_path, two_drives=False):
        if name not in page.get_template_names():
            page.open_add_modal()
            page.create_basic_template(name, sd_letter=sd_letter, to_letter=to_letter,
                                       to_path=to_path, two_drives=two_drives)
            page.navigate_to()

    # ══ 5a: 케이스A(전체 채움) — 저장 → 수정확인 → 속성확인 ══════════
    def test_scenario5a_full_case_lifecycle(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 5a: 케이스A 전체 채움 → 수정확인 → 속성확인 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = self._CASE_A
        self._ensure(page, name, "Q", "T", "C:\\sc5a", two_drives=True)   # 시큐어드라이브 2건

        # ── ① 전체 채우기(옵션 포함) 저장 ────────────────────────────
        page.open_modify_modal(name)
        page.set_checkbox(page.SEL_ECM, True)
        page.set_checkbox(page.SEL_TAKEOUT_HIDE, True)
        page.fill(page.SEL_OLD_DRIVE, "D;E")
        msg = page.submit_and_message()
        self._add("pass" if "저장" in msg else "warn",
                  "sc5a-① 전체 채움 저장(ECM·반출숨김·예외드라이브 D;E)",
                  f"입력: ECM ON+반출숨김 ON+예외 'D;E' / 결과: {msg!r}", sc=5,
                  repro="1. 수정 모달\n2. ECM·반출숨김 체크 + 예외드라이브 'D;E'\n3. 저장")
        page._close_modal_if_open()

        # ── ② 수정 모달 재오픈 → 진짜 저장값 round-trip ──────────────
        page.navigate_to()
        page.open_modify_modal(name)
        st = page.read_modify_modal_state()
        saved_ok = (st["ecm"] is True) and (st["hide"] is True) and ("D;E" in (st["old_drive"] or "")) \
                   and (st["to_letter"] == "T") and (len(st["sd_rows"]) >= 2)
        self._add("pass" if saved_ok else "fail",
                  "sc5a-② 수정 모달 저장값 round-trip(저장 검증)",
                  f"결과: ECM={st['ecm']}, 반출숨김={st['hide']}, 예외='{st['old_drive']}', "
                  f"반출문자='{st['to_letter']}', 시큐어드라이브 {len(st['sd_rows'])}행(기대 2) "
                  + ("(전부 저장됨)" if saved_ok else "[저장 손실 — 수정모달에도 없음]"), sc=5,
                  repro="1. 수정 재오픈\n2. 저장 직전 값(ECM/반출숨김/예외/반출/sd)이 그대로인지(=저장됨)")
        page.close_modal()

        # ── ③ 속성 모달 → 읽기전용 + 표시(수정모달값 대비) ───────────
        page.navigate_to()
        page.open_detail_modal(name)
        # 읽기전용은 'disabled 속성'이 아니라 '능동 클릭해도 불변'으로 검증(속성만 보면 거짓양성 — disabled 미설정이어도 기능적 읽기전용)
        changes = page.detail_modal_try_change()
        changed_any = [s for s, v in changes.items() if v.get("changed")]
        dtext = page.detail_modal_text()
        decm = page.detail_modal_ecm_hide()
        self._add("pass" if not changed_any else "fail",
                  "sc5a-③ 속성 모달 읽기전용(능동 — 클릭해도 불변)",
                  f"결과: " + ("클릭해도 전부 불변(읽기전용)" if not changed_any else f"클릭에 반응 {changed_any} [읽기전용 우회/UI 변동]"),
                  sc=5, repro="1. 행 더블클릭 속성\n2. 체크박스 클릭\n3. 값이 안 바뀌어야(읽기전용)")
        # 표시 검증: 수정모달 진짜값(st)이 속성 텍스트/체크박스에 보이는지
        missing = []
        for label, val in [("반출문자", st["to_letter"]), ("반출라벨", st["to_label"]),
                           ("반출경로", st["to_path"]), ("예외드라이브", "D;E" if "D;E" in (st["old_drive"] or "") else "")]:
            if val and val not in dtext:
                missing.append(f"{label}='{val}'")
        ecm_disp_ok = (decm["isRegistEcmDrive"] == st["ecm"]) and (decm["isTakeoutDrivePathHide"] == st["hide"])
        disp_ok = (not missing) and ecm_disp_ok
        self._add("pass" if disp_ok else "warn",
                  "sc5a-③ 속성 모달 표시(수정모달값 대비)",
                  f"결과: 텍스트 미표시 {missing or '없음'}, 체크박스 일치={ecm_disp_ok} "
                  + ("(표시 일치)" if disp_ok else "[속성 표시 불일치 — 데이터는 수정모달에 저장됨=안전, 속성 표시 버그]"),
                  sc=5, repro="1. 속성 열기\n2. 수정모달 값(반출·예외·ECM·숨김)이 속성에 표시되는지")
        page.close_detail_modal()

    # ══ 5b: 케이스B(필수만, 선택 비움) — 선택 빈값 유지 ═══════════════
    def test_scenario5b_minimal_case(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 5b: 케이스B 필수만(선택 빈값 유지) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = self._CASE_B
        self._ensure(page, name, "R", "U", "C:\\sc5b")   # 필수만(ECM/숨김 OFF, 예외 비움)
        # ② 수정 재오픈 → 선택 필드 빈값/OFF 유지
        page.open_modify_modal(name)
        st = page.read_modify_modal_state()
        opt_kept = (st["ecm"] is False) and (st["hide"] is False) and ((st["old_drive"] or "") == "")
        self._add("pass" if opt_kept else "warn",
                  "sc5b-② 선택 필드 빈값/OFF 유지(필수만 저장)",
                  f"결과: ECM={st['ecm']}(기대 False), 반출숨김={st['hide']}(기대 False), 예외='{st['old_drive']}'(기대 빈값) "
                  + ("(선택 빈값 유지)" if opt_kept else "[선택 필드에 예상 못한 값]"), sc=5,
                  repro="1. 필수만 저장\n2. 수정 재오픈\n3. ECM/반출숨김 OFF + 예외 빈값 유지")
        page.close_modal()
        # ③ 속성 모달 → 예외드라이브 '없음' 표시 등
        page.navigate_to()
        page.open_detail_modal(name)
        dtext = page.detail_modal_text()
        decm = page.detail_modal_ecm_hide()
        none_shown = ("없음" in dtext)   # 예외드라이브 미입력 시 '없음' 표시(직접조작 확인)
        # ※ 빈값 표시 불일치(경미): 예외드라이브 빈값='없음' / 경고용량 빈값='없음MB'(없음+단위) — 통일 안 됨.
        #   빈값이면 '없음'으로 통일하거나 단위 안 붙이는 게 일관적. (단위 자체 GB↔MB 불일치는 sc5c 별건)
        self._add("pass" if none_shown and (decm["isRegistEcmDrive"] is False) else "warn",
                  "sc5b-③ 속성 모달 — 선택 빈값 표시(예외 '없음' / ECM OFF)",
                  f"결과: 예외드라이브 빈값='없음' 표시={none_shown}, 속성 ECM={decm['isRegistEcmDrive']} "
                  + ("(빈값 '없음' 표시)" if none_shown else "[표시 확인 필요]")
                  + " [참고: 경고용량 빈값은 '없음MB'(없음+단위) — 빈값 표시 통일 안 됨(경미)]", sc=5,
                  repro="1. 필수만 템플릿 속성\n2. 예외드라이브 '없음' + ECM OFF 표시\n3. 빈값 표시 일관성(없음 vs 없음MB)")
        page.close_detail_modal()

    # ══ 5c: 속성 sd 상세 — 경고용량 단위 불일치(입력 GB ↔ 표시 MB) ════
    def test_scenario5c_warn_quota_unit_mismatch(self, logged_in_page, settings):
        """경고용량 단위 불일치 — 입력은 GB(편집 서브 라벨 'GB')인데 속성>시큐어드라이브 상세는 MB 로 표시.
        직접조작 확정 2026-06-29: 경고용량 50(GB 입력) 저장 → 속성 모달 > 문자 클릭 > 중첩 sd상세에 '경고용량 : 50MB'.
        값(50)은 같으나 단위 라벨이 GB→MB 로 바뀌어 1000배 의미 차이(오해 유발) = 버그."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 5c: 경고용량 단위 불일치(GB→MB) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = "[AUTO]_sztpl_sd_wqunit"
        if name not in page.get_template_names():
            page.open_add_modal()
            page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", name)
            page.add_secure_drive("wq", "Q", "C:\\wqu", "WRITE", "100", warn_quota="50")  # 경고용량 50(GB 입력)
            page.fill_takeout("C:\\wqu_to", "T", "lbl", "1024")
            page.submit_and_message()
            page.navigate_to()
        page.open_detail_modal(name)
        warn_disp = page.open_sd_detail_warn_quota()    # 속성 > 문자 클릭 > 중첩 sd상세 열림(경고용량 표시)
        is_mb = "MB" in warn_disp
        # ★중첩 sd상세가 '열린 채'에서 _add → 경고용량 표시(50MB)를 highlight 캡처(증거 직관화)
        self._add("warn" if is_mb else "pass",
                  "sc5c — 경고용량 단위 표시 일치(입력 GB ↔ 속성 sd상세)",
                  f"입력: 경고용량 50(GB 단위) / 속성>시큐어드라이브 상세 표시: '{warn_disp}' "
                  + ("[버그: 입력 단위 GB ↔ 표시 단위 MB 불일치 — 값 50이 GB/MB로 1000배 의미 차이]"
                     if is_mb else "(단위 일치)"), sc=5,
                  # 라벨만이 아니라 값(50MB)까지 포함되도록 경고용량 '행(dl)' 을 박스
                  highlight=(page.page.locator("div#addSecureDrive.in dl", has_text="경고용량") if is_mb else None),
                  repro="1. 경고용량 50(GB) 입력 저장\n2. 속성 모달 → 시큐어드라이브 문자 클릭(중첩 상세)\n"
                        "3. 경고용량 단위가 GB 인지(MB면 단위 불일치 버그)")
        page.close_sd_detail()
        page.close_detail_modal()
