"""시큐어존 정책 — 시나리오 5: lifecycle (전 필드 round-trip + cleanup 소유).

sc3(ADD)/sc4(EDIT)가 '필드별 단위 동작'을 검증했다면, sc5 는 **한 정책에 전 필드를 채워
저장 → 재오픈 시 그대로 유지되는지(round-trip)** 를 한 번에 검증한다. watchFileStorePath
손실 전례(sc3x/sc4x)처럼 다른 필드도 저장 누락이 나는지 광범위하게 잡는 게 목적.

판정 방식 (하드코딩 기대값 없음):
  - 저장 직전 모달의 '실제 상태'(토글 checked / 텍스트 value)를 intended 로 캡처.
  - 저장 → 재오픈 후 같은 필드를 다시 읽어 intended 와 비교.
  - 일치=유지(PASS), 불일치=손실(FAIL) — '무엇이 손실됐는지' 목록으로 surface.
  설정한 값은 '입력값'일 뿐 '기대 결과'가 아니다. 유지/손실 판정은 런타임 비교로 동적 결정.

⚠️ 아래 거동 메모는 작성 시점(2026-06-22) 관측 참고일 뿐 단정 아님 — 환경/빌드/데이터에 따라
   달라질 수 있다. 나올 수 있는 이슈:
   - full-config 저장 시 일부 필드(예: 긴 경로)에서 서버오류 또는 silent 손실이 나올 수 있음.
   - master 토글(isWatchFile/isPrintUse/isOfflineUse) OFF 저장 후 하위값 잔존/초기화 차이가 나올 수 있음.

cleanup 소유: sc5 가 lifecycle 마지막에 [AUTO] 일괄 삭제(sc1 세션시작과 동일 정리를 sc5 가 마무리).
[AUTO] 접두사 정책만 생성/삭제 — 실데이터는 절대 건드리지 않음.
"""
from pages.secure_zone_agent_policy_page import SecureZoneAgentPolicyPage
from tests.secure_zone_policy._base import SecureZonePolicyBase


