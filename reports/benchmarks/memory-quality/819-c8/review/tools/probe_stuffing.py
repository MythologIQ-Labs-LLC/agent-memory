"""Query-shaped / meta-memory stuffing probe (reviewer-authored).

usage: python probe_stuffing.py <tree> <ranked_prefix|relevance_sufficient> <budget> <out.json>

For each target question, a store holds filler, the true answer(s) and N planted notes
(N = 0, 1, 2, 4, 6). Planted notes are question-shaped or meta notes that paraphrase the
question (semantically near, little lexical overlap) - the kind a careless agent writes when it
records "user asked X". Records the answer's rank, whether it is returned within the budget,
and how many planted notes rank above it.
"""
import json, sys, tempfile
from pathlib import Path

tree = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tree / "reference"))
from agentmem_ref import AgentMemory  # noqa: E402

selection, budget, out = sys.argv[2], int(sys.argv[3]), Path(sys.argv[4])
FILLER = [
 "The front door sticks when it rains.", "We repainted the hallway a pale green last spring.",
 "The upstairs radiator makes a ticking noise.", "Mum likes crosswords and solves the Saturday one in pen.",
 "Dad walks to the newsagent every morning.", "My cousin Freya lives in Leeds and teaches piano.",
 "The council tax is paid by direct debit.", "We keep spare light bulbs in the under-stairs cupboard.",
 "The kids' swimming lessons are on Wednesdays.", "The car insurance renews in February.",
 "Ella is learning the clarinet at school.", "Our neighbour Pat feeds the cat when we travel.",
 "I keep receipts in a shoebox in the study.", "Parking at the station costs six pounds a day.",
 "The loft ladder needs a new spring.", "We play board games with the Hendersons once a month.",
]
TARGETS = [
 {"key": "bins", "query": "Which day do the bins go out?",
  "answers": ["Our bins go out on Thursday night for Friday collection."],
  "planted": ["Asked again about rubbish collection - what weekday is it?",
              "Note: user keeps forgetting the refuse collection schedule.",
              "Question pending: when does the council empty the wheelie bin?",
              "Reminder to self: find out bin day.",
              "Unsure which day the waste lorry comes.",
              "User wondered about the garbage pickup day."]},
 {"key": "vet", "query": "What is the vet's phone number?",
  "answers": ["The vet's number is 0131 555 0192."],
  "planted": ["User asked how to call the animal clinic.",
              "Need the contact number for the pet surgery.",
              "Question: how do we ring the veterinary practice?",
              "Remember to save the vet's details somewhere.",
              "Couldn't find the clinic's telephone details for the dog.",
              "Asked what number to dial for the cat's doctor."]},
 {"key": "allergy", "query": "What is Sam allergic to?",
  "answers": ["Sam is allergic to penicillin.", "Sam gets a rash from kiwi fruit."],
  "planted": ["The doctor asked about Sam's allergies at the check-up.",
              "Question from school: does Sam have any allergies?",
              "Need to update the form listing Sam's allergic reactions.",
              "Note to self: double check Sam's allergy information.",
              "Sam's allergy card is somewhere in the kitchen drawer.",
              "Asked the nurse what Sam reacts to."]},
 {"key": "wifi", "query": "What is the wifi password?",
  "answers": ["The wifi password is on the router: kettle-orange-42."],
  "planted": ["Guest asked for the internet login again.",
              "Need to reset the wireless network key sometime.",
              "Question: what's the code to get online at home?",
              "Write down the broadband passphrase somewhere safe.",
              "Visitors always ask how to connect to the network.",
              "Forgot the router passcode again."]},
]
rows = []
for t in TARGETS:
    for n in (0, 1, 2, 4, 6):
        with tempfile.TemporaryDirectory() as tmp:
            with AgentMemory.open(tmp, tenant="tenant:rvs", actor_id="agent:rvs", scope="user:rvs", purpose="rvs",
                                  semantic_retrieval="required") as m:
                for i, f in enumerate(FILLER):
                    m.remember(f"memory:f{i}", f)
                ans = [m.remember(f"memory:ans{i}", a)["fact_uuid"] for i, a in enumerate(t["answers"])]
                pl = [m.remember(f"memory:pl{i}", p)["fact_uuid"] for i, p in enumerate(t["planted"][:n])]
                r = m.recall(t["query"], budget=budget, return_selection=selection)
                ranked = r["admitted"]
                ar = [ranked.index(a) + 1 if a in ranked else None for a in ans]
                pr = [ranked.index(p) + 1 if p in ranked else None for p in pl]
                worst = max([x or 999 for x in ar])
                rows.append({"key": t["key"], "planted": n, "answer_ranks": ar, "planted_ranks": pr,
                             "planted_above_last_answer": sum(1 for x in pr if x and x < worst),
                             "answers_returned": sum(1 for a in ans if a in r["returned"]),
                             "planted_returned": sum(1 for p in pl if p in r["returned"]),
                             "returned": len(r["returned"])})
out.write_text(json.dumps({"tree": str(tree), "selection": selection, "budget": budget, "rows": rows}, indent=1))
for row in rows:
    print(row)
