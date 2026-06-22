"""시큐어존 정책 — 시나리오 5: lifecycle (속성-확인 방식, cleanup 소유).

접근제어 정책(tests/secure_zone)에서 깔끔하게 자리잡은 **속성 모달 확인** 설계를 확장:
  추가 → 속성으로 확인 → 수정으로 수정 → 속성으로 확인.
검증을 '수정 모달 재오픈'이 아니라 **읽기전용 속성 모달(detailSecureZoneAgentPolicy)** 로 한다.
속성 모달은 행 더블클릭으로 열리는 상세정보 보기 — 모든 input disabled(읽기전용),
토글/텍스트/라디오 id 는 수정 모달과 동일이라 같은 읽기 로직 재사용(Chrome MCP 실측 2026-06-22).

판정 방식 (하드코딩 기대값 없음):
  - 저장 직전 모달의 '실제 상태'(토글 checked / 텍스트 value)를 intended 로 캡처.
  - 저장 → 속성 모달로 같은 필드를 다시 읽어 intended 와 비교(일치=유지, 불일치=손실).
  - 수정 단계는 ADD 와 '다른 값'으로 바꾼 뒤, 속성에서 before→after 가 실제로 바뀌었는지(변경 반영) 확인.
  설정/변경값은 '입력값'일 뿐 '기대 결과'가 아니다 — 유지/변경 판정은 런타임 비교로 동적 결정.

⚠️ 아래 거동 메모는 작성 시점(2026-06-22) 관측 참고일 뿐 단정 아님 — 환경/빌드/데이터에 따라
   달라질 수 있다. 나올 수 있는 이슈:
   - full-config 저장 후 일부 필드(예: 긴 경로)에서 속성에 값이 안 보이거나(저장 누락) 다르게 보일 수 있음.
   - 속성 모달이 읽기전용이 아니거나(입력 가능) 수정 변경이 속성에 반영 안 될 수 있음.

cleanup 소유: sc5 가 lifecycle 마지막에 [AUTO] 일괄 삭제(sc1 세션시작과 동일 정리를 sc5 가 마무리).
[AUTO] 접두사 정책만 생성/삭제 — 실데이터는 절대 건드리지 않음.
"""
from pages.secure_zone_agent_policy_page import SecureZoneAgentPolicyPage
from tests.secure_zone_policy._base import SecureZonePolicyBase


