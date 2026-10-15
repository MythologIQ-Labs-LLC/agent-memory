import json,sys
names=sys.argv[1:]
runs=[json.load(open(n)) for n in names]
def cell(r):
    ret=r["returned"]
    s=("P " if r["pass"] else "- ")+f"{r['needed_returned']}/{r['needed']} x{r['extra']}"
    return s
print("| id | kind | query | "+" | ".join(n.replace('runs-gen-','').replace('.json','') for n in names)+" | C6 returned (route) |")
print("|"+"---|"*(4+len(names)))
for i,r in enumerate(runs[0]):
    c6=r
    ret=", ".join(f"{x}({'s' if any('vector' in z or 'semantic' in z for z in (r['returned_routes'].get(x) or [])) else 'l'})" for x in r["returned"])
    print(f"| {r['id']} | {r['kind']} | {r['query']} | "+" | ".join(cell(run[i]) for run in runs)+f" | {ret} |")
