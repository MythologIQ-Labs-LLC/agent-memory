# Vineyard blind corpus (kestrel-ridge-vineyard / harvest-2026)

This is an independent corpus in a new domain, a vineyard during harvest, for the served-memory-lifecycle-v3 predecessor and successor evaluation. It has 18 memories, 38 events (37 retrievable plus 1 delete) and 25 queries.

## Memories
| Memory | Versions | Notes |
|---|---|---|
| press-house | 5 | Old Barn, Millbrook, Lower Terrace, Winery Hall, North Gate mobile press |
| bottling-contractor | 4 | Vinline, Cork and Crown, Glassworth, Ridgeway |
| harvest-manager | 4 events | Marta, Owen Pryce (update), Owen Price (correct: Pryce was never true), Lena Kovac |
| picker-wage | 3 | 14, 16, then a drop to 15 |
| harvest-start | 3 | 7 Sep, 14 Sep, 11 Sep |
| barrel-supplier, tasting-room-hours, tank-7-north | 2 each | |
| consultant-fee | 2, then deleted | prohibited |
| rose-trial-press-house | 2, other project | Worded like press-house and shares Old Barn and Lower Terrace, so it is a trap. Prohibited. |
| hollowbrook-bottling-contractor | 1, other tenant | Worded like bottling and names Vinline. Prohibited. |
| tank-7-south | 1 | Near-duplicate of tank-7-north |
| must-lab, copper-spray-policy | 1 each | Never changed |
| bottling-switch-rationale, picker-wage-rationale, mobile-press-rationale | 1 each | Rationale memories |
| hilltop-hail-incident | 1 | One-off event |

## Queries
- There are 16 predecessor questions (Q01-Q16).
  - 6 ask about the latest value.
  - 5 ask about an older named value (Q05, Q06, Q07, Q09, Q10).
  - 5 have no safe answer: deleted (Q12), other project (Q13), never changed (Q14, Q16), and other tenant plus never changed (Q15).
- The rest are 1 origin question (Q17), 3 why questions (Q18, Q19, Q25), 3 current questions (Q20, Q21, Q24; Q21 contains "before" in a non-predecessor sense), 1 timeless question (Q22, also contains "before") and 1 one-off event question (Q23).

## Gold conventions
- `relevance` grades every non-delete event id. Prohibited items (cf-600, cf-750, rt-old-barn, rt-lower-terrace, hb-vinline) are graded 0 everywhere. The delete event cf-delete is not a retrievable item, so it is not in `relevance` or `prohibited`.
- Within `critical_groups`, ids in one inner list are alternatives. For example, in Q03 `hm-lena` also states that Owen Price was the previous manager, and in Q09 `hm-owen-price` also states that Marta Silva was replaced.
- `stale` for current-intent cases lists every superseded visible id across all memories. The mistaken `hm-owen-pryce` is included.
- In cases with no safe answer, no eligible item has a grade of 2 or higher. Never-changed memories are graded 1, as context only.
- In `successor-annotations.json`, successor is the event id stating the later value. For a value fixed by a correction (Owen Price), it is the `correct` event.
