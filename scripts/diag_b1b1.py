"""B-1-B-1 진단 — 시나리오 1 + 시나리오 2 자동 분류 카드 확인."""
import json, sys
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")

d = json.loads(open(
    r"C:/Users/D.K.Kim/cl/inno_test_tool/reports/RansomCruncher/last_report.json",
    encoding="utf-8"
).read())

print("generated_at:", d["generated_at"])

for pg in d["pages"]:
    if pg["page_id"] != "ransom_detect_policy":
        continue

    results = pg.get("results", [])

    # discovered_* (시나리오 1)
    sc1 = [r for r in results if r["pattern"].startswith("discovered_")]
    print(f"\n[시나리오 1] discovered_*: {len(sc1)}")
    for r in sc1:
        print(f"  {r.get('label','?')}")

    # 자동 분류 카드 (detail에 "[자동 분류" 있는 것)
    auto = [r for r in results if "[자동 분류" in r.get("detail", "")]
    print(f"\n[자동 분류 카드 — 시나리오 2]: {len(auto)}")
    for r in auto:
        st  = r["status"]
        pat = r["pattern"]
        lab = r.get("label", "?")[:50]
        print(f"  [{st}] {pat} - {lab}")
        # detail 첫 100자
        d_ = r.get("detail", "")[:100].replace("\n", " ")
        print(f"      > {d_}")
