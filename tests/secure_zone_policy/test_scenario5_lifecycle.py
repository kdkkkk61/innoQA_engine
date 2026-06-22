"""시큐어존 정책 — 시나리오 5: lifecycle (수정=기준 / 속성=표시검증, cleanup 소유).

[설계 — 직접조작으로 확정한 역할 분리 (Chrome MCP 2026-06-22, 콘솔 192.168.13.141)]
  수정(편집) 모달 = 저장값의 '진짜 기준(source of truth)'. 저장이 됐는지는 여기서 본다.
  속성(상세정보 보기) 모달 = 그 진짜값을 '맞게 보여주는지' 검증할 대상(읽기전용 표시).
  → 사이클 순서: 생성 → 수정모달 확인(저장 검증) → 속성모달 확인(표시 검증).

  관측된 속성 모달 표시 한계(작성 시점, 단정 아님):
   - 일부 토글을 저장값과 다르게 그림(예: isTakeoutDriveBlock 저장 ON 인데 속성 OFF).
   - 일부 텍스트값을 입력칸 대신 '텍스트'로 보여줌(예: watchFileStorePath 경로가 라벨 텍스트).
   - 일부 텍스트값을 아예 표시 안 함(예: secureDriveBlockTime).
  → 그래서 '저장 손실'과 '속성 표시 버그'를 구분: 수정모달에 값이 있으면 저장 정상(속성만 문제),
     수정모달에도 없으면 저장 손실.

[판정 — 하드코딩 기대값 없음]
  - 저장 검증: 저장 직전 모달 상태(intended) vs 수정모달 재오픈값. 불일치 = 저장 손실(fail).
  - 표시 검증: 수정모달값(truth) vs 속성모달값. 불일치 = 속성 표시 버그(warn, 데이터는 안전).
    속성이 텍스트로 보여주는 값은 모달 텍스트 포함 여부로 인정(watchFileStorePath).
  - 게이팅: master(파일감시/오프라인/프린트) OFF 면 그 하위 토글/필드는 비교 제외(N/A).

[사이클]
  sc5a 전체 ON: 생성 → 수정확인(저장) → 속성확인(표시)
  sc5b 전체 OFF: 수정에서 OFF 변경 → 수정확인(저장) → 속성확인(표시)
  sc5c cleanup: [AUTO] 일괄 삭제(정리 소유, 실데이터 보존)

⚠️ 거동 메모는 작성 시점 관측 참고 — 환경/빌드/데이터에 따라 다를 수 있고, 실제 결과로 동적 판정.
"""
from pages.secure_zone_agent_policy_page import SecureZoneAgentPolicyPage
from tests.secure_zone_policy._base import SecureZonePolicyBase