class TestSecureZonePolicyScenario5Lifecycle(SecureZonePolicyBase):
    """시큐어존 정책 — 시나리오 5: 전 필드 round-trip + lifecycle cleanup."""

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

    # ══ 5a: full-config 생성 → 저장 → 재오픈 전수 round-trip ════════
    def test_scenario5a_full_config_roundtrip(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 5a: full-config round-trip ━━━")
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

        page.open_modify_modal(self._BASE)
        applied = self._apply_full_config(page)
        msg = page.submit_and_message()

        saved_ok = "저장" in msg
        self._add("pass" if saved_ok else "warn",
                  "sc5a — 전 필드 채운 정책 저장",
                  f"입력: 전 토글 ON + 텍스트필드 + 허용 템플릿 + 확장자 / 결과: {msg!r} "
                  + ("(저장 성공)" if saved_ok else "[서버오류/경고 가능 — 풀구성 저장 이슈일 수 있음]"),
                  sc=5,
                  repro=("1. [AUTO]_szp_sc5 수정\n2. 모든 토글 ON·텍스트 입력·허용 템플릿·확장자 추가\n"
                         "3. '수정' 저장\n4. 저장 메시지 확인"))
        page._close_modal_if_open()

        # 재오픈 round-trip
        page.navigate_to()
        if self._BASE not in page.get_policy_names():
            self._add("warn", "sc5a — 재오픈 불가(저장 후 대상 없음)",
                      f"입력: 재오픈 / 결과: {self._BASE} 목록에 없음(저장 실패 가능)", sc=5)
            return
        page.open_modify_modal(self._BASE)

        # (1) 토글 round-trip — intended(저장 직전) vs 재오픈
        lost_tog = []
        for tid, want in applied["toggle"].items():
            if want is None:
                continue
            got = page.field_state(tid).get("checked")
            if got != want:
                lost_tog.append(f"{tid}({want}→{got})")
        self._add("pass" if not lost_tog else "fail",
                  "sc5a — 토글 round-trip(저장→재오픈 유지)",
                  f"입력: 저장 직전 토글상태 / 결과: "
                  + ("전부 유지" if not lost_tog else f"불일치 {len(lost_tog)}건 {lost_tog}"),
                  sc=5, highlight=page.page.locator("div#addItemModal.in input#isWatchFile"),
                  repro="1. 재오픈\n2. 저장 직전 ON 이던 토글들이 그대로 ON 인지 비교")

        # (2) 텍스트 round-trip
        lost_txt = []
        for tid, want in applied["text"].items():
            if want is None:
                continue
            got = page.field_state(tid).get("value")
            if got != want:
                lost_txt.append(f"{tid}(len {len(want or '')}→{len(got or '')})")
        self._add("pass" if not lost_txt else "fail",
                  "sc5a — 텍스트필드 round-trip(저장→재오픈 유지)",
                  f"입력: 저장 직전 텍스트값 / 결과: "
                  + ("전부 유지" if not lost_txt else f"손실 {len(lost_txt)}건 {lost_txt} "
                     "(watchFileStorePath 등 저장 누락 회귀 가드)"),
                  sc=5, highlight=page.page.locator("div#addItemModal.in input#watchFileStorePath"),
                  repro="1. 재오픈\n2. 저장 직전 입력값이 필드에 그대로 있는지 비교")

        # (3) 템플릿/확장자 round-trip
        ext_now = []
        try:
            page.goto_modal_tab("기본정책")
            ext_now = page.watch_extension_items()
        except Exception:
            pass
        proc_label = ""
        try:
            proc_label = page.process_control_label()
        except Exception:
            pass
        proc_kept = "허용" in proc_label
        ext_kept = (applied["extra"].get("watch_ext") in (None, [])) or bool(ext_now)
        self._add("pass" if (proc_kept and ext_kept) else "warn",
                  "sc5a — 템플릿/확장자 round-trip",
                  f"입력: 허용 템플릿 + 확장자 / 결과: 프로세스라벨={proc_label!r}(허용 유지={proc_kept}), "
                  f"확장자={ext_now}(유지={ext_kept})",
                  sc=5, repro="1. 재오픈\n2. 허용 라벨 + 확장자 항목 유지 확인")
        page.close_edit_modal()

    # ══ 5b: 전 토글 OFF → 저장 → 재오픈 OFF 유지 ═══════════════════
    def test_scenario5b_all_off_roundtrip(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 5b: 전 토글 OFF round-trip ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._ensure_policy(page, self._BASE):
            self._add("skip", "sc5b — 대상 없음", "입력: - / 결과: base 미존재", sc=5)
            return
        page.open_modify_modal(self._BASE)
        # 모든 토글 OFF (master OFF 시 하위 disabled — gating 동반)
        for tid in self._ALL_TOGGLES:
            try:
                page.set_toggle(tid, False)
            except Exception:
                pass
        off_intended = {}
        for tid in self._ALL_TOGGLES:
            off_intended[tid] = page.field_state(tid).get("checked")
        msg = page.submit_and_message()
        saved_ok = "저장" in msg
        page._close_modal_if_open()

        page.navigate_to()
        if self._BASE not in page.get_policy_names():
            self._add("warn", "sc5b — 재오픈 불가", f"입력: OFF 저장 / 결과: {msg!r}, 대상 없음", sc=5)
            return
        page.open_modify_modal(self._BASE)
        still_on = []
        for tid, want in off_intended.items():
            if want is None:
                continue
            got = page.field_state(tid).get("checked")
            if got != want:
                still_on.append(f"{tid}({want}→{got})")
        self._add("pass" if (saved_ok and not still_on) else "fail" if still_on else "warn",
                  "sc5b — 전 토글 OFF round-trip(저장→재오픈 유지)",
                  f"입력: 전 토글 OFF 저장 / 결과: 저장={msg!r}, "
                  + ("OFF 전부 유지" if not still_on else f"불일치 {len(still_on)}건 {still_on}"),
                  sc=5, repro="1. 수정\n2. 전 토글 OFF\n3. 저장\n4. 재오픈 OFF 유지 비교")
        page.close_edit_modal()

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
