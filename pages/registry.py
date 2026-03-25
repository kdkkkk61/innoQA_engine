"""
pages/registry.py — page_id → PageClass 매핑

새 페이지 추가 시 이 파일에 1줄만 추가:
    "new_page_id": NewPageClass,

page_id는 config/scan_hints/{page_id}.yaml 파일명과 일치해야 한다.
"""
from pages.ransom_detect_policy_page import RansomDetectPolicyPage
from pages.rdp_policy_page            import RdpPolicyPage

PAGE_REGISTRY: dict[str, type] = {
    "ransom_detect_policy": RansomDetectPolicyPage,
    "rdp_policy":           RdpPolicyPage,
}
