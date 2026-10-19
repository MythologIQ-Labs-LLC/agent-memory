# Cross-host determinism check against the developer's committed runs

These are a reproducibility check only, not holdout evidence. The developer's reviewer set (`819-c6/review/gen.json`, 55 queries) was run through the developer's own committed harness (`819-c6/review/tools/harness.py`), unchanged, on this evaluator host:
- Python 3.12.3, onnxruntime 1.30.0, tokenizers 0.23.2, numpy 2.4.6;
- model config digest `sha256:74477054…`.

The results were compared with the developer's committed outputs, produced under Python 3.13.16.

| Run here | Developer output compared | Returned lists identical | Max abs cosine difference (3 dp as recorded) |
| --- | --- | ---: | ---: |
| `here-c6-required.json` (C6 `171e67db`, route on) | `review/after-fixes/c6fix-gen-required.json` | 55/55 | 0 |
| `here-c4-required.json` (C4 `bc2be631`, route on) | `review/outputs/runs-gen-c4-required.json` | 55/55 | 0 |
| `here-c4-off.json` (C4, route off) | `review/outputs/runs-gen-c4-off.json` | 55/55 | 0 |

The aggregates reproduce exactly:

| Run | Strict | Needed recall | Extras |
| --- | ---: | ---: | ---: |
| C6+sem | 16 | 0.500 | 61 |
| C4+sem | 6 | 0.655 | 120 |
| C4-off | 11 | 0.276 | 53 |
