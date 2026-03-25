"""
tests/test_scan_pages.py — 범용 페이지 스캔 테스트

새 페이지 추가 시 이 파일은 수정하지 않는다.
아래 3단계만 수행하면 자동으로 테스트에 포함된다:
  1. config/scan_hints/{page_id}.yaml 작성
  2. pages/{page_id}_page.py 작성
     - AUTO_NAME_PREFIX 상수 정의 (maxlength 제약 있는 페이지)
     - save_policy(name) 구현
     - close_edit_modal() 구현
     - get_verify_values(saved_name) 구현
  3. pages/registry.py 에 page_id → PageClass 한 줄 추가

실행:
  pytest tests/test_scan_pages.py -v -s                 # 전체 등록 페이지
  pytest tests/test_scan_pages.py -v -s -k ransom       # ransom_detect_policy
  pytest tests/test_scan_pages.py -v -s -k rdp_policy   # rdp_policy
"""
import pytest
from core.qa_runner import run_3phase_scan
from pages.registry import PAGE_REGISTRY


@pytest.mark.ui_scan
@pytest.mark.parametrize("page_id", list(PAGE_REGISTRY.keys()))
def test_page_scan(logged_in_page, settings, request, page_id):
    """범용 3-Phase 스캔 테스트. page_id별로 parametrize 실행."""
    combined = run_3phase_scan(logged_in_page, settings, page_id)
    request.node._scan_report = combined

    assert not combined.failed, (
        f"[{page_id}] UI 패턴 검사 실패 {len(combined.failed)}건:\n"
        + "\n".join(
            f"  [Phase {r.phase}][{r.pattern}] {r.label}: {r.detail}"
            for r in combined.failed
        )
    )
