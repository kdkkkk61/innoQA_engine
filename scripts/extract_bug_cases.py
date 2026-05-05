"""최근 리포트 last_report.json에서 BUG/WARN/FAIL/ERROR 케이스 추출."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPORTS = [
    Path(r"C:\Users\D.K.Kim\cl\inno_test_tool\reports\RansomCruncher\last_report.json"),
    Path(r"C:\Users\D.K.Kim\cl\inno_test_tool\reports\nPouch\last_report.json"),
]

for path in REPORTS:
    print(f"\n{'='*70}\n{path.parent.name}\n{'='*70}")
    if not path.exists():
        print("  (없음)")
        continue
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        print(f"generated_at: {data.get('generated_at')}")
        for pg in data.get("pages", []):
            bugs = [
                r for r in pg.get("results", [])
                if r["status"] in ("fail", "warn", "known_bug", "error")
            ]
            print(f"\n[{pg['page_id']}] {pg['label']} — {len(bugs)}건")
            for r in bugs:
                ss = " [SS]" if r.get("screenshot") else " [no SS]"
                print(f"  [{r['status']:5}]{ss} {r['pattern']:25} | {r['label']}")
                detail = r["detail"][:120].replace("\n", " ")
                print(f"             > {detail}")
    except Exception as e:
        print(f"  ERROR: {e}")
