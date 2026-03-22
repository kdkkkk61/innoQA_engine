"""
tests/conftest.py — ui_scan 전용 fixtures & hooks

루트 conftest.py는 수정하지 않는다.
이 파일은 tests/ 디렉터리 스코프에서만 동작한다.

[버그 수정 이력]
  QA AI 원본 버그 ①: autouse=True fixture가 logged_in_page를 직접 인자로 받음
    → test_login.py 실행 시 logged_in_page(session fixture)가 강제 생성됨
    → 로그인 이중 실행 + 서버 단일세션 충돌 위험
  수정: 마커 확인 후 request.getfixturevalue()로 조건부 요청

  QA AI 원본 버그 ②: pytest_configure에서 ui_scan 마커 등록
    → 루트 conftest.py의 pytest_configure와 이름 충돌 위험
  수정: 루트에 이미 의존성 마커가 등록되므로 ui_scan 마커만 별도 등록
"""

import pytest
from pages.ransom_detect_policy_page import RansomDetectPolicyPage


def pytest_configure(config):
    """ui_scan 마커 등록 — 루트 conftest.py의 dependency 마커와 별개."""
    config.addinivalue_line(
        "markers",
        "ui_scan: UI 패턴 자동 스캔 테스트 (UIScanner 기반, 새 페이지 검증용)",
    )


@pytest.fixture(autouse=True)
def restore_after_scan(request):
    """
    ui_scan 마커 테스트 후 모달 닫기 + pageSize 복원.

    autouse=True 이지만 ui_scan 마커가 없으면 즉시 yield하고 반환.
    → test_login.py 등 다른 테스트에 영향 없음.

    logged_in_page 는 ui_scan 마커가 확인된 후에만 getfixturevalue()로 요청.
    → login 테스트 실행 시 session-scope logged_in_page 강제 생성 방지.
    """
    if "ui_scan" not in request.keywords:
        yield
        return

    # ui_scan 테스트만 여기 도달
    # getfixturevalue()는 이미 생성된 fixture를 재사용하므로 추가 비용 없음
    logged_in_page = request.getfixturevalue("logged_in_page")
    settings       = request.getfixturevalue("settings")

    yield

    # teardown — crash가 나도 복원 시도
    # navigate_to() 내부에서 모달 닫기 + pageSize 복원을 모두 처리한다
    try:
        page_obj = RansomDetectPolicyPage(logged_in_page, settings)
        page_obj.navigate_to()
    except Exception:
        pass


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    ui_scan 테스트 전용 후처리.
    루트 conftest.py의 스크린샷 훅은 그대로 동작하며 이 훅과 별개로 실행된다.

    scan 결과(PageScanReport)를 item에 저장해 나중에 리포트 생성에 활용한다.
    실패 시 fail 상세 목록을 item._scan_failures에 보관.
    """
    if "ui_scan" not in item.keywords:
        yield
        return

    outcome = yield
    report  = outcome.get_result()

    if call.when == "call":
        scan_report = getattr(item, "_scan_report", None)
        if scan_report:
            item._scan_summary  = scan_report.summary()
            if report.failed:
                item._scan_failures = [
                    f"  [{r.pattern}] {r.label}: {r.detail}"
                    for r in scan_report.failed
                ]
