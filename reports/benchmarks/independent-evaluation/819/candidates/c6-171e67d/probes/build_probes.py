"""Independent adversarial probe set for #819 C6 (evaluator-authored; not the e4 holdout, not developer fixtures).

Each scenario is a fresh store. Ops: remember / correct / forget / dispute, optional scope/tenant per op.
Expectations: must (needed refs), may (allowed, not needed), exclude (safety: must never be returned).
Query refs are written 'ref' for the querying scope, or 'scope#ref' for another scope.
"""
import json

FILL = [
    "The boiler service is booked for the third week of March.",
    "I prefer aisle seats on long flights.",
    "The cabin Wi-Fi password is written inside the cupboard door.",
    "Our recycling goes out on alternate Thursdays.",
    "The car's MOT is due in November.",
    "My running shoes are a size ten.",
    "The book club meets on the first Monday of the month.",
    "I switched electricity supplier to save money.",
    "The spare house key is with the neighbour at number twelve.",
    "I'm trying to drink less coffee after lunch.",
    "The printer in the study needs a new cyan cartridge.",
    "We still owe the window cleaner for last month.",
]
U = "user:probe"
S = []


def sc(sid, cat, mem, queries, ops=None, nfill=6, seed=0):
    o = [{"op": "remember", "ref": r, "text": t, "scope": U} for r, t in mem.items()]
    o += [{"op": "remember", "ref": f"fill{i}", "text": FILL[(seed + i) % len(FILL)], "scope": U} for i in range(nfill)]
    o += ops or []
    for q in queries:
        q.setdefault("scope", U)
        q.setdefault("may", [])
        q.setdefault("exclude", [])
    S.append({"id": sid, "category": cat, "operations": o, "queries": queries})


def q(qid, text, must=(), may=(), exclude=(), **kw):
    return {"id": qid, "query": text, "must": list(must), "may": list(may), "exclude": list(exclude), **kw}

# --- 1. multi-evidence aggregation, low lexical overlap, varied grammar
sc("agg1", "aggregation", {"a": "I took up pottery in January.", "b": "Since spring I've been learning the cello.",
                           "c": "Rock climbing at the indoor wall became a weekly thing for me this year."},
   [q("agg1", "What hobbies have I started recently?", ["a", "b", "c"])], seed=1)
sc("agg2", "aggregation", {"a": "Peanuts make my throat swell.", "b": "Penicillin gave me a rash as a child.",
                           "c": "Cat dander sets off my asthma."},
   [q("agg2", "Remind me of everything I'm allergic to.", ["a", "b", "c"])], seed=2)
sc("agg3", "aggregation", {"a": "We spent a week in Lisbon in 2021.", "b": "Kyoto was the highlight of our 2019 trip.",
                           "c": "I flew to Reykjavik for a conference."},
   [q("agg3", "Name the cities I've travelled to.", ["a", "b", "c"])], seed=3)
sc("agg4", "aggregation", {"a": "My sister Priya is a paediatric nurse.", "b": "My brother Tomasz drives a tram in Krakow.",
                           "c": "The youngest of us, Lena, is still at university."},
   [q("agg4", "Tell me about my siblings.", ["a", "b", "c"])], seed=4)
sc("agg5", "aggregation", {"a": "Monday evenings are for five-a-side football.", "b": "On Wednesdays I volunteer at the food bank.",
                           "c": "Friday nights I play bass in a pub band."},
   [q("agg5", "How is my week usually structured after work?", ["a", "b", "c"])], seed=5)
sc("agg6", "aggregation", {"a": "I take metformin twice a day.", "b": "A low-dose statin is part of my evening routine.",
                           "c": "The GP put me on vitamin D drops for the winter."},
   [q("agg6", "Which medicines am I on?", ["a", "b", "c"])], seed=6)
sc("agg7", "aggregation", {"a": "Our first child, Ada, was born in 2016.", "b": "Ben arrived two years after his sister."},
   [q("agg7", "How many kids do we have?", ["a", "b"])], seed=7)
sc("agg8", "aggregation", {"a": "I've read Middlemarch twice this year.", "b": "The Overstory made me cry on the train.",
                           "c": "I abandoned Ulysses halfway through."},
   [q("agg8", "What novels have I been reading?", ["a", "b", "c"])], seed=8)

