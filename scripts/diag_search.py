"""정책 갱신주기 관련 카드 시나리오별 검색."""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")

d = json.loads(open(
    r"C:/Users/D.K.Kim/cl/inno_test_tool/reports/RansomCruncher/last_report.json",
    encoding="utf-8"
).read())

for pg in d["pages"]:
    if pg["page_id"] != "ransom_detect_policy":
        continue
    related = [
        r for r in pg["results"]
        if "isPolicyUpdate" in (r.get("selector") or "")
        or "policyUpdate" in (r.get("selector") or "")
        or "정책 갱신" in (r.get("label") or "")
        or "주기" in (r.get("label") or "")
    ]
    print(f"정책 갱신주기 관련 카드: {len(related)}건")
    for r in related:
        sc = r.get("scenario", "?")
        st = r["status"]
        pat = r["pattern"]
        lab = (r.get("label") or "?")[:60]
        print(f"  [시나리오 {sc}] [{st:5}] {pat:20} - {lab}")
