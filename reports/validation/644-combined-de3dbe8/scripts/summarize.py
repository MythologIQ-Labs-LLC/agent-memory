import json, sys, os
d = sys.argv[1]
trees = ["v6f", "e002536", "de3dbe8", "46d84ad"]
def g(r, sec, k):
    v = (r.get(sec) or {}).get(k)
    return "—" if not v else f"{v['median_ms']:.2f} / {v['p95_ms']:.2f}"
for n in (1000, 3000, 10000):
    print(f"\n### {n:,} facts (median / p95 ms)\n")
    rows = [("warm", "recall", "governed recall (includes receipt capture where present)"),
            ("warm", "receipt_capture", "receipt capture alone"),
            ("warm", "receipt_verify", "receipt verification (observation_unchanged)"),
            ("warm", "audit_indexed", "slot audit (e002536: full-store scan)"),
            ("warm", "observer_combined", "combined observer (coverage + audit [+ receipt check])"),
            ("warm", "audit_full_scan_reference", "reference: full-store enumeration, same per-fact work"),
            ("warm", "index_rebuild", "index rebuild (warm process)"),
            ("cold", "open", "cold open"), ("cold", "first_recall", "cold first recall"),
            ("cold", "first_index_build", "cold first index build"), ("cold", "first_audit", "cold first audit"),
            ("cold", "first_observer", "cold first observer")]
    res = {t: json.load(open(f"{d}/m_{t}_{n}.json")) for t in trees if os.path.exists(f"{d}/m_{t}_{n}.json")}
    print("| measure | " + " | ".join(res) + " |"); print("|---|" + "---|" * len(res))
    for sec, k, label in rows:
        print(f"| {label} | " + " | ".join(g(r, sec, k) for r in res.values()) + " |")
    print("samples: warm " + ", ".join(f"{t}={(r['warm']['recall'] or {}).get('n')}" for t, r in res.items())
          + "; cold " + ", ".join(f"{t}={(r['cold']['open'] or {}).get('n')}" for t, r in res.items())
          + "; admitted/candidates " + ", ".join(f"{t}={r.get('admitted')}/{r.get('candidates')}" for t, r in res.items()))
