"""원본보호 정책 — 시나리오 4: EDIT 모달 수정 동작 검증.

sc3 (ADD) 와 sc4 (EDIT) 의 동작 차이를 검증. EDIT 모달은 ADD 와 같은 컨테이너
(#addItemModal) 재사용 → 입력 마스킹·워터마크·list 등 자동 검증은 ADD 와 동일.
단 다음 영역에서 ADD 와 다른 동작 발견 (Chrome MCP 직접 재현 2026-05-29):

  🔴 HIGH:
    sc4c 이름 중복 검증 부재 — 다른 정책 이름으로 변경 + 저장 성공 (sc3b 와 동작 불일치)
    sc4e Quota 빈값 → 0 silent 변환 (실 데이터 변경, sc3a β3 차단 메시지 부재)

  🟡 MEDIUM:
    sc4d driveLetter/driveLabel 빈값 silent revert + 거짓 성공 메시지
    sc4f 4-3 패턴 부재 (client 검증 케이스만 — server reject 케이스는 정상)

  ⚠ UX:
    sc4l EDIT 모달 title='정책 추가' 그대로
    sc4m 워터마크 numeric default '' (ADD) vs '0' (EDIT) 불일치
    sc4n CSU picker radio unchecked

sc4 전제 조건: sc3g 가 [AUTO]_sc3g_normal_save 정책을 사전 등록 (driveLetter=Y,
driveLabel=Sc3gLabel, Quota=200, CSU=[AUTO_KEEP]_sc5_step1). 본 시나리오는 그 정책
재사용 — sc3 → sc4 lifecycle.
"""
from pages.npouch_origin_protect_policy_page import NpouchOriginProtectPolicyPage
from tests.origin_protect._base import OriginProtectBase


# 공통 헬퍼 — EDIT 모달 진입
def _enter_edit_modal(page, name: str):
    """list 행 선택 + modifyItemBtn click → EDIT 모달 진입.

    list 렌더 안정화 wait 강화 (2026-05-29 사용자 보고 — click_policy_row 3000ms timeout
    원인 = list 미렌더). navigate_to 후 SEL_TABLE_ROW first attached + 정책 row attached
    명시 대기 후 open_modify_modal 호출.
    """
    page.navigate_to()
    # 검색 input 잔존 reset (사용자 보고 + Chrome MCP 확인 2026-05-29):
    # sc3k 가 NAME 검색 후 비우지 않음 → sc4 통합 실행 시 list 필터링 → row not found.
    # navigate_to 의 early return 케이스에서도 검색 input 은 reset 안 됨.
    try:
        si = page.page.locator(page.SEL_SEARCH_INPUT)
        if si.count() > 0 and si.input_value():
            si.fill("")
            page.page.locator("button#searchBtn").first.evaluate("el => el.click()")
            page.page.wait_for_timeout(800)
    except Exception:
        pass
    # ① list 첫 행이 DOM 에 attached 될 때까지 대기 (최대 10초)
    page.page.locator(page.SEL_TABLE_ROW).first.wait_for(state="attached", timeout=10000)
    # ② AngularJS 비동기 list 렌더 안정화 추가 wait
    page.page.wait_for_timeout(800)
    # ③ 정책 row 자체 attached 확인 (없으면 명시 예외 — silent stuck 차단)
    target_row = page.page.locator(page.SEL_TABLE_ROW).filter(has_text=name).first
    try:
        target_row.wait_for(state="attached", timeout=5000)
    except Exception:
        raise RuntimeError(
            f"_enter_edit_modal: row '{name}' list 에 미발견. "
            f"_ensure_sc3g_policy 실패 또는 cleanup race 가능성."
        )
    page.open_modify_modal(name)
    page.page.wait_for_timeout(800)  # EDIT 모달 진입 안정화


def _save_click(page):
    """EDIT 모달 저장 버튼 click (overlay 우회)."""
    page.page.evaluate(
        """() => {
            const m = document.querySelector('#addItemModal.in');
            const btn = Array.from(m.querySelectorAll('button'))
                .filter(b => b.offsetParent && b.classList.contains('btn-primary'))[0];
            if (btn) btn.click();
        }"""
    )
    page.page.wait_for_timeout(1500)


SC3G_NAME = "[AUTO]_sc3g_normal_save"


def _safe_close_modal(page):
    """모달 안전 close — 이미 닫혔으면 skip (silent revert 자동 닫힘 케이스 cover)."""
    try:
        if page.page.locator("#addItemModal.in").count() > 0:
            page.close_modal()
    except Exception:
        pass


def _csu_select_first(page):
    """CSU picker 첫 행 선택 — raw JS row click (Chrome MCP 검증 2026-05-29).

    row.click() (raw JS) 가 ng-click directive 발화 → radio.checked + ng-model 동기화 자동.
    """
    page.page.locator(page.SEL_CSU_SELECT_BTN).first.evaluate("el => el.click()")
    page.page.locator("#selectCommonPolicyItemModal.in").wait_for(
        state="attached", timeout=5000
    )
    page.page.locator("#selectCommonPolicyItemModal table tbody tr").first.evaluate(
        "el => el.click()"
    )
    page.page.wait_for_timeout(500)
    page.page.locator("#selectCommonPolicyItemModal .btn-primary").first.evaluate(
        "el => el.click()"
    )
    page.page.wait_for_timeout(1500)


def _pick_process_in_picker(page, prefer_keyword: str = "AUTO") -> str:
    """globalProcessList picker 에서 프로세스 1건 선택 + 확인.

    사용자 정책 (2026-05-29):
      - 기본: 맨 위 프로세스 (첫 행 fallback)
      - sc6 있으면 'AUTO' 검색해서 사용 (검색 결과 있으면 첫 행)
    multi-select picker — 첫 행 체크박스 click + 확인 버튼.
    Returns: 선택된 프로세스 이름 (또는 '').
    """
    picker = page.page.locator("#globalProcessList.in")
    picker.wait_for(state="attached", timeout=5000)
    # AUTO 검색 시도
    try:
        si = page.page.locator("#globalProcessList.in input[type='search'], #globalProcessList.in input[placeholder]").first
        si.fill(prefer_keyword)
        page.page.locator("#globalProcessList.in button i.fa-search, #globalProcessList.in button.searchBtn").first.evaluate(
            "el => (el.closest('button') || el).click()"
        )
        page.page.wait_for_timeout(800)
    except Exception:
        pass
    # 검색 결과 0건 시 검색 비우고 fallback
    rows = page.page.locator("#globalProcessList.in table tbody tr:has(input[type='checkbox'])")
    if rows.count() == 0:
        try:
            si.fill("")
            page.page.locator("#globalProcessList.in button i.fa-search, #globalProcessList.in button.searchBtn").first.evaluate(
                "el => (el.closest('button') || el).click()"
            )
            page.page.wait_for_timeout(800)
        except Exception:
            pass
        rows = page.page.locator("#globalProcessList.in table tbody tr:has(input[type='checkbox'])")
    # 첫 행 체크박스 click + 이름 추출
    process_name = ""
    if rows.count() > 0:
        first = rows.first
        process_name = first.evaluate(
            "el => { const a = el.querySelector('a, span'); return a ? a.textContent.trim() : ''; }"
        )
        cb = first.locator("input[type='checkbox']").first
        cb.evaluate("el => { if (!el.checked) el.click(); }")
        page.page.wait_for_timeout(300)
    # 확인 버튼 click
    page.page.locator("#globalProcessList.in button.btn-primary, #globalProcessList.in button:has-text('확인')").first.evaluate(
        "el => el.click()"
    )
    page.page.wait_for_timeout(1500)
    return process_name