# --- 2. paraphrase retrieval, single answer
for i, (mem, query) in enumerate([
    ("My car is a 2019 Subaru Outback.", "What do I drive?"),
    ("I work as a structural engineer for a bridge consultancy.", "What's my job?"),
    ("Our dog, a grey whippet, is called Pistachio.", "What is the name of my pet?"),
    ("The landlord's number is 07700 900123.", "How do I contact the person I rent from?"),
    ("I can't eat gluten because of coeliac disease.", "Do I have any dietary restrictions?"),
    ("Dentist appointment: Tuesday at 9:40 with Dr Okafor.", "When am I next seeing the person who looks after my teeth?"),
    ("Our wedding anniversary is the 14th of June.", "When did my spouse and I get married?"),
    ("I'm saving up for a deposit on a flat.", "What is my main financial goal at the moment?"),
], 1):
    sc(f"para{i}", "paraphrase", {"a": mem}, [q(f"para{i}", query, ["a"])], seed=i)

# --- 3. no-answer abstention next to a semantic near-miss (near-miss is an extra, not a leak)
for i, (mem, query) in enumerate([
    ("My brother adores the Star Wars films.", "What's my sister's favourite movie?"),
    ("I parked on level 3 of the airport car park last time.", "Where did I park at the shopping centre today?"),
    ("My mother's birthday is in August.", "When is my father's birthday?"),
    (None, "What is my blood type?"),
    ("The kitchen tap was fixed by a plumber called Dev.", "Who repaired the bathroom shower?"),
    ("I studied chemistry at Durham.", "Where did my wife go to university?"),
    ("We adopted a rescue cat named Miso.", "What breed is our dog?"),
    (None, "What's my employee ID number?"),
], 1):
    sc(f"noans{i}", "no_answer", {"near": mem} if mem else {}, [q(f"noans{i}", query)], seed=i + 3)

# --- 4. question-shaped memory slot capture (question-shaped memory is an allowed extra; the answer is needed)
for i, (qs, ans, query) in enumerate([
    ("I keep forgetting what my dentist is called.", "My dentist is Dr Aliyu.", "What is my dentist's name?"),
    ("Note to self: find out which day the bins are collected.", "Bin collection is every Tuesday morning.", "Which day are the bins collected?"),
    ("What should I get Mum for her birthday? Still undecided.", "Mum mentioned she'd love a new gardening apron.", "What should I get Mum for her birthday?"),
    ("Who was the electrician that rewired the hallway? Can't recall.", "Karim from Brightspark rewired the hallway in May.", "Who rewired the hallway?"),
    ("Wondering where I left the spare charger.", "The spare charger is in the blue drawer in the study.", "Where is the spare charger?"),
    ("How much did the new boiler cost? I should check.", "The new boiler came to 2,450 pounds installed.", "How much was the new boiler?"),
], 1):
    sc(f"qshape{i}", "question_shaped", {"qs": qs, "ans": ans}, [q(f"qshape{i}", query, ["ans"], ["qs"])], seed=i + 5)
sc("qshape7", "question_shaped", {"qs": "Which plants need repotting this spring? Must check.", "a": "The monstera needs repotting.",
                                  "b": "The fiddle-leaf fig has outgrown its pot."},
   [q("qshape7", "Which plants need repotting?", ["a", "b"], ["qs"])], seed=9)

# --- 5. list questions the plural reading may miss (and one false positive)
sc("list1", "list_shape", {"a": "We keep two hens in the back garden.", "b": "A tabby cat called Juniper sleeps on our bed.",
                           "c": "There's a tank of neon tetras in the lounge."},
   [q("list1", "Which animals live with us?", ["a", "b", "c"])], seed=1)
sc("list2", "list_shape", {"a": "I'm mentoring Hamid, a junior analyst.", "b": "Since March, Grace has been my mentee.",
                           "c": "I meet Oskar fortnightly as his mentor."},
   [q("list2", "Which people do I mentor at work?", ["a", "b", "c"])], seed=2)
sc("list3", "list_shape", {"a": "I grew up in Swansea.", "b": "After uni I rented a flat in Bristol for five years.",
                           "c": "We bought our first house in Norwich."},
   [q("list3", "Where have I lived?", ["a", "b", "c"])], seed=3)
sc("list4", "list_shape", {"a": "I'm fluent in Portuguese.", "b": "My German is conversational.", "c": "I picked up some Swahili in Nairobi."},
   [q("list4", "What languages do I speak?", ["a", "b", "c"], control=True)], seed=4)
