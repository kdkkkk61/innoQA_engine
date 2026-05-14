"""scan_diff.py 단위 검증 (개발용 — 정식 테스트 아님)."""
import sys, yaml
sys.path.insert(0, r"C:\Users\D.K.Kim\cl\inno_test_tool")
sys.stdout.reconfigure(encoding="utf-8")

from core.scan_diff import extract_yaml_selectors, compare

# 1. RDP 정책 yaml 추출
hints = yaml.safe_load(
    open(r"C:\Users\D.K.Kim\cl\inno_test_tool\config\scan_hints\rdp_policy.yaml",
         encoding="utf-8")
)
y_set = extract_yaml_selectors(hints)
print(f"[yaml] RDP 정책 추출: {len(y_set)}개")
for s in sorted(list(y_set))[:10]:
    print(f"  {s}")
if len(y_set) > 10:
    print(f"  ... (+{len(y_set) - 10})")

# 2. 랜섬 탐지 yaml 추출
hints2 = yaml.safe_load(
    open(r"C:\Users\D.K.Kim\cl\inno_test_tool\config\scan_hints\ransom_detect_policy.yaml",
         encoding="utf-8")
)
y_set2 = extract_yaml_selectors(hints2)
print(f"\n[yaml] 랜섬 탐지 추출: {len(y_set2)}개")
for s in sorted(list(y_set2))[:10]:
    print(f"  {s}")

# 3. compare mock 검증
mock_dom  = {"input#policyName", "input#newField", "input#isAllowConnect"}
mock_yaml = {"input#policyName", "input#isAllowConnect", "input#removedField"}
result = compare(mock_yaml, mock_dom)
print(f"\n[compare] mock 비교:")
print(f"  new     (DOM only)  : {result['new']}")
print(f"  missing (yaml only) : {result['missing']}")
print(f"  common              : {result['common']}")

# 4. 빈값 안전성
print(f"\n[edge cases]")
print(f"  empty dict: {len(extract_yaml_selectors({}))}개")
print(f"  None      : {len(extract_yaml_selectors(None))}개")
