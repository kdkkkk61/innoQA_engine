"""시큐어존 템플릿(특수폴더) — 시나리오 5: 케이스 검증(lifecycle) + 속성 모달 표시.

구조(SD sc5 동일, 속성-확인 법칙): ① 채워 저장 → ② 재오픈해 '진짜 저장값' round-trip → ③ 속성(상세) 모달 '표시' 검증.
역할 구분: 재오픈=저장됐나(손실=fail) / 속성 모달=재오픈값과 같게 표시되나(불일치=warn=표시 버그, 데이터는 안전).

특수폴더 필드 구성(케이스A/B 대상):
  1단계 = 이름·용도·상태뿐 — 선택 텍스트 필드 없음(스캔힌트 stage1_fields 실측).
  연결 항목 = 폴더 매핑(등록된 경로) / 항목의 선택 필드 = 설명.
- 5a 케이스A(전체): 매핑 1건(설명 포함) — **요소별 카드**(사용자 지시 2026-07-02):
  설정명/원본/대상/설명/카운트 = 재오픈 유지 + 속성 표시 통합 판정(손실=fail / 표시만 불일치=warn)
  + 속성 헤더도 요소별(이름/용도/사용처 각 1장 — 스캔 묶음 금지)
- 5b 케이스B(필수만): 요소=연결 항목 1개 → 카드 1장(폴더모달 0·리스트 0·속성 '0 건' 3계층 통합 판정)
- 5c 되돌리기(lifecycle 후반부): 5a 를 수정으로 선택 비움(설명)+매핑 제거(필수 제외) → 편집 로드·속성 재검증
  (채우기→검증→비우기→검증 순서 — 제어스위트 sc5c 동일 패턴, 사용자 지시 2026-07-02)
- 5d 마무리 cleanup: 날짜 없는 [AUTO](휘발성) 전부 삭제, [AUTO_<MMDD>](날짜본·연계) 보존
  (cleanup 라이프사이클: sc1 시작=전부 삭제 / sc5 끝=휘발성만 삭제 — 사용자 지시 2026-07-02)

직접조작 수집(2026-07-02): 속성 모달 = div#detailSecureZoneTemplate(행 용도 셀 더블클릭, 읽기전용 텍스트 — SD 탭과 모달 id 공유).
구성 = 템플릿 이름/용도/등록된 경로 N 건/항목 테이블(설정명·원본·대상·설명·수정일·상태)/※ 사용처 확인(정책명).
※ 항목 테이블 '상태' 표기 = 'O/X' — 폴더모달('활성')과 표기 상이(경미, detail 부기).
"""
from pages.secure_zone_template_manage_folder_page import SecureZoneTemplateManageFolderPage
from tests.secure_zone_template_manage_folder._base import SecureZoneTemplateManageFolderBase