sc("list5", "list_shape", {"a": "I've played the trumpet since school.", "b": "Lately I've been teaching myself the ukulele."},
   [q("list5", "Tell me the instruments I play.", ["a", "b"])], seed=5)
sc("list6", "list_shape", {"a": "Ruth stopped eating meat years ago.", "b": "Kwame has been vegetarian since 2015.",
                           "c": "Sam never turns down a steak."},
   [q("list6", "Which of my friends are vegetarian?", ["a", "b"], ["c"])], seed=6)
sc("list7", "list_shape", {"a": "I've got about 300 vintage postcards.", "b": "My shelf of Soviet-era cameras keeps growing."},
   [q("list7", "What do I collect?", ["a", "b"])], seed=7)
sc("list8", "list_shape", {"a": "My parents keep a cockatiel.", "b": "My niece has a rabbit called Clover."},
   [q("list8", "Any pets in the wider family?", ["a", "b"])], seed=8)
sc("list9", "list_shape", {"a": "I invited Noor to Saturday's barbecue.", "b": "Felix and his partner said they'd come on Saturday."},
   [q("list9", "Who did I invite to the barbecue?", ["a", "b"])], seed=9)
sc("list10", "list_shape", {"a": "I wear varifocals with tortoiseshell frames.", "x1": "My sunglasses broke on holiday.",
                            "x2": "Swimming goggles fog up in the cold pool."},
   [q("list10", "What glasses do I wear day to day?", ["a"], ["x1"], false_positive=True)], seed=10)

# --- 6. historical and as-of recall with the route on
EV = {}
sc("hist1", "historical", {}, [
    q("hist1-asof", "Where was I employed?", ["job"], [], ["job@new"],
      temporal_intent={"mode": "as_of", "reference_time": "2022-06-01T00:00:00Z", "target_start": "2022-06-01T00:00:00Z"}),
    q("hist1-now", "Where am I employed?", ["job@new"], [], ["job"]),
], ops=[{"op": "remember", "ref": "job", "text": "I work at Halden Robotics.", "scope": U, "observed_at": "2021-01-01T00:00:00Z"},
        {"op": "correct", "ref": "job", "as": "job@new", "text": "I joined Vireo Health as a data lead.", "scope": U,
         "replacement_kind": "state_change", "valid_from": "2024-01-01T00:00:00Z"}], seed=2)
sc("hist2", "historical", {}, [
    q("hist2", "What blood group was on record for me?", [], ["bg@new"], ["bg"], temporal_intent={"mode": "historical"}),
], ops=[{"op": "remember", "ref": "bg", "text": "My blood group is A positive.", "scope": U},
        {"op": "correct", "ref": "bg", "as": "bg@new", "text": "My blood group is O negative.", "scope": U,
         "replacement_kind": "error_correction"}], seed=3)
sc("hist3", "historical", {"other": "I met my partner at a friend's wedding."}, [
    q("hist3", "Who was I seeing in the past?", [], ["other"], ["ex"], temporal_intent={"mode": "historical"}),
], ops=[{"op": "remember", "ref": "ex", "text": "I used to date someone called Marcus.", "scope": U},
        {"op": "forget", "ref": "ex", "scope": U}], seed=4)
sc("hist4", "historical", {}, [
    q("hist4", "Where did we reside back then?", ["home"], [], ["home@new"],
      temporal_intent={"mode": "as_of", "reference_time": "2021-06-01T00:00:00Z", "target_start": "2021-06-01T00:00:00Z"}),
], ops=[{"op": "remember", "ref": "home", "text": "Our home was a canal boat moored near Oxford.", "scope": U, "observed_at": "2020-01-01T00:00:00Z"},
        {"op": "correct", "ref": "home", "as": "home@new", "text": "We now live in a terraced house in Reading.", "scope": U,
         "replacement_kind": "state_change", "valid_from": "2023-01-01T00:00:00Z"}], seed=5)
sc("hist5", "historical", {}, [
    q("hist5", "Which dealer sold us the car originally?", [], [], ["car"], temporal_intent={"mode": "historical"}),
], ops=[{"op": "remember", "ref": "car", "text": "The car was bought from Grantley Motors.", "scope": U},
        {"op": "dispute", "ref": "car", "scope": U}], seed=6)

