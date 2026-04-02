"""
tests/test_scan_pages.py — 범용 페이지 스캔 테스트

새 페이지 추가 시 이 파일은 수정하지 않는다.
아래 2단계만 수행하면 자동으로 테스트에 포함된다:
  1. config/scan_hints/{page_id}.yaml 작성  (scan_mode 명시)
  2. pages/{page_id}_page.py 작성 + pages/registry.py 에 1줄 추가

scan_mode별 실행 흐름:
  modal_form (기본) → run_3phase_scan (Phase 1/2/3)
  list_page         → run_list_page_scan (탭/검색/버튼/테이블/모달/CRUD)

실행:
  pytest tests/test_scan_pages.py -v -s                      # 전체 등록 페이지
  pytest tests/test_scan_pages.py -v -s -m ransom_cruncher   # RansomCruncher만
  pytest tests/test_scan_pages.py -v -s -k common_process    # 특정 페이지
"""
import pytest
from core.qa_runner import run_scan
from pages.registry import PAGE_REGISTRY, MODULE_GROUPS


def _make_params() -> list:
    """page_id 목록을 모듈 마커와 함께 pytest.param으로 생성."""
    # page_id → 소속 모듈 역색인
    page_module: dict[str, str] = {}
    for module, pages in MODULE_GROUPS.items():
        for pid in pages:
            page_module[pid] = module

    return [
        pytest.param(
            pid,
            marks=getattr(pytest.mark, page_module.get(pid, "unclassified")),
        )
        for pid in PAGE_REGISTRY
    ]


@pytest.mark.ui_scan
@pytest.mark.parametrize("page_id", _make_params())
def test_page_scan(logged_in_page, settings, request, page_id):
    """범용 스캔 테스트. scan_mode에 따라 자동으로 적절한 스캐너 실행."""
    combined = run_scan(logged_in_page, settings, page_id)
    request.node._scan_report = combined

    assert not combined.failed, (
        f"[{page_id}] UI 패턴 검사 실패 {len(combined.failed)}건:\n"
        + "\n".join(
            f"  [Phase {r.phase}][{r.pattern}] {r.label}: {r.detail}"
            for r in combined.failed
        )
    )
