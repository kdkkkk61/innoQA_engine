"""시큐어존 템플릿(프로세스) — 시나리오 5: 케이스 검증 + lifecycle (폴더동기화 sc5 미러).

속성-확인 법칙: ①채워 저장 → ②재오픈 round-trip(손실=fail) → ③속성 모달 표시(불일치=warn — 표시 버그).
5a 케이스A(전체): 예외처리 타입 — L3 저장 가능 필드 전수(설명·재시작·드라이브권한 2종) 채워
   등록 1건 → 재오픈 요소별 + 속성 모달(이름/타입/카운트/항목명/사용처)
5b 케이스B(필수만): 이름만 생성(타입·상태 기본) — 등록 0건 + 속성 '0 건' 표기
5c 되돌리기: 5a 항목 설명 값→비움 '수정'(silent 무시 버그 클래스) + 항목 제거 → 속성 재확인
5d 마무리 cleanup: 날짜 없는 [AUTO](휘발성) 전부 삭제, 날짜본([AUTO_<MMDD>]) 보존
속성 모달 = div#detailSecureZoneTemplate — Chrome 실측(2026-07-10): 이름/프로세스 타입/
  등록된 프로세스 N건/등록된 태그 N건/개별 프로세스·태그 목록 탭/사용처(시큐어존 정책) 표기.
※ 템플릿 상태(활성/비활성)는 속성 모달에 **미표기**(Chrome 재실측 2026-07-14 — 표기 항목
  전수 판독, 상태 항목 부재) → 상태 표시 검증은 리스트 상태열(sc4b 3점 대조)이 담당,
  속성 모달 쪽은 기능 부재로 제외(매트릭스 제외 근거).
※ 거부 타입은 항목 편집 '수정' 불능(JS 오류 — sc4i/sc4n 카드)이라 5c 되돌리기 소재로 부적합 —
  케이스A 는 필드가 가장 많은 예외처리 타입으로 수행.
"""
from pages.secure_zone_template_process_page import SecureZoneTemplateProcessPage
from tests.secure_zone_template_process._base import SecureZoneTemplateProcessBase

_FULL = "[AUTO]_sz_proc_5a"
_MIN  = "[AUTO]_sz_proc_5b"
_DESC = "proc_5a_desc"