class TestSecureZoneTemplateManageFolderScenario5Lifecycle(SecureZoneTemplateManageFolderBase):
    """시큐어존 템플릿(특수폴더) — 시나리오 5: 케이스 검증 + 속성 표시."""

    _CASE_A = "[AUTO]_sz_mf_sc5a"
    _CASE_B = "[AUTO]_sz_mf_sc5b"

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateManageFolderPage(logged_in_page, settings)
        self._page = page.page
        return page

    # ══ 5a: 케이스A(전체 채움) — 저장 → 재오픈 → 속성 ═══════════════
    def test_scenario5a_full_case_lifecycle(self, logged_in_page, settings):
        print("\n━━ [특수폴더] 시나리오 5a: 케이스A 매핑+설명 → 재오픈 → 속성 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = self._CASE_A
        page.ensure_template(name, "SHORTCUT")

        # ── ① 폴더 매핑 1건(선택 필드 '설명' 포함) 저장 ─────────────
        page.open_folder_modal(name)
        if not page.folder_row_values("sc5a_map"):
            page.open_content_add()
            msg = page.add_folder_mapping("sc5a_map", use_picker=True, src_index=0, tgt_index=1,
                                          description="sc5a_desc")
        else:
            msg = "(기존 존재)"
        page.close_folder_modal()
        self._add("pass" if not msg.strip() or "기존" in msg else "warn",
                  "sc5a-① 매핑 저장(설정명+원본/대상+설명)",
                  f"입력: sc5a_map / [/DESKTOP/]→[/MYDOC/] / 설명 'sc5a_desc' / 결과: 경고={msg!r}", sc=5,
                  repro="1. 폴더 내용 추가\n2. 설정명+picker 경로+설명\n3. 추가")

        # ── ②+③ 요소별 카드(사용자 지시 2026-07-02): 재오픈 유지 + 속성 표시 통합 판정 ──
        #    판정: 재오픈에 없음=fail(저장 손실) / 재오픈엔 있는데 속성 미표시=warn(표시 버그, 데이터 안전) / 둘 다=pass
        page.open_folder_modal(name)
        vals = " ".join(page.folder_row_values("sc5a_map"))
        page.close_folder_modal()
        cnt = page.template_path_count(name)
        page.open_detail_modal(name)
        dtext = page.detail_modal_text()
        items = " ".join(page.detail_item_rows())
        # 하위속성(항목 설정명 링크 → 중첩 상세, 직접조작 확정 2026-07-02) — 표시 3계층째 + 읽기전용
        sub_text, ro = "", None
        try:
            page.open_item_detail_modal("sc5a_map")
            sub_text = page.item_detail_text()
            ro = page.item_detail_status_readonly()
            page.close_item_detail_modal()
        except Exception as e:
            self._add("warn", "sc5a — 하위속성 상세 열기 실패",
                      f"항목 설정명 링크 클릭으로 하위속성 미오픈: {e!r}", sc=5,
                      repro="1. 속성 모달\n2. 항목 설정명 링크 클릭\n3. 하위속성 상세 열림")
        for elem, val in (("설정명", "sc5a_map"), ("원본위치", "[/DESKTOP/]"),
                          ("대상위치", "[/MYDOC/]"), ("설명", "sc5a_desc")):
            saved = val in vals
            shown = val in items
            sub_shown = (val in sub_text) if sub_text else None   # None=하위속성 미오픈(판정 제외)
            if not saved:
                st, note = "fail", "재오픈 행에 없음 — 저장 손실"
            elif not shown:
                st, note = "warn", "저장은 됨(재오픈 확인) — 속성 항목 테이블 미표시(표시 버그, 데이터 안전)"
            elif sub_shown is False:
                st, note = "warn", "재오픈·속성 테이블은 표시 — 하위속성 상세 미표시(표시 버그)"
            else:
                st, note = "pass", "재오픈·속성 테이블·하위속성 표시 일치"
            self._add(st, f"sc5a — {elem} 저장값 유지 + 속성/하위속성 표시",
                      f"입력: {val!r} / 재오픈={saved}, 속성 테이블={shown}, 하위속성={sub_shown} / {note}", sc=5,
                      repro=f"1. 매핑 저장({elem}={val!r})\n2. 폴더모달 재오픈 행값\n"
                            "3. 속성 항목 테이블\n4. 설정명 링크 → 하위속성 상세 표시")
        # 하위속성 읽기전용 — 상태 radio disabled + 능동(클릭 시도 → 불변)
        if ro is not None:
            ro_ok = ro["disabled"] and ro["unchanged"]
            self._add("pass" if ro_ok else "fail",
                      "sc5a — 하위속성 상세 읽기전용(상태 radio disabled + 클릭 불변)",
                      f"결과: disabled={ro['disabled']}, 클릭 시도 후 불변={ro['unchanged']} "
                      + ("(읽기전용 정상)" if ro_ok else "[읽기전용 우회 가능 — 상태가 바뀜]"), sc=5,
                      repro="1. 하위속성 상세\n2. 상태 radio disabled 확인\n3. 클릭해도 값 불변인지")
        # 연결 항목 카운트 요소 — 리스트 '등록된 경로' + 속성 'N 건'
        cnt_ok = (cnt == "1")
        cnt_shown = "1 건" in dtext
        st = "pass" if (cnt_ok and cnt_shown) else ("fail" if not cnt_ok else "warn")
        self._add(st, "sc5a — 등록된 경로 카운트(리스트 + 속성 'N 건')",
                  f"결과: 리스트={cnt!r}(기대 '1'), 속성 '1 건' 표시={cnt_shown} "
                  "[참고: 속성 항목 '상태' 표기는 'O/X' — 폴더모달 '활성/비활성'과 표기 상이(경미)]", sc=5,
                  repro="1. 매핑 1건 상태\n2. 리스트 등록된 경로=1\n3. 속성 모달 '1 건' 표시")
        # 속성 모달 헤더 — 요소별 카드(이름/용도/사용처 각 1장, 사용자 지시 2026-07-02: 스캔 묶음도 분리)
        for lbl, v in (("템플릿 이름", name), ("템플릿 용도", "바로가기"), ("사용처 확인 섹션", "사용처")):
            shown = v in dtext
            self._add("pass" if shown else "warn",
                      f"sc5a — 속성 모달 {lbl} 표시",
                      f"기대 표시값: {v!r} / 결과: 표시={shown}", sc=5,
                      repro=f"1. 행 가운데(용도 셀) 더블클릭 → 속성\n2. {lbl} 표시 확인")
        # 관찰(제품 표시 공백, 낮음): 속성 모달에는 '템플릿 상태(활성/비활성)' 항목 자체가 없음.
        # (항목 테이블의 O/X 는 '폴더 항목'의 상태 — 템플릿 상태와 별개, 혼동 주의)
        status_shown = ("활성" in dtext) or ("비활성" in dtext)
        if status_shown:
            self._add("pass", "sc5a — 속성 모달 템플릿 '상태' 항목 표시(관찰)",
                      "결과: 속성 모달에 템플릿 상태(활성/비활성) 표기 있음", sc=5)
        else:
            # 부재 증거 = '대비 2장'(사용자 지시 2026-07-03): ①수정 모달(상태 라디오 있음, 빨간 표시)
            # ②속성 모달 전체(상태 항목 없음). 단독 샷으론 '공백이 어디인지' 안 보임.
            # ⚠ 모달 wrapper(div#…in) highlight 는 bbox 불일치로 crop 오작동(실측) → ②는 전체 페이지.
            page.close_detail_modal()
            page.open_modify_modal(name)
            shot_has = self._shot("상태항목_수정모달에는_있음",
                                  highlight=page.page.locator(page.SEL_STATUS_CREATE),
                                  caption="1. 수정 모달 — 상태(활성/비활성) 항목 있음")
            page._close_modal_if_open()
            page.open_detail_modal(name)
            shot_none = self._shot("상태항목_속성모달엔_없음",
                                   caption="2. 속성 모달 — 상태 항목 없음(전체 화면)")
            self._add("warn", "sc5a — 속성 모달에 템플릿 '상태' 항목 없음(표시 공백 관찰)",
                      "결과: 수정 모달에는 상태(활성/비활성) 항목이 있는데(스크린샷1 빨간 표시) "
                      "속성 모달에는 이름/용도/등록된 경로/항목 테이블/사용처뿐 — 상태 항목이 없음(스크린샷2 전체 화면). "
                      "속성 모달만 봐서는 이 템플릿이 활성인지 비활성인지 알 수 없음 "
                      "(항목 테이블의 O/X 는 '폴더 항목' 상태로 별개) — 표시 공백(낮음).",
                      sc=5, screenshot=False, screenshots=[shot_has, shot_none],
                      repro="1. 수정 모달 → 상태(활성/비활성) 항목 존재 확인\n"
                            "2. 행 가운데 더블클릭 → 속성 모달 → 상태 항목이 없는 것 확인\n"
                            "3. 속성만으로는 활성/비활성 확인 불가")
        page.close_detail_modal()

    # ══ 5b: 케이스B(필수만) — 연결 항목 0 유지 → 속성 ════════════════
    def test_scenario5b_minimal_case(self, logged_in_page, settings):
        """케이스B: 필수(이름+용도)만 저장, 선택 일절 없음 — 특수폴더 1단계엔 선택 텍스트 필드가 없어
        빈값 유지 검증 대상 = 연결 항목(폴더 매핑) 0 유지가 전부(스캔힌트 stage1_fields 실측 근거)."""
        print("\n━━ [특수폴더] 시나리오 5b: 케이스B 필수만(매핑 0 유지) → 속성 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = self._CASE_B
        page.ensure_template(name, "SHORTCUT")   # 이름+용도만 — 매핑 추가 안 함

        # ── 요소(연결 항목) 카드 1장 — 폴더모달·리스트·속성 3계층 통합 판정 ──
        page.open_folder_modal(name)
        n = page.folder_item_count()
        page.close_folder_modal()
        cnt = page.template_path_count(name)
        page.open_detail_modal(name)
        dtext = page.detail_modal_text()
        items = page.detail_item_rows()   # 항목 테이블만(사용처 테이블 제외 — 오카운트 fix 2026-07-02)
        empty_kept = (n == 0) and (cnt == "0")
        empty_shown = ("0 건" in dtext) and (not items)
        if not empty_kept:
            st, note = "warn", "예상 못한 항목 존재 — 케이스B 전제(연결 0) 깨짐"
        elif not empty_shown:
            st, note = "warn", "데이터는 0 유지 — 속성 모달 빈 상태 표시 불일치(표시 버그)"
        else:
            st, note = "pass", "폴더모달 0·리스트 0·속성 '0 건'+항목 없음 전부 일치"
        self._add(st, "sc5b — 연결 항목(폴더 매핑) 0 유지 + 속성 빈 상태 표시",
                  f"결과: 폴더모달 항목={n}, 리스트={cnt!r}, 속성 '0 건'={'0 건' in dtext}, "
                  f"속성 항목 행={len(items)}(기대 0) / {note}", sc=5,
                  repro="1. 필수만으로 생성(매핑 없음)\n2. 폴더모달 0 + 리스트 0\n3. 속성 '0 건' + 항목 테이블 빈 상태")
        page.close_detail_modal()

    # ══ 5c: 케이스A 되돌리기 — 선택 비움·제거(필수 제외) → 재검증 ═════
    def test_scenario5c_strip_then_verify(self, logged_in_page, settings):
        """lifecycle 후반부(표준): 채운 것(5a)을 수정으로 되돌림 — 선택 필드 비움 + 매핑 제거(필수 제외)
        → 수정모달(편집 로드)·속성 모달로 재검증. 제어스위트 sc5c(요소 전부 제거) 동일 패턴."""
        print("\n━━ [특수폴더] 시나리오 5c: 선택 비움·제거(필수 제외) → 재검증 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = self._CASE_A   # 5a 산출물 사용(없으면 5a 와 동일하게 보장)
        page.ensure_template(name, "SHORTCUT")
        page.open_folder_modal(name)
        if not page.folder_row_values("sc5a_map"):
            page.open_content_add()
            page.add_folder_mapping("sc5a_map", use_picker=True, src_index=0, tgt_index=1,
                                    description="sc5a_desc")

        # ── 요소 ①: 설명(선택 필드) 비움 → 편집 로드·폴더모달 행·속성 3계층 재검증 ──
        # 계층 우선순위 판정: 저장(편집 재로드) > 리스트(행 '설명' 컬럼) > 속성 모달.
        # 캡처 지점 = 판정 지점 / 두 화면 대조 판정(warn)만 _shot 으로 한 장 더.
        page.open_folder_item_edit("sc5a_map")
        page.fill(page.SEL_C_DESC, "")
        msg = page.content_save_message()
        page.open_folder_item_edit("sc5a_map")
        desc_after = page.page.locator(page.SEL_C_DESC).first.input_value()
        if desc_after != "":
            # 저장 계층 fail — '1회 리턴 재생'(사용자 설계 2026-07-03): 이슈 확정 후 같은 흐름을
            # 한 번 더 실행하며 스텝별 캡처 → repro 각 줄과 1:1 대응하는 이미지 스토리로 보고.
            # 스토리 3컷(사용자 지시 2026-07-03): 지운 화면(저장 전) → 저장 → 재편집 잔존(=이슈 화면, 빨간 표시).
            # '잔존 확인' 선행 컷은 마지막 컷과 같은 화면 상태라 제외(중복).
            shots = self._replay_shots([
                ("설명을 지움 — 입력이 빈 상태(저장 전)",
                 lambda: page.fill(page.SEL_C_DESC, ""),
                 page.page.locator(page.SEL_C_DESC)),                         # 지운 화면 자체(핵심 컷)
                ("수정 저장(경고 없음)",
                 lambda: page.content_save_message(),
                 None),                                                       # 저장 직후 화면
                ("재편집 — 여전히 잔존(비움 미적용) = 이슈 화면",
                 lambda: page.open_folder_item_edit("sc5a_map"),
                 page.page.locator(page.SEL_C_DESC)),                         # 결말 = 증거(빨간 표시)
            ])
            self._add("fail", "sc5c — 설명(선택) 비움 → 편집·행·속성 재검증",
                      f"입력: 설명 비우고 수정(경고={msg!r}) / 편집 재로드={desc_after!r}(기대 '') "
                      "— 설명 비움 미저장(silent). 스크린샷=리턴 재생 스토리(이슈 확정 후 같은 흐름 재실행 캡처: "
                      "①지움 ②저장 ③재편집 잔존=이슈)",
                      sc=5, screenshot=False, screenshots=shots,
                      repro="1. 항목 편집 → 설명 지움(빈 입력)\n2. 수정 저장(경고 없음)\n"
                            "3. 재편집 → 설명에 옛 값 그대로(비움 미적용)")
            page.close_content_modal()
            page.close_folder_modal()
        else:
            page.close_content_modal()
            # 리스트 계층 — 폴더모달 행 '설명' 컬럼(제어스위트 클립보드와 같은 '행 표시 stale' 클래스)
            row_stale = "sc5a_desc" in " ".join(page.folder_row_values("sc5a_map"))
            if row_stale:
                page.open_folder_item_edit("sc5a_map")
                shot1 = self._shot("sc5c_설명빈값_편집로드", highlight=page.page.locator(page.SEL_C_DESC),
                                   caption="1. 편집 모달 — 설명 빈값(데이터는 비워짐)")
                page.close_content_modal()
                shot2 = self._shot("sc5c_행_설명_잔존",
                                   highlight=page.page.locator(f"{page.SEL_FOLDER_MODAL} tbody tr", has_text="sc5a_map"),
                                   caption="2. 폴더모달 행 — '설명' 컬럼에 옛값 잔존(행 표시 stale)")
                self._add("warn", "sc5c — 설명(선택) 비움 → 편집·행·속성 재검증",
                          "입력: 설명 비우고 수정 / 편집 재로드=''(비워짐, 스크린샷1) "
                          "— 폴더모달 행 '설명' 컬럼에 옛값 잔존(스크린샷2 — 행 표시 stale, 데이터는 안전)",
                          sc=5, screenshot=False, screenshots=[shot1, shot2],
                          repro="1. 설명 비우고 수정\n2. 재편집 로드는 빈값\n3. 행 '설명' 컬럼에 옛값 남는지")
                page.close_folder_modal()
            else:
                page.close_folder_modal()
                page.open_detail_modal(name)
                items = " ".join(page.detail_item_rows())
                desc_gone = "sc5a_desc" not in items
                shots = None
                if not desc_gone:
                    # 속성 계층 warn — 편집 모달 '빈 설명' 증거를 추가 캡처(필요할 때만 한 장 더)
                    page.close_detail_modal()
                    page.open_folder_modal(name)
                    page.open_folder_item_edit("sc5a_map")
                    shot1 = self._shot("sc5c_설명_편집로드_빈값", highlight=page.page.locator(page.SEL_C_DESC),
                                       caption="1. 편집 모달 — 설명 빈값(데이터는 비워짐)")
                    page.close_content_modal()
                    page.close_folder_modal()
                    page.open_detail_modal(name)
                    shot2 = self._shot("sc5c_속성_설명_잔존",
                                       highlight=page.page.locator(f"{page.SEL_DETAIL_MODAL} tbody tr", has_text="sc5a_map"),
                                       caption="2. 속성 모달 항목 — 옛 설명 잔존(표시 버그)")
                    shots = [shot1, shot2]
                self._add("pass" if desc_gone else "warn",
                          "sc5c — 설명(선택) 비움 → 편집·행·속성 재검증",
                          f"입력: 설명 비우고 수정 / 편집 재로드=''·행 컬럼 비움(확인) / 속성 옛값 제거={desc_gone} "
                          + ("(편집·행·속성 모두 반영)" if desc_gone
                             else "[데이터·행은 비워짐(스크린샷1 편집 모달) — 속성 항목에만 옛 설명 잔존(스크린샷2 표시 버그)]"),
                          sc=5, screenshot=desc_gone, screenshots=shots,
                          repro="1. 항목 편집 설명 비움\n2. 수정 저장\n3. 재편집 로드·행 컬럼·속성 항목 전부 빈값인지")
                page.close_detail_modal()

        # ── 요소 ②: 매핑 제거(연결 항목 → 0) → 폴더모달·리스트·속성 3계층 재검증 ──
        page.open_folder_modal(name)
        page.remove_folder_item(0)
        n = page.folder_item_count()
        if n != 0:
            # fail — 폴더모달 열린 상태에서 잔존 행에 빨간 테두리(제거 미반영 증거)
            self._add("fail", "sc5c — 매핑 제거(연결 0) → 폴더모달·리스트·속성 재검증",
                      f"입력: 항목 제거 / 결과: 폴더모달에 {n}건 잔존 — 제거 미반영(스크린샷=잔존 행)",
                      sc=5,
                      highlight=page.page.locator(f"{page.SEL_FOLDER_MODAL} tbody tr:has(input[type='checkbox'])"),
                      repro="1. 항목 체크+제거\n2. 확인 후에도 행이 남아있는지")
            page.close_folder_modal()
        else:
            page.close_folder_modal()
            cnt = page.template_path_count(name)
            page.open_detail_modal(name)
            dtext = page.detail_modal_text()
            items2 = page.detail_item_rows()
            shown_empty = (cnt == "0") and ("0 건" in dtext) and (not items2)
            shots = None
            if not shown_empty:
                # 두 화면 대조 판정(warn) — 폴더모달 '빈 테이블' 증거를 추가 캡처(필요할 때만 한 장 더)
                page.close_detail_modal()
                page.open_folder_modal(name)
                shot1 = self._shot("sc5c_매핑제거_폴더모달_빈상태",
                                   highlight=page.page.locator(f"{page.SEL_FOLDER_MODAL} tbody"),
                                   caption="1. 폴더모달 — 항목 0건(제거 반영됨)")
                page.close_folder_modal()
                page.open_detail_modal(name)
                shot2 = self._shot("sc5c_속성_잔존표시",
                                   highlight=page.page.locator(f"{page.SEL_DETAIL_MODAL} tbody tr"),
                                   caption="2. 속성 모달 — 제거된 항목이 여전히 표시(표시 버그)")
                shots = [shot1, shot2]
            self._add("pass" if shown_empty else "warn",
                      "sc5c — 매핑 제거(연결 0) → 폴더모달·리스트·속성 재검증",
                      f"결과: 폴더모달=0(제거 확인), 리스트={cnt!r}, 속성 '0 건'={'0 건' in dtext}, "
                      f"속성 항목={len(items2)} "
                      + ("(3계층 전부 반영)" if shown_empty
                         else "[데이터는 제거됨(스크린샷1 폴더모달) — 리스트/속성 표시 불일치(스크린샷2 표시 버그)]"),
                      sc=5, screenshot=shown_empty, screenshots=shots,
                      repro="1. 항목 체크+제거\n2. 폴더모달 0 + 리스트 0\n3. 속성 '0 건' + 항목 없음")
            page.close_detail_modal()

    # ══ 5d: 마무리 cleanup — [AUTO] 휘발성 전부 삭제, 날짜본 보존 ═════
    def test_scenario5d_final_cleanup(self, logged_in_page, settings):
        """sc5 종료 cleanup — 날짜 없는 [AUTO](휘발성) 전부 삭제, [AUTO_<MMDD>](날짜본·연계 데이터) 보존.
        startswith("[AUTO]") 는 [AUTO_날짜] 와 불일치(6번째가 '_') → 날짜본 자동 보존(명명 규칙 2026-06-30)."""
        print("\n━━ [특수폴더] 시나리오 5d: 마무리 cleanup([AUTO] 삭제·날짜본 보존) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        before = [n for n in page.get_template_names() if n.startswith("[AUTO]")]
        page.delete_all_auto()
        page.navigate_to()
        names = page.get_template_names()
        leftover = [n for n in names if n.startswith("[AUTO]")]
        dated = [n for n in names if page._AUTO_ANY.match(n) and not n.startswith("[AUTO]")]
        self._add("pass" if not leftover else "warn",
                  "sc5d — 마무리 cleanup: [AUTO] 휘발성 전부 삭제 + 날짜본 보존",
                  f"삭제 대상 {len(before)}건 → 잔여 {leftover or '없음'} / 날짜본 보존: {dated or '없음(해당 없음)'}",
                  sc=5,
                  repro="1. sc5 종료 시점\n2. 날짜 없는 [AUTO] 전부 삭제\n3. [AUTO_날짜]만 남는지")
