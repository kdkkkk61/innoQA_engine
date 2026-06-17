"""시큐어존 정책 — 시나리오 3: 동작/CRUD (ADD). 모달 top→bottom 순서로 구성.

원칙: 기본정책 탭 위→아래 순서대로 각 요소를 완결 검증.
  타입 → 정책이름 → 드라이브/제어스위트 picker → 프로세스통제 → 기타토글 → 파일감시(보관소/확장자/헤더/예외폴더)
  → 프린트 → 메뉴 → 오프라인 → 커스텀 → 정상생성/삭제.
각 토글: 존재→기본값→ON동작→OFF gating(disabled+추가/수정/삭제 무반응)→이슈.
보고서엔 _add(detail="입력:X / 결과:Y", repro="단계") 로 상세 기록. [AUTO] 만 생성+자체 cleanup.
기본반출정책(singleton)은 확인다이얼로그 '취소'만(데이터안전). picker 선택은 overlay OFF.

템플릿 동작 커버리지: 추가(드라이브 3e/제어스위트 3f/허용·거부 3g/실행차단·특수폴더·폴더동기화 3h
/예외처리·레지스트리 3v), 변경/재설정(드라이브 3e/제어스위트 3f/허용↔거부 3g), 할당해제(3u),
검색(3f — 3진입점 미동작 검출). 드라이브/제어스위트 할당해제는 없음(필수*).
"""
from pages.secure_zone_agent_policy_page import SecureZoneAgentPolicyPage
from tests.secure_zone_policy._base import SecureZonePolicyBase

SERVER_ERR = "서버에서 오류가 발생 하였습니다."
_T_REPRO = "드라이브/제어스위트 '템플릿 선택' → picker 맨 위 행 선택(검색 버그로 fallback)"


