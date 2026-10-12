# Gold fixture correction (v1 -> v1.1), made BEFORE any result existed

`gold.json` (sha256 314e06ff...) failed the scorer contract: no-safe-answer case Q17
("Which sound hire company did we use before Brightwell?") graded the eligible
`ss-brightwell` as 2. The scorer forbids eligible grade>=2 items in a no-safe-answer
case. The author's stated intent (brief.md) is that the memory is supporting context
for "no earlier supplier on record", so it is regraded 1 (topical context). No other
change. `gold.json` is kept unmodified; measurements use `gold-v1.1.json`.