class TestSecureZonePolicyScenario5Lifecycle(SecureZonePolicyBase):
    """시큐어존 정책 — 시나리오 5: 생성→수정확인→속성확인 lifecycle + cleanup."""

    _BASE = "[AUTO]_szp_sc5"

    # 입력값(기대결과 아님) — round-trip 비교 대상으로만 사용.
    _VAL = {
        "watchFileStorePath":   "C:\\sc5\\store",
        "allowPrintModel":      "sc5_model",
        "exceptPrintPort":      "9100",
        "secureDriveBlockTime": "30",
        "customOptionText":     "sc5_custom",
    }
    _MASTERS = ("isWatchFile", "isPrintUse", "isOfflineUse")
    _ALL_TOGGLES = (
        "isBlockExecuteProcess", "isManageFolder", "isSyncFolder",
        "isWatchFile", "isWatchFileExtention", "isWatchFileHeader", "isWatchFolder",
        "isPrintUse",
        "isShowAgentShutdownMenu", "isShowEmergencyCodeMenu",
        "isOfflineUse", "isTakeoutDriveBlock",
    )
    # 게이팅: 하위 토글/텍스트 → 그 master. master OFF 면 비교 제외(N/A).
    _SUB_TO_MASTER = {
        "isWatchFileExtention": "isWatchFile",
        "isWatchFileHeader": "isWatchFile",
        "isWatchFolder": "isWatchFile",
        "isTakeoutDriveBlock": "isOfflineUse",
    }
    _TEXT_TO_MASTER = {
        "watchFileStorePath": "isWatchFile",
        "allowPrintModel": "isPrintUse",
        "exceptPrintPort": "isPrintUse",
        "secureDriveBlockTime": "isOfflineUse",
    }

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneAgentPolicyPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _ensure_policy(self, page, name) -> bool:
        page.navigate_to()
        if name in page.get_policy_names():
            return True
        page.open_add_modal()
        page.create_basic_policy(name)
        page.navigate_to()
        return name in page.get_policy_names()

    def _apply_full_config(self, page) -> dict:
        """모달에 전 필드를 채운다. 반환: {'toggle':{id:checked}, 'text':{id:value}, 'extra':{...}}
        = '저장 직전 실제 모달 상태'(intended). gating 등으로 일부가 안 들어가도 throw 없이 진행."""
        applied = {"toggle": {}, "text": {}, "extra": {}}

        def tog(tid):
            try:
                page.set_toggle(tid, True)
                applied["toggle"][tid] = page.field_state(tid).get("checked")
            except Exception:
                applied["toggle"][tid] = None

        def txt(tid, val):
            # 태그 무관 선택자(#id) — allowPrintModel/exceptPrintPort 는 <textarea> 라 'input#id' 미매칭.
            try:
                page.fill(f"div#addItemModal.in #{tid}", val)
                applied["text"][tid] = page.field_state(tid).get("value")
            except Exception:
                applied["text"][tid] = None

        for t in ("isBlockExecuteProcess", "isManageFolder", "isSyncFolder"):
            tog(t)
        tog("isWatchFile")
        txt("watchFileStorePath", self._VAL["watchFileStorePath"])
        for t in ("isWatchFileExtention", "isWatchFileHeader", "isWatchFolder"):
            tog(t)
        try:
            page.add_watch_extension("sc5")
            applied["extra"]["watch_ext"] = page.watch_extension_items()
        except Exception:
            applied["extra"]["watch_ext"] = None
        tog("isPrintUse")
        try:
            page.set_print_radio("1")
        except Exception:
            pass
        applied["extra"]["print_radio"] = page.print_radio_value()
        txt("allowPrintModel", self._VAL["allowPrintModel"])
        txt("exceptPrintPort", self._VAL["exceptPrintPort"])
        for t in ("isShowAgentShutdownMenu", "isShowEmergencyCodeMenu"):
            tog(t)
        tog("isOfflineUse")
        txt("secureDriveBlockTime", self._VAL["secureDriveBlockTime"])
        tog("isTakeoutDriveBlock")
        txt("customOptionText", self._VAL["customOptionText"])
        try:
            applied["extra"]["proc"] = page.assign_process_template("허용")
        except Exception:
            applied["extra"]["proc"] = None
        return applied

    # ── 비교 헬퍼 (게이팅 인식) ───────────────────────────────────
    def _toggle_diff(self, intended: dict, observed: dict, gate: dict):
        """intended vs observed 토글 비교. gate 에서 master 가 False 인 하위 토글은 제외(게이팅)."""
        out = []
        for tid, want in intended.items():
            if want is None:
                continue
            m = self._SUB_TO_MASTER.get(tid)
            if m and gate.get(m) is False:
                continue
            got = observed.get(tid)
            if got != want:
                out.append((tid, want, got))
        return out

    def _modify_text_diff(self, intended: dict, observed: dict, gate: dict):
        """저장 검증용: intended vs 수정모달 텍스트(입력값). master OFF 하위 제외."""
        out = []
        for tid, want in intended.items():
            if not want:
                continue
            m = self._TEXT_TO_MASTER.get(tid)
            if m and gate.get(m) is False:
                continue
            got = observed.get(tid)
            if got != want:
                out.append((tid, want, got))
        return out

    def _detail_text_diff(self, truth: dict, detail_inputs: dict, detail_text: str, gate: dict):
        """표시 검증용: 수정값(truth) 이 속성에 보이는지. 입력칸 값 OR 모달 텍스트 포함이면 인정.
        (속성이 watchFileStorePath 처럼 텍스트로 보여주는 케이스 false loss 방지.) master OFF 하위 제외."""
        out = []
        for tid, want in truth.items():
            if not want:
                continue
            m = self._TEXT_TO_MASTER.get(tid)
            if m and gate.get(m) is False:
                continue
            dv = detail_inputs.get(tid)
            if dv == want:
                continue                      # 속성 입력칸에 값 있음
            if want in (detail_text or ""):
                continue                      # 속성에 텍스트로 표시됨(watchFileStorePath 등)
            out.append((tid, want, dv))
        return out

    @staticmethod
    def _fmt(diffs):
        return [f"{t}({w}->{g})" for t, w, g in diffs]

    @staticmethod
    def _hl(page, modal_sel, diffs):
        """불일치 첫 필드 highlight locator (없으면 None)."""
        if not diffs:
            return None
        return page.page.locator(f"{modal_sel} #{diffs[0][0]}")

    # ══ 5a: 전체 ON — 생성 → 수정확인(저장) → 속성확인(표시) ════════
    def test_scenario5a_full_on_lifecycle(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 5a: 전체 ON 생성→수정확인→속성확인 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)

        if self._BASE in page.get_policy_names():
            try:
                page.delete_policy(self._BASE)
            except Exception:
                pass
        if not self._ensure_policy(page, self._BASE):
            self._add("skip", "sc5a — 대상 생성 실패", f"입력: - / 결과: {self._BASE} 미생성", sc=5)
            return

        # ── ① 생성: 전 필드 ON ──────────────────────────────────
        page.open_modify_modal(self._BASE)
        applied = self._apply_full_config(page)
        msg = page.submit_and_message()
        saved_ok = "저장" in msg
        self._add("pass" if saved_ok else "warn",
                  "sc5a-① 전 필드 ON 저장",
                  f"입력: 전 토글 ON + 텍스트 + 허용 템플릿 + 확장자 / 결과: {msg!r} "
                  + ("(저장 성공)" if saved_ok else "[서버오류/경고 가능]"),
                  sc=5, repro="1. [AUTO]_szp_sc5 수정\n2. 모든 토글 ON·텍스트·허용 템플릿·확장자\n3. 저장")
        page._close_modal_if_open()

        # ── ② 수정 모달로 확인 (저장 검증 = 진짜값) ──────────────
        page.navigate_to()
        if self._BASE not in page.get_policy_names():
            self._add("warn", "sc5a-② 수정 확인 불가(대상 없음)",
                      f"입력: 수정 재오픈 / 결과: {self._BASE} 목록에 없음(저장 실패 가능)", sc=5)
            return
        page.open_modify_modal(self._BASE)
        truth = page.read_modify_modal_state()
        tog_lost = self._toggle_diff(applied["toggle"], truth["toggle"], applied["toggle"])
        self._add("pass" if not tog_lost else "fail",
                  "sc5a-② 수정모달 토글 저장 round-trip(저장 검증)",
                  f"입력: 저장 직전 ON 토글 / 결과: "
                  + ("전부 저장됨" if not tog_lost else f"저장 손실 {len(tog_lost)}건 {self._fmt(tog_lost)} [수정모달에도 없음=진짜 손실]"),
                  sc=5, highlight=self._hl(page, page.SEL_MODAL, tog_lost),
                  repro="1. 수정 재오픈\n2. 저장 직전 ON 이던 토글이 수정모달에도 ON 인지(=저장됨) 확인")
        txt_lost = self._modify_text_diff(applied["text"], truth["text"], applied["toggle"])
        self._add("pass" if not txt_lost else "fail",
                  "sc5a-② 수정모달 텍스트 저장 round-trip(저장 검증)",
                  f"입력: 저장 직전 텍스트값 / 결과: "
                  + ("전부 저장됨" if not txt_lost else f"저장 손실 {len(txt_lost)}건 {self._fmt(txt_lost)} [수정모달에도 없음=진짜 손실]"),
                  sc=5, highlight=self._hl(page, page.SEL_MODAL, txt_lost),
                  repro="1. 수정 재오픈\n2. 저장 직전 입력값이 수정모달에도 그대로인지(=저장됨) 확인")
        page.close_edit_modal()

        # ── ③ 속성 모달로 확인 (표시 검증 = 수정값 대비) ─────────
        page.navigate_to()
        page.open_detail_modal(self._BASE)
        readonly = page.detail_modal_readonly()
        changes = page.detail_modal_try_change()
        changed_any = [s for s, v in changes.items() if v.get("changed")]
        detail = page.read_detail_modal()
        dtext = page.detail_modal_text()

        self._add("pass" if readonly else "warn",
                  "sc5a-③ 속성 모달 읽기전용(disabled)",
                  f"입력: 행 더블클릭 속성 열기 / 결과: 모든 input disabled={readonly}",
                  sc=5, repro="1. 행 더블클릭 → 속성\n2. 모든 input 읽기전용인지 확인")
        self._add("pass" if not changed_any else "fail",
                  "sc5a-③ 속성 모달 능동 읽기전용(클릭해도 값 불변)",
                  f"입력: 속성 토글/라디오 클릭 시도 / 결과: "
                  + ("클릭해도 전부 불변" if not changed_any else f"클릭에 반응 {changed_any} [읽기전용 우회/UI 변동]"),
                  sc=5, highlight=(page.page.locator(f"{page.SEL_DETAIL_MODAL} {changed_any[0]}") if changed_any else None),
                  repro="1. 속성 열기\n2. 토글/라디오 클릭\n3. 값이 바뀌면 안 됨")
        # 속성 표시 = 수정값(truth) 대비. 불일치 = 속성 표시 버그(데이터는 수정모달에 있음=안전).
        tog_disp = self._toggle_diff(truth["toggle"], detail["toggle"], truth["toggle"])
        self._add("pass" if not tog_disp else "warn",
                  "sc5a-③ 속성모달 토글 표시(수정값 대비)",
                  f"입력: 수정모달 토글값 / 결과: "
                  + ("속성 표시 일치" if not tog_disp else f"속성 표시 불일치 {len(tog_disp)}건 {self._fmt(tog_disp)} "
                     "[데이터는 수정모달에 저장됨 — 속성 모달 표시 버그]"),
                  sc=5, highlight=self._hl(page, page.SEL_DETAIL_MODAL, tog_disp),
                  repro="1. 속성 열기\n2. 수정모달 값과 속성 표시가 같은지 비교(다르면 속성 표시 버그)")
        txt_disp = self._detail_text_diff(truth["text"], detail["text"], dtext, truth["toggle"])
        self._add("pass" if not txt_disp else "warn",
                  "sc5a-③ 속성모달 텍스트 표시(수정값 대비)",
                  f"입력: 수정모달 텍스트값 / 결과: "
                  + ("속성 표시 일치(입력칸 또는 텍스트)" if not txt_disp
                     else f"속성 미표시 {len(txt_disp)}건 {self._fmt(txt_disp)} [데이터는 저장됨 — 속성 모달 표시 버그]"),
                  sc=5, highlight=self._hl(page, page.SEL_DETAIL_MODAL, txt_disp),
                  repro="1. 속성 열기\n2. 수정모달 값이 속성에 입력칸/텍스트로든 보이는지 확인")
        page.close_detail_modal()

    # ══ 5b: 전체 OFF — 수정에서 OFF 변경 → 수정확인 → 속성확인 ════
    def test_scenario5b_all_off_lifecycle(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 5b: 전체 OFF 변경→수정확인→속성확인 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._ensure_policy(page, self._BASE):
            self._add("skip", "sc5b — 대상 없음", "입력: - / 결과: base 미존재", sc=5)
            return

        # ── ① 수정모달에서 전 토글 OFF 변경 ─────────────────────
        page.open_modify_modal(self._BASE)
        for tid in self._ALL_TOGGLES:
            try:
                page.set_toggle(tid, False)
            except Exception:
                pass
        msg = page.submit_and_message()
        saved_ok = "저장" in msg
        self._add("pass" if saved_ok else "warn",
                  "sc5b-① 전 토글 OFF 저장",
                  f"입력: 전 토글 OFF 로 수정 / 결과: {msg!r}",
                  sc=5, repro="1. 수정\n2. 전 토글 OFF\n3. 저장")
        page._close_modal_if_open()

        # ── ② 수정 모달로 확인 (OFF 저장 검증) ──────────────────
        page.navigate_to()
        if self._BASE not in page.get_policy_names():
            self._add("warn", "sc5b-② 수정 확인 불가", f"입력: 수정 재오픈 / 결과: {msg!r}, 대상 없음", sc=5)
            return
        page.open_modify_modal(self._BASE)
        truth = page.read_modify_modal_state()
        off_intended = {tid: False for tid in self._ALL_TOGGLES}
        # gate=truth → master OFF 면 하위 제외(게이팅, #29 노이즈 방지)
        still_on = self._toggle_diff(off_intended, truth["toggle"], truth["toggle"])
        self._add("pass" if (saved_ok and not still_on) else "fail" if still_on else "warn",
                  "sc5b-② 수정모달 OFF 저장 round-trip(저장 검증)",
                  f"입력: 전 토글 OFF 저장 / 결과: 저장={msg!r}, "
                  + ("수정모달 OFF 전부 유지" if not still_on else f"OFF 안 됨 {len(still_on)}건 {self._fmt(still_on)}"),
                  sc=5, highlight=self._hl(page, page.SEL_MODAL, still_on),
                  repro="1. OFF 저장 후 수정 재오픈\n2. 토글이 수정모달에서 OFF 유지인지 확인")
        page.close_edit_modal()

        # ── ③ 속성 모달로 확인 (OFF 표시) ───────────────────────
        page.navigate_to()
        page.open_detail_modal(self._BASE)
        detail = page.read_detail_modal()
        # 표시 검증: 수정값(truth, 전부 OFF) 대비 속성 표시. master OFF 하위 제외.
        disp = self._toggle_diff(truth["toggle"], detail["toggle"], truth["toggle"])
        self._add("pass" if not disp else "warn",
                  "sc5b-③ 속성모달 OFF 표시(수정값 대비)",
                  f"입력: 수정모달 OFF 토글 / 결과: "
                  + ("속성도 OFF 일치" if not disp else f"속성 표시 불일치 {len(disp)}건 {self._fmt(disp)} [데이터는 저장됨 — 속성 표시 버그]"),
                  sc=5, highlight=self._hl(page, page.SEL_DETAIL_MODAL, disp),
                  repro="1. 속성 열기\n2. 수정모달 OFF 와 속성 표시가 같은지 비교")
        page.close_detail_modal()

    # ══ 5c: lifecycle cleanup — [AUTO] 일괄 삭제(정리 소유) ═════════
    def test_scenario5c_lifecycle_cleanup(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 5c: lifecycle cleanup ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        before = [n for n in page.get_policy_names() if n.startswith("[AUTO]")]
        try:
            page.delete_all_auto_policies()
        except Exception as e:
            self._add("warn", "sc5c — cleanup 중 예외", f"입력: [AUTO] 삭제 / 결과: 예외 {e!r}", sc=5)
        page.navigate_to()
        after = [n for n in page.get_policy_names() if n.startswith("[AUTO]")]
        self._add("pass" if not after else "warn",
                  "sc5c — lifecycle 마무리 [AUTO] 일괄 삭제",
                  f"입력: [AUTO] 전부 삭제 / 결과: {len(before)}건 → {len(after)}건 잔여 "
                  + ("(clean)" if not after else f"{after}"),
                  sc=5, repro="1. [AUTO] 정책 전부 삭제\n2. 잔여 0건 확인(실데이터 보존)")
