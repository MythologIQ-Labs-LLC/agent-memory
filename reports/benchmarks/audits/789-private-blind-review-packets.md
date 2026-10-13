# Private human-review packet preparation for #789

**Status:** Source-verifying packet-generation candidate stacked on draft PR #793. No human review has occurred. 0/96 locked forms. This is not an accepted competitor score, a public data release, or a substitute for independent reviewers.

## Why

The 77-case PrecisionMemBench v6 dossier and qualitative review checker already exist, but reviewers need the **original question and retrieved context**. A public committed packet would leak prompts, source facts and potential private text. We therefore prepare the 24 preregistered cases × two measured systems as **48 private, label-blinded records**, retaining the exact source SHA and mapping in a restricted coordinator-only key.

## Running it, only on an authorized local checkout

Use a private output directory **outside the repository** (existing parent directory, new nonexisting child directory):

\`\`\`sh
python scripts/prepare_789_blind_review_packets.py \
  --output-dir /private/secure-review/study-001 \
  --accept-private-material
\`\`\`

The command verifies all 77 case IDs, both source reports' Git blob IDs, profile, native correct counts, aligned query/gold arrays, exact dossier source/native verdict match, and locked 24-case target selection. It refuses existing output directories and any destination within the repo.

It writes:
- \`reviewer/packet.json\`: 48 source queries and raw retrieval contexts in random order, with **per-case randomly flipped A/B labels** and unpredictable trace tokens. No product names, native pass/fail labels, numerical scores, gold answer arrays, raw source paths, or BM25 controls are deliberately included.
- \`coordinator/key.json\`: **SECRET** arm-to-provider mapping, exact source paths/blob SHAs, trace hashes and packet SHA-256. Keep it inaccessible to reviewers until both human ratings are locked.

Files are created with private permissions (0700 dirs / 0600 files where supported); machine and storage permissions are still the study coordinator's responsibility. Even label-blind source contexts may reveal identifying styles or answer content. A coordinator MUST inspect the entire reviewer packet privately for vendor/source leakage, personal data and eligibility before distributing it. The program blocks explicit \`Agent Memory\`, \`Mem0\` and \`BM25\` vendor-name strings in contexts; it **does not prove complete blinding**.

**Interpretation limits:** This is retrieval-only context, not a generated task answer. Query blanks are retained faithfully and task utility, recovery or other unsupported dimensions must be justified as \`not_applicable\` rather than scored artificially. Case sampling is purposeful and not population-representative.

## After genuine independent ratings

Each reviewer must submit one fully locked \`competitive-qualitative-review/1\` form for each case/arm, including its exact packet \`source_trace\`. Two *independent verified humans* per arm/case are needed, a maximum expected 96 forms. Store submitted forms securely outside the repository until rights, privacy and evidence review are satisfied.

Verify source-trace alignment to the original private packet and run the original #793 structural evaluator:

\`\`\`sh
python scripts/prepare_789_blind_review_packets.py \
  --verify-reviews /private/secure-review/study-001/coordinator/key.json \
  --packet /private/secure-review/study-001/reviewer/packet.json \
  --reviews /private/secure-review/reviews.json
\`\`\`

It **does not** verify whether the identities are truly independent humans, whether reviewers saw privileged labels outside the packet, or whether final adjudication is correct. It never publishes scores, averages multiple quality dimensions, or authorizes a product ranking. P0 privacy flags remain explicit blockers requiring separate safety adjudication.

## Not part of the benchmark-refresh pipeline

Generating or verifying reviewer packets is **a human-coordinated sensitive-data activity**, not a no-CI automated evidence projection. Do not run this from pre-commit hooks, PR CI, GitHub Actions, hosted viewers, or the public GitHub Pages app. Only publish a vetted, redacted qualitative outcome after separate independent evidence acceptance. No current canonical dashboard acceptance is implied.
