"""
pages/shared/_overlay.py — qa-block-overlay 토글 헬퍼

설계 의도:
  - overlay (id='qa-block-overlay') 는 conftest 가 모든 페이지에 inject
  - 목적: 자동화 테스트 중 사람의 마우스 입력을 차단 (실수 방지)
  - 자동화 클릭 시점에는 잠깐 OFF → 클릭 완료 → 즉시 ON 복원
  - 좌표 hit-testing 정상 통과 → AngularJS mousedown/click 핸들러 정상 동작

사용:
    with overlay_off(self.page):
        self.page.locator(SEL).first.click()
"""
from contextlib import contextmanager


@contextmanager
def overlay_off(page):
    """클릭 동안 overlay 의 pointer-events 를 'none' 으로, 끝나면 'all' 로 복원."""
    page.evaluate(
        "var el = document.getElementById('qa-block-overlay');"
        "if (el) el.style.pointerEvents = 'none';"
    )
    try:
        yield
    finally:
        page.evaluate(
            "var el = document.getElementById('qa-block-overlay');"
            "if (el) el.style.pointerEvents = 'all';"
        )
