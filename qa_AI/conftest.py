"""
tests/conftest.py

scan 전용 fixtures & hooks.
루트 conftest.py는 수정하지 않음.
ui_scan 마커가 붙은 테스트에만 적용됨.
"""

import pytest
from pages.ransom_detect_policy_page import RansomDetectPolicyPage


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "ui_scan: UI 패턴 자동 스캔 테스트 (scanner 기반, 새 페이지 검증용)",
    )


@pytest.fixture(autouse=True)
def restore_after_scan(request, logged_in_page, settings):
    """
    ui_scan 마커 테스트 후 pageSize 복원 + 모달 닫기.
    validator 내부에서 restore를 직접 호출하지 않아도 됨.
    """
    if "ui_scan" not in request.keywords:
        yield
        return

    yield

    # teardown — crash가 나도 복원 시도
    try:
        page_obj = RansomDetectPolicyPage(logged_in_page, settings)
        page_obj.navigate_to()   # 모달 닫기 + pageSize 복원 포함
    except Exception:
        pass


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    ui_scan 테스트 전용 후처리.
    루트 conftest의 스크린샷 훅과 중복 실행되지 않도록 scan 전용 로직만 담당.
    """
    if "ui_scan" not in item.keywords:
        yield
        return

    outcome = yield
    report  = outcome.get_result()

    # scan 결과를 item에 저장 (나중에 xlsx 리포트 등에서 활용 가능)
    if call.when == "call":
        scan_report = getattr(item, "_scan_report", None)
        if scan_report and report.failed:
            # 실패 시 scan 결과 상세를 longrepr에 추가
            summary = scan_report.summary()
            failed_details = [
                f"  [{r.pattern}] {r.label}: {r.detail}"
                for r in scan_report.failed
            ]
            item._scan_summary = summary
            item._scan_failures = failed_details
