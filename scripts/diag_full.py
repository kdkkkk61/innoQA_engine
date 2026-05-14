"""전체 시나리오 카운트 진단."""
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
    print(f"\n전체 결과: {len(results)}건")

    # 시나리오별 카운트
    sc_counter = Counter(r.get("extra", {}).get("scenario") for r in results)
    print("\n[시나리오별 카운트]")
    for sc, n in sorted(sc_counter.items(), key=lambda x: (x[0] is None, x[0] or 0)):
        print(f"  시나리오 {sc}: {n}건")

    # status별
    st_counter = Counter(r["status"] for r in results)
    print("\n[status별]")
    for s, n in sorted(st_counter.items()):
        print(f"  {s}: {n}건")

    # phase별
    ph_counter = Counter(r["phase"] for r in results)
    print("\n[phase별]")
    for p, n in sorted(ph_counter.items()):
        print(f"  phase {p}: {n}건")

    # 시나리오 3/4/5 샘플
    for sc in (3, 4, 5):
        items = [r for r in results if r.get("extra", {}).get("scenario") == sc]
        print(f"\n[시나리오 {sc} 샘플 (최대 5개)]: 총 {len(items)}건")
        for r in items[:5]:
            print(f"  [{r['status']}] {r['pattern']:20} - {r.get('label','?')[:60]}")