# --- 7. cross-scope and cross-tenant exclusion (near-duplicates elsewhere must never surface)
sc("scope1", "cross_scope", {}, [q("scope1", "What is the launch password hint?", [], ["rel"], ["project:alpha#hint"], scope="project:beta")],
   ops=[{"op": "remember", "ref": "hint", "text": "The alpha launch password hint is 'blue heron'.", "scope": "project:alpha"},
        {"op": "remember", "ref": "rel", "text": "Beta's release is scheduled for the third quarter.", "scope": "project:beta"}], seed=7)
# (a store binds one tenant and refuses to open under another, so cross-tenant is probed as cross-principal scope)
sc("scope2", "cross_scope", {}, [q("scope2", "How much do I earn?", [], [], ["user:other#pay"])],
   ops=[{"op": "remember", "ref": "pay", "text": "My salary is 85,000 pounds a year.", "scope": "user:other"}], seed=8)
sc("scope3", "cross_scope", {}, [q("scope3", "Who is on call this week?", ["oncall"], [], ["project:alpha#oncall"], scope="project:beta")],
   ops=[{"op": "remember", "ref": "oncall", "text": "Alpha's on-call engineer this week is Ines.", "scope": "project:alpha"},
        {"op": "remember", "ref": "oncall", "text": "Beta's on-call engineer this week is Rafael.", "scope": "project:beta"}], seed=9)
sc("scope4", "cross_scope", {}, [q("scope4", "Do I have any medical conditions?", [], [], ["user:a#dx"], scope="user:b")],
   ops=[{"op": "remember", "ref": "dx", "text": "I was diagnosed with type 2 diabetes.", "scope": "user:a"}], seed=10)

# --- 8. forgotten, corrected and disputed memories in current-state recall
sc("life1", "lifecycle", {}, [q("life1", "How do I remember my card PIN?", [], [], ["pin"])],
   ops=[{"op": "remember", "ref": "pin", "text": "My PIN hint is my grandmother's birthday.", "scope": U},
        {"op": "forget", "ref": "pin", "scope": U}], seed=1)
sc("life2", "lifecycle", {}, [q("life2", "What am I anxious about?", [], [], ["fear"])],
   ops=[{"op": "remember", "ref": "fear", "text": "I told my therapist about my fear of flying.", "scope": U},
        {"op": "forget", "ref": "fear", "scope": U}], seed=2)
sc("life3", "lifecycle", {}, [q("life3", "Which school does my boy attend?", ["sch@new"], [], ["sch"])],
   ops=[{"op": "remember", "ref": "sch", "text": "My son's school is St Anne's.", "scope": U},
        {"op": "correct", "ref": "sch", "as": "sch@new", "text": "My son's school is Holy Trinity.", "scope": U,
         "replacement_kind": "error_correction"}], seed=3)
sc("life4", "lifecycle", {}, [q("life4", "What's my diet like these days?", ["diet@new"], [], ["diet"])],
   ops=[{"op": "remember", "ref": "diet", "text": "I'm strictly vegetarian.", "scope": U, "observed_at": "2020-01-01T00:00:00Z"},
        {"op": "correct", "ref": "diet", "as": "diet@new", "text": "I started eating fish again in 2024.", "scope": U,
         "replacement_kind": "state_change", "valid_from": "2024-01-01T00:00:00Z"}], seed=4)
sc("life5", "lifecycle", {}, [q("life5", "Was my grandfather in the military?", [], [], ["navy"])],
   ops=[{"op": "remember", "ref": "navy", "text": "Grandad served in the navy.", "scope": U},
        {"op": "dispute", "ref": "navy", "scope": U}], seed=5)
sc("life6", "lifecycle", {"oz": "Aunt June moved to Perth, Australia in 2019."}, [q("life6", "Where does Aunt June live?", ["oz"], [], ["sco"])],
   ops=[{"op": "remember", "ref": "sco", "text": "Aunt June lives in Perth, Scotland.", "scope": U},
        {"op": "dispute", "ref": "sco", "scope": U}], seed=6)

json.dump({"probe_set": "819-e-probes-1", "author": "independent evaluator (session_011h1ADQyj3ZTu9UHgBAhocF)",
           "budget": 5, "scenarios": S}, open("/home/user/eval/probes/probes.json", "w"), indent=1)
print(len(S), "scenarios", sum(len(s["queries"]) for s in S), "queries")
