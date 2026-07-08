"""행위 저널(action journal) — 전역 캡처/재생 공용 모듈 (사용자 설계 2026-07-07).

테스트가 흐름을 `_act("라벨", fn, shot_target)` 로 기술(기록만 — 캡처 0, pass 비용 0)
→ `_add` 가 warn/fail 검출 시 `_ckpt` 블록의 행위들을 자동 재실행하며 단계별
캡처(캡션=행위 라벨). 어느 행위에서 오류가 나든 동일 품질의 재현 시퀀스 —
손코딩 캡처 지점이 필요 없다. control_suite 에서 확립(커밋 747979a·dacd992) 후 공용 승격.

사용 (각 suite _base 에 mixin + _add 훅 1줄):
    class FooBase(ActionJournalMixin):
        def _add(self, status, ..., screenshots=None):
            ...(리턴재생 가드/sub-numbering 뒤)...
            screenshots = self._journal_frames_for_issue(status, screenshots)

규칙 (TROUBLESHOOTING 2026-07-07 확립):
  - 재생 전 alert 열림 스냅샷 — 본 흐름이 직접 dismiss 할 alert(서버오류 등)는 보존,
    재생이 '새로' 만든 alert(no-op 확인 등)만 정리. 본 흐름의 상태 계약 보존.
  - 프레임은 블록 자산 — 같은 블록의 모든 warn/fail 카드가 공유(재실행은 블록당 1회).
  - 공유-세션 흐름은 블록 첫 행위를 fresh 재진입/상태 리셋으로(재생 가능 조건).
  - 재생도 데이터를 만지므로 [AUTO] 데이터 한정(데이터 안전 규칙 그대로).

requires (suite _base 가 제공): self._page(playwright Page),
self._shot(label, highlight=None, caption=None) → 경로 또는 {"path","caption"}.
"""

_ALERT_OPEN = "div#__globalMessageModal.in"
_ALERT_CONFIRM = "div#__globalMessageModal.in button:has-text('확인')"


class ActionJournalMixin:
    """행위 저널 — _ckpt(블록 시작) / _act(행위 기록) / _journal_frames_for_issue(_add 훅)."""

    def _ckpt(self) -> None:
        """행위 블록 시작 — 이후 warn/fail 검출 시 여기서부터 재생. 블록당 재생 1회(프레임 공유)."""
        self._journal = []
        self._journal_replayed = False
        self._journal_frames = None

    def _act(self, label: str, fn, shot_target=None) -> None:
        """행위 실행 + 저널 기록. 1차 실행에선 캡처하지 않음(검출 시에만 재생 캡처)."""
        fn()
        if not hasattr(self, "_journal"):
            self._journal, self._journal_replayed, self._journal_frames = [], False, None
        self._journal.append((label, fn, shot_target))

    def _journal_replay(self, steps) -> list:
        """저널 행위들을 재실행하며 단계별 캡처(캡션=순번+라벨). 예외 시 그 시점 캡처 후 중단
        (끊긴 지점 = 오류 지점). suite _base 의 _shot 사용 — 자급형."""
        frames = []
        for label, action, target in steps:
            try:
                action()
                self._page.wait_for_timeout(300)
                f = self._shot(f"replay_{label}", highlight=target,
                               caption=f"{len(frames) + 1}. {label}")
                if f:
                    frames.append(f)
            except Exception as e:
                # 재생 실패 원인을 로그에 남김 — 어느 행위에서 왜 끊겼는지 진단 가능하게
                print(f"  [저널 재생 중단] 행위 {len(frames) + 1} {label!r} — {e!r}"[:400])
                f = self._shot(f"replay_{label}_예외중단",
                               caption=f"{len(frames) + 1}. {label} — 예외로 중단(오류 지점)")
                if f:
                    frames.append(f)
                break
        return frames

    def _journal_frames_for_issue(self, status: str, screenshots):
        """_add 훅 — 캡처는 '카드가 이슈(warn/fail)일 때만' 붙는다(사용자 원칙 2026-07-08).
        - pass/skip: 캡처 없음 → None (테스트가 screenshots= 를 넘겼어도 버림. pass 는 캡처 안 함).
        - warn/fail + 큐레이션(수동) 캡처 있음: 그대로 사용.
        - warn/fail + 큐레이션 없음 + 저널 블록 활성: 블록 자동 재생 프레임.
        재생은 블록당 1회, 프레임은 블록 내 카드 공유."""
        if status not in ("fail", "warn"):
            return None   # ★pass/skip 카드엔 캡처 미부착 (전역 강제)
        if screenshots or not getattr(self, "_journal", None):
            return screenshots
        if not getattr(self, "_journal_replayed", True):
            self._journal_replayed = True
            # 재생 전 alert 상태 스냅샷 — 본 흐름이 dismiss 할 alert 는 보존(닫으면
            # 본 흐름 dismiss 가 timeout — sc3j 회귀 2026-07-07).
            _alert_before = False
            try:
                _alert_before = self._page.locator(_ALERT_OPEN).count() > 0
            except Exception:
                pass
            self._journal_frames = self._journal_replay(list(self._journal))
            if not _alert_before:
                # 재생이 새로 띄운 alert 만 정리 (예: no-op 확인의 '수정된 항목이 없습니다').
                try:
                    _btn = self._page.locator(_ALERT_CONFIRM)
                    if _btn.count() > 0:
                        _btn.first.evaluate("el => el.click()")
                        self._page.wait_for_timeout(300)
                    self._page.evaluate(
                        "() => { if (!document.querySelector('.modal-wrap.in, .modal.in')) {"
                        " document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());"
                        " document.body.classList.remove('modal-open'); } }")
                except Exception:
                    pass
        _frames = getattr(self, "_journal_frames", None)
        return list(_frames) if _frames else None
