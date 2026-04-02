"""
pages/registry.py — page_id → PageClass 매핑 + 모듈 그룹

새 페이지 추가 시:
  1. PAGE_REGISTRY 에 page_id → PageClass 한 줄 추가
  2. 해당 제품 MODULE_GROUPS 리스트에 page_id 추가

page_id는 config/scan_hints/{page_id}.yaml 파일명과 일치해야 한다.

실행 예시:
  pytest tests/test_scan_pages.py                      # 전체
  pytest tests/test_scan_pages.py -m ransom_cruncher   # RansomCruncher만
"""
from pages.ransom_detect_policy_page import RansomDetectPolicyPage
from pages.rdp_policy_page           import RdpPolicyPage
from pages.common_process_page       import CommonProcessPage

PAGE_REGISTRY: dict[str, type] = {
    "ransom_detect_policy": RansomDetectPolicyPage,
    "rdp_policy":           RdpPolicyPage,
    "common_process":       CommonProcessPage,
}

# 제품/모듈별 그룹 — pytest -m {module} 으로 선택 실행
MODULE_GROUPS: dict[str, list[str]] = {
    "ransom_cruncher": [
        "ransom_detect_policy",
        "rdp_policy",
        "common_process",
    ],
}
