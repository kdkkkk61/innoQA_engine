"""B-1-A 진단 — discovered_new 누락 + 스크린샷 누락 원인."""
import json, sys
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
    new_items     = [r for r in results if r["pattern"] == "discovered_new"]
    missing_items = [r for r in results if r["pattern"] == "discovered_missing"]
    print(f"\ndiscovered_new     : {len(new_items)}")
    for r in new_items[:5]:
        print(" ", r.get("label", "?"))
    print(f"discovered_missing : {len(missing_items)}")

    # 스크린샷 카운트
    ss_count = sum(1 for r in results if r.get("screenshot"))
    no_ss_warn = [r for r in results
                  if r["status"] in ("fail", "warn") and not r.get("screenshot")]
    print(f"\nscreenshot 가진 항목: {ss_count}")
    print(f"fail/warn 인데 screenshot 없는 항목: {len(no_ss_warn)}")
    for r in no_ss_warn[:8]:
        st  = r["status"]
        pat = r["pattern"]
        lab = r.get("label", "?")[:60]
        print(f"  [{st}] {pat} - {lab}")

    # 모든 pattern 카운트
    print("\n모든 pattern 카운트:")
    from collections import Counter
    c = Counter(r["pattern"] for r in results)
    for p, n in sorted(c.items()):
        print(f"  {p}: {n}")
