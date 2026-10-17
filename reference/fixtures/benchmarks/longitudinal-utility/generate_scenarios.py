"""Regenerates scenarios-v1.json (run from reference/). The JSON is the authoritative fixture."""
import json
def rem(i, ref, text, **kw): return {"id": i, "op": "remember", "ref": ref, "text": text, **kw}
def cor(i, ref, text, kind, **kw): return {"id": i, "op": "correct", "ref": ref, "text": text, "replacement_kind": kind, **kw}
def prop(subject, attribute, value, assertion="state", cardinality="single", **kw):
    return {"subject": subject, "attribute": attribute, "value": value, "assertion": assertion, "cardinality": cardinality, **kw}
def probe(i, query, phrasing="unqualified", **kw): return {"id": i, "query": query, "phrasing": phrasing, **kw}
HIST = {"mode": "historical"}
NOISE = [
 "The team uses GitHub Actions for continuous integration",
 "The user's laptop runs macOS Sonoma",
 "The marketing site is hosted on Netlify",
 "Code review requires one approving reviewer",
 "The user writes commit messages in the imperative mood",
 "The design system lives in the shared Figma workspace",
 "The on-call rotation changes every Monday",
 "Integration tests take about twelve minutes",
 "The user dislikes trailing whitespace in diffs",
 "The analytics dashboard is built with Grafana",
 "The mobile app targets iOS 17 and later",
 "Feature flags are managed in LaunchDarkly",
]
scenarios = [
 {"id": "pref-editor-state-change", "family": "preference_change", "sessions": [
   {"writes": [rem("w1", "pref:editor", "The user prefers the Vim editor for coding"),
               rem("w2", "pref:theme", "The user prefers a dark color theme in every editor")]},
   {"writes": [cor("w3", "pref:editor", "The user prefers the Helix editor for coding", "state_change")]},
   {"probes": [probe("p1", "Which editor does the user prefer for coding?", current=["w3"], stale=["w1"]),
               probe("p2", "Which editor does the user prefer for coding now?", "explicit_current", current=["w3"], stale=["w1"]),
               probe("p3", "Which editor did the user prefer for coding in the past?", "historical", temporal_intent=HIST, current=["w3"], history=["w1"]),
               probe("p4", "What color theme does the user like in the editor?", current=["w2"])]}]},
 {"id": "timezone-error-correction", "family": "corrected_fact", "sessions": [
   {"writes": [rem("w1", "profile:timezone", "The user's timezone is Pacific Time")]},
   {"writes": [cor("w2", "profile:timezone", "The user's timezone is Central European Time", "error_correction")]},
   {"probes": [probe("p1", "What timezone is the user in?", current=["w2"], stale=["w1"]),
               probe("p2", "Which timezone should I use when scheduling a meeting for the user?", current=["w2"], stale=["w1"]),
               probe("p3", "What timezone was the user in before?", "historical", temporal_intent=HIST, current=["w2"], stale=["w1"])]}]},
 {"id": "atlas-ship-date", "family": "superseded_commitment", "sessions": [
   {"writes": [rem("w1", "s1:commitment", "We committed to ship the Atlas beta on March 1",
                   proposition=prop("atlas beta", "ship_date", "March 1"))]},
   {"writes": [rem("w2", "s2:dependency", "The Atlas beta cannot ship until the billing migration is finished")]},
   {"writes": [rem("w3", "s3:commitment", "The Atlas beta ship date moved to April 15",
                   proposition=prop("atlas beta", "ship_date", "April 15", "change", replaces_value="March 1"))]},
   {"writes": [rem("w4", "s4:hearsay", "Dana says the Atlas beta ship date moved to May 20", source_ref="user:dana",
                   proposition=prop("atlas beta", "ship_date", "May 20", "change", replaces_value="April 15",
                                    flags={"attributed_to_other": True}))],
    "probes": [probe("p1", "When will the Atlas beta ship?", current=["w3"], stale=["w1"]),
               probe("p2", "When will the Atlas beta ship now?", "explicit_current", current=["w3"], stale=["w1"]),
               probe("p3", "What has to be finished before the Atlas beta can ship?", current=["w2"]),
               probe("p4", "When does the Atlas beta ship and what is blocking it?", current=["w3"], dependency=["w2"], stale=["w1"])]}]},
 {"id": "atlas-database-migration", "family": "evolving_project", "sessions": [
   {"writes": [rem("w1", "project:atlas:database", "Project Atlas stores its data in PostgreSQL"),
               rem("w2", "project:atlas:db-credentials", "Atlas database credentials live in the vault path secret/atlas-db")]},
   {"writes": [cor("w3", "project:atlas:database", "Project Atlas stores its data in CockroachDB", "state_change")]},
   {"writes": [rem("w4", "project:atlas:backups", "Atlas database backups run nightly at 02:00 UTC")]},
   {"probes": [probe("p1", "Which database does Project Atlas use?", current=["w3"], stale=["w1"]),
               probe("p2", "How do I connect to the Atlas database?", current=["w3"], dependency=["w2"], stale=["w1"]),
               probe("p3", "When do Atlas database backups run?", current=["w4"]),
               probe("p4", "Which database did Project Atlas use before?", "historical", temporal_intent=HIST, current=["w3"], history=["w1"])]}]},
 {"id": "allergies-multivalued", "family": "no_false_supersession", "sessions": [
   {"writes": [rem("w1", "s1:allergy", "The user is allergic to peanuts", proposition=prop("user", "allergy", "peanuts", cardinality="multi"))]},
   {"writes": [rem("w2", "s2:allergy", "The user is also allergic to shellfish", proposition=prop("user", "allergy", "shellfish", cardinality="multi"))]},
   {"probes": [probe("p1", "What foods is the user allergic to?", current=["w1", "w2"]),
               probe("p2", "What is the user allergic to now?", "explicit_current", current=["w1", "w2"])]}]},
 {"id": "teammate-languages", "family": "no_false_supersession", "sessions": [
   {"writes": [rem("w1", "s1:alice", "Alice's favorite programming language is Go", proposition=prop("alice", "favorite_language", "Go")),
               rem("w2", "s1:bob", "Bob's favorite programming language is Kotlin", proposition=prop("bob", "favorite_language", "Kotlin"))]},
   {"writes": [rem("w3", "s2:bob", "Bob's favorite programming language is now Scala",
                   proposition=prop("bob", "favorite_language", "Scala", "change", replaces_value="Kotlin"))]},
   {"probes": [probe("p1", "What is Alice's favorite programming language?", current=["w1"]),
               probe("p2", "What is Bob's favorite programming language?", current=["w3"], stale=["w2"]),
               probe("p3", "What is Bob's favorite programming language now?", "explicit_current", current=["w3"], stale=["w2"]),
               probe("p4", "What is Alice's favorite programming language now?", "explicit_current", current=["w1"])]}]},
 {"id": "project-scope-isolation", "family": "isolation", "sessions": [
   {"writes": [rem("w1", "deploy:target", "The deploy target for this project is the east Kubernetes cluster", scope="project:atlas"),
               rem("w2", "deploy:target", "The deploy target for this project is the west Kubernetes cluster", scope="project:borealis")]},
   {"probes": [probe("p1", "What is the deploy target for this project?", scope="project:atlas", current=["w1"], forbidden=["w2"]),
               probe("p2", "What is the deploy target for this project?", scope="project:borealis", current=["w2"], forbidden=["w1"])]}]},
 {"id": "privacy-forget", "family": "withdrawn", "sessions": [
   {"writes": [rem("w1", "profile:home-address", "The user's home address is 12 Elm Street"),
               rem("w2", "profile:office", "The user's office is on the fourth floor of the Harbor building")]},
   {"writes": [{"id": "w3", "op": "forget", "ref": "profile:home-address"}]},
   {"probes": [probe("p1", "What is the user's home address?", forbidden=["w1"]),
               probe("p2", "Where is the user's office?", current=["w2"], forbidden=["w1"])]}]},
 {"id": "long-gap-recall", "family": "cross_session_recall", "sessions": [
   {"writes": [rem("w1", "pref:package-manager", "The user's preferred package manager is pnpm")] +
              [rem(f"n{i}", f"note:{i}", text) for i, text in enumerate(NOISE[:4])]},
   {"writes": [rem(f"n{i}", f"note:{i}", text) for i, text in enumerate(NOISE[4:8], start=4)]},
   {"writes": [rem(f"n{i}", f"note:{i}", text) for i, text in enumerate(NOISE[8:], start=8)]},
   {"probes": [probe("p1", "Which package manager should I use for the user's projects?", current=["w1"]),
               probe("p2", "What do we use for continuous integration?", current=["n0"]),
               probe("p3", "Where are feature flags managed?", current=["n11"])]}]},
 {"id": "standup-untyped-change", "family": "untyped_episodic_change", "sessions": [
   {"writes": [rem("w1", "s1:note", "The team standup is at 9am")]},
   {"writes": [rem("w2", "s2:note", "The team standup moved to 10am")]},
   {"probes": [probe("p1", "What time is the team standup?", current=["w2"], stale=["w1"]),
               probe("p2", "What time is the team standup now?", "explicit_current", current=["w2"], stale=["w1"])]}]},
 {"id": "parked-correction", "family": "governed_admission", "sessions": [
   {"writes": [rem("w1", "release:branch", "The release branch is main")]},
   {"writes": [cor("w2", "release:branch", "The release branch is trunk", "error_correction", evidence=False, expect_committed=False)]},
   {"probes": [probe("p1", "What is the release branch?", current=["w1"])]}]},
 {"id": "diet-change", "family": "preference_change", "sessions": [
   {"writes": [rem("w1", "s1:diet", "The user is vegetarian", proposition=prop("user", "diet", "vegetarian")),
               rem("w2", "s1:cuisine", "The user enjoys Thai food")]},
   {"writes": [rem("w3", "s2:diet", "The user is now vegan", proposition=prop("user", "diet", "vegan", "change", replaces_value="vegetarian"))]},
   {"probes": [probe("p1", "What diet does the user follow?", current=["w3"], stale=["w1"]),
               probe("p2", "Suggest a restaurant: what diet and cuisine does the user like?", current=["w3"], dependency=["w2"], stale=["w1"]),
               probe("p3", "What diet does the user follow currently?", "explicit_current", current=["w3"], stale=["w1"])]}]},
]

