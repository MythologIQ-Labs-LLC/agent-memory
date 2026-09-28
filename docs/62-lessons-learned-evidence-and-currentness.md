# Lessons Learned: Evidence Discipline and the Temporal/Currentness Arc

Status: retrospective. This document records what the work from #538 through #550 taught us about building and qualifying temporal/currentness behavior in Agent Memory. It sets no doctrine: ADR-039 remains **Proposed**. It complements [`SHADOW_GENOME.md`](SHADOW_GENOME.md), which logs individual rejected approaches. This document collects the cross-cutting lessons: the habits that kept the evidence honest, and the places where evidence overturned what we expected.

Scope: the query-conditioned ranking work (#538, docs/57), deterministic BM25 (#576), historical admission (#549, docs/58), the repository-owned temporal/currentness gauntlet (#580, docs/60), dispute durability (#582), the temporal-cue relevance separation that was held (#583, PR #587), and write-time proposition semantics (#550, docs/61, draft at the time of writing).

## 1. Freeze the gold before anything can be fitted to it

**What we did.** The #580 gold corpus was committed before an evaluator existed and before it had run against any runtime. Its digest is pinned by a test, and no expected outcome has been edited since. Later changes touched only evaluator mechanics.

**Why it mattered.** Every later result could be read against a fixed target. When #550's first design turned seven target units from `honest_unknown` to `fail`, the frozen gold, not a convenient reinterpretation, forced a design change (§5).

**Practice.** Commit gold first and pin its digest. Never change an expected outcome to match a runtime. If gold is wrong, say so in a separate, reviewed change with its own justification.

## 2. Keep required, target, and ambiguous separate; never aggregate

**What we did.** Each assertion has a level. *Required* means doctrine or ruling. *Target* means desirable but not required. *Ambiguous* is recorded and never scored. Metrics are reported per dimension, with no aggregate "memory score".

**Why it mattered.** An aggregate would have hidden the one thing that mattered in several slices: a required regression masked by target gains, or the reverse. The monotonic guard (a previously passing required unit may never regress) is only expressible because the levels stay separate.

## 3. "Honest unknown" is not a pass, and an incidental pass is not a capability

**What we did.** A missed target where every memory involved has an unknown temporal basis is scored `honest_unknown`, separately from `pass`. A target ordering that holds while neither memory has an affirmed basis is flagged as an **incidental** pass: relevance happened to order it.

**Why it mattered.** All seven target passes in the pre-#550 baseline were incidental. Without that flag the baseline would have looked partially capable when it had no temporal knowledge in those cases. After #550, two of those orderings hold for the intended temporal reason and leave the incidental list. That is progress a pass count alone cannot show.

## 4. Synthetic falsification and natural data can disagree; run both before merging

**What happened (#583).** The gauntlet found a real defect (F30): a query's own temporal cue (`currently`) was counted as lexical relevance, so a memory repeating the cue gained rank. PR #587 removed consumed intent cues from the relevance query. Repository CI and the gauntlet were green, and AgentMemBench agreed. LongMemEval_S did not: turn-plane retrieval and latest-gold-first regressed.

**Why.** On natural first-person data the removed words are frequently memory *content*: "I'm **currently** devouring…", "I'm actually **planning to** stay on Oahu", "started **going to** the gym". Lexical overlap on those words was the only thing carrying a memory's own temporal self-description. Removing the proxy before a typed replacement existed cost real currentness.

**Lessons.**
* A green internal gauntlet is necessary, not sufficient. External replay against frozen corpora is a real gate, and a failure there is a valid outcome, not an obstacle.
* Classify every changed row by cause (intended effect, numerical, unrelated drift, governance change, unexplained) rather than reading headline deltas. Every #583 change was *intended*, and that is exactly what exposed the flawed premise.
* Replace an accidental signal with a typed one before removing it. The ruling reordered the work: #550 now precedes #583.

## 5. Interpretation may limit itself; it may not promote itself

**What happened (#550).** The first design let an interpreted self-validity window ("for the next two weeks", "starting next month") both demote and **affirm** a memory's applicability. Against the frozen gauntlet this converted seven target units from `honest_unknown` to `fail` without changing any order. The self-describing memory became affirmed while its rival stayed unknown-basis, so relevance still decided, and the miss was merely exposed.

**Resolution.** Interpreted windows may only **limit** a memory's own applicability ("after two weeks, I no longer apply"; "not until next month"). They never affirm it. A memory's text may always make a weaker claim about itself. Affirming its own currentness is the self-promotion class the gauntlet's adversarial case forbids. The asymmetry kept only true improvements (four target units) and no regressions.

**Lesson.** When a mechanism flips "unknown" into "fail", ask whether it created knowledge or only exposed ignorance on one side. Asymmetric authority (self-limiting yes, self-promoting no) is often the principled line.

## 6. Prove the forbidden automation is forbidden with a counterfactual, not an argument

**What we did.** #550 emits governed `state_change` proposals ("moved", "no longer", "used to … now") but never applies them. An evaluation-only counterfactual played a reviewing caller who accepts every proposal through the ordinary governed correction. It showed that the proposals are right (every F23/F24/F28 target would pass) and that accepting them breaks the gold's **required** no-mutation units.

**Lesson.** The gold encodes that text alone must not mutate memory. The counterfactual makes that constraint concrete and measurable, instead of leaving it as a design opinion that could be relitigated later.

## 7. Attribute changes with enough columns

**What we did.** The #550 comparison uses three columns: the frozen baseline, current `main`, and the candidate. `main` had already fixed B9 (#582 dispute durability) after the baseline froze. A two-column comparison would have credited #550 with #582's two required fixes.

**Lesson.** When the base moves between a frozen baseline and a candidate, compare against the current base as well as the frozen one.

## 8. Determinism has to be proven across processes, and its limits stated

**What happened (#576).** BM25 summed per-term contributions in `set` iteration order, which follows `PYTHONHASHSEED`. The same revision and query could produce last-bit-different scores in different processes, and tied candidates could reorder. Sorted accumulation made the evidence identical across processes. It did **not** make every mathematically tied pair bit-equal: a deterministic 1-ulp residual remains and is pinned by a test instead of being hidden.

**Lessons.** Test determinism in fresh interpreters with different hash seeds, since one process cannot vary its own seed. State the exact guarantee, and pin known residuals so a later change to them is visible.

## 9. Durability is a property of the transition, not of later writes (#582)

The only dispute mechanism changed in-memory state. It became durable only if some later operation happened to persist governance state in the same session. #549's "disputed stays controlling" silently depended on persistence ordering. The fix made dispute a governed transition that commits its own durable state and audit evidence.

**Lesson.** A test that closes and reopens immediately after each governed transition catches this class of bug. Restart-reproduction checks belong in every qualification suite.

## 10. Evidence hygiene: small operational failures that nearly produced wrong conclusions

These were caught, but each could have produced a wrong claim.

| failure | effect | guard |
| --- | --- | --- |
| A benchmark "baseline" worktree path already existed at an old commit, and `git worktree add` into it silently did nothing | #550 appeared 5x *faster* than `main` | print `git log -1` inside every comparison worktree; name worktrees by SHA |
| A refactor moved a function call, so an evaluation mutant that monkeypatches `temporal_applicability` no longer took effect | a negative control went blind (the full suite caught it) | keep patch points stable; run the negative controls in the full suite |
| `pkill -f <pattern>` matched the shell that ran it | the command killed itself | kill by PID from an exact process listing |
| A regex written into a non-raw string (`"\b..."`) | `\b` became a backspace and never matched | always use raw strings for patterns; test the negative case |
| A list-membership test on dicts inside a loop | quadratic slowdown that looked like an algorithmic cost | profile before concluding; cheap micro-benchmarks against a clean base |
| Benchmarks run concurrently with the test suite | wall times not comparable | label concurrent timings as not comparable; take timing pairs on an idle machine |

**Practice.**
* Generate committed evidence only from a committed, clean runtime tree, and re-run external replays at the exact head proposed for merge.
* When code changes after an evidence run, regenerate the evidence rather than arguing that the change "cannot matter".

## 11. Honest limits are results

Several outcomes in this arc were "not yet": #583 held; `now` calibration (#585), unknown-basis ordering (#584), and exception precedence (#586) deferred; #550's grammar leaving most natural turns `unknown` or `ambiguous`. Recording these as results, with the evidence that produced them, kept the sequencing honest. It also stopped any single slice from being stretched into a claim the evidence did not support.

## Summary of practices

1. Freeze gold first; pin its digest; never fit it.
2. Separate required, target, and ambiguous; no aggregate score.
3. Score honest-unknown and incidental passes separately.
4. Gate on external replay with per-row cause classification.
5. Replace accidental signals with typed ones before removing them.
6. Let interpretation limit, never promote, its own authority.
7. Prove forbidden automation with a counterfactual.
8. Attribute against the current base, not only the frozen one.
9. Prove determinism across processes; pin residuals.
10. Test durability with immediate close/reopen.
11. Keep evidence provenance exact: clean tree, exact head, verified worktrees.

ADR-039 remains **Proposed**. None of these lessons changes doctrine by itself.
