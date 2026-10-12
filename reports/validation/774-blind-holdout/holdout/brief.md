# Blind holdout: historical-predecessor retrieval

## Domain
A theatre production company (tenant `harbourlight-theatre`) working on one main project: a production of
"The Lighthouse Keeper" (project `lighthouse-keeper-production`, purpose `production-assistant`).
Reference time 2026-10-12T12:00:00Z.

## Design intent
- 18 logical memories, 38 events (37 non-delete labels), 24 questions.
- Revision chains: rehearsal room (retain + 4 updates), ticket price (retain + 3 updates),
  lighting supplier and opening night (retain + 2 updates each), and stage manager (retain, update, correct, update).
  In that last chain the update to "Priya Raman" was a mistake, corrected to "Priya Ramesh", and then updated to Tomasz.
  So the person immediately before Tomasz is Priya Ramesh (the corrected label). Felix is the person before Priya.
- Single-update chains: costume storage, programme printer, box office hours.
- Single-version memories: sound supplier, set designer, stage-door sign-in policy, plus rationale memories
  (why Lumen was dropped, why the Drill Hall was chosen, why the price went to 28) and a one-off event (Studio B flood).
- Deleted memory with an update: lead actor fee (retain, update, delete).
- Other-project memory (spring tour rehearsal room, with an update) and other-tenant memory (Tidewater Players lighting
  supplier), both worded like visible memories.
- Vocabulary overlap between different memories: Brightwell is both a (former) lighting supplier and the sound supplier;
  Studio B shows up in rehearsal room, costume storage, the flood event and the other-project memory; the
  Bayview Church Hall shows up in the main rehearsal chain and the other-project chain.
- Questions mix immediate-predecessor phrasings (with and without words like "before", "replace", "until",
  "prior to", "take over from"), predecessor-of-older-version questions, origin questions, why-questions, current
  questions (two use "before" in a non-temporal-predecessor sense), a timeless question, and three no-safe-answer
  predecessor questions (deleted memory, other-project memory, never-changed memory).

## Annotation conventions
- Prohibited labels (deleted, other-project, other-tenant) are graded 0 in every case, so serving them is never
  rewarded. They are not repeated in `stale`.
- For `current` cases, `stale` lists every visible label in the corpus that has been superseded by an update or
  correction, not only the ones on the question's topic.
- No-safe-answer cases have empty `critical_groups`. For Q17 (sound supplier never changed), the single sound memory
  is graded 2 because it supports the answer that there was no earlier supplier on record.
- `declared-routing.json` lists the questions that ask for the value that held immediately before a later value of
  the same thing (13 questions), including the no-safe-answer predecessor questions. Origin ("first", "originally")
  and why-questions are not listed.

## Isolation statement
I wrote this corpus blind. I did not read, list, grep or open any repository content, including anything under
/home/user/agent-memory, and I did not run git. The only tools I used were file writes into this directory,
`mkdir -p`, and `python3 -c` to validate and hash my own files.