def _add_process_to_tab(page, tab_name: str, proc_type: str, description: str = "") -> dict:
    """탭 (허용/예외처리/실행차단) 의 + 버튼 → sub-modal → picker → 저장.

    Returns: {process_name, sub_msg, registered}
    """
    # 탭 진입
    page.page.evaluate(
        """(name) => {
            const tabs = Array.from(document.querySelectorAll('#addItemModal.in ul li'));
            const t = tabs.find(li => li.textContent.trim() === name);
            if (t) (t.querySelector('a') || t).click();
        }""",
        tab_name,
    )
    page.page.wait_for_timeout(600)
    # + 버튼
    page.page.evaluate(
        """(pt) => {
            const btn = document.querySelector(`#addItemModal.in button[data-process-type="${pt}"]`);
            if (btn) btn.click();
        }""",
        proc_type,
    )
    page.page.wait_for_timeout(1500)
    # "프로세스 선택" 버튼
    page.page.evaluate(
        """() => {
            const subs = Array.from(document.querySelectorAll('.modal-wrap.in'));
            const sub = subs.find(m => /추가\\/수정/.test((m.querySelector('.modal-title')||{}).textContent||''));
            if (sub) {
                const btn = Array.from(sub.querySelectorAll('button')).find(b => /프로세스 선택/.test(b.textContent));
                if (btn) btn.click();
            }
        }"""
    )
    page.page.wait_for_timeout(1500)
    # picker — AUTO 검색 / 첫 행 fallback
    proc_name = _pick_process_in_picker(page, "AUTO")
    # 설명 입력
    if description:
        page.page.evaluate(
            """(desc) => {
                const subs = Array.from(document.querySelectorAll('.modal-wrap.in'));
                const sub = subs.find(m => /추가\\/수정/.test((m.querySelector('.modal-title')||{}).textContent||''));
                if (sub) {
                    const ta = sub.querySelector('textarea');
                    if (ta) {
                        const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                        setter.call(ta, desc);
                        ta.dispatchEvent(new Event('input', {bubbles:true}));
                    }
                }
            }""",
            description,
        )
        page.page.wait_for_timeout(300)
    # 등록
    page.page.evaluate(
        """() => {
            const subs = Array.from(document.querySelectorAll('.modal-wrap.in'));
            const sub = subs.find(m => /추가\\/수정/.test((m.querySelector('.modal-title')||{}).textContent||''));
            if (sub) {
                const btn = Array.from(sub.querySelectorAll('button')).find(b => /등록|저장/.test(b.textContent));
                if (btn) btn.click();
            }
        }"""
    )
    page.page.wait_for_timeout(1500)
    # 결과 확인
    sub_msg = ""
    if page.is_confirm_modal_visible(timeout=1000):
        sub_msg = page.get_confirm_message()
        page.dismiss_confirm_modal()
    sub_still_open = page.page.evaluate(
        """() => {
            const subs = Array.from(document.querySelectorAll('.modal-wrap.in'));
            return subs.some(m => /추가\\/수정/.test((m.querySelector('.modal-title')||{}).textContent||''));
        }"""
    )
    return {
        "process_name": proc_name,
        "sub_msg": sub_msg,
        "registered": not sub_still_open,
    }


def _ensure_sc3g_policy(page):
    """sc3g 정책 없으면 즉시 생성 (사용자 정정 2026-05-29: 없으면 만들어서 테스트).

    sc3 가 다 돌렸는데도 일부 누락 가능 (sc3g 자체 fail 등) — 그럴 때 sc4 가 skip 하면
    부정확. sc3g 패턴으로 fallback 생성 → sc4 가 그것 사용.
    """
    if page.is_policy_exists(SC3G_NAME):
        return  # 이미 존재 — fallback 불필요
    page.open_add_modal()
    page.page.locator(page.SEL_POLICY_NAME).fill(SC3G_NAME)
    page.page.locator(page.SEL_DRIVE_LETTER).fill("Y")
    page.page.locator(page.SEL_DRIVE_LABEL).fill("Sc3gLabel")
    page.page.locator(page.SEL_DRIVE_QUOTA).fill("200")
    _csu_select_first(page)
    page.page.locator(page.SEL_SUBMIT_BTN).first.evaluate("el => el.click()")
    page.page.wait_for_timeout(2000)
    if page.is_confirm_modal_visible(timeout=2000):
        msg = page.get_confirm_message()
        page.dismiss_confirm_modal()
        if "오류" in msg or "선택" in msg or "필수" in msg:
            raise RuntimeError(
                f"_ensure_sc3g_policy 저장 실패 — server msg: {msg!r}"
            )
    page.navigate_to()
    page.page.wait_for_timeout(800)