class TestSecureZoneTemplateProcessScenario5Cases(SecureZoneTemplateProcessBase):
    """시큐어존 템플릿(프로세스) — 시나리오 5: 케이스 검증."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    _EX = "EXCEPT_PROCESS"   # L3 저장 가능 필드 최다 타입(설명+재시작+드라이브권한 radio 2종)

    def _ensure_full_item(self, page) -> str:
        """5a 케이스A 항목 확보 — 예외처리 템플릿에 전 필드 채운 프로세스 1건.
        L2 열린 상태로 등록 프로세스명 반환('' = 확보 실패)."""
        page.navigate_to_clean()
        page.ensure_template(_FULL, self._EX)
        page.open_l2_modal(_FULL)
        if page.l2_item_count() == 1:
            return page.l2_rows()[0].locator("td").nth(1).inner_text().strip()
        page.l2_bulk_remove()
        page.open_l3_add(self._EX)
        picked = page.l3_register(self._EX, count=1)
        if not picked:
            page.close_l3_modal(self._EX)
            return ""
        scope = page.l3_scope(self._EX)
        page.fill(f"div#{page.L3_MAP[self._EX]}.in {page.SEL_L3_DESC}", _DESC)
        scope.locator("input#isProcessRestart").first.evaluate(
            "el => { if (!el.checked) el.click(); }")
        scope.locator("input[name='isSecureDriveWrite']#BLOCK").first.evaluate("el => el.click()")
        scope.locator("input[name='isTakeoutDriveWrite']#ALLOW").first.evaluate("el => el.click()")
        page.l3_add_message(self._EX)
        page.dismiss_alert()
        return picked[0]

    # ── 5a: 케이스A 전체 — 저장 → 재오픈 요소별 + 속성 표시 ─────────
    def test_scenario5a_full_case_lifecycle(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc5a: 케이스A(전체) lifecycle ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        item = self._ensure_full_item(page)
        if not item:
            page.close_l2_modal()
            self._add("warn", "sc5a — 케이스A [검증 불가 — 항목 확보 실패]",
                      "picker 선택 0건 — 재실측 필요", sc=5)
            return
        # ① 재오픈 — 저장 가능 필드 전수 round-trip
        page.l2_open_item_edit(0)
        scope = page.l3_scope(self._EX)
        checks = {
            "프로세스명": page.l3_selected_name(self._EX) == item,
            "설명": scope.locator(page.SEL_L3_DESC).first.input_value() == _DESC,
            "재시작(ON)": scope.locator("input#isProcessRestart").first.is_checked(),
            "시큐어드라이브 접근(차단)":
                scope.locator("input[name='isSecureDriveWrite']#BLOCK").first.is_checked(),
            "반출드라이브 쓰기(허용)":
                scope.locator("input[name='isTakeoutDriveWrite']#ALLOW").first.is_checked(),
            "상태(활성)": scope.locator("input#CREATE").first.is_checked(),
        }
        page.close_l3_modal(self._EX)
        cnt = page.l2_item_count()
        page.close_l2_modal()
        for label, ok in checks.items():
            self._add("pass" if ok else "fail",
                      f"sc5a — 재오픈 round-trip: {label}",
                      f"결과: 유지={ok}", sc=5,
                      repro=f"1. 예외처리 항목 저장(전체 필드)\n2. 재오픈\n3. {label} 유지 확인")
        self._add("pass" if cnt == 1 else "fail",
                  "sc5a — 연결 항목 카운트 유지(1건)",
                  f"결과: L2 {cnt}건(기대 1)", sc=5)
        # ② 속성 모달 표시 — 요소별 (실측 2026-07-10: 이름/타입/카운트/항목 목록/사용처)
        try:
            page.open_detail_modal(_FULL)
            dtext = page.detail_modal_text()
            for label, expected in (("템플릿 이름", _FULL),
                                    ("프로세스 타입", "예외처리 프로세스"),
                                    ("등록 카운트(1 건)", "1 건"),
                                    ("항목 프로세스명", item)):
                shown = expected in dtext
                self._add("pass" if shown else "warn",
                          f"sc5a — 속성 모달 표시: {label}",
                          f"입력: 속성 열람 / 결과: {expected!r} 표시={shown}", sc=5)
            has_usage = "사용처" in dtext
            self._add("pass" if has_usage else "warn",
                      "sc5a — 속성 모달: 사용처 섹션 존재(시큐어존 정책 연계 표시 위치)",
                      f"결과: 사용처 섹션={has_usage}", sc=5)
            page.close_detail_modal()
        except Exception as e:
            self._add("warn", "sc5a — 속성 모달 표시 검증", f"예외: {e!r}", sc=5)

    # ── 5b: 케이스B 필수만 — 선택 전부 기본값 + 항목 0건 ────────────
    def test_scenario5b_minimal_case(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc5b: 케이스B(필수만) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        if _MIN in page.get_template_names():   # 재실행 잔존 가드
            page.delete_template(_MIN)
            page.navigate_to()
        page.create_template(_MIN)   # 이름만 — 타입(허용)·상태(활성) 기본값
        page.navigate_to()
        # 수정 모달 재오픈 — 기본값 유지(허용 radio + 활성 radio)
        page.open_modify_modal(_MIN)
        type_default = page.page.locator(
            f"{page.SEL_MODAL} input#ALLOW_PROCESS").first.is_checked()
        status_default = page.page.locator(
            f"{page.SEL_MODAL} input#CREATE").first.is_checked()
        page._close_modal_if_open()
        page.open_l2_modal(_MIN)
        cnt_p = page.l2_item_count()
        page.switch_l2_tab("태그")
        cnt_t = page.l2_item_count()
        page.close_l2_modal()
        detail_zero = None
        try:
            page.open_detail_modal(_MIN)
            dtext = page.detail_modal_text()
            detail_zero = "0 건" in dtext
            page.close_detail_modal()
        except Exception:
            pass
        ok = type_default and status_default and cnt_p == 0 and cnt_t == 0
        self._add("pass" if ok else "fail",
                  "sc5b — 필수(이름)만 생성 → 기본값·빈 연결 유지",
                  f"입력: 이름만 저장 / 결과: 타입 기본(허용)={type_default}, "
                  f"상태 기본(활성)={status_default}, 프로세스={cnt_p}건(기대 0), "
                  f"태그={cnt_t}건(기대 0), 속성 '0 건' 표기={detail_zero}", sc=5,
                  repro="1. 이름만으로 생성\n2. 재오픈 → 타입/상태 기본값\n"
                        "3. 프로세스·태그 0건 + 속성 '0 건'")

    # ── 5c: 되돌리기 — 설명 값→비움 '수정' + 항목 제거 → 속성 재확인 ──
    def test_scenario5c_strip_then_verify(self, logged_in_page, settings):
        """5a 를 수정으로 되돌림: 설명 값→비움(silent 무시 버그 클래스 — 특수폴더 sc5c 전례)
        + 항목 제거 → 속성 재확인(제거 반영)."""
        print("\n━━ [프로세스] sc5c: 되돌리기(설명 비움 + 항목 제거) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        item = self._ensure_full_item(page)
        if not item:
            page.close_l2_modal()
            self._add("warn", "sc5c — 되돌리기 [검증 불가 — 항목 확보 실패]",
                      "picker 선택 0건 — 재실측 필요", sc=5)
            return
        DESC = f"div#{page.L3_MAP[self._EX]}.in {page.SEL_L3_DESC}"
        page.l2_open_item_edit(0)
        page.fill(DESC, "")
        msg = page.l3_add_message(self._EX, button="수정")
        page.dismiss_alert()
        if page.page.locator(f"div#{page.L3_MAP[self._EX]}.in").count() > 0:
            page.close_l3_modal(self._EX)
        page.l2_open_item_edit(0)
        desc_after = page.l3_scope(self._EX).locator(page.SEL_L3_DESC).first.input_value()
        page.close_l3_modal(self._EX)
        cleared = desc_after.strip() == ""
        self._add("pass" if cleared else "fail",
                  ("sc5c — 설명 값→비움 수정 반영" if cleared else
                   "sc5c — 설명을 비워 저장해도 이전 값이 남음 — 빈값 수정 silent 무시"),
                  f"입력: 설명 비우고 '수정'({msg!r}) / 재오픈={desc_after!r} "
                  + ("(정상 반영)" if cleared else "[값→빈값 전이가 조용히 무시됨 — 데이터 버그]"),
                  sc=5, highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody tr:visible"),
                  merge_key=(None if cleared else "szproc_desc_strip::EXCEPT_PROCESS"),
                  repro="1. 항목 설명 전체 지움\n2. '수정'(경고 없음)\n3. 재오픈 → 빈값이어야")
        # 항목 제거 → 0건 + 속성 재확인(속성-확인 법칙)
        msg_rm = page.l2_remove_item(0)
        cnt = page.l2_item_count()
        page.close_l2_modal()
        self._add("pass" if cnt == 0 else "fail",
                  "sc5c — 항목 제거 → 등록 0건",
                  f"입력: 항목 제거 / 결과: 확인={msg_rm!r}, 잔여={cnt}건", sc=5)
        try:
            page.open_detail_modal(_FULL)
            dtext = page.detail_modal_text()
            item_gone = item not in dtext
            self._add("pass" if item_gone else "warn",
                      "sc5c — 수정 후 속성 재확인: 제거된 항목이 속성에서도 사라짐",
                      f"입력: 제거 후 속성 열람 / 결과: {item!r} 미표시={item_gone} "
                      "(표시되면 속성 stale — 표시 버그)", sc=5,
                      repro="1. 항목 제거\n2. 속성 모달 열람\n3. 제거 항목이 안 보여야")
            page.close_detail_modal()
        except Exception as e:
            self._add("warn", "sc5c — 수정 후 속성 재확인", f"예외: {e!r}", sc=5)

    # ── 5d: 마무리 cleanup — 휘발성 [AUTO] 만 삭제 ──────────────────
    def test_scenario5d_final_cleanup(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc5d: 마무리 cleanup(휘발성 [AUTO]) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.delete_all_auto()
        leftover = [n for n in page.get_template_names() if n.startswith("[AUTO]")]
        self._add("pass" if not leftover else "warn",
                  "sc5d — [AUTO] 휘발성 일괄 삭제(cleanup, 날짜본 보존)",
                  f"결과: 잔여 {len(leftover)}건" + (f" — {leftover}" if leftover else ""), sc=5,
                  repro="1. sc5 종료 시 [AUTO]_ 전부 삭제\n2. [AUTO_<날짜>] 보존")