scenarios += [
 {"id": "typed-change-guards", "family": "no_false_supersession", "sessions": [
   {"writes": [rem("w1", "s1:laptop", "The user's work laptop is a ThinkPad", proposition=prop("user", "work_laptop", "ThinkPad")),
               rem("w2", "s1:shell", "The user's login shell is zsh", proposition=prop("user", "login_shell", "zsh")),
               rem("w3", "s1:region", "The user's cloud region is eu-west-1", proposition=prop("user", "cloud_region", "eu-west-1"))]},
   {"writes": [rem("w4", "s2:laptop", "The user might switch the work laptop to a MacBook",
                   proposition=prop("user", "work_laptop", "MacBook", "change", replaces_value="ThinkPad", flags={"hedged": True})),
               rem("w5", "s2:shell", "The user's login shell is now fish", source_ref="tool:dotfiles-scan",
                   proposition=prop("user", "login_shell", "fish", "change", replaces_value="zsh")),
               rem("w6", "s2:region", "The user's cloud region is now us-east-1", scope="project:sandbox",
                   proposition=prop("user", "cloud_region", "us-east-1", "change", replaces_value="eu-west-1"))]},
   {"probes": [probe("p1", "What work laptop does the user have?", current=["w1"]),
               probe("p2", "What is the user's login shell?", current=["w2"]),
               probe("p3", "What is the user's cloud region?", current=["w3"], forbidden=["w6"])]}]},
 {"id": "language-history", "family": "history_preservation", "sessions": [
   {"writes": [rem("w1", "s1:lang", "My favorite language is Python", proposition=prop("user", "favorite_language", "Python"))]},
   {"writes": [rem("w2", "s2:lang", "My favorite language is now Rust", proposition=prop("user", "favorite_language", "Rust", "change", replaces_value="Python"))]},
   {"probes": [probe("p1", "What is my favorite language?", current=["w2"], stale=["w1"]),
               probe("p2", "Which favorite languages have I mentioned over the sessions?", current=["w2"], history=["w1"]),
               probe("p3", "What was my favorite language before Rust?", "historical", temporal_intent=HIST, current=["w2"], history=["w1"])]}]},
]

fixture = {"fixture_version": "1.0.0", "description": "Deterministic multi-session agent-utility scenarios (#819 longitudinal lane). Expectations name writes and are read only by the scorer.", "default_budget": 5, "scenarios": scenarios}
json.dump(fixture, open("fixtures/benchmarks/longitudinal-utility/scenarios-v1.json", "w"), indent=1)
print(sum(len(s.get("probes",[])) for sc in scenarios for s in sc["sessions"]))
