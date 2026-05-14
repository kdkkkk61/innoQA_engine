"""nPouch 제어 스위트 테스트 — 시나리오별 분리.

순서 (pytest 알파벳 자동):
  test_scenario1_ui.py        — 1a/1b/1c (UI 진입, 세션 시작점)
  test_scenario2_input.py     — 2a~2f   (입력 구조 + 필드 동작)
  test_scenario3_action.py    — 3b~3e   (ADD 모달 검증)
  test_scenario4_modify.py    — 4b~4g   (EDIT 모달 검증)
  test_scenario5_lifecycle.py — 5a~5c   (한 정책 lifecycle)
  test_zz_cleanup.py          — 최종 정리

공유 인프라:
  _base.py — ControlSuiteBase: _setup fixture, _add, _emit_pass, _attach, _finish 등.
"""