class TestSecureZonePolicyScenario5Lifecycle(SecureZonePolicyBase):
    """시큐어존 정책 — 시나리오 5: 추가→속성→수정→속성 lifecycle + cleanup."""

    _BASE = "[AUTO]_szp_sc5"

    # 입력값(기대결과 아님) — round-trip 비교 대상으로만 사용.
    _VAL = {
        "watchFileStorePath":   "C:\\sc5\\store",
        "allowPrintModel":      "sc5_model",
        "exceptPrintPort":      "9100",
        "secureDriveBlockTime": "30",
        "customOptionText":     "sc5_custom",
    }
    # 전체 토글 (master 가 sub 앞에 오도록 정렬 — gating 때문에 master ON 후라야 sub 조작 가능).
    _MASTERS = ("isWatchFile", "isPrintUse", "isOfflineUse")
    _ALL_TOGGLES = (
        "isBlockExecuteProcess", "isManageFolder", "isSyncFolder",
        "isWatchFile", "isWatchFileExtention", "isWatchFileHeader", "isWatchFolder",
        "isPrintUse",
        "isShowAgentShutdownMenu", "isShowEmergencyCodeMenu",
        "isOfflineUse", "isTakeoutDriveBlock",
    )

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
            # 태그 무관 선택자(#id) — allowPrintModel/exceptPrintPort 는 <input> 아닌 <textarea>
            # 라서 'input#id' 로 잡으면 매칭 실패→조용히 round-trip 누락(직접조작 확인 2026-06-22).
            try:
                page.fill(f"div#addItemModal.in #{tid}", val)
                applied["text"][tid] = page.field_state(tid).get("value")
            except Exception:
                applied["text"][tid] = None

        for t in ("isBlockExecuteProcess", "isManageFolder", "isSyncFolder"):
            tog(t)
        # 파일감시 (master ON → 하위)
        tog("isWatchFile")
        txt("watchFileStorePath", self._VAL["watchFileStorePath"])
        for t in ("isWatchFileExtention", "isWatchFileHeader", "isWatchFolder"):
            tog(t)
        try:
            page.add_watch_extension("sc5")
            applied["extra"]["watch_ext"] = page.watch_extension_items()
        except Exception:
            applied["extra"]["watch_ext"] = None
        # 프린트 (master ON → radio 허용 → brand/port)
        tog("isPrintUse")
        try:
            page.set_print_radio("1")
        except Exception:
            pass
        applied["extra"]["print_radio"] = page.print_radio_value()
        txt("allowPrintModel", self._VAL["allowPrintModel"])
        txt("exceptPrintPort", self._VAL["exceptPrintPort"])
        # 메뉴
        for t in ("isShowAgentShutdownMenu", "isShowEmergencyCodeMenu"):
            tog(t)
        # 오프라인 (master ON → 대기시간 → 반출드라이브차단)
        tog("isOfflineUse")
        txt("secureDriveBlockTime", self._VAL["secureDriveBlockTime"])
        tog("isTakeoutDriveBlock")
        # 커스텀
        txt("customOptionText", self._VAL["customOptionText"])
        # 허용 프로세스 템플릿 (탭 전환 발생 — 마지막에)
        try:
            applied["extra"]["proc"] = page.assign_process_template("허용")
        except Exception:
            applied["extra"]["proc"] = None
        return applied

    @staticmethod
    def _diff(intended: dict, observed: dict):
        """intended(저장 직전) vs observed(속성 모달) 비교. 반환: (불일치토글[], 불일치텍스트[])."""
        lost_t = [f"{k}({v}->{observed['toggle'].get(k)})"
                  for k, v in intended["toggle"].items()
                  if v is not None and observed["toggle"].get(k) != v]
        lost_x = [f"{k}(\"{v}\"->\"{observed['text'].get(k)}\")"
                  for k, v in intended["text"].items()
                  if v is not None and observed["text"].get(k) != v]
        return lost_t, lost_x

    # ══ 5a: 추가 → 속성확인 → 수정 → 속성확인 (lifecycle 체인) ═══════
    def test_scenario5a_add_detail_modify_detail(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 5a: 추가→속성→수정→속성 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)

        # clean slate — sc5 는 lifecycle 소유라 자기 대상 재생성 OK
        if self._BASE in page.get_policy_names():
            try:
                page.delete_policy(self._BASE)
            except Exception:
                pass
        if not self._ensure_policy(page, self._BASE):
            self._add("skip", "sc5a — 대상 생성 실패", f"입력: - / 결과: {self._BASE} 미생성", sc=5)
            return

        # ── ① 추가(full-config) ──────────────────────────────────
        page.open_modify_modal(self._BASE)
        applied = self._apply_full_config(page)
        msg = page.submit_and_message()
        saved_ok = "저장" in msg
        self._add("pass" if saved_ok else "warn",
                  "sc5a-① 전 필드 채워 저장",
                  f"입력: 전 토글 ON + 텍스트 + 허용 템플릿 + 확장자 / 결과: {msg!r} "
                  + ("(저장 성공)" if saved_ok else "[서버오류/경고 가능 — 풀구성 저장 이슈일 수 있음]"),
                  sc=5,
                  repro="1. [AUTO]_szp_sc5 수정\n2. 모든 토글 ON·텍스트·허용 템플릿·확장자\n3. '수정' 저장")
        page._close_modal_if_open()

        # ── ② 속성으로 확인 (추가 결과) ───────────────────────────
        page.navigate_to()
        if self._BASE not in page.get_policy_names():
            self._add("warn", "sc5a-② 속성 확인 불가(저장 후 대상 없음)",
                      f"입력: 속성 열기 / 결과: {self._BASE} 목록에 없음(저장 실패 가능)", sc=5)
            return
        page.open_detail_modal(self._BASE)
        readonly = page.detail_modal_readonly()
        detail1 = page.read_detail_modal()
        text1 = page.detail_modal_text()
        # ⚠️ 속성 모달을 '열어둔 채' 카드 emit — fail 스크린샷이 닫힌 목록이 아니라
        #    속성 모달의 불일치 필드를 잡도록(사진이 근거가 되게). 카드 후 close_detail_modal().
        lt, lx = self._diff(applied, detail1)
        bad_tog = next((k for k, v in applied["toggle"].items()
                        if v is not None and detail1["toggle"].get(k) != v), None)
        bad_txt = next((k for k, v in applied["text"].items()
                        if v is not None and detail1["text"].get(k) != v), None)
        dm = page.SEL_DETAIL_MODAL

        self._add("pass" if readonly else "warn",
                  "sc5a-② 속성 모달 읽기전용",
                  f"입력: 행 더블클릭으로 속성 열기 / 결과: 모든 input disabled={readonly} "
                  + ("(읽기전용)" if readonly else "[입력 가능하면 결함 — 상세보기에서 수정됨]"),
                  sc=5, repro="1. 행 더블클릭 → 속성(상세정보 보기)\n2. 모든 input 읽기전용인지 확인")

        self._add("pass" if not lt else "fail",
                  "sc5a-② 추가 후 속성 round-trip(토글)",
                  f"입력: 저장 직전 토글상태 / 결과: "
                  + ("속성과 전부 일치" if not lt else f"불일치 {len(lt)}건 {lt}"),
                  sc=5,
                  highlight=page.page.locator(f"{dm} #{bad_tog}") if bad_tog else None,
                  repro="1. 속성 열기\n2. 저장 직전 ON 이던 토글이 속성에서도 ON 인지 비교")
        self._add("pass" if not lx else "fail",
                  "sc5a-② 추가 후 속성 round-trip(텍스트)",
                  f"입력: 저장 직전 텍스트값 / 결과: "
                  + ("속성과 전부 일치" if not lx else f"손실/불일치 {len(lx)}건 {lx} (watchFileStorePath 등 저장누락 회귀 가드)"),
                  sc=5,
                  highlight=page.page.locator(f"{dm} #{bad_txt}") if bad_txt else None,
                  repro="1. 속성 열기\n2. 저장 직전 입력값이 속성에도 그대로인지 비교")
        proc_kept = "허용" in text1
        ext_kept = (applied["extra"].get("watch_ext") in (None, [])) or ("sc5" in text1)
        self._add("pass" if (proc_kept and ext_kept) else "warn",
                  "sc5a-② 추가 후 속성 템플릿/확장자",
                  f"입력: 허용 템플릿 + 확장자 sc5 / 결과: 속성텍스트 '허용' 포함={proc_kept}, 'sc5' 포함={ext_kept}",
                  sc=5, repro="1. 속성 열기\n2. 허용 라벨·확장자 항목 표시 확인")
        page.close_detail_modal()

        # ── ③ 수정으로 수정 (ADD 와 다른 값) ─────────────────────
        new_custom = "sc5_edit"   # 입력값(기대 아님) — 변경 반영 delta 확인용
        page.open_modify_modal(self._BASE)
        try:
            page.fill("div#addItemModal.in #customOptionText", new_custom)
        except Exception:
            pass
        try:
            page.set_toggle("isManageFolder", False)   # 토글 하나 끔(변경)
        except Exception:
            pass
        msg2 = page.submit_and_message()
        saved2 = "저장" in msg2
        self._add("pass" if saved2 else "warn",
                  "sc5a-③ 수정 저장(다른 값)",
                  f"입력: 커스텀='{new_custom}' + isManageFolder OFF 로 수정 / 결과: {msg2!r}",
                  sc=5, repro="1. 수정\n2. 커스텀 변경 + isManageFolder OFF\n3. '수정' 저장")
        page._close_modal_if_open()

        # ── ④ 속성으로 확인 (수정 변경이 반영됐는지 — before→after delta) ──
        page.navigate_to()
        if self._BASE not in page.get_policy_names():
            self._add("warn", "sc5a-④ 속성 확인 불가", f"입력: 속성 열기 / 결과: 대상 없음", sc=5)
            return
        page.open_detail_modal(self._BASE)
        detail2 = page.read_detail_modal()
        custom_before = detail1["text"].get("customOptionText")
        custom_after = detail2["text"].get("customOptionText")
        mf_before = detail1["toggle"].get("isManageFolder")
        mf_after = detail2["toggle"].get("isManageFolder")
        custom_reflected = (custom_after == new_custom) and (custom_after != custom_before)
        mf_reflected = (mf_after is False) and (mf_after != mf_before)
        # 변경 안 된 필드를 highlight (custom 우선, 아니면 isManageFolder) — 속성 모달 열어둔 채 emit.
        bad_sel = "customOptionText" if not custom_reflected else ("isManageFolder" if not mf_reflected else "customOptionText")
        self._add("pass" if (custom_reflected and mf_reflected) else "fail",
                  "sc5a-④ 수정 변경이 속성에 반영(before→after delta)",
                  f"입력: 커스텀 '{custom_before}'→'{new_custom}', isManageFolder ON→OFF / "
                  f"결과: 속성 커스텀='{custom_after}'(반영={custom_reflected}), "
                  f"isManageFolder={mf_after}(반영={mf_reflected})",
                  sc=5,
                  highlight=page.page.locator(f"{page.SEL_DETAIL_MODAL} #{bad_sel}"),
                  repro="1. 수정 후 속성 열기\n2. 바꾼 값이 속성에 새 값으로 보이는지 + 이전과 달라졌는지 확인")
        page.close_detail_modal()

    # ══ 5b: 전 토글 OFF → 저장 → 속성으로 OFF 확인 ════════════════
    def test_scenario5b_all_off_detail(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 5b: 전 토글 OFF → 속성 확인 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._ensure_policy(page, self._BASE):
            self._add("skip", "sc5b — 대상 없음", "입력: - / 결과: base 미존재", sc=5)
            return
        page.open_modify_modal(self._BASE)
        for tid in self._ALL_TOGGLES:
            try:
                page.set_toggle(tid, False)
            except Exception:
                pass
        off_intended = {tid: page.field_state(tid).get("checked") for tid in self._ALL_TOGGLES}
        msg = page.submit_and_message()
        saved_ok = "저장" in msg
        page._close_modal_if_open()

        page.navigate_to()
        if self._BASE not in page.get_policy_names():
            self._add("warn", "sc5b — 속성 확인 불가", f"입력: OFF 저장 / 결과: {msg!r}, 대상 없음", sc=5)
            return
        page.open_detail_modal(self._BASE)
        detail = page.read_detail_modal()
        still_on_ids = [tid for tid in self._ALL_TOGGLES
                        if off_intended.get(tid) is not None
                        and detail["toggle"].get(tid) != off_intended[tid]]
        still_on = [f"{tid}({off_intended[tid]}->{detail['toggle'].get(tid)})" for tid in still_on_ids]
        # 속성 모달 열어둔 채 emit — fail 스크린샷이 불일치 토글을 잡도록. 카드 후 close.
        self._add("pass" if (saved_ok and not still_on) else "fail" if still_on else "warn",
                  "sc5b — 전 토글 OFF 속성 round-trip",
                  f"입력: 전 토글 OFF 저장 / 결과: 저장={msg!r}, "
                  + ("속성에서 OFF 전부 유지" if not still_on else f"불일치 {len(still_on)}건 {still_on}"),
                  sc=5,
                  highlight=page.page.locator(f"{page.SEL_DETAIL_MODAL} #{still_on_ids[0]}") if still_on_ids else None,
                  repro="1. 수정\n2. 전 토글 OFF\n3. 저장\n4. 속성에서 OFF 유지 확인")
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
