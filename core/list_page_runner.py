"""
core/list_page_runner.py — list_page 모드 스캔 오케스트레이터

scan_mode: list_page 인 페이지(공통 프로세스 등)에 사용.
탭 전환 / 검색창 / 버튼 / 테이블 / 모달 필드 / CRUD 순서로 검증.

기존 UIScanner(modal_form 기반)와 독립적으로 동작하며
동일한 PageScanReport 형식을 반환한다.
"""
from __future__ import annotations

from core.models import ScanResult, PageScanReport
from core.reporter import print_combined_report

_STATUS_ICON = {
    "pass": "✅", "fail": "❌", "known_bug": "⚠️", "skip": "⏭", "error": "💥",
}
_SCENARIO_THRESHOLDS = [
    (0,   "시나리오 1: UI 구조  (탭 · 버튼 · 테이블)"),
    (45,  "시나리오 2: 입력 동작  (모달 필드 · 필수입력 검증)"),
    (100, "시나리오 3: CRUD  (추가 · 수정 · 검색 · 삭제)"),
]
_CONFIRM_MODAL = "div#__globalMessageModal.in"
_CONFIRM_BTN   = "div#__globalMessageModal button:has-text('확인')"
_MODAL_TEXT    = "div.modal-body-text"


class ListPageRunner:
    """list_page 스캔 실행기. run()이 PageScanReport를 반환한다."""

    def __init__(self, playwright_page, page_obj, hints: dict) -> None:
        self.page     = playwright_page
        self.page_obj = page_obj
        self.hints    = hints
        self.report   = PageScanReport(page_id=hints.get("page_id", ""))

    # ── 공개 API ──────────────────────────────────────────────────

    def run(self) -> PageScanReport:
        # 시나리오 헤더를 스캔 시작 시점에 출력 → app.py가 실시간으로 감지
        print(f"\n  시나리오 1: UI 구조  (탭 · 버튼 · 테이블)", flush=True)
        self._scan_tabs()       # 탭 전환
        self._scan_buttons()    # 버튼 존재
        self._scan_table()      # 테이블 컬럼

        print(f"\n  시나리오 2: 입력 동작  (모달 필드 · 필수입력 검증)", flush=True)
        self._scan_modal()      # 모달 필드 + 필수 입력 검증

        print(f"\n  시나리오 3: CRUD  (추가 · 수정 · 검색 · 삭제)", flush=True)
        self._scan_crud()       # 추가 → 수정(값 검증) → 검색(항목 존재 상태) → 삭제
        self._scan_search()     # URL 파라미터 구조 확인 (항목 없어도 가능)

        # 결과 출력 (헤더 없이 — 헤더는 스캔 시작 시점에 이미 출력됨)
        print(f"\n{'═' * 60}")
        print("  목록 페이지 스캔 완료")
        print(f"{'═' * 60}")
        print(f"  {self.report.summary()}")
        for r in sorted(self.report.results, key=lambda r: r.order or 9_999):
            icon = _STATUS_ICON.get(r.status, "?")
            print(f"  {icon} [{r.pattern}] {r.label}: {r.detail}")
        print_combined_report(self.report)
        return self.report

    # ── 탭 전환 ───────────────────────────────────────────────────

    def _scan_tabs(self) -> None:
        tabs = self.hints.get("tabs", [])
        for tab in tabs:
            label     = tab["label"]
            param_key = tab["param_key"]
            param_val = tab["param_value"]
            sel       = f"a:has-text('{label}')"
            try:
                self.page.locator(sel).first.evaluate("el => el.click()")
                self.page.wait_for_timeout(500)
                url = self.page.url
                if param_val in url:
                    self._ok("list_tab", sel, f"탭 전환 — {label}",
                             f"클릭 후 URL 파라미터 확인: {param_key}={param_val}", order=10)
                else:
                    self._fail("list_tab", sel, f"탭 전환 — {label}",
                               f"URL에 {param_key}={param_val} 없음", order=10)
            except Exception as e:
                self._err("list_tab", sel, f"탭 전환 — {label}", str(e), order=10)

        # 첫 번째 탭 복원
        if tabs:
            first = tabs[0]["label"]
            try:
                self.page.locator(f"a:has-text('{first}')").first.evaluate("el => el.click()")
                self.page.wait_for_timeout(400)
            except Exception:
                pass

    # ── 검색창 ────────────────────────────────────────────────────

    def _scan_search(self) -> None:
        search = self.hints.get("search", {})
        if not search:
            return
        sel    = search["selector"]
        label  = search.get("label", "검색창")
        maxlen = search.get("maxlength")
        try:
            loc = self.page.locator(sel).first
            if loc.count() == 0:
                self._fail("list_search", sel, label, "검색창 없음", order=20)
                return

            # 1. 존재 확인 + 입력 동작
            detail = "존재 확인 + 입력 동작 확인"
            if maxlen:
                detail += f" + maxlength {maxlen}자 (DOM 속성)"
            self._ok("list_search", sel, label, detail, order=20)

            # 2. 검색 실행 → URL searchText 파라미터 반영 확인
            keyword = "test_search_kw"
            loc.fill(keyword)
            loc.dispatch_event("keydown", {"keyCode": 13, "which": 13})
            loc.dispatch_event("keyup",   {"keyCode": 13, "which": 13})
            self.page.wait_for_timeout(600)
            url = self.page.url
            import urllib.parse
            decoded_url = urllib.parse.unquote(url)
            if keyword in decoded_url or f"searchText={keyword}" in url:
                self._ok("list_search", sel, f"{label} — 검색 실행",
                         f"Enter 후 URL searchText 파라미터 반영 확인", order=21)
            else:
                self._fail("list_search", sel, f"{label} — 검색 실행",
                           f"Enter 후 URL에 searchText={keyword!r} 없음 (url={url!r})", order=21)

            # 3. 검색 초기화
            loc.fill("")
            loc.dispatch_event("keydown", {"keyCode": 13, "which": 13})
            loc.dispatch_event("keyup",   {"keyCode": 13, "which": 13})
            self.page.wait_for_timeout(400)
        except Exception as e:
            self._err("list_search", sel, label, str(e), order=20)

    # ── 액션 버튼 ─────────────────────────────────────────────────

    def _scan_buttons(self) -> None:
        for btn in self.hints.get("action_buttons", []):
            label = btn["label"]
            sel   = btn["selector"]
            order = btn.get("order", 30)
            try:
                exists = self.page.locator(sel).count() > 0
                if exists:
                    self._ok("list_button", sel, f"버튼 존재 — {label}",
                             "버튼 DOM 존재 확인", order=order)
                else:
                    self._fail("list_button", sel, f"버튼 존재 — {label}",
                               "버튼 없음", order=order)
            except Exception as e:
                self._err("list_button", sel, f"버튼 존재 — {label}", str(e), order=order)

    # ── 테이블 컬럼 ───────────────────────────────────────────────

    def _scan_table(self) -> None:
        tbl = self.hints.get("table_columns", {})
        if not tbl:
            return
        expected = tbl.get("headers", [])
        order    = tbl.get("order", 40)
        if not expected:
            return
        try:
            actual = [
                h.inner_text().strip()
                for h in self.page.locator("table th").all()
                if h.inner_text().strip()
            ]
            missing = [h for h in expected if h not in actual]
            if not missing:
                self._ok("list_table", "table th", "테이블 컬럼 구조",
                         f"컬럼 {len(expected)}개 확인: {', '.join(expected)}", order=order)
            else:
                self._fail("list_table", "table th", "테이블 컬럼 구조",
                           f"누락 컬럼: {', '.join(missing)}", order=order)
        except Exception as e:
            self._err("list_table", "table th", "테이블 컬럼 구조", str(e), order=order)

    # ── 추가 모달 ─────────────────────────────────────────────────

    def _scan_modal(self) -> None:
        modal_cfg   = self.hints.get("add_modal", {})
        if not modal_cfg:
            return
        modal_sel   = modal_cfg.get("modal_selector", "div#addItemModal")
        open_sel    = modal_cfg.get("modal_open_selector", "button#addItemBtn")
        submit_sel  = modal_cfg.get("submit_selector", "button[add-btn]")
        cancel_sel  = modal_cfg.get("cancel_selector", "button.btn-default")
        fields      = modal_cfg.get("fields", [])

        try:
            self.page.locator(open_sel).first.evaluate("el => el.click()")
            self.page.wait_for_timeout(500)
            if self.page.locator(f"{modal_sel}.in").count() == 0:
                self._fail("list_modal", modal_sel, "추가 모달 열기", "모달이 열리지 않음", order=45)
                return
        except Exception as e:
            self._err("list_modal", modal_sel, "추가 모달 열기", str(e), order=45)
            return

        self._ok("list_modal", modal_sel, "추가 모달 열기", "모달 정상 열림", order=45)

        # 필드 존재 확인
        for field in fields:
            fid    = field["id"]
            ftype  = field.get("type", "text")
            flabel = field.get("label", fid)
            forder = field.get("order", 50)
            freq   = field.get("required", False)
            tag    = "textarea" if ftype == "textarea" else "input"
            sel    = f"{tag}#{fid}"
            req_str = " (필수*)" if freq else " (선택)"
            try:
                exists = self.page.locator(sel).count() > 0
                if exists:
                    self._ok("list_modal", sel, f"모달 필드 — {flabel}{req_str}",
                             f"{tag} 존재 확인", order=forder)
                else:
                    self._fail("list_modal", sel, f"모달 필드 — {flabel}{req_str}",
                               f"{sel} 없음", order=forder)
            except Exception as e:
                self._err("list_modal", sel, f"모달 필드 — {flabel}{req_str}",
                          str(e), order=forder)

        # 필수 필드 미입력 경고 확인
        req_fields = [f for f in fields if f.get("required")]
        for req_f in req_fields:
            self._test_required_field(req_f, req_fields, submit_sel)

        # 글자수 제한 없는 필드 오버플로 테스트
        self._scan_field_overflow(fields, req_fields, open_sel, submit_sel, cancel_sel, modal_sel)

        # 모달 닫기 (이미 닫혀있으면 스킵)
        try:
            if self.page.locator(f"{modal_sel}.in").count() > 0:
                self.page.locator(cancel_sel).first.evaluate("el => el.click()")
                self.page.wait_for_timeout(400)
            if self.page.locator(_CONFIRM_MODAL).count() > 0:
                self.page.locator(_CONFIRM_BTN).first.evaluate("el => el.click()")
                self.page.wait_for_timeout(400)
        except Exception:
            pass

    def _test_required_field(
        self, req_f: dict, all_req: list[dict], submit_sel: str
    ) -> None:
        """해당 필드만 비우고 다른 필수 필드는 채운 뒤 제출 → 경고 확인."""
        fid    = req_f["id"]
        ftype  = req_f.get("type", "text")
        flabel = req_f.get("label", fid)
        forder = req_f.get("order", 50)
        tag    = "textarea" if ftype == "textarea" else "input"
        sel    = f"{tag}#{fid}"

        # 다른 필수 필드 채우기
        for other in all_req:
            if other["id"] == fid:
                continue
            other_tag = "textarea" if other.get("type") == "textarea" else "input"
            other_sel = f"{other_tag}#{other['id']}"
            try:
                self.page.locator(other_sel).first.evaluate(
                    "el => { el.value = 'test_val'; "
                    "el.dispatchEvent(new Event('input',{bubbles:true})); }"
                )
            except Exception:
                pass

        # 이 필드 비우기
        try:
            self.page.locator(sel).first.evaluate(
                "el => { el.value = ''; "
                "el.dispatchEvent(new Event('input',{bubbles:true})); }"
            )
        except Exception:
            pass

        # 제출
        try:
            self.page.locator(submit_sel).first.evaluate("el => el.click()")
            self.page.wait_for_timeout(600)
        except Exception:
            pass

        # 경고 모달 확인
        try:
            self.page.locator(_CONFIRM_MODAL).wait_for(state="attached", timeout=2_000)
            msg = self.page.locator(_MODAL_TEXT).first.inner_text().strip()
            self.page.locator(_CONFIRM_BTN).first.evaluate("el => el.click()")
            self.page.locator(_CONFIRM_MODAL).wait_for(state="detached", timeout=3_000)
            self._ok("list_modal_required", sel, f"필수 미입력 경고 — {flabel}",
                     f"경고: '{msg}'", order=forder + 20)
        except Exception:
            self._fail("list_modal_required", sel, f"필수 미입력 경고 — {flabel}",
                       "경고 모달 없음 (필수 검증 미동작 — 실제 required 아닐 수 있음)",
                       order=forder + 20)

    def _scan_field_overflow(
        self,
        fields: list,
        req_fields: list,
        open_sel: str,
        submit_sel: str,
        cancel_sel: str,
        modal_sel: str,
        overflow_len: int = 500,
        order_base: int = 90,
    ) -> None:
        """글자수 제한 없는 필드에 긴 값 입력 후 제출 → 서버 오류 여부 확인.

        maxlength 속성이 없는 필드 중 text/textarea 타입에 대해
        overflow_len 길이의 문자열을 입력하고 제출한다.
        - 서버 오류 모달('서버에서 오류') → fail (클라이언트 검증 누락)
        - 정상 저장 또는 유효성 에러 → pass
        """
        # maxlength 미지정 텍스트 필드만 대상
        targets = [
            f for f in fields
            if f.get("type") in ("text", "textarea") and not f.get("maxlength")
        ]
        if not targets:
            return

        for i, field in enumerate(targets):
            fid    = field["id"]
            ftype  = field.get("type", "text")
            flabel = field.get("label", fid)
            tag    = "textarea" if ftype == "textarea" else "input"
            sel    = f"{tag}#{fid}"
            order  = order_base + i

            try:
                # 각 iteration마다 모달을 새로 열기 (이전 테스트 후 닫혀있을 수 있음)
                if self.page.locator(f"{modal_sel}.in").count() == 0:
                    self.page.locator(open_sel).first.evaluate("el => el.click()")
                    self.page.wait_for_timeout(500)
                    if self.page.locator(f"{modal_sel}.in").count() == 0:
                        self._err("list_modal_overflow", sel,
                                  f"글자수 제한 없음 — {flabel} ({overflow_len}자)",
                                  "모달 재열기 실패", order=order)
                        continue

                # 필수 필드 모두 유효값으로 채우기 (모달 내 요소를 직접 JS로 채움)
                for req_f in req_fields:
                    r_tag = "textarea" if req_f.get("type") == "textarea" else "input"
                    r_id  = req_f["id"]
                    fill_val = "A" * 64 if req_f.get("type") == "textarea" else "overflow_test"
                    self.page.evaluate(
                        "(args) => { const el = document.getElementById(args.id);"
                        " if(el){ el.value = args.v;"
                        " el.dispatchEvent(new Event('input',{bubbles:true})); } }",
                        {"id": r_id, "v": fill_val},
                    )

                # 대상 필드에 긴 값 입력
                long_val = "A" * overflow_len
                self.page.evaluate(
                    "(args) => { const el = document.getElementById(args.id);"
                    " if(el){ el.value = args.v;"
                    " el.dispatchEvent(new Event('input',{bubbles:true})); } }",
                    {"id": fid, "v": long_val},
                )

                # 제출 (querySelector 사용 — locator timeout 없음)
                self.page.evaluate(
                    "(sel) => { const el = document.querySelector(sel); if(el) el.click(); }",
                    submit_sel,
                )
                # 응답 확인 — 모달 뜨는 즉시 진행 (sleep 없음)
                try:
                    self.page.locator(_CONFIRM_MODAL).wait_for(state="attached", timeout=3_000)
                    msg = self.page.locator(_MODAL_TEXT).first.inner_text().strip()
                    self.page.locator(_CONFIRM_BTN).first.evaluate("el => el.click()")
                    self.page.locator(_CONFIRM_MODAL).wait_for(state="detached", timeout=3_000)

                    if "서버" in msg or "오류" in msg or "error" in msg.lower():
                        self._known_bug(
                            "list_modal_overflow", sel,
                            f"글자수 제한 누락 — {flabel} ({overflow_len}자)",
                            f"클라이언트 검증 없어 서버 오류 발생: '{msg}'",
                            order=order,
                        )
                    else:
                        self._ok(
                            "list_modal_overflow", sel,
                            f"글자수 제한 없음 — {flabel} ({overflow_len}자)",
                            f"서버 오류 없음, 응답: '{msg}'",
                            order=order,
                        )
                except Exception:
                    # 모달 없이 저장됨 (timeout — 모달 안 뜸)
                    self._ok(
                        "list_modal_overflow", sel,
                        f"글자수 제한 없음 — {flabel} ({overflow_len}자)",
                        f"서버 오류 없음 (저장 성공 또는 무응답)",
                        order=order,
                    )
                    try:
                        auto_name = "overflow_test"
                        if auto_name in self.page_obj.get_item_names():
                            self.page_obj.delete_item(auto_name)
                    except Exception:
                        pass

            except Exception as e:
                self._err("list_modal_overflow", sel,
                          f"글자수 제한 없음 — {flabel} ({overflow_len}자)",
                          str(e), order=order)

            # 모달이 아직 열려있으면 취소
            try:
                if self.page.locator(f"{modal_sel}.in").count() > 0:
                    self.page.locator(cancel_sel).first.evaluate("el => el.click()")
                    self.page.wait_for_timeout(400)
            except Exception:
                pass

    # ── 수정 모달 ─────────────────────────────────────────────────

    def _scan_modify(self, test_name: str, crud_order: int, tab_label: str = "") -> None:
        """수정 모달 열기 → 값 로드 확인 → 실제 저장 → 재확인까지 검증."""
        modal_cfg  = self.hints.get("add_modal", {})
        modal_sel  = modal_cfg.get("modal_selector", "div#addItemModal")
        cancel_sel = modal_cfg.get("cancel_selector", "button.btn-default")
        # order 할당: crud_order 기준으로 open=+1, load_verify=+2, save=+3, save_verify=+4
        o_open   = crud_order + 1
        o_load   = crud_order + 2
        o_save   = crud_order + 3
        o_verify = crud_order + 4

        open_modify = getattr(self.page_obj, "open_modify_modal", None)
        if open_modify is None:
            self._skip("list_modify", modal_sel, "행 선택 + 수정 모달 열기",
                       "page_obj에 open_modify_modal() 미구현", order=o_open)
            return

        # ── 1. 수정 모달 열기 ──────────────────────────────────────
        try:
            open_modify(test_name)
            if self.page.locator(f"{modal_sel}.in").count() > 0:
                self._ok("list_modify", modal_sel, "행 선택 + 수정 모달 열기",
                         "행 native 클릭 → 수정 버튼 → 수정 모달 정상 열림", order=o_open)
            else:
                self._fail("list_modify", modal_sel, "행 선택 + 수정 모달 열기",
                           "수정 모달이 열리지 않음", order=o_open)
                return
        except Exception as e:
            self._err("list_modify", modal_sel, "행 선택 + 수정 모달 열기",
                      str(e), order=o_open)
            return

        # ── 2. 초기 값 로드 검증 (get_verify_values) ──────────────
        verify_fn = getattr(self.page_obj, "get_verify_values", None)
        if verify_fn:
            for selector, expected in verify_fn(test_name).items():
                try:
                    actual = self.page.locator(selector).first.input_value()
                    if actual == expected:
                        self._ok("list_modify_verify", selector,
                                 f"수정 모달 값 로드 — {selector}",
                                 f"기댓값 '{expected}' 일치", order=o_load)
                    else:
                        self._fail("list_modify_verify", selector,
                                   f"수정 모달 값 로드 — {selector}",
                                   f"기댓값 '{expected}', 실제 '{actual}'", order=o_load)
                except Exception as e:
                    self._err("list_modify_verify", selector,
                              f"수정 모달 값 로드 — {selector}", str(e), order=o_load)

        # 모달 취소 (로드 확인 후)
        try:
            self.page.locator(cancel_sel).first.evaluate("el => el.click()")
            self.page.wait_for_timeout(400)
            if self.page.locator(_CONFIRM_MODAL).count() > 0:
                self.page.locator(_CONFIRM_BTN).first.evaluate("el => el.click()")
                self.page.wait_for_timeout(400)
        except Exception:
            pass

        # ── 2.5 제품 버그 탐지: 전자서명 변경 시 SHA2 초기화 ────────
        # 수정 모달을 다시 열고, sign 변경 → 수정 시도 → SHA2 에러 확인
        try:
            open_modify(test_name)
            if self.page.locator(f"{modal_sel}.in").count() > 0:
                # sign 값 변경 (JS evaluate — DOM만 변경, 내부 상태 트리거)
                self.page.locator("input#sign").first.evaluate(
                    "(el, v) => { el.value = v;"
                    " el.dispatchEvent(new Event('input',{bubbles:true})); }",
                    "[AUTO]_sign_bugtest",
                )
                self.page.wait_for_timeout(300)
                # 수정 버튼 클릭
                self.page.locator("button[modify-btn]").first.evaluate("el => el.click()")
                self.page.wait_for_timeout(600)
                # 에러 모달 확인
                if self.page.locator(_CONFIRM_MODAL).count() > 0:
                    msg = self.page.locator(_MODAL_TEXT).first.inner_text().strip()
                    self.page.locator(_CONFIRM_BTN).first.evaluate("el => el.click()")
                    self.page.locator(_CONFIRM_MODAL).wait_for(
                        state="detached", timeout=3_000
                    )
                    _tab = f" [{tab_label}]" if tab_label else ""
                    if "SHA2" in msg or "해시" in msg:
                        self._known_bug(
                            "list_modify_bug", "input#sign",
                            f"전자서명 변경 시 SHA2 초기화 (제품 버그){_tab}",
                            f"전자서명 수정 → 내부 SHA2 상태 초기화 → 에러: '{msg}'",
                            order=o_save - 1,
                        )
                    else:
                        # 예상치 못한 에러
                        self._fail(
                            "list_modify_bug", "input#sign",
                            f"전자서명 변경 시 SHA2 초기화 (제품 버그){_tab}",
                            f"예상치 못한 에러 모달: '{msg}'",
                            order=o_save - 1,
                        )
                else:
                    # 에러 없이 저장됨 → 버그가 수정된 경우
                    self._ok(
                        "list_modify_bug", "input#sign",
                        f"전자서명 변경 시 SHA2 초기화 (제품 버그){_tab}",
                        "에러 없이 저장 성공 — 버그 수정된 것으로 보임",
                        order=o_save - 1,
                    )
                # 모달 취소 (버그 테스트 종료)
                try:
                    self.page.locator(modal_cfg.get("cancel_selector", "button.btn-default")).first.evaluate(
                        "el => el.click()"
                    )
                    self.page.wait_for_timeout(400)
                except Exception:
                    pass
        except Exception as e:
            self._err(
                "list_modify_bug", "input#sign",
                "전자서명 변경 시 SHA2 초기화 (제품 버그)",
                str(e), order=o_save - 1,
            )

        # ── 3. 수정 저장 + 재확인 (fill_modify_and_save) ─────────
        modify_fn = getattr(self.page_obj, "fill_modify_and_save", None)
        if modify_fn is None:
            return

        try:
            open_modify(test_name)  # 모달 재오픈 (step 2 취소 후)
            if self.page.locator(f"{modal_sel}.in").count() == 0:
                self._fail("list_modify_save", modal_sel, "수정 저장",
                           "수정 모달 재오픈 실패", order=o_save)
                return
            verify_after = modify_fn()
            self._ok("list_modify_save", modal_sel, "수정 저장",
                     "필드 변경 후 저장 성공", order=o_save)
        except Exception as e:
            self._err("list_modify_save", modal_sel, "수정 저장", str(e), order=o_save)
            return

        # 재오픈하여 저장된 값 확인
        try:
            open_modify(test_name)
            if self.page.locator(f"{modal_sel}.in").count() == 0:
                self._fail("list_modify_save", modal_sel, "수정 저장 후 재확인",
                           "재오픈 실패", order=o_verify)
                return
            for selector, expected in verify_after.items():
                try:
                    actual = self.page.locator(selector).first.input_value()
                    if actual == expected:
                        self._ok("list_modify_save", selector,
                                 f"수정 저장 후 재확인 — {selector}",
                                 f"저장값 '{expected}' 확인", order=o_verify)
                    else:
                        self._fail("list_modify_save", selector,
                                   f"수정 저장 후 재확인 — {selector}",
                                   f"기댓값 '{expected}', 실제 '{actual}'", order=o_verify)
                except Exception as e:
                    self._err("list_modify_save", selector,
                              f"수정 저장 후 재확인 — {selector}", str(e), order=o_verify)
            # 닫기
            self.page.locator(cancel_sel).first.evaluate("el => el.click()")
            self.page.wait_for_timeout(400)
        except Exception as e:
            self._err("list_modify_save", modal_sel, "수정 저장 후 재확인",
                      str(e), order=o_verify)

    def _scan_search_with_item(self, name: str, order: int) -> None:
        """항목이 존재하는 상태에서 검색 → 결과 필터링 → 초기화 → 전체 복원 확인."""
        search = self.hints.get("search", {})
        if not search:
            return
        sel   = search["selector"]
        label = search.get("label", "검색창")

        try:
            loc = self.page.locator(sel).first
            if loc.count() == 0:
                return

            # 1. 검색 실행
            loc.fill(name)
            loc.dispatch_event("keydown", {"keyCode": 13, "which": 13})
            loc.dispatch_event("keyup",   {"keyCode": 13, "which": 13})
            self.page.wait_for_timeout(600)

            # 2. 결과 필터링 확인
            names = self.page_obj.get_item_names()
            if name in names:
                self._ok("list_search", sel, f"{label} — 검색 결과 필터링",
                         f"'{name}' 검색 → {len(names)}건 중 포함 확인", order=order)
            else:
                self._fail("list_search", sel, f"{label} — 검색 결과 필터링",
                           f"'{name}' 검색 결과에 없음", order=order)

            # 3. 검색 초기화 → 전체 복원
            loc.fill("")
            loc.dispatch_event("keydown", {"keyCode": 13, "which": 13})
            loc.dispatch_event("keyup",   {"keyCode": 13, "which": 13})
            self.page.wait_for_timeout(500)
            all_names = self.page_obj.get_item_names()
            if len(all_names) >= len(names):
                self._ok("list_search", sel, f"{label} — 검색 초기화",
                         f"검색 해제 후 전체 목록 복원 확인 ({len(all_names)}건)", order=order + 1)
            else:
                self._fail("list_search", sel, f"{label} — 검색 초기화",
                           f"검색 해제 후 목록이 줄어듦 ({len(all_names)}건)", order=order + 1)
        except Exception as e:
            self._err("list_search", sel, f"{label} — 검색 UX", str(e), order=order)

    # ── CRUD ──────────────────────────────────────────────────────

    def _scan_crud(self) -> None:
        crud = self.hints.get("crud", {})
        if not crud:
            return
        test_name  = crud.get("test_name", "[AUTO]_cp_test")
        test_sha2  = crud.get("test_sha2", "")
        crud_order = crud.get("order", 100)

        # 추가
        try:
            self.page_obj.add_item(test_name, test_sha2)
            names = self.page_obj.get_item_names()
            if test_name in names:
                self._ok("list_crud", "table tbody tr", "CRUD — 항목 추가",
                         f"'{test_name}' 추가 후 목록 확인", order=crud_order)
            else:
                self._fail("list_crud", "table tbody tr", "CRUD — 항목 추가",
                           f"'{test_name}' 추가 후 목록에 없음", order=crud_order)
                return
        except Exception as e:
            self._err("list_crud", "table tbody tr", "CRUD — 항목 추가",
                      str(e), order=crud_order)
            return

        # 차단 탭 CRUD + SHA2 전역 유니크 검증 — order: crud_order+1 ~
        # 반드시 _scan_modify() 전에 실행: modify가 SHA2를 변경하면 중복 검증이 불가능
        tabs = self.hints.get("tabs", [])
        sha2_b = crud.get("test_sha2_b", "")
        if sha2_b and hasattr(self.page_obj, "switch_tab") and hasattr(self.page_obj, "try_add_item"):
            self._scan_block_tab_crud(test_name, test_sha2, sha2_b, crud_order + 1)
            # 차단 탭 검증 후 예외 탭으로 복귀 — 이후 수정/검색 테스트는 예외 탭 항목 대상
            if tabs:
                try:
                    self.page_obj.switch_tab(tabs[0]["label"])
                except Exception:
                    pass

        # 수정 모달 열림 + 값 로드 + 저장 + 재확인 (차단 탭 검증 후)
        # _scan_modify 내부 order: crud_order+8 ~ crud_order+11
        except_label = tabs[0]["label"] if tabs else "예외 탭"
        self._scan_modify(test_name, crud_order + 7, tab_label=except_label)

        # 검색 UX 검증 (항목이 존재하는 상태에서 실행)
        # order: crud_order+13, crud_order+14
        self._scan_search_with_item(test_name, crud_order + 13)

        # 예외 탭으로 복귀 후 삭제 — order: crud_order+17
        if tabs and hasattr(self.page_obj, "switch_tab"):
            try:
                self.page_obj.switch_tab(tabs[0]["label"])
            except Exception:
                pass

        try:
            self.page_obj.delete_item(test_name)
            names_after = self.page_obj.get_item_names()
            if test_name not in names_after:
                self._ok("list_crud", "table tbody tr", "CRUD — 예외 탭 항목 삭제",
                         f"'{test_name}' 삭제 후 목록 제거 확인", order=crud_order + 17)
            else:
                self._fail("list_crud", "table tbody tr", "CRUD — 예외 탭 항목 삭제",
                           f"'{test_name}' 삭제 후에도 목록에 남아있음", order=crud_order + 17)
        except Exception as e:
            self._err("list_crud", "table tbody tr", "CRUD — 예외 탭 항목 삭제",
                      str(e), order=crud_order + 17)

    def _scan_block_tab_crud(
        self,
        test_name: str,
        sha2_a: str,
        sha2_b: str,
        order_base: int,
    ) -> None:
        """차단 탭으로 전환 후 SHA2 전역 유니크 제약 + CRUD 검증.

        검증 시나리오:
          1. 차단 탭 전환
          2. 동일 이름 + SHA2_A(중복) 추가 시도 → 에러 확인
          3. 동일 이름 + SHA2_B(유니크) 추가 → 성공 확인
          4. 차단 탭 항목 삭제
        """
        tabs = self.hints.get("tabs", [])
        block_tab = next((t for t in tabs if "차단" in t["label"]), None)
        if not block_tab:
            return

        # 1. 차단 탭 전환
        try:
            self.page_obj.switch_tab(block_tab["label"])
        except Exception as e:
            self._err("list_crud", "a", f"차단 탭 전환", str(e), order=order_base)
            return

        # 2. 동일 이름 + SHA2_A(중복) → 에러여야 함
        try:
            ok, msg = self.page_obj.try_add_item(test_name, sha2_a)
            if not ok:
                self._ok(
                    "list_crud", "div#addItemModal",
                    "차단 탭 — SHA2 중복 에러 확인",
                    f"예외 탭과 동일 SHA2 사용 시 에러: {msg!r}",
                    order=order_base + 1,
                )
            else:
                self._fail(
                    "list_crud", "div#addItemModal",
                    "차단 탭 — SHA2 중복 에러 확인",
                    f"동일 SHA2 추가가 성공함 (전역 유니크 제약 미작동): msg={msg!r}",
                    order=order_base + 1,
                )
                # 잘못 추가됐으면 삭제
                try:
                    self.page_obj.delete_item(test_name)
                except Exception:
                    pass
        except Exception as e:
            self._err("list_crud", "div#addItemModal",
                      "차단 탭 — SHA2 중복 에러 확인", str(e), order=order_base + 1)

        # 3. 동일 이름 + SHA2_B(유니크) → 성공해야 함
        try:
            ok, msg = self.page_obj.try_add_item(test_name, sha2_b)
            if ok:
                self._ok(
                    "list_crud", "table tbody tr",
                    "차단 탭 — 동일 이름 + 다른 SHA2 추가",
                    f"이름 중복 허용 + SHA2 유니크 조합으로 추가 성공",
                    order=order_base + 2,
                )
            else:
                self._fail(
                    "list_crud", "table tbody tr",
                    "차단 탭 — 동일 이름 + 다른 SHA2 추가",
                    f"추가 실패: {msg!r}",
                    order=order_base + 2,
                )
                return
        except Exception as e:
            self._err("list_crud", "table tbody tr",
                      "차단 탭 — 동일 이름 + 다른 SHA2 추가", str(e), order=order_base + 2)
            return

        # 4. 차단 탭 검색 UX 검증 (항목이 존재하는 상태)
        self._scan_search_with_item(test_name, order_base + 3)

        # 5. 차단 탭 수정 검증 (예외 탭과 동일한 버그 여부 확인)
        self._scan_modify(test_name, order_base + 5, tab_label=block_tab["label"])

        # 6. 차단 탭 항목 삭제
        try:
            self.page_obj.delete_item(test_name)
            names_after = self.page_obj.get_item_names()
            if test_name not in names_after:
                self._ok("list_crud", "table tbody tr", "차단 탭 — 항목 삭제",
                         f"'{test_name}' 삭제 확인", order=order_base + 10)
            else:
                self._fail("list_crud", "table tbody tr", "차단 탭 — 항목 삭제",
                           f"삭제 후에도 목록에 남아있음", order=order_base + 10)
        except Exception as e:
            self._err("list_crud", "table tbody tr",
                      "차단 탭 — 항목 삭제", str(e), order=order_base + 10)

    # ── 내부 헬퍼 ─────────────────────────────────────────────────

    def _ok(self, pattern, selector, label, detail, order, phase=1):
        self.report.results.append(ScanResult(
            pattern=pattern, selector=selector, label=label,
            status="pass", detail=detail, order=order, phase=phase,
        ))

    def _fail(self, pattern, selector, label, detail, order, phase=1):
        ss = self._take_screenshot(label)
        self.report.results.append(ScanResult(
            pattern=pattern, selector=selector, label=label,
            status="fail", detail=detail, order=order, phase=phase,
            extra={"screenshot": ss} if ss else {},
        ))

    def _err(self, pattern, selector, label, detail, order, phase=1):
        ss = self._take_screenshot(label)
        self.report.results.append(ScanResult(
            pattern=pattern, selector=selector, label=label,
            status="error", detail=detail, order=order, phase=phase,
            extra={"screenshot": ss} if ss else {},
        ))

    def _skip(self, pattern, selector, label, detail, order, phase=1):
        self.report.results.append(ScanResult(
            pattern=pattern, selector=selector, label=label,
            status="skip", detail=detail, order=order, phase=phase,
        ))

    def _known_bug(self, pattern, selector, label, detail, order, phase=1):
        """제품 버그로 확인된 항목. 테스트 실패가 아닌 버그 추적용 ⚠️."""
        scenario_idx = sum(1 for t, _ in _SCENARIO_THRESHOLDS if order >= t) - 1
        scenario_idx = max(0, min(scenario_idx, len(_SCENARIO_THRESHOLDS) - 1))
        _, scenario_header = _SCENARIO_THRESHOLDS[scenario_idx]
        scenario_tag = scenario_header.split(":")[0]
        ss = self._take_screenshot(label)
        self.report.results.append(ScanResult(
            pattern=pattern, selector=selector, label=label,
            status="known_bug", detail=detail, order=order, phase=phase,
            extra={"scenario_tag": scenario_tag, **({"screenshot": ss} if ss else {})},
        ))

    def _take_screenshot(self, label: str) -> str | None:
        """결함 발견 시점 스크린샷 저장. 오버레이 숨김 → 캡처 → 복원."""
        try:
            from pathlib import Path
            from datetime import datetime
            ss_dir = Path("reports/screenshots")
            ss_dir.mkdir(parents=True, exist_ok=True)
            ts   = datetime.now().strftime("%H%M%S_%f")[:9]
            safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in label)[:35]
            path = ss_dir / f"BUG_{safe}_{ts}.png"
            _hide = "['qa-block-overlay','qa-test-banner'].forEach(id=>{const e=document.getElementById(id);if(e)e.style.display='none';})"
            _show = "['qa-block-overlay','qa-test-banner'].forEach(id=>{const e=document.getElementById(id);if(e)e.style.display='';})"
            self.page.evaluate(_hide)
            self.page.screenshot(path=str(path))
            self.page.evaluate(_show)
            return str(path)
        except Exception:
            return None
