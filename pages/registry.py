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
from pages.ransom_detect_policy_page          import RansomDetectPolicyPage
from pages.rdp_policy_page                    import RdpPolicyPage
from pages.common_process_page                import CommonProcessPage
from pages.npouch_operation_process_page      import NpouchOperationProcessPage
from pages.npouch_tag_page                    import NpouchTagPage
from pages.npouch_control_suite_page          import NpouchControlSuitePage
from pages.npouch_origin_protect_policy_page  import NpouchOriginProtectPolicyPage
from pages.npouch_policy_page                 import NpouchPolicyPage
from pages.secure_zone_access_control_policy_page import SecureZoneAccessControlPolicyPage
from pages.secure_zone_agent_policy_page          import SecureZoneAgentPolicyPage

PAGE_REGISTRY: dict[str, type] = {
    "ransom_detect_policy":       RansomDetectPolicyPage,
    "rdp_policy":                 RdpPolicyPage,
    "common_process":             CommonProcessPage,
    "npouch_operation_process":   NpouchOperationProcessPage,
    "npouch_tag":                 NpouchTagPage,
    "npouch_control_suite":       NpouchControlSuitePage,
    "npouch_origin_protect":      NpouchOriginProtectPolicyPage,
    "npouch_policy":              NpouchPolicyPage,
    "secure_zone_access_control": SecureZoneAccessControlPolicyPage,
    "secure_zone_agent_policy":   SecureZoneAgentPolicyPage,
}

# 제품/모듈별 그룹 — pytest -m {module} 으로 선택 실행
MODULE_GROUPS: dict[str, list[str]] = {
    "ransom_cruncher": [
        "ransom_detect_policy",
        "rdp_policy",
        "common_process",
    ],
    "npouch": [
        "npouch_operation_process",  # 1. 운용 프로세스 (의존성 없음)
        "npouch_tag",                # 2. 태그 관리 (의존성 없음)
        "npouch_control_suite",      # 3. 제어 스위트 (운용 프로세스 참조)
        "npouch_origin_protect",     # 4. 원본보호 정책 (제어 스위트 참조)
        "npouch_policy",             # 5. 엔파우치 정책 (원본보호 정책 참조)
    ],
    "secure_zone": [
        "secure_zone_access_control",  # 1. 접근제어 정책 (독립 — 템플릿 의존 없음)
        "secure_zone_agent_policy",    # 2. 시큐어존 정책 (템플릿/제어스위트 참조 — 기존 선택)
    ],
}