class TestOriginProtectScenario4Modify(OriginProtectBase):
    """원본보호 정책 — sc4: EDIT 모달 수정 동작 검증."""

    # ==================================================================
    # sc4a — EDIT 진입 + 저장값 정확 load 검증 (Chrome MCP 2026-05-29 확인)
    # ==================================================================
    def test_scenario4a_edit_enter_and_load(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4a: EDIT 진입 + 저장값 load ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        # sc3g 정책 없으면 즉시 생성 (sc4 단독 실행 지원)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        # 저장값 정확 load 검증 (Chrome MCP 기준값)
        loaded = page.page.evaluate(
            """() => ({
                name: document.getElementById('originProtectPolicyName').value,
                letter: document.getElementById('driveLetter').value,
                label: document.getElementById('driveLabel').value,
                quota: document.getElementById('originProtectDriveQuota').value,
                csu: document.getElementById('controlSuiteId').textContent.trim(),
                wm_screen: document.getElementById('isScreenWaterMark').checked,
                wm_print: document.getElementById('isPrintWaterMark').checked,
                file_watch: document.getElementById('isWatchFileExtension').checked,
                shutdown: document.getElementById('isAllowProcessShutdownText').checked,
            })"""
        )
        # csu 는 sc3g 가 picker 첫 행 선택했으므로 실제 저장된 값 = 환경 의존 (cleanup 후
        # [AUTO_KEEP] 사라지면 일반 정책 "전사 시큐어존 테스트" 등 첫 행). 빈값 아닌지만 검증.
        expected = {
            "name": SC3G_NAME, "letter": "Y", "label": "Sc3gLabel",
            "quota": "200",
            "wm_screen": True, "wm_print": True,
            "file_watch": True, "shutdown": True,
        }
        for k, v in expected.items():
            ok = loaded.get(k) == v
            self._add("pass" if ok else "fail",
                      f"sc4a — [{k}] 저장값 load 정확",
                      f"기대: {v!r} / 실제: {loaded.get(k)!r}", sc=4)
        # csu 별도 — 빈값 아니고 "없음" 아니면 pass (실제 정책 이름 무관)
        csu_val = loaded.get("csu", "")
        csu_ok = csu_val and csu_val != "없음"
        self._add("pass" if csu_ok else "fail",
                  "sc4a — [csu] 저장값 load 정확 (정책 이름 무관, 빈값 아닌지만 검증)",
                  f"실제: {csu_val!r} (cleanup 후 [AUTO_KEEP] 사라지면 첫 행 사용)", sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4b — 이름 빈값 차단 (sc3a 와 동일 동작 확인)
    # ==================================================================
    def test_scenario4b_name_empty_blocked(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4b: 이름 빈값 차단 (ADD 동일) ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        page.page.locator(page.SEL_POLICY_NAME).fill("")
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        # 결과 분석 (사용자 보고 2026-05-29):
        #   - ADD sc3a: '정책 이름을 입력해 주세요.' 차단 메시지
        #   - EDIT: '저장 하였습니다' + 모달 자동 닫힘 (silent revert 추정 — sc4d 패턴)
        # 재 진입해서 실제 값 확인
        if "저장" in msg and "오류" not in msg:
            # silent revert 패턴 의심 — 다시 진입해서 이름 보존 여부 확인
            page.navigate_to()
            page.page.wait_for_timeout(500)
            reverted = page.is_policy_exists(SC3G_NAME)
            self._add("warn" if reverted else "fail",
                      "sc4b — [정책 이름] EDIT 이름 빈값 silent revert + 거짓 성공 메시지 🟡 (known_bug)",
                      f"입력: '' / 결과 msg: {msg!r}, "
                      f"silent revert (이름 보존): {reverted} "
                      f"(ADD sc3a 차단 메시지 vs EDIT 거짓 성공 — data 안전, UX 결함) "
                      f"yaml known_bug:edit_required_validation_silent_skip_with_false_success",
                      sc=4, highlight=page.page.locator(page.SEL_POLICY_NAME))
        else:
            # 차단 메시지 떴으면 정상 동작 (ADD sc3a 와 동일)
            expected = "정책 이름을 입력해 주세요."
            self._add("pass" if msg == expected else "fail",
                      "sc4b — EDIT 이름 빈값 차단 메시지 (sc3a 동일)",
                      f"기대: {expected!r} / 실제: {msg!r}",
                      sc=4, highlight=page.page.locator(page.SEL_POLICY_NAME))
            # 모달 정리 — 닫혀있을 수도
            try:
                if page.page.locator("#addItemModal.in").count() > 0:
                    _safe_close_modal(page)
            except Exception:
                pass

    # ==================================================================
    # sc4c — 이름 중복 검증 부재 결함 재현 🔴 HIGH
    # Chrome MCP 재현 2026-05-29: 다른 정책 이름으로 변경 → 차단 없이 저장 성공
    # ==================================================================
    def test_scenario4c_name_duplicate_not_blocked_defect(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4c: 이름 중복 검증 부재 결함 재현 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)
        # 다른 [AUTO] 정책 — sc3b/sc3k 가 있으면 사용, 없으면 fallback 으로 1건 생성
        other_name = "[AUTO]_sc3b_dup" if page.is_policy_exists("[AUTO]_sc3b_dup") else \
                     "[AUTO]_sc3k_wm_sync" if page.is_policy_exists("[AUTO]_sc3k_wm_sync") else \
                     "[AUTO]_sc4c_other_for_dup"
        if not page.is_policy_exists(other_name):
            # fallback — 다른 정책 1건 생성 (driveLetter 다르게)
            page.open_add_modal()
            page.page.locator(page.SEL_POLICY_NAME).fill(other_name)
            page.page.locator(page.SEL_DRIVE_LETTER).fill("Z")
            page.page.locator(page.SEL_DRIVE_LABEL).fill("OtherLabel")
            page.page.locator(page.SEL_DRIVE_QUOTA).fill("100")
            _csu_select_first(page)
            page.page.locator(page.SEL_SUBMIT_BTN).first.evaluate("el => el.click()")
            page.page.wait_for_timeout(1500)
            if page.is_confirm_modal_visible():
                page.dismiss_confirm_modal()
            page.navigate_to()

        _enter_edit_modal(page, SC3G_NAME)
        page.page.locator(page.SEL_POLICY_NAME).fill(other_name)
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        is_success = "저장" in msg
        defect_reproduced = is_success and "이미 등록" not in msg
        self._add("warn" if defect_reproduced else "pass",
                  "sc4c — [정책 이름] EDIT 이름 중복 검증 부재 결함 🔴 (known_bug)",
                  f"입력: {SC3G_NAME} → {other_name} / 결과 msg: {msg!r} / "
                  f"결함 재현 (success 메시지): {defect_reproduced} "
                  f"(yaml known_bug:edit_name_duplicate_not_blocked)",
                  sc=4, highlight=page.page.locator(page.SEL_POLICY_NAME))

        # 원상복구 — sc3g 가 other_name 으로 rename 됐으면 다시 SC3G_NAME 로 복구.
        # rename 된 row 식별: data-name 또는 latest mtime row 직접 click + EDIT.
        # (사용자 보고 2026-05-29: 이전 _enter_edit_modal(other_name) 가 first match 사용 →
        #  잘못된 row 클릭 → cascade fail. row click 자체를 JS 로 latest mtime 행 정확 selection)
        if not defect_reproduced:
            return  # 결함 재현 안 됐으면 rename 안 일어남 — 원상복구 불필요

        page.navigate_to()
        page.page.wait_for_timeout(800)
        try:
            # JS 로 latest mtime row 직접 click + tActive 적용
            clicked = page.page.evaluate(
                """(other) => {
                    const rows = Array.from(document.querySelectorAll('table tbody tr'));
                    const dups = rows.filter(r => {
                        const td0 = r.querySelector('td');
                        return td0 && td0.textContent.trim() === other;
                    });
                    if (dups.length === 0) return 'no_dup';
                    // latest mtime row (rename 된 것)
                    let latest = dups[0], latest_t = '';
                    for (const r of dups) {
                        const cells = r.querySelectorAll('td');
                        // 수정일 컬럼 — 보통 마지막에서 2~3번째
                        const mtime = cells[cells.length - 2] ? cells[cells.length - 2].textContent.trim() : '';
                        if (mtime > latest_t) { latest_t = mtime; latest = r; }
                    }
                    const td = latest.querySelector('td');
                    ['mousedown','mouseup','click'].forEach(ev =>
                        td.dispatchEvent(new MouseEvent(ev, {bubbles:true,cancelable:true,view:window,button:0})));
                    return 'clicked:' + latest_t;
                }""",
                other_name,
            )
            page.page.wait_for_timeout(500)
            # modifyItemBtn click → EDIT 모달
            page.page.locator(page.SEL_MODIFY_BTN).first.evaluate("el => el.click()")
            page.page.wait_for_timeout(1500)
            # 이름 복구
            page.page.locator(page.SEL_POLICY_NAME).fill(SC3G_NAME)
            _save_click(page)
            if page.is_confirm_modal_visible(timeout=2000):
                page.dismiss_confirm_modal()
        except Exception as e:
            # 원상복구 fail 해도 sc4c 검증 자체는 OK — 명시 print 만
            print(f"[sc4c 원상복구 fail — 무시] {e!r}")

    # ==================================================================
    # sc4d — driveLetter/driveLabel 빈값 silent revert + 거짓 성공 메시지 🟡
    # Chrome MCP 재현 2026-05-29: 빈값 저장 → '저장 하였습니다' + 모달 닫힘 → 실제 변경 안 됨
    # ==================================================================
    def test_scenario4d_required_field_silent_revert(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4d: 필수 빈값 silent revert + 거짓 메시지 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        for field_label, sel, original in [
            ("드라이브 문자", page.SEL_DRIVE_LETTER, "Y"),
            ("드라이브 라벨", page.SEL_DRIVE_LABEL,  "Sc3gLabel"),
        ]:
            _enter_edit_modal(page, SC3G_NAME)
            page.page.locator(sel).fill("")
            _save_click(page)
            msg = ""
            if page.is_confirm_modal_visible(timeout=2000):
                msg = page.get_confirm_message()
                page.dismiss_confirm_modal()
            is_success = "저장" in msg and "오류" not in msg
            # 재 진입해서 실제 값 확인
            _enter_edit_modal(page, SC3G_NAME)
            actual = page.page.locator(sel).input_value()
            silent_revert = (is_success and actual == original)
            self._add("warn" if silent_revert else ("pass" if not is_success else "fail"),
                      f"sc4d — [{field_label}] 빈값 silent revert + 거짓 메시지 🟡 (known_bug)",
                      f"입력: '' / 결과: msg={msg!r}, 재진입값={actual!r} (기대 차단 메시지 또는 silent revert={original!r})",
                      sc=4, highlight=page.page.locator(sel))
            # 모달 안전 close — 이미 닫혔을 수도 (silent revert success → 자동 닫힘)
            try:
                if page.page.locator("#addItemModal.in").count() > 0:
                    _safe_close_modal(page)
            except Exception:
                pass

    # ==================================================================
    # sc4e — Quota 빈값 → 0 silent 변환 결함 재현 🔴 HIGH
    # Chrome MCP 재현 2026-05-29: 200 → 0 으로 실제 변경됨 (data 영향)
    # ==================================================================
    def test_scenario4e_quota_empty_silent_zero(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4e: Quota 빈값 → 0 silent 변환 🔴 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        page.page.locator(page.SEL_DRIVE_QUOTA).fill("")
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        # 재 진입해서 실제 Quota 값 확인
        _enter_edit_modal(page, SC3G_NAME)
        actual = page.page.locator(page.SEL_DRIVE_QUOTA).input_value()
        defect_reproduced = ("저장" in msg and actual == "0")
        self._add("warn" if defect_reproduced else ("pass" if not "저장" in msg else "fail"),
                  "sc4e — [드라이브 용량] Quota 빈값 → 0 silent 변환 결함 🔴 (known_bug)",
                  f"입력: '' / 결과 msg: {msg!r}, 재진입 Quota: {actual!r} "
                  f"(결함 재현 시 '0' / sc3a β3 차단 메시지 부재) "
                  f"yaml known_bug:edit_quota_empty_silent_zero_conversion",
                  sc=4, highlight=page.page.locator(page.SEL_DRIVE_QUOTA))
        # Quota=200 복구
        page.page.locator(page.SEL_DRIVE_QUOTA).fill("200")
        _save_click(page)
        if page.is_confirm_modal_visible(timeout=2000):
            page.dismiss_confirm_modal()

    # ==================================================================
    # sc4f — EDIT 입력 마스킹 sanity (sc3c/h/i 와 동일 동작)
    # Chrome MCP 검증 2026-05-29: 입력 마스킹은 ADD 와 100% 동일 (같은 JS 핸들러)
    # ==================================================================
    def test_scenario4f_input_masking_sanity(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4f: 입력 마스킹 sanity ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        cases = [
            (page.SEL_DRIVE_LETTER, "abc",  "A",   "driveLetter 'abc' → 'A' (첫 글자 + 대문자)"),
            (page.SEL_DRIVE_LETTER, "5",    "",    "driveLetter '5' → '' (숫자 reset)"),
            (page.SEL_DRIVE_QUOTA,  "1.5",  "15",  "Quota '1.5' → '15' (소수점 제거)"),
            (page.SEL_DRIVE_QUOTA,  "-5",   "5",   "Quota '-5' → '5' (음수 부호 제거)"),
            (page.SEL_SCREEN_WM_OPACITY, "150", "100", "Opacity 150 → 100 (cap)"),
            (page.SEL_SCREEN_WM_DEGREE,  "720", "360", "Degree 720 → 360 (cap)"),
        ]
        for sel, inp, expected, desc in cases:
            loc = page.page.locator(sel)
            loc.fill("")
            page.page.wait_for_timeout(80)
            loc.evaluate(
                "(el, v) => { el.value=v; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); }",
                inp,
            )
            page.page.wait_for_timeout(250)
            actual = loc.input_value()
            self._add("pass" if actual == expected else "fail",
                      f"sc4f — EDIT 입력 마스킹 — {desc}",
                      f"입력: {inp!r} / 결과: {actual!r} (기대 {expected!r})",
                      sc=4, highlight=loc)

        # 원상복구
        page.page.locator(page.SEL_DRIVE_LETTER).fill("Y")
        page.page.locator(page.SEL_DRIVE_QUOTA).fill("200")
        page.page.locator(page.SEL_SCREEN_WM_OPACITY).fill("0")
        page.page.locator(page.SEL_SCREEN_WM_DEGREE).fill("0")
        _safe_close_modal(page)

    # ==================================================================
    # sc4g — 워터마크 토큰 자동 삽입 sanity (sc3f/m 와 동일)
    # Chrome MCP 검증 2026-05-29: 화면+출력 워터마크 토큰 EDIT = ADD 동일
    # ==================================================================
    def test_scenario4g_watermark_token_sanity(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4g: 워터마크 토큰 sanity ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        for area, wm_text_sel, pc_sel, time_sel in [
            ("화면 워터마크", page.SEL_SCREEN_WM_TEXT, page.SEL_SCREEN_WM_PC_INFO, page.SEL_SCREEN_WM_TIME),
            ("출력 워터마크", page.SEL_PRINT_WM_TEXT,  page.SEL_PRINT_WM_PC_INFO,  page.SEL_PRINT_WM_TIME),
        ]:
            page.page.locator(wm_text_sel).fill("")
            page.page.locator(pc_sel).first.evaluate("el => el.click()")
            page.page.wait_for_timeout(300)
            v1 = page.page.locator(wm_text_sel).input_value()
            self._add("pass" if v1 == "[/PCINFO/]" else "fail",
                      f"sc4g — [{area}] PC 체크 → '[/PCINFO/]' (EDIT = ADD)",
                      f"결과: {v1!r}", sc=4, highlight=page.page.locator(wm_text_sel))
            page.page.locator(time_sel).first.evaluate("el => el.click()")
            page.page.wait_for_timeout(300)
            v2 = page.page.locator(wm_text_sel).input_value()
            self._add("pass" if v2 == "[/PCINFO/][/TIME/]" else "fail",
                      f"sc4g — [{area}] TIME 추가 → '[/PCINFO/][/TIME/]'",
                      f"결과: {v2!r}", sc=4, highlight=page.page.locator(wm_text_sel))
            # 원상복구 — 두 체크박스 해제
            page.page.locator(pc_sel).first.evaluate("el => el.click()")
            page.page.locator(time_sel).first.evaluate("el => el.click()")
            page.page.locator(wm_text_sel).fill("")
        _safe_close_modal(page)

    # ==================================================================
    # sc4h — 텍스트 길이 server reject + 4-3 패턴 정상 검증
    # Chrome MCP 검증 2026-05-29: server reject 시 모달 안 닫힘 (정상)
    # ==================================================================
    def test_scenario4h_text_length_server_reject(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4h: 텍스트 길이 server reject + 4-3 패턴 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        page.page.locator(page.SEL_SHUTDOWN_MSG_TEXT).fill("X" * 3000)
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=3000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        modal_still_open = page.page.locator("#addItemModal.in").count() > 0
        SERVER_ERR = "서버에서 오류가 발생 하였습니다."
        # 결과: msg=server error + 모달 안 닫힘 (4-3 패턴 정상) = warn (known_bug + 정상 부분)
        self._add("warn" if msg == SERVER_ERR else "fail",
                  "sc4h — [허용 프로세스 종료 알림] 3000자 → server reject 메시지 + 4-3 패턴 정상",
                  f"결과: msg={msg!r}, modal_still_open={modal_still_open} "
                  f"(yaml known_bug:text_length_no_client_guard / 4-3 정상)",
                  sc=4, highlight=page.page.locator(page.SEL_SHUTDOWN_MSG_TEXT))
        # 정리
        page.page.locator(page.SEL_SHUTDOWN_MSG_TEXT).fill("")
        _safe_close_modal(page)

    # ==================================================================
    # sc4i — EDIT 모달 title 결함 (⚠ UX known_bug)
    # ==================================================================
    def test_scenario4i_edit_modal_title_defect(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4i: EDIT 모달 title 결함 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        title = page.page.evaluate(
            "() => { const m=document.querySelector('#addItemModal.in'); "
            "const t=m.querySelector('.modal-title,h4,h3'); return t?t.textContent.trim():null; }"
        )
        is_defect = (title == "정책 추가")  # EDIT 인데 title 이 'ADD' 그대로 = 결함
        self._add("warn" if is_defect else "pass",
                  "sc4i — [EDIT 모달] title='정책 추가' 그대로 결함 ⚠ (known_bug)",
                  f"EDIT 진입 후 title={title!r} (기대 '정책 수정') "
                  f"yaml known_bug:edit_modal_title_not_updated",
                  sc=4, highlight=page.page.locator("#addItemModal .modal-title"))
        _safe_close_modal(page)

    # ==================================================================
    # sc4j — 확장자/예외폴더 list EDIT 동작 (sc3d/e 대응)
    # 중복/형식 차단 메시지 EDIT 에서도 동일 + 예외폴더 typo 결함 EDIT 재현
    # ==================================================================
    def test_scenario4j_list_input_edit(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4j: list 입력 EDIT 동작 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        ext_input = page.page.locator(page.SEL_WATCH_EXT_INPUT)
        ext_btn = page.page.locator(page.SEL_WATCH_EXT_BTN)

        def _add_ext(val):
            ext_input.fill(val)
            page.page.wait_for_timeout(150)
            ext_btn.first.evaluate("el => el.click()")
            page.page.wait_for_timeout(500)

        _add_ext("doc")
        if page.is_confirm_modal_visible(timeout=500):
            page.dismiss_confirm_modal()
        _add_ext("doc")
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            ok = msg == "이미 동일한 확장자가 존재합니다."
            self._add("pass" if ok else "fail",
                      "sc4j — [확장자] EDIT 중복 차단 메시지 (sc3d 동일)",
                      f"입력: 동일 'doc' / msg={msg!r}", sc=4, highlight=ext_input)
            page.dismiss_confirm_modal()

        _add_ext("@#$")
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            ok = ". * ; ?" in msg
            self._add("pass" if ok else "fail",
                      "sc4j — [확장자] EDIT 형식 차단 메시지 (sc3d 동일)",
                      f"입력: '@#$' / msg={msg!r}", sc=4, highlight=ext_input)
            page.dismiss_confirm_modal()

        fld_input = page.page.locator(page.SEL_WATCH_EXCEPT_INPUT)
        fld_input.fill("")
        page.page.locator(page.SEL_WATCH_EXCEPT_BTN).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(500)
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            is_typo = msg == "확장자를 입력하세요"
            self._add("warn" if is_typo else "fail",
                      "sc4j — [예외 폴더] EDIT 빈값 → '확장자' typo 결함 재현 (sc3e 동일 known_bug)",
                      f"입력: '' / msg={msg!r}", sc=4, highlight=fld_input)
            page.dismiss_confirm_modal()
        _safe_close_modal(page)

    # ==================================================================
    # sc4k — 워터마크 단방향 sync state2/3 결함 EDIT 재현 (sc3f/m 대응)
    # ==================================================================
    def test_scenario4k_watermark_single_sync_edit(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4k: 워터마크 단방향 sync EDIT (화면+출력) ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        for area, wm_text_sel, pc_sel, time_sel in [
            ("화면 워터마크", page.SEL_SCREEN_WM_TEXT, page.SEL_SCREEN_WM_PC_INFO, page.SEL_SCREEN_WM_TIME),
            ("출력 워터마크", page.SEL_PRINT_WM_TEXT,  page.SEL_PRINT_WM_PC_INFO,  page.SEL_PRINT_WM_TIME),
        ]:
            page.page.locator(wm_text_sel).fill("")
            for sel in [pc_sel, time_sel]:
                el = page.page.locator(sel).first
                if not el.is_checked():
                    el.evaluate("el => el.click()")
                    page.page.wait_for_timeout(200)
            page.page.locator(wm_text_sel).fill("[/TIME/]")
            page.page.wait_for_timeout(400)
            pc = page.page.locator(pc_sel).is_checked()
            tm = page.page.locator(time_sel).is_checked()
            defect = (pc is True and tm is True)
            self._add("warn" if defect else "pass",
                      f"sc4k — [{area}] state2 결함 EDIT — '[/PCINFO/]' 만 삭제 → PC/TIME 둘 다 ON 유지",
                      f"text='[/TIME/]' / pc={pc}, time={tm}",
                      sc=4, highlight=page.page.locator(pc_sel))
            page.page.locator(wm_text_sel).fill("")
            page.page.wait_for_timeout(400)
            pc2 = page.page.locator(pc_sel).is_checked()
            tm2 = page.page.locator(time_sel).is_checked()
            defect2 = (pc2 is True and tm2 is True)
            self._add("warn" if defect2 else "pass",
                      f"sc4k — [{area}] state3 결함 EDIT — text 전체 비움 → PC/TIME 둘 다 ON 유지",
                      f"text='' / pc={pc2}, time={tm2}",
                      sc=4, highlight=page.page.locator(time_sel))
            for sel in [pc_sel, time_sel]:
                el = page.page.locator(sel).first
                if el.is_checked():
                    el.evaluate("el => el.click()")
            page.page.locator(wm_text_sel).fill("")
        _safe_close_modal(page)

    # ==================================================================
    # sc4l — 투명도/각도 cap EDIT (sc3i 대응, 화면+출력 분리)
    # ==================================================================
    def test_scenario4l_opacity_degree_cap_edit(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4l: 투명도/각도 cap EDIT ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)

        def _try(loc, v):
            loc.fill("")
            page.page.wait_for_timeout(80)
            loc.evaluate(
                "(el, v) => { el.value=v; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); }",
                v,
            )
            page.page.wait_for_timeout(250)
            return loc.input_value()

        for area, op_sel, dg_sel in [
            ("화면 워터마크", page.SEL_SCREEN_WM_OPACITY, page.SEL_SCREEN_WM_DEGREE),
            ("출력 워터마크", page.SEL_PRINT_WM_OPACITY,  page.SEL_PRINT_WM_DEGREE),
        ]:
            op = page.page.locator(op_sel)
            dg = page.page.locator(dg_sel)
            for inp, expected, note in [("150", "100", "100 cap"), ("-50", "50", "음수 부호 제거")]:
                actual = _try(op, inp)
                self._add("pass" if actual == expected else "fail",
                          f"sc4l — [{area}] 투명도 '{inp}' → '{expected}' ({note})",
                          f"입력: {inp!r} / 결과: {actual!r}", sc=4, highlight=op)
            for inp, expected, note in [("720", "360", "360 cap"), ("-90", "90", "음수 부호 제거")]:
                actual = _try(dg, inp)
                self._add("pass" if actual == expected else "fail",
                          f"sc4l — [{area}] 각도 '{inp}' → '{expected}' ({note})",
                          f"입력: {inp!r} / 결과: {actual!r}", sc=4, highlight=dg)

        page.page.locator(page.SEL_SCREEN_WM_OPACITY).fill("0")
        page.page.locator(page.SEL_SCREEN_WM_DEGREE).fill("0")
        page.page.locator(page.SEL_PRINT_WM_OPACITY).fill("0")
        page.page.locator(page.SEL_PRINT_WM_DEGREE).fill("0")
        _safe_close_modal(page)

    # ==================================================================
    # sc4m — free text 한글/특수 EDIT (sc3j 대응)
    # ==================================================================
    def test_scenario4m_free_text_edit(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4m: free text 한글/특수 EDIT ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        lb = page.page.locator(page.SEL_DRIVE_LABEL)
        for inp, label in [("한글라벨", "한글"), ("$@%", "특수문자"), ("a"*200, "200자")]:
            lb.fill(inp)
            page.page.wait_for_timeout(150)
            ok = lb.input_value() == inp
            self._add("pass" if ok else "fail",
                      f"sc4m — [드라이브 레이블] EDIT '{label}' 입력 보존 (free text)",
                      f"입력: '{inp[:20]}'({len(inp)}자) / 보존={ok}", sc=4, highlight=lb)
        lb.fill("Sc3gLabel")

        sh = page.page.locator(page.SEL_SHUTDOWN_MSG_TEXT)
        sh.fill("한글종료알림")
        page.page.wait_for_timeout(150)
        ok_sh = sh.input_value() == "한글종료알림"
        self._add("pass" if ok_sh else "fail",
                  "sc4m — [허용 프로세스 종료 알림] EDIT 한글 입력 (free text)",
                  f"결과: 보존={ok_sh}", sc=4, highlight=sh)
        sh.fill("")
        _safe_close_modal(page)

    # ==================================================================
    # sc4n — 토글 종속 disabled EDIT (sc3o 대응)
    # ==================================================================
    def test_scenario4n_toggle_dependency_disabled_edit(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4n: 토글 종속 disabled EDIT ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        toggle_specs = [
            ("파일 감시 기능", "isWatchFileExtension",
             ["watchFileExtensions", "watchExceptFolders", "isWatchFileHeader",
              "watchFileExtensionAddBtn", "watchExceptFolderAddBtn"]),
            ("종료 알림 출력", "isAllowProcessShutdownText", ["allowProcessShutdownText"]),
            ("화면 워터마크", "isScreenWaterMark",
             ["screenWaterMarkText", "isScreenWaterMarkPcInfo", "isScreenWaterMarkCurrentTime",
              "screenWaterMarkOpacity", "screenWaterMarkDegree"]),
            ("출력 워터마크", "isPrintWaterMark",
             ["printWaterMarkText", "isPrintWaterMarkPcInfo", "isPrintWaterMarkCurrentTime",
              "printWaterMarkOpacity", "printWaterMarkDegree"]),
        ]
        for area, toggle_id, dep_ids in toggle_specs:
            toggle_loc = page.page.locator(f"input#{toggle_id}")
            toggle_loc.first.evaluate("el => el.click()")
            page.page.wait_for_timeout(400)
            disabled_states = page.page.evaluate(
                "(ids) => ids.map(id => { const el=document.getElementById(id); "
                "return {id, disabled: el? el.disabled : null}; })",
                dep_ids,
            )
            not_disabled = [s["id"] for s in disabled_states if s["disabled"] is not True]
            all_disabled = not not_disabled
            self._add("pass" if all_disabled else "fail",
                      f"sc4n — [{area}] EDIT 토글 OFF → 종속 {len(dep_ids)}건 disabled (sc3o 동일)",
                      f"결과: {'전부 disabled' if all_disabled else 'disabled 안 됨=' + str(not_disabled)}",
                      sc=4, highlight=page.page.locator(f"input#{dep_ids[0]}"))
            toggle_loc.first.evaluate("el => el.click()")
            page.page.wait_for_timeout(300)
        _safe_close_modal(page)

    # ==================================================================
    # sc4o — 텍스트 길이 server reject EDIT 4 필드 (sc3n 대응, sc4h 외 보강)
    # ==================================================================
    def test_scenario4o_text_length_edit_4fields(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4o: 텍스트 길이 server reject EDIT 4 필드 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        SERVER_ERR = "서버에서 오류가 발생 하였습니다."
        long_text = "X" * 3000
        for area, sel in [
            ("정책 이름",       page.SEL_POLICY_NAME),
            ("드라이브 레이블", page.SEL_DRIVE_LABEL),
            ("화면 워터마크 텍스트", page.SEL_SCREEN_WM_TEXT),
            ("출력 워터마크 텍스트", page.SEL_PRINT_WM_TEXT),
        ]:
            _enter_edit_modal(page, SC3G_NAME)
            page.page.locator(sel).fill(long_text)
            _save_click(page)
            msg = ""
            if page.is_confirm_modal_visible(timeout=3000):
                msg = page.get_confirm_message()
                page.dismiss_confirm_modal()
            is_generic = (msg == SERVER_ERR)
            self._add("warn" if is_generic else ("pass" if "최대" in msg else "fail"),
                      f"sc4o — [{area}] EDIT 3000자 → server reject (sc3n 동일 known_bug)",
                      f"결과: msg={msg!r}", sc=4, highlight=page.page.locator(sel))
            _safe_close_modal(page)

    # ==================================================================
    # sc4p — driveLetter 공존 EDIT 도메인 의도 (sc3l 대응)
    # 다른 정책 letter 를 sc3g 와 같은 letter 로 변경 → 공존 허용 검증
    # ==================================================================
    def test_scenario4p_drive_letter_coexist_edit(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4p: driveLetter 공존 EDIT ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        other_name = "[AUTO]_sc4p_other"
        if not page.is_policy_exists(other_name):
            page.open_add_modal()
            page.page.locator(page.SEL_POLICY_NAME).fill(other_name)
            page.page.locator(page.SEL_DRIVE_LETTER).fill("Z")
            page.page.locator(page.SEL_DRIVE_LABEL).fill("OtherLabel")
            page.page.locator(page.SEL_DRIVE_QUOTA).fill("100")
            _csu_select_first(page)
            page.page.locator(page.SEL_SUBMIT_BTN).first.evaluate("el => el.click()")
            page.page.wait_for_timeout(1500)
            if page.is_confirm_modal_visible():
                page.dismiss_confirm_modal()
            page.navigate_to()

        _enter_edit_modal(page, other_name)
        page.page.locator(page.SEL_DRIVE_LETTER).fill("Y")
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        letter_blocked = any(k in msg for k in ("드라이브", "letter", "중복", "이미"))
        ok = "저장" in msg and not letter_blocked
        self._add("pass" if ok else "warn",
                  "sc4p — [드라이브 문자] EDIT 같은 letter='Y' 변경 허용 (sc3l 도메인 의도)",
                  f"입력: {other_name} letter → 'Y' / msg={msg!r} (차단 메시지 부재 = 도메인 일치)",
                  sc=4, highlight=page.page.locator(page.SEL_DRIVE_LETTER))
        _safe_close_modal(page)

    # ==================================================================
    # sc4q — EDIT 3 탭 진입 sanity (sc1c 의 ADD 차단과 대비)
    # Chrome MCP 검증 2026-05-29: ADD = 탭 차단 / EDIT = 진입 가능 (사용자 알림)
    # ==================================================================
    def test_scenario4q_three_tabs_enter_edit(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4q: EDIT 3 탭 진입 sanity ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        for tab_name in ["허용 프로세스", "예외처리 프로세스", "실행차단 프로세스"]:
            clicked = page.page.evaluate(
                """(name) => {
                    const tabs = Array.from(document.querySelectorAll('#addItemModal.in ul li'));
                    const t = tabs.find(li => li.textContent.trim() === name);
                    if (!t) return 'not_found';
                    (t.querySelector('a') || t).click();
                    return 'clicked';
                }""",
                tab_name,
            )
            page.page.wait_for_timeout(600)
            active = page.page.evaluate(
                """() => {
                    const a = document.querySelector('#addItemModal.in ul li.active');
                    return a ? a.textContent.trim() : null;
                }"""
            )
            ok = active == tab_name
            self._add("pass" if ok else "fail",
                      f"sc4q — EDIT '{tab_name}' 탭 진입 가능 (ADD sc1c 차단과 대비)",
                      f"click 결과: {clicked} / 현재 active: {active!r} (기대 '{tab_name}')",
                      sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4r — 허용 프로세스 sub-modal 구조 검증 (필수 필드 + picker 진입)
    # Chrome MCP 검증 2026-05-29: sub-modal title='허용 프로세스 추가/수정',
    #   필수 = 프로세스 명, picker id='globalProcessList' (마스터 1252건)
    # ==================================================================
    def test_scenario4r_allow_process_submodal(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4r: 허용 프로세스 sub-modal 구조 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        # 허용 프로세스 탭 진입 + + 버튼 click
        page.page.evaluate(
            """() => {
                const tabs = Array.from(document.querySelectorAll('#addItemModal.in ul li'));
                const t = tabs.find(li => li.textContent.trim() === '허용 프로세스');
                (t.querySelector('a') || t).click();
            }"""
        )
        page.page.wait_for_timeout(800)
        # + 버튼 (data-process-type="ALLOW_PROCESS")
        plus_clicked = page.page.evaluate(
            """() => {
                const btn = document.querySelector('#addItemModal.in button[data-process-type="ALLOW_PROCESS"]');
                if (btn) { btn.click(); return 'clicked'; }
                return 'no_btn';
            }"""
        )
        page.page.wait_for_timeout(1500)
        # sub-modal 진입 확인
        sub_open = page.page.evaluate(
            """() => {
                const modals = Array.from(document.querySelectorAll('.modal-wrap.in'));
                const sub = modals.find(m => {
                    const t = m.querySelector('.modal-title, h4');
                    return t && /허용 프로세스 추가/.test(t.textContent);
                });
                return !!sub;
            }"""
        )
        self._add("pass" if sub_open else "fail",
                  "sc4r — 허용 프로세스 + 버튼 → sub-modal 진입",
                  f"+ button click: {plus_clicked} / sub-modal open: {sub_open}",
                  sc=4)

        # "프로세스 선택" 버튼 → picker 진입
        if sub_open:
            picker_clicked = page.page.evaluate(
                """() => {
                    const subs = Array.from(document.querySelectorAll('.modal-wrap.in'));
                    const sub = subs.find(m => /허용 프로세스 추가/.test((m.querySelector('.modal-title')||{}).textContent||''));
                    if (!sub) return 'no_sub';
                    const btn = Array.from(sub.querySelectorAll('button')).find(b => /프로세스 선택/.test(b.textContent));
                    if (btn) { btn.click(); return 'clicked'; }
                    return 'no_btn';
                }"""
            )
            page.page.wait_for_timeout(1500)
            picker_open = page.page.locator("#globalProcessList.in").count() > 0
            picker_count = page.page.evaluate(
                """() => {
                    const p = document.querySelector('#globalProcessList.in');
                    if (!p) return 0;
                    const text = p.textContent || '';
                    const m = text.match(/등록된 프로세스 *: *([\\d,]+)/);
                    return m ? m[1] : '?';
                }"""
            )
            self._add("pass" if picker_open else "fail",
                      "sc4r — '프로세스 선택' 버튼 → globalProcessList picker 진입",
                      f"picker click: {picker_clicked} / open: {picker_open} / 마스터 프로세스 count: {picker_count}",
                      sc=4)
            # picker 닫기
            page.page.evaluate(
                """() => {
                    const p = document.querySelector('#globalProcessList.in');
                    if (p) {
                        const c = p.querySelector('button.close, button[data-dismiss="modal"]');
                        if (c) c.click();
                    }
                }"""
            )
            page.page.wait_for_timeout(500)
            # sub-modal 닫기
            page.page.evaluate(
                """() => {
                    const subs = Array.from(document.querySelectorAll('.modal-wrap.in'));
                    const sub = subs.find(m => /허용 프로세스 추가/.test((m.querySelector('.modal-title')||{}).textContent||''));
                    if (sub) {
                        const c = Array.from(sub.querySelectorAll('button')).find(b => /취소|닫기/.test(b.textContent));
                        if (c) c.click();
                    }
                }"""
            )
            page.page.wait_for_timeout(500)
        _safe_close_modal(page)

    # ==================================================================
    # sc4s — 같은 프로세스 다중 탭 등록 결함 검증 🔴 (사용자 의심 결함)
    # 도메인: 허용/예외처리/실행차단 는 상호 배타적이어야 정상
    # ==================================================================
    def test_scenario4s_same_process_multi_tab_defect(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4s: 같은 프로세스 다중 탭 등록 결함 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        # 같은 프로세스를 허용/예외처리/실행차단 3 탭에 순차 등록 시도
        target_process_idx = 0  # picker 의 첫 프로세스 (모든 탭에 동일하게)
        registered_tabs = []
        block_messages = []

        for tab_name, proc_type in [
            ("허용 프로세스", "ALLOW_PROCESS"),
            ("예외처리 프로세스", "EXCEPT_PROCESS"),
            ("실행차단 프로세스", "BLOCK_PROCESS"),
        ]:
            # 탭 진입
            page.page.evaluate(
                """(name) => {
                    const tabs = Array.from(document.querySelectorAll('#addItemModal.in ul li'));
                    const t = tabs.find(li => li.textContent.trim() === name);
                    if (t) (t.querySelector('a') || t).click();
                }""",
                tab_name,
            )
            page.page.wait_for_timeout(600)

            # + 버튼 click
            page.page.evaluate(
                """(proc_type) => {
                    const btn = document.querySelector(`#addItemModal.in button[data-process-type="${proc_type}"]`);
                    if (btn) btn.click();
                }""",
                proc_type,
            )
            page.page.wait_for_timeout(1500)

            # "프로세스 선택" 버튼 click
            page.page.evaluate(
                """() => {
                    const subs = Array.from(document.querySelectorAll('.modal-wrap.in'));
                    const sub = subs.find(m => /추가\\/수정/.test((m.querySelector('.modal-title')||{}).textContent||''));
                    if (sub) {
                        const btn = Array.from(sub.querySelectorAll('button')).find(b => /프로세스 선택/.test(b.textContent));
                        if (btn) btn.click();
                    }
                }"""
            )
            page.page.wait_for_timeout(1500)

            # picker 첫 행 (target_process_idx) 체크 + 확인
            page.page.evaluate(
                """(idx) => {
                    const p = document.querySelector('#globalProcessList.in');
                    if (!p) return;
                    const rows = p.querySelectorAll('table tbody tr');
                    const row = rows[idx];
                    if (row) {
                        const cb = row.querySelector('input[type="checkbox"]');
                        if (cb && !cb.checked) cb.click();
                    }
                    const confirm = Array.from(p.querySelectorAll('button')).find(b => /확인/.test(b.textContent));
                    if (confirm) confirm.click();
                }""",
                target_process_idx,
            )
            page.page.wait_for_timeout(1500)

            # sub-modal 의 "등록" 버튼
            msg = ""
            try:
                page.page.evaluate(
                    """() => {
                        const subs = Array.from(document.querySelectorAll('.modal-wrap.in'));
                        const sub = subs.find(m => /추가\\/수정/.test((m.querySelector('.modal-title')||{}).textContent||''));
                        if (sub) {
                            const btn = Array.from(sub.querySelectorAll('button')).find(b => /등록|저장/.test(b.textContent));
                            if (btn) btn.click();
                        }
                    }"""
                )
                page.page.wait_for_timeout(1500)
            except Exception:
                pass

            # 차단 메시지 또는 등록 성공 여부 확인
            gm_open = page.page.locator("#__globalMessageModal.in").count() > 0
            if gm_open:
                msg = page.get_confirm_message()
                page.dismiss_confirm_modal()

            # sub-modal 이 닫혔으면 등록 성공
            sub_open = page.page.evaluate(
                """() => {
                    const subs = Array.from(document.querySelectorAll('.modal-wrap.in'));
                    return subs.some(m => /추가\\/수정/.test((m.querySelector('.modal-title')||{}).textContent||''));
                }"""
            )
            if not sub_open:
                registered_tabs.append(tab_name)
            else:
                block_messages.append((tab_name, msg))
                # sub-modal 닫기
                page.page.evaluate(
                    """() => {
                        const subs = Array.from(document.querySelectorAll('.modal-wrap.in'));
                        const sub = subs.find(m => /추가\\/수정/.test((m.querySelector('.modal-title')||{}).textContent||''));
                        if (sub) {
                            const c = Array.from(sub.querySelectorAll('button')).find(b => /취소|닫기/.test(b.textContent));
                            if (c) c.click();
                        }
                    }"""
                )
                page.page.wait_for_timeout(500)

        # 결과 — 같은 프로세스가 3 탭에 다 등록되면 결함 (배타성 위반)
        defect_reproduced = len(registered_tabs) >= 2
        self._add("warn" if defect_reproduced else "pass",
                  "sc4s — [다중 탭] 같은 프로세스 ALLOW+EXCEPT+BLOCK 동시 등록 결함 🔴 (도메인 배타성 위반)",
                  f"등록 성공 탭: {registered_tabs} / 차단 메시지: {block_messages} "
                  f"(결함 재현 시 2+ 탭 등록 — 허용/차단 모순 가능)",
                  sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4t — 태그 sub-tab 진입 + 구조 검증
    # ==================================================================
    def test_scenario4t_tag_subtab_edit(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4t: 태그 sub-tab 진입 EDIT ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        # 허용 프로세스 탭 진입
        page.page.evaluate(
            """() => {
                const tabs = Array.from(document.querySelectorAll('#addItemModal.in ul li'));
                const t = tabs.find(li => li.textContent.trim() === '허용 프로세스');
                if (t) (t.querySelector('a') || t).click();
            }"""
        )
        page.page.wait_for_timeout(800)
        # 태그 sub-tab click
        tag_clicked = page.page.evaluate(
            """() => {
                const modal = document.querySelector('#addItemModal.in');
                const tags = Array.from(modal.querySelectorAll('a, li, button')).filter(el => el.textContent.trim() === '태그' && el.offsetParent);
                if (tags[0]) { tags[0].click(); return 'clicked'; }
                return 'not_found';
            }"""
        )
        page.page.wait_for_timeout(800)
        # 태그 sub-tab 활성화 확인
        tag_active = page.page.evaluate(
            """() => {
                const modal = document.querySelector('#addItemModal.in');
                const actives = Array.from(modal.querySelectorAll('.active, [class*="active"]'));
                return actives.some(a => a.textContent.trim() === '태그' || a.textContent.includes('태그'));
            }"""
        )
        self._add("pass" if tag_active else "warn",
                  "sc4t — [허용 프로세스] 태그 sub-tab 진입 (개별/태그 분리)",
                  f"click: {tag_clicked} / 태그 active: {tag_active}",
                  sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4u — 사용 체크박스 OFF 시 탭 진입 가능 여부 (UX 결함 가능성)
    # Chrome MCP 확인 2026-05-29: '허용 프로세스 사용: 사용안함' 상태에서도 탭 진입 가능
    # ==================================================================
    def test_scenario4u_use_checkbox_off_tab_enter(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4u: 사용 체크박스 OFF + 탭 진입 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        # 기본 설정 탭에서 "허용 프로세스 사용" 체크박스 상태 확인
        # selector: 본 화면에서 보면 isAllowProcess 같은 id 추정
        use_checkboxes = [
            ("허용 프로세스 사용", "isAllowProcess"),
            ("예외처리 프로세스 사용", "isExceptProcess"),
            ("실행차단 프로세스 사용", "isBlockProcess"),
        ]
        for label, cb_id in use_checkboxes:
            state = page.page.evaluate(
                """(id) => {
                    const el = document.getElementById(id);
                    return el ? {checked: el.checked, disabled: el.disabled} : null;
                }""",
                cb_id,
            )
            self._add("pass" if state else "warn",
                      f"sc4u — [{label}] 체크박스 ({cb_id}) 상태 확인",
                      f"결과: {state} (선언: ADD 시 OFF default, EDIT 진입 시 저장값 load)",
                      sc=4)

        # 사용 체크박스 OFF 상태에서도 허용 프로세스 탭 진입 가능 여부 (Chrome MCP 확인됨)
        # 실제 click 시도
        page.page.evaluate(
            """() => {
                const tabs = Array.from(document.querySelectorAll('#addItemModal.in ul li'));
                const t = tabs.find(li => li.textContent.trim() === '허용 프로세스');
                if (t) (t.querySelector('a') || t).click();
            }"""
        )
        page.page.wait_for_timeout(800)
        gm_open = page.page.locator("#__globalMessageModal.in").count() > 0
        active_tab = page.page.evaluate(
            """() => {
                const a = document.querySelector('#addItemModal.in ul li.active');
                return a ? a.textContent.trim() : null;
            }"""
        )
        # 도메인 의도: 사용 OFF → 탭 진입 차단이 자연스러움 / 진입 가능 = UX 결함 후보
        is_blocked = gm_open or active_tab != "허용 프로세스"
        self._add("warn" if not is_blocked else "pass",
                  "sc4u — [허용 프로세스] 사용 체크박스 OFF 상태 탭 진입 가능 ⚠ (UX 결함 후보)",
                  f"active tab: {active_tab!r}, 알림: {gm_open} "
                  f"(도메인 의도 = 사용 OFF 시 탭 차단 자연 / 진입 가능 = 사용자 혼란)",
                  sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4v — 개별 프로세스 add 3 탭 + 저장 + 재진입 list 확인
    # 프로세스 선택: AUTO 검색 → 0건 fallback 첫 행 / 설명 입력 / 등록 흐름 전체
    # 사용자 명시: "기본 맨 위 / sc6 있으면 AUTO 검색"
    # ==================================================================
    def test_scenario4v_process_add_3tabs(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4v: 개별 프로세스 add 3 탭 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        for tab_name, proc_type in [
            ("허용 프로세스", "ALLOW_PROCESS"),
            ("예외처리 프로세스", "EXCEPT_PROCESS"),
            ("실행차단 프로세스", "BLOCK_PROCESS"),
        ]:
            r = _add_process_to_tab(page, tab_name, proc_type,
                                     description=f"sc4v {tab_name} 설명")
            self._add("pass" if r["registered"] else "fail",
                      f"sc4v — [{tab_name}] 프로세스 add (AUTO 검색 → 첫행 fallback)",
                      f"선택 process: {r['process_name']!r} / "
                      f"sub-modal 등록 성공: {r['registered']} / msg: {r['sub_msg']!r}",
                      sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4w — 개별 프로세스 remove 동작 (- 버튼)
    # ==================================================================
    def test_scenario4w_process_remove(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4w: 개별 프로세스 remove ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        page.page.evaluate(
            """() => {
                const tabs = Array.from(document.querySelectorAll('#addItemModal.in ul li'));
                const t = tabs.find(li => li.textContent.trim() === '허용 프로세스');
                if (t) (t.querySelector('a') || t).click();
            }"""
        )
        page.page.wait_for_timeout(800)
        before_count = page.page.locator(
            "#addItemModal.in table tbody tr:has(input[type='checkbox'])"
        ).count()
        if before_count > 0:
            page.page.evaluate(
                """() => {
                    const rows = document.querySelectorAll('#addItemModal.in table tbody tr');
                    if (rows[0]) {
                        const cb = rows[0].querySelector('input[type="checkbox"]');
                        if (cb && !cb.checked) cb.click();
                    }
                    const minus = document.querySelectorAll('#addItemModal.in i.fa-minus');
                    for (const m of minus) {
                        const btn = m.closest('button');
                        if (btn && btn.offsetParent) { btn.click(); break; }
                    }
                }"""
            )
            page.page.wait_for_timeout(1500)
            if page.is_confirm_modal_visible(timeout=1000):
                page.dismiss_confirm_modal()
        after_count = page.page.locator(
            "#addItemModal.in table tbody tr:has(input[type='checkbox'])"
        ).count()
        removed = before_count > after_count
        self._add("pass" if (before_count == 0 or removed) else "warn",
                  "sc4w — [허용 프로세스] 개별 프로세스 remove (- 버튼)",
                  f"before: {before_count} / after: {after_count} / removed: {removed}",
                  sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4x — 태그 sub-tab add 동작
    # ==================================================================
    def test_scenario4x_tag_add(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4x: 태그 sub-tab add ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        page.page.evaluate(
            """() => {
                const tabs = Array.from(document.querySelectorAll('#addItemModal.in ul li'));
                const t = tabs.find(li => li.textContent.trim() === '허용 프로세스');
                if (t) (t.querySelector('a') || t).click();
            }"""
        )
        page.page.wait_for_timeout(800)
        page.page.evaluate(
            """() => {
                const modal = document.querySelector('#addItemModal.in');
                const tags = Array.from(modal.querySelectorAll('a, li, button')).filter(el => el.textContent.trim() === '태그' && el.offsetParent);
                if (tags[0]) tags[0].click();
            }"""
        )
        page.page.wait_for_timeout(800)
        page.page.evaluate(
            """() => {
                const plus = document.querySelectorAll('#addItemModal.in i.fa-plus');
                for (const p of plus) {
                    const btn = p.closest('button');
                    if (btn && btn.offsetParent) { btn.click(); break; }
                }
            }"""
        )
        page.page.wait_for_timeout(1500)
        modals_open = page.page.evaluate(
            """() => {
                return Array.from(document.querySelectorAll('.modal-wrap.in,.modal.in'))
                    .map(m => (m.querySelector('.modal-title,h4')||{}).textContent?.trim() || m.id);
            }"""
        )
        opened = any(("태그" in m or "추가" in m or "Tag" in m) for m in modals_open if m and m != "addItemModal")
        self._add("pass" if opened else "warn",
                  "sc4x — [태그 sub-tab] + 버튼 → 태그 add modal 진입",
                  f"열린 modals: {modals_open}",
                  sc=4)
        page.page.evaluate(
            """() => {
                const subs = Array.from(document.querySelectorAll('.modal-wrap.in')).filter(m => m.id !== 'addItemModal');
                for (const s of subs) {
                    const c = Array.from(s.querySelectorAll('button')).find(b => /취소|닫기/.test(b.textContent));
                    if (c) c.click();
                }
            }"""
        )
        page.page.wait_for_timeout(500)
        _safe_close_modal(page)

    # ==================================================================
    # sc4y — 태그 sub-tab remove 동작
    # ==================================================================
    def test_scenario4y_tag_remove(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4y: 태그 sub-tab remove ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        page.page.evaluate(
            """() => {
                const tabs = Array.from(document.querySelectorAll('#addItemModal.in ul li'));
                const t = tabs.find(li => li.textContent.trim() === '허용 프로세스');
                if (t) (t.querySelector('a') || t).click();
            }"""
        )
        page.page.wait_for_timeout(800)
        page.page.evaluate(
            """() => {
                const modal = document.querySelector('#addItemModal.in');
                const tags = Array.from(modal.querySelectorAll('a, li, button')).filter(el => el.textContent.trim() === '태그' && el.offsetParent);
                if (tags[0]) tags[0].click();
            }"""
        )
        page.page.wait_for_timeout(800)
        before_count = page.page.locator(
            "#addItemModal.in [id*='Tag'] tbody tr:has(input[type='checkbox'])"
        ).count()
        if before_count > 0:
            page.page.evaluate(
                """() => {
                    const rows = document.querySelectorAll('#addItemModal.in [id*="Tag"] tbody tr');
                    if (rows[0]) {
                        const cb = rows[0].querySelector('input[type="checkbox"]');
                        if (cb && !cb.checked) cb.click();
                    }
                    const minus = document.querySelectorAll('#addItemModal.in i.fa-minus');
                    for (const m of minus) {
                        const btn = m.closest('button');
                        if (btn && btn.offsetParent) { btn.click(); break; }
                    }
                }"""
            )
            page.page.wait_for_timeout(1500)
            if page.is_confirm_modal_visible(timeout=1000):
                page.dismiss_confirm_modal()
        after_count = page.page.locator(
            "#addItemModal.in [id*='Tag'] tbody tr:has(input[type='checkbox'])"
        ).count()
        removed = before_count > after_count
        self._add("pass" if (before_count == 0 or removed) else "warn",
                  "sc4y — [허용 프로세스 태그] remove 동작",
                  f"before: {before_count} / after: {after_count} / removed: {removed}",
                  sc=4)
        _safe_close_modal(page)

    # ==================================================================
    # sc4z — sub-modal 설명 textarea free text (한글/특수/3000자)
    # ==================================================================
    def test_scenario4z_description_textarea(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 4z: 프로세스 설명 textarea free text ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        _ensure_sc3g_policy(page)

        _enter_edit_modal(page, SC3G_NAME)
        page.page.evaluate(
            """() => {
                const tabs = Array.from(document.querySelectorAll('#addItemModal.in ul li'));
                const t = tabs.find(li => li.textContent.trim() === '허용 프로세스');
                if (t) (t.querySelector('a') || t).click();
            }"""
        )
        page.page.wait_for_timeout(800)
        page.page.evaluate(
            """() => {
                const btn = document.querySelector('#addItemModal.in button[data-process-type="ALLOW_PROCESS"]');
                if (btn) btn.click();
            }"""
        )
        page.page.wait_for_timeout(1500)

        for inp, label in [("한글설명", "한글"), ("$@%*^&", "특수문자"), ("X"*3000, "3000자")]:
            page.page.evaluate(
                """(desc) => {
                    const subs = Array.from(document.querySelectorAll('.modal-wrap.in'));
                    const sub = subs.find(m => /추가\\/수정/.test((m.querySelector('.modal-title')||{}).textContent||''));
                    if (sub) {
                        const ta = sub.querySelector('textarea');
                        if (ta) {
                            const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                            setter.call(ta, desc);
                            ta.dispatchEvent(new Event('input', {bubbles:true}));
                        }
                    }
                }""",
                inp,
            )
            page.page.wait_for_timeout(200)
            actual = page.page.evaluate(
                """() => {
                    const subs = Array.from(document.querySelectorAll('.modal-wrap.in'));
                    const sub = subs.find(m => /추가\\/수정/.test((m.querySelector('.modal-title')||{}).textContent||''));
                    if (sub) {
                        const ta = sub.querySelector('textarea');
                        return ta ? ta.value : null;
                    }
                    return null;
                }"""
            )
            ok = actual == inp
            self._add("pass" if ok else "fail",
                      f"sc4z — [허용 프로세스 설명] '{label}' 입력 보존 (free text)",
                      f"입력 {len(inp)}자 / 결과 {len(actual or '')}자 / 보존={ok}",
                      sc=4)

        page.page.evaluate(
            """() => {
                const subs = Array.from(document.querySelectorAll('.modal-wrap.in'));
                const sub = subs.find(m => /추가\\/수정/.test((m.querySelector('.modal-title')||{}).textContent||''));
                if (sub) {
                    const c = Array.from(sub.querySelectorAll('button')).find(b => /취소|닫기/.test(b.textContent));
                    if (c) c.click();
                }
            }"""
        )
        page.page.wait_for_timeout(500)
        _safe_close_modal(page)