class TestSecureZonePolicyScenario3Add(SecureZonePolicyBase):
    """시큐어존 정책 — 시나리오 3: 동작/CRUD (모달 순서)."""

    _CREATED = None

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneAgentPolicyPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _cleanup(self, page, name):
        try:
            page.navigate_to()
            if name in page.get_policy_names():
                page.delete_policy(name)
        except Exception:
            pass

    # ══ 타입 ══════════════════════════════════════════════════════
    def test_scenario3a_type_and_takeout_default(self, logged_in_page, settings):
        """타입(일반/반출) default·전환 + 기본반출정책 singleton(확인다이얼로그 '취소'만)."""
        print("\n━━ [시큐어존 정책] 시나리오 3a: 타입/기본반출정책 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3a 타입/기본반출정책",
                                 ["div#addItemModal.in input#szAgentPolicyTypeDefault"], sc=3):
            page._close_modal_if_open(); return

        td = page.field_state("szAgentPolicyTypeDefault")
        self._add("pass" if td.get("checked") else "fail",
                  "sc3a — 타입 default '일반' 선택",
                  f"입력: 모달 최초 열림 / 결과: 일반 radio checked={td.get('checked')} (기대 True)", sc=3,
                  repro="1. 정책추가 모달 열기\n2. 타입 기본 선택값(일반) 확인")

        # 반출 전환 (dialog 없음 — 실측)
        page.set_toggle("szAgentPolicyTypeTakeout", True)
        tt = page.field_state("szAgentPolicyTypeTakeout")
        self._add("pass" if tt.get("checked") else "fail",
                  "sc3a — 타입 '반출' 전환",
                  f"입력: 반출 radio 클릭 / 결과: 반출 checked={tt.get('checked')}", sc=3,
                  repro="1. 타입 '반출' 클릭\n2. 반출 선택 전환 확인")

        # 기본반출정책 체크 → 확인 다이얼로그 → '취소'(데이터안전, 절대 확인 X)
        page.set_toggle("isSzAgentPolicyTypeTakeoutDefault", True)
        msg = page.cancel_confirm_modal()
        warned = "기본반출정책" in msg or "변경" in msg
        self._add("pass" if warned else "warn",
                  "sc3a — 기본반출정책 체크 시 singleton 경고(취소)",
                  f"입력: 기본반출정책 체크 / 결과: 확인다이얼로그={msg!r} → '취소' 처리 "
                  "(전역 singleton — 확인 시 타 정책 영향이라 절대 확인 안 함)", sc=3,
                  repro=("1. 타입 반출\n2. '기본반출정책' 체크\n"
                         "3. '타 정책의 기본반출정책이 제거됩니다' 다이얼로그 확인\n4. **취소** 클릭(데이터안전)"))
        page._close_modal_if_open()

    # ══ 정책이름 ══════════════════════════════════════════════════
    def test_scenario3b_name_required_empty(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 3b: 정책이름 필수 빈값 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3b 정책이름 필수",
                                 [f"div#addItemModal.in {page.SEL_NAME}"], sc=3):
            page._close_modal_if_open(); return
        msg = page.submit_and_message()
        expected = "필수 입력값이 입력되지 않았습니다."
        self._add("pass" if msg == expected else "fail",
                  "sc3b — 필수(이름/드라이브/제어스위트) 빈값 제출 차단",
                  f"입력: 이름·드라이브·제어스위트 전부 빈값 등록 / 결과: 경고={msg!r} (기대={expected!r})",
                  sc=3, highlight=page.page.locator(page.SEL_NAME),
                  repro=("1. 모달 열기\n2. 이름/드라이브/제어스위트 빈값\n3. 등록 클릭\n4. 경고 확인"))
        page._close_modal_if_open()

    def test_scenario3c_name_duplicate(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 3c: 정책이름 중복 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_dup"
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3c 정책이름 중복",
                                 [f"div#addItemModal.in {page.SEL_NAME}"], sc=3):
            page._close_modal_if_open(); return
        msg1 = page.create_basic_policy(name)
        page.navigate_to()
        page.open_add_modal()
        msg2 = page.create_basic_policy(name)
        dup = "이미" in msg2 or "중복" in msg2
        self._add("pass" if dup else "fail",
                  "sc3c — 동일 이름 재생성 중복 차단",
                  f"입력: 동일 '{name}' 2회 생성 / 결과: 1차={msg1!r}, 2차={msg2!r} (기대 '이미/중복')",
                  sc=3, highlight=page.page.locator(page.SEL_NAME),
                  repro=(f"1. '{name}'+템플릿+등록(1차)\n2. 같은 '{name}'+템플릿+등록(2차)\n3. 2차 경고 확인"))
        page._close_modal_if_open()
        self._cleanup(page, name)

    def test_scenario3d_name_special_char(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 3d: 정책이름 특수문자 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = page.AUTO_NAME_PREFIX + "_sc';!@#$%"
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3d 특수문자 이름",
                                 [f"div#addItemModal.in {page.SEL_NAME}"], sc=3):
            page._close_modal_if_open(); return
        msg = page.create_basic_policy(name)
        saved = "저장" in msg and "오류" not in msg
        self._add("warn" if saved else "pass",
                  "sc3d — 특수문자 이름 차단 여부",
                  f"입력: 이름=\"{name}\" + 템플릿 / 결과: {msg!r} "
                  + ("[차단 없이 저장됨 — known issue 가능]" if saved else "[차단됨]"),
                  sc=3, highlight=page.page.locator(page.SEL_NAME),
                  repro=(f"1. 이름=\"{name}\"\n2. {_T_REPRO}\n3. 등록 → 저장/차단 확인"))
        page._close_modal_if_open()
        self._cleanup(page, name)

    # ══ 드라이브 / 제어스위트 설정 (템플릿 picker) ════════════════
    def test_scenario3e_drive_template_picker(self, logged_in_page, settings):
        """드라이브 설정 picker: default '없음' + 선택→'템플릿명' 출력. (할당해제/재설정=SKIP)."""
        print("\n━━ [시큐어존 정책] 시나리오 3e: 드라이브 템플릿 picker ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3e 드라이브 템플릿 picker",
                                 [page.SEL_TEMPLATE_BTN], sc=3):
            page._close_modal_if_open(); return

        m = page.page.locator("div#addItemModal.in")
        txt0 = m.inner_text()
        none_default = "드라이브 설정" in txt0  # 기본 '없음' 영역 존재
        picked = page.select_template_top(0)   # 맨 위 템플릿 선택
        txt1 = page.page.locator("div#addItemModal.in").inner_text()
        shown = bool(picked) and picked.split()[0] in txt1
        self._add("pass" if shown else "fail",
                  "sc3e — 드라이브 설정 picker 선택 → '없음→템플릿명' 출력",
                  f"입력: 드라이브 '템플릿 선택' → 맨 위 행 선택('{picked}') / 결과: 드라이브 행에 템플릿명 표시={shown}",
                  sc=3, highlight=page.page.locator(page.SEL_TEMPLATE_BTN).first,
                  repro=("1. 드라이브 '템플릿 선택' 클릭 → picker\n2. 맨 위 템플릿 선택 → 확인\n"
                         "3. 드라이브 설정에 '없음'→'템플릿명'으로 바뀌는지 확인"))
        # 재설정(다른 템플릿으로 변경) — 할당해제 버튼은 없음(필수*, 실측 2026-06-12)
        name2 = page.reselect_template(0, 1)   # 2번째 행으로 재설정
        row = page.drive_row_text()
        reset_ok = bool(name2) and name2.split()[0] in row and picked != name2
        self._add("pass" if reset_ok else "warn",
                  "sc3e — 드라이브 재설정(다른 템플릿으로 변경)",
                  f"입력: 템플릿 선택 재클릭 → 2번째 템플릿('{name2}') / 결과: 드라이브 행={row!r}, 변경됨={reset_ok} "
                  "(드라이브/제어스위트는 필수* — 할당해제 버튼 없음, 재클릭=재설정만)",
                  sc=3, highlight=page.page.locator(page.SEL_TEMPLATE_BTN).first,
                  repro=("1. 드라이브 템플릿 선택(1번째)\n2. '템플릿 선택' 재클릭 → 2번째 선택 → 확인\n"
                         "3. 드라이브 행이 2번째 템플릿으로 바뀌는지 확인"))
        page._close_modal_if_open()

    def test_scenario3f_suite_picker_and_search(self, logged_in_page, settings):
        """제어스위트 picker + 템플릿 picker 검색 동작(제품 버그 검출)."""
        print("\n━━ [시큐어존 정책] 시나리오 3f: 제어스위트 picker + 검색 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3f 제어스위트 picker",
                                 [page.SEL_TEMPLATE_BTN], sc=3):
            page._close_modal_if_open(); return

        picked = page.select_template_top(1)   # 제어스위트
        txt = page.page.locator("div#addItemModal.in").inner_text()
        shown = bool(picked) and picked.split()[0] in txt
        self._add("pass" if shown else "fail",
                  "sc3f — 제어스위트 picker 선택 → 템플릿명 출력",
                  f"입력: 제어스위트 '템플릿 선택' → 맨 위 행('{picked}') / 결과: 표시={shown}", sc=3,
                  repro="1. 제어스위트 '템플릿 선택' → picker\n2. 맨 위 선택 → 확인\n3. 템플릿명 표시 확인")

        # 제어스위트 재설정(다른 템플릿으로 변경) — 드라이브와 동일(할당해제 없음, 재클릭=재설정)
        name2 = page.reselect_template(1, 1)   # 제어스위트(btn 1) → 2번째 행
        txt2 = page.page.locator("div#addItemModal.in").inner_text()
        reset_ok = bool(name2) and name2.split()[0] in txt2 and picked != name2
        self._add("pass" if reset_ok else "warn",
                  "sc3f — 제어스위트 재설정(다른 템플릿으로 변경)",
                  f"입력: 제어스위트 재클릭 → 2번째 템플릿('{name2}') / 결과: 변경됨={reset_ok} "
                  "(제어스위트는 필수* — 할당해제 없음, 재클릭=재설정만. 템플릿 1개뿐이면 변경 불가→warn)",
                  sc=3, highlight=page.page.locator(page.SEL_TEMPLATE_BTN).nth(1),
                  repro=("1. 제어스위트 템플릿 선택(1번째)\n2. '템플릿 선택' 재클릭 → 2번째 선택 → 확인\n"
                         "3. 제어스위트 행이 2번째 템플릿으로 바뀌는지 확인"))

        # picker 검색 미동작 — 모든 진입점이 동일 div#selectCommonPolicyItemModal 단일 요소 공유(근원 중복).
        #   중복 이슈지만 사용자 검색 진입점이 8군데로 다 달라 '전 진입점' 검출(곳곳에서 노출).
        #   기본정책 탭: 드라이브(0)/제어스위트(1)
        #   템플릿설정 탭: 허용·거부(0)/예외처리(1)/실행차단(2)/특수폴더(3)/레지스트리(4)/폴더동기화(5)
        #   실측 2026-06-12: 검색 미동작. 빈 picker(해당 템플릿 0건)는 필터 판정 불가 → skip.
        for idx, nm, tab in [
            (0, "드라이브", "기본정책"),
            (1, "제어스위트", "기본정책"),
            (0, "템플릿설정 허용/거부", "템플릿설정"),
            (1, "템플릿설정 예외처리", "템플릿설정"),
            (2, "템플릿설정 실행차단", "템플릿설정"),
            (3, "템플릿설정 특수폴더", "템플릿설정"),
            (4, "템플릿설정 레지스트리", "템플릿설정"),
            (5, "템플릿설정 폴더동기화", "템플릿설정"),
        ]:
            res = page.picker_search_filters(idx, "전사", tab=tab)
            if res["before"] == 0:
                self._add("skip", f"sc3f — {nm} picker 검색 (빈 목록)",
                          f"입력: [{tab}] {nm} picker / 결과: 검색 전 0건 — 필터 판정 불가, 생략", sc=3)
                page.close_picker()
                continue
            self._add("warn" if not res["filtered"] else "pass",
                      f"sc3f — {nm} 템플릿 picker 검색 필터 동작",
                      f"입력: [{tab}] {nm} picker 검색창 '전사' + 검색 버튼 / 결과: 검색 전 {res['before']} → 후 {res['after']}건 "
                      + ("[결함: 결과 불변 = 검색 미동작(낮음). 공유 컴포넌트라 근원 중복이나 진입점마다 노출]" if not res["filtered"] else "[필터 동작]"),
                      sc=3, highlight=page.page.locator(page.SEL_PICKER_SEARCH),
                      repro=f"1. [{tab}] {nm} '템플릿 선택/설정' → picker\n2. 검색창 '전사' 입력\n3. 검색 버튼\n4. 결과 건수 변화 확인")
            page.close_picker()
        page._close_modal_if_open()

    # ══ 프로세스 통제기능 ═════════════════════════════════════════
    def test_scenario3g_process_control_gating(self, logged_in_page, settings):
        """프로세스 통제기능(master) OFF→하위(강제종료/예외처리) 비활성, ON→활성.
        (검증A: OFF인데 템플릿설정 할당 / 검증B: 허용·거부→강제종료 gating = SKIP, 세션 필요)."""
        print("\n━━ [시큐어존 정책] 시나리오 3g: 프로세스 통제기능 gating ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3g 프로세스 통제기능",
                                 ["div#addItemModal.in input#isAllowDenyProcessUse"], sc=3):
            page._close_modal_if_open(); return

        for dep, dl in [("isAllowProcessForceStop", "강제종료"), ("isExceptProcess", "예외처리")]:
            off = page.field_state(dep)
            self._add("pass" if off.get("disabled") else "warn",
                      f"sc3g — 프로세스통제 OFF 시 '{dl}' 비활성",
                      f"입력: 프로세스 통제기능 OFF(기본) / 결과: {dep} disabled={off.get('disabled')} (기대 True)",
                      sc=3, repro=f"1. 모달 열기(프로세스통제 OFF)\n2. '{dl}' 체크박스 disabled 확인")
        page.set_toggle("isAllowDenyProcessUse", True)
        on = page.field_state("isAllowProcessForceStop")
        # ON 만으로 활성 안 될 수 있음(템플릿 종속) → 상태만 보고, disabled True 면 정보성
        self._add("pass" if on.get("disabled") is False else "warn",
                  "sc3g — 프로세스통제 ON 시 '강제종료' 활성 여부",
                  f"입력: 프로세스 통제기능 ON / 결과: isAllowProcessForceStop disabled={on.get('disabled')} "
                  "(허용 프로세스 템플릿 없으면 비활성 유지일 수 있음 — 검증B로 정밀 확인 예정)", sc=3,
                  repro="1. '프로세스 통제기능 사용' ON\n2. '강제종료' 활성 여부 확인")
        page.set_toggle("isAllowDenyProcessUse", False)   # 다시 OFF (검증A 준비)

        # 검증A: 프로세스통제 OFF 상태에서 템플릿설정 탭에 허용 템플릿 '할당 가능'한지
        allow_nm = page.assign_process_template("허용")
        # 등록 표시: 허용 등록 후 행이 '없음'→'허용 프로세스 [할당해제] {명}' 으로 정확히 뜨는지
        area = page.process_template_area_text()
        shown = ("허용 프로세스" in area) and ("할당해제" in area)
        self._add("pass" if shown else "fail",
                  "sc3g — 허용 프로세스 템플릿 등록 표시 정확성",
                  f"입력: 허용 템플릿('{allow_nm}') 할당 / 결과: 프로세스 템플릿 행={area!r} "
                  "(기대: '없음' → '허용 프로세스 [할당해제] 템플릿명')",
                  sc=3, repro=("1. 허용/거부 프로세스 [설정] → 허용 선택 → 확인\n"
                               "2. 행이 '허용 프로세스 [할당해제] {템플릿명}'으로 정확히 뜨는지 확인"))
        page.goto_modal_tab("기본정책")
        master_after = page.field_state("isAllowDenyProcessUse")
        assigned = bool(allow_nm)
        self._add("warn" if (assigned and master_after.get("checked") is False) else "pass",
                  "sc3g — 검증A: 프로세스통제 OFF인데 템플릿설정 할당 가능",
                  f"입력: 프로세스통제 OFF 상태에서 템플릿설정 탭 허용 템플릿('{allow_nm}') 할당 / "
                  f"결과: 할당됨={assigned}, master={master_after.get('checked')} "
                  + ("[미사용(OFF)인데 템플릿 할당됨 — UX 결함 가능(낮음)]" if assigned else ""),
                  sc=3,
                  repro=("1. 프로세스 통제기능 OFF\n2. 템플릿설정 탭 → 허용/거부 프로세스 [설정] → 허용 선택\n"
                         "3. OFF인데 할당되는지 확인"))

        # 검증B-허용: master ON → 강제종료 활성
        page.set_toggle("isAllowDenyProcessUse", True)
        f_allow = page.field_state("isAllowProcessForceStop")
        self._add("pass" if f_allow.get("disabled") is False else "fail",
                  "sc3g — 검증B: 허용 템플릿 + master ON → '강제종료' 활성",
                  f"입력: 허용 프로세스 템플릿 할당 + 프로세스통제 ON / 결과: isAllowProcessForceStop disabled={f_allow.get('disabled')} (기대 False=활성)",
                  sc=3, highlight=page.page.locator("div#addItemModal.in #isAllowProcessForceStop"),
                  repro=("1. 허용 프로세스 템플릿 할당\n2. 프로세스 통제기능 ON\n3. '강제종료' 활성 확인"))

        # 예외처리 프로세스 사용 — master ON 으로 활성 (강제종료와 달리 템플릿 무관, 실측 2026-06-12)
        e_on = page.field_state("isExceptProcess")
        self._add("pass" if e_on.get("disabled") is False else "warn",
                  "sc3g — 예외처리 프로세스 사용 (master ON 시 활성)",
                  f"입력: 프로세스 통제기능 ON / 결과: isExceptProcess disabled={e_on.get('disabled')} "
                  "(기대 False=활성. 예외처리는 강제종료와 달리 허용 템플릿 없이 master 만으로 활성)",
                  sc=3, repro="1. 프로세스 통제기능 ON\n2. '예외처리 프로세스 사용' 활성 확인")

        # 검증B-거부: 거부 템플릿으로 교체 → 강제종료 막힘
        deny_nm = page.assign_process_template("거부")
        page.goto_modal_tab("기본정책")
        f_deny = page.field_state("isAllowProcessForceStop")
        self._add("pass" if f_deny.get("disabled") is True else "fail",
                  "sc3g — 검증B: 거부 템플릿 → '강제종료' 막힘",
                  f"입력: 거부 프로세스 템플릿('{deny_nm}') 교체(master ON) / 결과: isAllowProcessForceStop disabled={f_deny.get('disabled')} (기대 True=막힘) "
                  "[허용 프로세스가 있어야 강제종료 의미 → 거부면 막힘 = 정상 gating]",
                  sc=3, highlight=page.page.locator("div#addItemModal.in #isAllowProcessForceStop"),
                  repro=("1. 거부 프로세스 템플릿으로 교체\n2. '강제종료' 비활성(막힘) 확인"))
        page._close_modal_if_open()

    # ══ 기타 top 토글 (실행차단/특수폴더/폴더동기화) + 검증A ══════
    def test_scenario3h_other_toggles(self, logged_in_page, settings):
        """실행차단/특수폴더/폴더동기화 토글 반응 + 검증A(토글 OFF인데 템플릿설정 할당 가능, 프로세스통제와 동일)."""
        print("\n━━ [시큐어존 정책] 시나리오 3h: 기타 토글 + 검증A ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3h 기타 토글(실행차단/특수폴더/폴더동기화)",
                                 ["div#addItemModal.in input#isBlockExecuteProcess"], sc=3):
            page._close_modal_if_open(); return
        # ① 토글 반응 (OFF→ON)
        for cid, label in [("isBlockExecuteProcess", "실행차단 프로세스"),
                           ("isManageFolder", "특수폴더"), ("isSyncFolder", "폴더 동기화")]:
            s0 = page.field_state(cid)
            page.set_toggle(cid, True)
            s1 = page.field_state(cid)
            self._add("pass" if (s0.get("checked") is False and s1.get("checked") is True) else "fail",
                      f"sc3h — '{label} 사용' 토글 반응",
                      f"입력: '{label} 사용' 클릭 / 결과: OFF({s0.get('checked')})→ON({s1.get('checked')})", sc=3,
                      repro=f"1. '{label} 사용' 체크박스 클릭\n2. OFF→ON 토글 확인")
            page.set_toggle(cid, False)

        # ② 검증A: 각 토글 OFF(기본)인데 템플릿설정 탭에서 해당 템플릿 할당 가능 (실측 2026-06-12)
        #    [설정] index: 2실행차단 / 3바로가기(특수폴더) / 5폴더동기화
        for cid, btn_idx, feat in [("isBlockExecuteProcess", 2, "실행차단 프로세스"),
                                   ("isManageFolder", 3, "특수폴더(바로가기)"),
                                   ("isSyncFolder", 5, "폴더동기화")]:
            name = page.assign_template_setting(btn_idx)
            page.goto_modal_tab("기본정책")
            tog = page.field_state(cid)
            assigned = bool(name)
            if not assigned:
                self._add("skip", f"sc3h — 검증A: '{feat}' (할당 가능 템플릿 없음)",
                          f"입력: - / 결과: {feat} 템플릿 picker 비어있음/실패 — 검증 생략", sc=3)
                continue
            self._add("warn" if tog.get("checked") is False else "pass",
                      f"sc3h — 검증A: '{feat}' 사용 OFF인데 템플릿 할당 가능",
                      f"입력: '{feat} 사용' OFF에서 {feat} 템플릿('{name}') 할당 / 결과: 할당됨={assigned}, 토글={tog.get('checked')} "
                      + ("[미사용(OFF)인데 템플릿 할당됨 — UX 결함 가능(낮음)]" if tog.get("checked") is False else ""),
                      sc=3,
                      repro=(f"1. '{feat} 사용' 토글 OFF\n2. 템플릿설정 탭 → {feat} [설정] → 선택\n"
                             "3. OFF인데 할당되는지 확인"))
        page._close_modal_if_open()

    # ══ 파일 감시기능 (master) ════════════════════════════════════
    def test_scenario3i_filewatch_master_gating(self, logged_in_page, settings):
        """파일감시 master OFF→하위(보관소/확장자/예외폴더 등) disabled+버튼 클릭 무반응, ON→활성."""
        print("\n━━ [시큐어존 정책] 시나리오 3i: 파일감시 master gating ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()   # 파일감시 OFF 기본
        if self._skip_if_missing(page, "sc3i 파일감시 master",
                                 ["div#addItemModal.in input#isWatchFile"], sc=3):
            page._close_modal_if_open(); return

        # master OFF → 하위항목 전체(보관소/확장자 3종/예외폴더 3종/헤더) 비활성 확인
        subs = page.filewatch_sub_disabled()
        enabled_left = [k for k, v in subs.items() if v is not True]
        all_off = len(enabled_left) == 0
        self._add("pass" if all_off else "warn",
                  "sc3i — 파일감시 OFF 시 하위항목 전체 비활성",
                  "입력: 파일감시 OFF / 결과: " + ", ".join(f"{k}={v}" for k, v in subs.items())
                  + (" [전체 disabled — gating 정상]" if all_off else f" [결함: 활성 잔존 {enabled_left}]"),
                  sc=3, highlight=page.page.locator(page.SEL_WATCH_EXT_INPUT),
                  repro="1. 모달 열기(파일감시 OFF)\n2. 보관소/확장자(체크박스·입력·추가)/예외폴더(체크박스·특수폴더·추가)/헤더 전부 disabled 확인")
        # OFF 에서 확장자 [추가] 클릭 → 무반응
        before = len(page.watch_extension_items())
        try:
            page.page.locator(page.SEL_WATCH_EXT_ADD).evaluate("el => el.click()")
            page.page.wait_for_timeout(150)
        except Exception:
            pass
        after = len(page.watch_extension_items())
        self._add("pass" if after == before else "warn",
                  "sc3i — 파일감시 OFF 시 확장자 [추가] 클릭 무반응",
                  f"입력: 파일감시 OFF에서 확장자 [추가] 클릭 / 결과: 리스트 {before}→{after} "
                  + ("(불변 — gating 정상)" if after == before else "[결함: OFF인데 추가됨]"),
                  sc=3, highlight=page.page.locator(page.SEL_WATCH_EXT_ADD),
                  repro="1. 파일감시 OFF\n2. 확장자 [추가] 클릭\n3. 리스트 불변 확인")
        # ON → 활성
        page.set_toggle("isWatchFile", True)
        sp_on = page.field_state("watchFileStorePath")
        self._add("pass" if sp_on.get("disabled") is False else "fail",
                  "sc3i — 파일감시 ON 시 '보관소 지정' 활성",
                  f"입력: 파일감시 ON / 결과: 보관소 disabled={sp_on.get('disabled')} (기대 False)", sc=3,
                  repro="1. 파일 감시기능 ON\n2. 보관소 필드 활성 확인")
        page._close_modal_if_open()

    def test_scenario3j_watchpath_data_loss(self, logged_in_page, settings):
        """보관소 400자 저장 → 재오픈 시 빈값(데이터 손실 🔴)."""
        print("\n━━ [시큐어존 정책] 시나리오 3j: 보관소 값 손실 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_wfsp"
        sel = "div#addItemModal.in input#watchFileStorePath"
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3j 보관소 값 손실",
                                 ["div#addItemModal.in input#isWatchFile"], sc=3):
            page._close_modal_if_open(); return
        page.fill(page.SEL_NAME, name)
        page.select_template_top(0); page.select_template_top(1)
        page.set_toggle("isWatchFile", True)
        page.fill(sel, "a" * 400)
        msg = page.submit_and_message()
        self._add("pass" if "저장" in msg else "fail",
                  "sc3j — 보관소 400자 입력 후 저장 메시지",
                  f"입력: 보관소에 'a'×400자 / 결과: 저장 메시지={msg!r}", sc=3,
                  repro=(f"1. 이름='{name}'+템플릿\n2. 파일감시 ON\n3. 보관소 a×400자\n4. 등록"))
        if name in page.get_policy_names():
            page.open_modify_modal(name)
            st = page.field_state("watchFileStorePath")
            wf = page.field_state("isWatchFile")
            saved_len = len(st.get("value") or "")
            empty = saved_len == 0
            self._add("fail" if empty else "pass",
                      ("🔴 sc3j — 저장 후 재오픈 시 보관소 경로 값 유지" if empty
                       else "sc3j — 저장 후 재오픈 시 보관소 경로 값 유지"),
                      f"입력: 400자 저장 정책 '{name}' 재오픈 / 결과: 파일감시={wf.get('checked')}, "
                      f"저장된 보관소 길이={saved_len}자 (기대 400) "
                      + ("[🔴 결함: 저장 성공인데 값 비워져 저장됨 = 데이터 손실]" if empty else ""),
                      sc=3, highlight=page.page.locator(sel),
                      repro=(f"1. '{name}' 선택 → 수정\n2. 보관소 값/길이 확인"))
            page.close_edit_modal()
        self._cleanup(page, name)

    def test_scenario3k_extension_cases(self, logged_in_page, settings):
        """확장자 입력 8케이스: 단일/;다중/빈값/중복/특수문자/한글/와일드카드/삭제."""
        print("\n━━ [시큐어존 정책] 시나리오 3k: 확장자 입력 케이스 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3k 확장자 입력",
                                 ["div#addItemModal.in input#isWatchFile"], sc=3):
            page._close_modal_if_open(); return
        page.set_toggle("isWatchFile", True)
        _ext = page.page.locator(page.SEL_WATCH_EXT_INPUT)

        it, _ = page.add_extension_msg("exe")
        self._add("pass" if "exe" in it else "fail", "sc3k — ① 확장자 단일 추가('exe')",
                  f"입력: 'exe'+[추가] / 결과: 리스트={it}", sc=3,
                  repro="1. 파일감시 ON\n2. 'exe' 입력\n3. [추가]")
        it, _ = page.add_extension_msg("dll;txt")
        self._add("pass" if ("dll" in it and "txt" in it) else "fail", "sc3k — ② ';' 다중('dll;txt')",
                  f"입력: 'dll;txt'+[추가] / 결과: 리스트={it} (분리 기대)", sc=3,
                  repro="1. 'dll;txt' 입력\n2. [추가]\n3. 2개 분리")
        it, msg = page.add_extension_msg("")
        self._add("pass" if "입력" in msg else "fail", "sc3k — ③ 빈값 차단",
                  f"입력: 빈값+[추가] / 결과: 경고={msg!r} (기대 '확장자를 입력하세요')", sc=3,
                  repro="1. 빈값\n2. [추가]\n3. 경고 확인")
        it, msg = page.add_extension_msg("exe")
        self._add("pass" if ("이미" in msg or "동일" in msg) else "fail", "sc3k — ④ 중복 차단('exe')",
                  f"입력: 'exe' 재추가 / 결과: 경고={msg!r} (기대 '이미 동일한 확장자')", sc=3,
                  repro="1. 'exe' 재입력\n2. [추가]\n3. 중복 경고")
        it, msg = page.add_extension_msg("a!@#")
        self._add("pass" if ("제외" in msg or "특수문자" in msg) else "warn", "sc3k — ⑤ 특수문자 차단('a!@#')",
                  f"입력: 'a!@#' / 결과: 경고={msg!r} (기대 '. * ; ? 이외 제외')", sc=3, highlight=_ext,
                  repro="1. 'a!@#' 입력\n2. [추가]\n3. 특수문자 차단 경고")
        it, msg = page.add_extension_msg("한글")
        self._add("pass" if ("제외" in msg or "한글" in msg) else "warn", "sc3k — ⑥ 한글 차단('한글')",
                  f"입력: '한글' / 결과: 경고={msg!r}", sc=3, highlight=_ext,
                  repro="1. '한글' 입력\n2. [추가]\n3. 한글 차단 경고")
        it, msg = page.add_extension_msg("*")
        self._add("pass" if "*" in it else "warn", "sc3k — ⑦ 와일드카드 '*' 허용",
                  f"입력: '*' / 결과: 리스트={it} (. * ; ? 허용)", sc=3,
                  highlight=page.page.locator(page.SEL_WATCH_EXT_LIST),
                  repro="1. '*' 입력\n2. [추가]\n3. 허용 확인")
        before = len(page.watch_extension_items())
        page.delete_first_watch_extension()
        after = len(page.watch_extension_items())
        self._add("pass" if after == before - 1 else "fail", "sc3k — ⑧ 확장자 삭제(x)",
                  f"입력: 첫 항목 x / 결과: {before}→{after} (1 감소)", sc=3,
                  repro="1. 첫 항목 x 클릭\n2. 1 감소 확인")
        page._close_modal_if_open()

    def test_scenario3l_subtoggle_off_gating(self, logged_in_page, settings):
        """파일감시 하위 체크박스(확장자/예외폴더) OFF인데 동작되면 gating 부재 WARN.
        둘 다 같은 유형 — 나란히 검증 (실측 2026-06-12: 예외폴더 버튼도 OFF인데 enabled)."""
        print("\n━━ [시큐어존 정책] 시나리오 3l: 하위 체크박스 OFF gating ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3l 하위 체크박스 OFF gating",
                                 ["div#addItemModal.in input#isWatchFile"], sc=3):
            page._close_modal_if_open(); return
        page.set_toggle("isWatchFile", True)

        # ① 감시할 확장자 체크박스 OFF → 추가 시도
        page.set_toggle("isWatchFileExtention", False)
        cb = page.field_state("isWatchFileExtention")
        page.add_watch_extension("exe")
        items = page.watch_extension_items()
        added = "exe" in items
        self._add("warn" if added else "pass",
                  "sc3l — ① '감시할 확장자' OFF 시 입력 차단 여부",
                  f"입력: 감시할 확장자 OFF(checked={cb.get('checked')})에서 'exe' 추가 / 결과: 리스트={items} "
                  + ("[결함: OFF인데 추가됨 — gating 부재(낮음)]" if added else "[정상 차단]"), sc=3,
                  highlight=page.page.locator(page.SEL_WATCH_EXT_LIST),
                  repro=("1. 파일감시 ON\n2. '감시할 확장자' 체크박스 OFF\n3. 'exe'+[추가]\n4. 차단 여부 확인"))

        # ② 감시 예외 폴더 체크박스 OFF → [특수폴더]/[추가] 버튼 비활성 여부 (확장자와 동일 유형)
        page.set_toggle("isWatchFolder", False)
        wfo = page.field_state("isWatchFolder")
        sp = page.page.locator(page.SEL_WATCH_FOLDER_SPECIAL).first
        ad = page.page.locator(page.SEL_WATCH_FOLDER_ADD).first
        sp_dis = sp.is_disabled() if sp.count() else None
        ad_dis = ad.is_disabled() if ad.count() else None
        blocked = bool(sp_dis) and bool(ad_dis)
        self._add("pass" if blocked else "warn",
                  "sc3l — ② '감시 예외 폴더' OFF 시 버튼 비활성 여부",
                  f"입력: 예외폴더 체크박스 OFF(checked={wfo.get('checked')}) / 결과: [특수폴더] disabled={sp_dis}, [추가] disabled={ad_dis} "
                  + ("[정상 차단]" if blocked else "[결함: OFF인데 버튼 활성 — gating 부재(낮음). 확장자와 동일 패턴]"),
                  sc=3, highlight=page.page.locator(page.SEL_WATCH_FOLDER_SPECIAL),
                  repro=("1. 파일감시 ON\n2. '감시 예외 폴더' 체크박스 OFF\n"
                         "3. [특수폴더]/[추가] 버튼 비활성(클릭불가) 여부 확인"))
        page._close_modal_if_open()

    def test_scenario3m_header_check(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 3m: 헤더 체크 토글 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3m 헤더 체크",
                                 ["div#addItemModal.in input#isWatchFile"], sc=3):
            page._close_modal_if_open(); return
        page.set_toggle("isWatchFile", True)
        s0 = page.field_state("isWatchFileHeader")
        page.set_toggle("isWatchFileHeader", True)
        s1 = page.field_state("isWatchFileHeader")
        self._add("pass" if (s0.get("checked") is False and s1.get("checked") is True) else "fail",
                  "sc3m — 헤더 체크 기능 토글 반응",
                  f"입력: 파일감시 ON 후 '헤더 체크 기능 사용' 클릭 / 결과: OFF({s0.get('checked')})→ON({s1.get('checked')})",
                  sc=3, repro="1. 파일감시 ON\n2. '헤더 체크 기능 사용' 클릭\n3. OFF→ON 확인")
        page._close_modal_if_open()

    def test_scenario3n_watch_folder_area(self, logged_in_page, settings):
        """감시 예외폴더: 토글 gating + [특수폴더]/[추가]/리스트 UI. (특수폴더 추가/중복=SKIP)."""
        print("\n━━ [시큐어존 정책] 시나리오 3n: 감시 예외 폴더 영역 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3n 감시 예외 폴더",
                                 ["div#addItemModal.in input#isWatchFile"], sc=3):
            page._close_modal_if_open(); return
        off = page.field_state("isWatchFolder")
        self._add("pass" if off.get("disabled") else "warn",
                  "sc3n — 파일감시 OFF 시 '감시 예외 폴더' 비활성",
                  f"입력: 파일감시 OFF / 결과: isWatchFolder disabled={off.get('disabled')} (기대 True)", sc=3,
                  repro="1. 모달 열기(파일감시 OFF)\n2. 예외폴더 체크박스 disabled 확인")
        page.set_toggle("isWatchFile", True)
        on = page.field_state("isWatchFolder")
        self._add("pass" if on.get("disabled") is False else "fail",
                  "sc3n — 파일감시 ON 시 '감시 예외 폴더' 활성",
                  f"입력: 파일감시 ON / 결과: isWatchFolder disabled={on.get('disabled')} (기대 False)", sc=3,
                  repro="1. 파일감시 ON\n2. 예외폴더 체크박스 활성 확인")
        page.set_toggle("isWatchFolder", True)
        sp = page.page.locator(page.SEL_WATCH_FOLDER_SPECIAL).count() > 0
        ad = page.page.locator(page.SEL_WATCH_FOLDER_ADD).count() > 0
        ls = page.page.locator(page.SEL_WATCH_FOLDER_LIST).count() > 0
        self._add("pass" if (sp and ad and ls) else "fail",
                  "sc3n — 예외 폴더 UI([특수폴더]/[추가]/리스트) 존재",
                  f"입력: 예외폴더 ON / 결과: [특수폴더]={sp},[추가]={ad},리스트={ls} (자유입력칸 없음·특수폴더 picker 방식)",
                  sc=3, repro="1. 예외폴더 ON\n2. [특수폴더]/[추가]/리스트 존재 확인")
        # ① 특수폴더(예약어) 추가 — 확인(칩) → [추가] 눌러야 리스트 반영 (실측 2026-06-12)
        items, _ = page.add_watch_folder_reserved("DESKTOP")
        added = any("DESKTOP" in it for it in items)
        self._add("pass" if added else "fail",
                  "sc3n — ① 예외폴더 예약어([/DESKTOP/]) 추가",
                  f"입력: [특수폴더] → '[/DESKTOP/]' 체크 → 확인 → [추가] / 결과: 리스트={items}", sc=3,
                  highlight=page.page.locator(page.SEL_WATCH_FOLDER_LIST),
                  repro=("1. 파일감시+예외폴더 ON\n2. [특수폴더] → '[/DESKTOP/]' 체크 → 확인(칩 생성)\n"
                         "3. **[추가] 클릭**(이거 빠지면 안 들어감)\n4. 리스트 반영 확인"))

        if not added:
            # ① 추가가 안 됐으면 ②중복·③삭제는 대상 없음 → skip (타임아웃 방지)
            self._add("skip", "sc3n — ②중복/③삭제 (추가 미성공으로 생략)",
                      f"입력: - / 결과: ① 추가 실패({items})로 후속 생략", sc=3)
            page._close_modal_if_open()
            return

        # ② 중복 차단
        items2, msg = page.add_watch_folder_reserved("DESKTOP")
        dup_blocked = ("이미" in msg or "존재" in msg) and len(items2) == len(items)
        self._add("pass" if dup_blocked else "warn",
                  "sc3n — ② 동일 예외폴더 중복 차단",
                  f"입력: 같은 '[/DESKTOP/]' 재추가 / 결과: 경고={msg!r}, 리스트={items2} (기대 '이미 등록된 폴더 경로')",
                  sc=3, repro="1. 같은 '[/DESKTOP/]' 다시 [특수폴더]→확인→[추가]\n2. 중복 경고 확인")

        # ③ 삭제
        before = len(page.watch_folder_items())
        deleted = page.delete_first_watch_folder()
        after = len(page.watch_folder_items())
        self._add("pass" if (deleted and after == before - 1) else "fail",
                  "sc3n — ③ 예외폴더 삭제(x)",
                  f"입력: 첫 폴더 항목 x 클릭 / 결과: 개수 {before}→{after} (1 감소 기대), 삭제버튼={deleted}", sc=3,
                  repro="1. 리스트 첫 항목 x 클릭\n2. 1 감소 확인")
        page._close_modal_if_open()

    # ══ 프린트 설정 ═══════════════════════════════════════════════
    def test_scenario3o_print_settings(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 3o: 프린트 설정 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3o 프린트 설정",
                                 ["div#addItemModal.in input#isPrintUse"], sc=3):
            page._close_modal_if_open(); return
        # OFF 기본 → 라디오 disabled + 클릭 무반응
        before_v = page.print_radio_value()
        try:
            page.page.locator("div#addItemModal.in input[name='isPrint'][value='0']").evaluate("el => el.click()")
            page.page.wait_for_timeout(120)
        except Exception:
            pass
        after_v = page.print_radio_value()
        self._add("pass" if before_v == after_v else "warn",
                  "sc3o — 프린트 OFF 시 라디오 클릭 무반응",
                  f"입력: 프린트 OFF에서 '차단'(0) 클릭 / 결과: 선택 {before_v!r}→{after_v!r} "
                  + ("(불변 — gating 정상)" if before_v == after_v else "[결함: OFF인데 변경됨]"),
                  sc=3, repro="1. 프린트 OFF\n2. '차단' 라디오 클릭\n3. 불변 확인")
        # ON → 라디오/입력
        page.set_toggle("isPrintUse", True)
        dv = page.print_radio_value()
        self._add("pass" if dv == "1" else "warn", "sc3o — 프린트 ON default '허용'(1)",
                  f"입력: 프린트 ON / 결과: 선택 value={dv!r} (1 기대)", sc=3,
                  repro="1. 프린트 ON\n2. 기본 '허용' 확인")
        page.set_print_radio("0")
        self._add("pass" if page.print_radio_value() == "0" else "fail", "sc3o — 라디오 '차단'(0) 전환",
                  f"입력: '차단' 클릭 / 결과: {page.print_radio_value()!r} (0 기대)", sc=3,
                  repro="1. '차단' 라디오 클릭\n2. 선택 확인")
        page.set_print_radio("1")
        page.fill("div#addItemModal.in textarea#allowPrintModel", "HP;Canon")
        page.fill("div#addItemModal.in textarea#exceptPrintPort", "USB001;LPT1")
        am = page.page.locator("div#addItemModal.in textarea#allowPrintModel").first.input_value()
        ep = page.page.locator("div#addItemModal.in textarea#exceptPrintPort").first.input_value()
        self._add("pass" if am == "HP;Canon" and ep == "USB001;LPT1" else "fail",
                  "sc3o — 허용 브랜드/제외 포트 입력",
                  f"입력: 허용브랜드='HP;Canon',제외포트='USB001;LPT1' / 결과: {am!r}, {ep!r}", sc=3,
                  repro="1. '허용' 선택\n2. 브랜드/포트 입력\n3. 값 유지 확인")
        page._close_modal_if_open()

    # ══ 메뉴 토글 ═════════════════════════════════════════════════
    def test_scenario3p_menu_toggles(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 3p: 메뉴 토글 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3p 메뉴 토글",
                                 ["div#addItemModal.in input#isShowAgentShutdownMenu"], sc=3):
            page._close_modal_if_open(); return
        for cid, label in [("isShowAgentShutdownMenu", "에이전트 종료 메뉴"),
                           ("isShowEmergencyCodeMenu", "긴급 허용 코드 메뉴")]:
            s0 = page.field_state(cid)
            page.set_toggle(cid, True)
            s1 = page.field_state(cid)
            self._add("pass" if (s0.get("checked") is False and s1.get("checked") is True) else "fail",
                      f"sc3p — '{label} 표시' 토글 반응",
                      f"입력: '{label}' 클릭 / 결과: OFF({s0.get('checked')})→ON({s1.get('checked')})", sc=3,
                      repro=f"1. '{label} 표시' 체크박스 클릭\n2. OFF→ON 확인")
            page.set_toggle(cid, False)
        page._close_modal_if_open()

    # ══ 오프라인 설정 ═════════════════════════════════════════════
    def test_scenario3q_offline_blocktime(self, logged_in_page, settings):
        """오프라인 사용 ON → 차단 대기시간 입력 규칙(소수점 허용/문자 거부/12자)."""
        print("\n━━ [시큐어존 정책] 시나리오 3q: 오프라인 차단 대기시간 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3q 오프라인 차단 대기시간",
                                 ["div#addItemModal.in input#isOfflineUse"], sc=3):
            page._close_modal_if_open(); return
        page.set_toggle("isOfflineUse", True)
        v1, _ = page.type_block_time("1.5")
        self._add("pass" if v1 == "1.5" else "warn", "sc3q — 소수점 입력 허용(분)",
                  f"입력: '1.5' / 결과: {v1!r} (소수 허용)", sc=3,
                  repro="1. 오프라인 ON\n2. 차단대기시간 '1.5'\n3. 값 유지 확인")
        v2, _ = page.type_block_time("abc")
        self._add("pass" if v2 in ("0", "") else "warn", "sc3q — 문자 입력 거부(abc→0)",
                  f"입력: 'abc' / 결과: {v2!r} (문자 거부)", sc=3,
                  repro="1. 'abc' 입력\n2. 0/빈값 거부 확인")
        v3, msg3 = page.type_block_time("1234567890123456")
        if "12자" in msg3:
            self._add("pass", "sc3q — 12자 초과 글자수 경고(정상)",
                      f"입력: 16자 / 결과: 경고={msg3!r} (정상)", sc=3,
                      repro="1. 13자+ 입력\n2. '최대 12자까지' 경고")
        else:
            self._add("skip", "sc3q — 12자 초과 경고 (자동화 미발화)",
                      f"입력: 16자(필드 {len(v3)}자) / 결과: keypress 경고 자동화 미발화 — 수동영역(정상,버그아님)", sc=3)
        # 반출 드라이브 차단 토글
        s0 = page.field_state("isTakeoutDriveBlock")
        page.set_toggle("isTakeoutDriveBlock", True)
        s1 = page.field_state("isTakeoutDriveBlock")
        self._add("pass" if (s0.get("checked") is False and s1.get("checked") is True) else "warn",
                  "sc3q — 반출 드라이브 차단 토글 반응",
                  f"입력: '반출 드라이브 차단' 클릭 / 결과: OFF({s0.get('checked')})→ON({s1.get('checked')})", sc=3,
                  repro="1. 오프라인 ON\n2. '반출 드라이브 차단' 클릭\n3. 토글 확인")
        page._close_modal_if_open()

    # ══ 커스텀 옵션값 ═════════════════════════════════════════════
    def test_scenario3r_custom_option(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 3r: 커스텀 옵션값 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        sel = "div#addItemModal.in input#customOptionText"
        if self._skip_if_missing(page, "sc3r 커스텀 옵션값", [sel], sc=3):
            page._close_modal_if_open(); return
        page.fill(sel, "custom_test_123")
        val = page.page.locator(sel).first.input_value()
        self._add("pass" if val == "custom_test_123" else "fail",
                  "sc3r — 커스텀 옵션값 입력",
                  f"입력: 커스텀 옵션값='custom_test_123' / 결과: 수용값={val!r}", sc=3,
                  repro="1. 커스텀 옵션값 칸에 입력\n2. 값 유지 확인")
        page._close_modal_if_open()

    # ══ CRUD 정상생성 / 삭제 ══════════════════════════════════════
    def test_scenario3s_normal_create(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 3s: 일반 정책 정상 생성 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_add"
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3s 일반 정책 생성",
                                 [f"div#addItemModal.in {page.SEL_NAME}"], sc=3):
            page._close_modal_if_open(); return
        msg = page.create_basic_policy(name)
        ok = "저장" in msg and "오류" not in msg
        self._add("pass" if ok else "fail", "sc3s — 일반 정책 생성 저장",
                  f"입력: 이름='{name}'+드라이브/제어스위트(맨위)+일반 / 결과: {msg!r}", sc=3,
                  repro=f"1. 이름='{name}'\n2. {_T_REPRO}\n3. 등록")
        page.navigate_to()
        exists = name in page.get_policy_names()
        self._add("pass" if exists else "fail", "sc3s — 생성 정책 목록 등록 확인",
                  f"입력: '{name}' / 결과: 목록 존재={exists}", sc=3,
                  repro=f"1. 목록 새로고침\n2. '{name}' 존재 확인")
        if exists:
            TestSecureZonePolicyScenario3Add._CREATED = name

    def test_scenario3t_delete(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 3t: 생성 정책 삭제 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = TestSecureZonePolicyScenario3Add._CREATED
        if not name or name not in page.get_policy_names():
            self._add("skip", "sc3t — 삭제 대상 없음", f"입력: - / 결과: sc3s 생성분 미존재({name})", sc=3)
            return
        page.delete_policy(name)
        page.navigate_to()
        gone = name not in page.get_policy_names()
        self._add("pass" if gone else "fail", "sc3t — 생성 정책 삭제 → 목록에서 사라짐",
                  f"입력: 체크 후 삭제→확인 / 결과: '{name}' 삭제 후 존재={not gone}", sc=3,
                  repro=(f"1. '{name}' 체크\n2. 삭제 버튼\n3. 확인\n4. 목록에서 사라짐 확인"))

    # ══ 템플릿설정 탭: 할당해제 동작 ══════════════════════════════
    def test_scenario3u_template_unassign(self, logged_in_page, settings):
        """템플릿설정 행 할당 → [할당해제] 클릭 → '없음' 복귀 (할당해제 동작 검증).
        드라이브/제어스위트는 할당해제 없음(필수*) → 템플릿설정 탭 행 전용."""
        print("\n━━ [시큐어존 정책] 시나리오 3u: 템플릿 할당해제 동작 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3u 템플릿 할당해제",
                                 [f"div#addItemModal.in {page.SEL_NAME}"], sc=3):
            page._close_modal_if_open(); return

        nm = page.assign_process_template("허용")
        area1 = page.process_template_area_text()
        assigned = bool(nm) and "할당해제" in area1
        if not assigned:
            self._add("skip", "sc3u — 할당해제 (할당 가능 허용 템플릿 없음)",
                      f"입력: - / 결과: 허용 템플릿 할당 실패({nm!r}) — 후속 생략", sc=3)
            page._close_modal_if_open(); return

        released = page.unassign_template_setting()
        area2 = page.process_template_area_text()
        gone = released and ("할당해제" not in area2)
        self._add("pass" if gone else "fail",
                  "sc3u — 허용 프로세스 [할당해제] → '없음' 복귀",
                  f"입력: 허용 템플릿('{nm}') 할당 후 [할당해제] 클릭 / 결과: 해제전={area1!r} → 해제후={area2!r} "
                  + ("(해제됨 — '할당해제' 링크 사라짐)" if gone else "[결함: 할당해제 후에도 잔존]"),
                  sc=3, repro=("1. 템플릿설정 탭 → 허용/거부 [설정] → 허용 선택 → 확인\n"
                               "2. '허용 프로세스 [할당해제] {명}'에서 [할당해제] 클릭\n"
                               "3. '없음'으로 복귀하는지 확인"))
        page._close_modal_if_open()

    # ══ 템플릿설정 탭: 예외처리/레지스트리 [설정] 할당 (3g/3h 미커버분) ══
    def test_scenario3v_remaining_template_settings(self, logged_in_page, settings):
        """6행 중 sc3g(허용/거부)·sc3h(실행차단/특수폴더/폴더동기화) 미커버분 = 예외처리(1)/레지스트리(4) 할당."""
        print("\n━━ [시큐어존 정책] 시나리오 3v: 예외처리/레지스트리 템플릿 할당 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        if self._skip_if_missing(page, "sc3v 예외처리/레지스트리 할당",
                                 [f"div#addItemModal.in {page.SEL_NAME}"], sc=3):
            page._close_modal_if_open(); return

        for btn_idx, feat in [(1, "예외처리 프로세스"), (4, "레지스트리 변경")]:
            nm = page.assign_template_setting(btn_idx)
            if not nm:
                self._add("skip", f"sc3v — '{feat}' (할당 가능 템플릿 없음)",
                          f"입력: {feat} [설정] / 결과: picker 비어있음/실패 — 검증 생략", sc=3)
                continue
            txt = page.template_tab_text()
            shown = nm.split()[0] in txt
            self._add("pass" if shown else "fail",
                      f"sc3v — '{feat}' 템플릿 할당 등록 표시",
                      f"입력: {feat} [설정] → 맨 위 템플릿('{nm}') / 결과: 탭 텍스트에 표시={shown}", sc=3,
                      repro=(f"1. 템플릿설정 탭 → {feat} [설정]\n2. 맨 위 템플릿 선택 → 확인\n"
                             f"3. 행에 '[할당해제] 템플릿명'으로 등록 표시되는지 확인"))
        page._close_modal_if_open()
