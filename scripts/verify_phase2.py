"""Phase 2 (ui_scanner._scan_diff_yaml_dom) import + 메서드 검증."""
import sys
sys.path.insert(0, r"C:\Users\D.K.Kim\cl\inno_test_tool")

import core.ui_scanner
import core.scan_diff

from core.ui_scanner import UIScanner

print("[OK] imports successful")
print(f"  UIScanner._scan_diff_yaml_dom: {hasattr(UIScanner, '_scan_diff_yaml_dom')}")
print(f"  scan_diff.extract_yaml_selectors: {hasattr(core.scan_diff, 'extract_yaml_selectors')}")
print(f"  scan_diff.extract_dom_selectors:  {hasattr(core.scan_diff, 'extract_dom_selectors')}")
print(f"  scan_diff.compare:                {hasattr(core.scan_diff, 'compare')}")
