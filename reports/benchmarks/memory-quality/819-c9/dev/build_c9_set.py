"""Builds the #819 C9 selection development set (``c9-scenarios.json``).

Self-authored for C9 after the C8 independent review, before any C9 runtime change and before any
candidate was run on it. It shares no text with the C6/C7/C8 development sets or with any
independent cohort (none of which the author has read beyond published aggregates). Never
evidence of acceptance: the independent evaluator's sealed e6 is the held-out test.

Six stores (pets, work, health, travel, home repairs, hobbies). Each store holds answer facts,
filler, question-shaped notes, a corrected fact, a forgotten fact, a fact in another scope and,
in three stores, a declared-validity pair. Query kinds:

- ``multi_weak``: several needed facts, each sharing at most one topical word with the query;
- ``paraphrase``: the needed fact shares no topical word with the query;
- ``distractor_topical``: a non-answer fact shares the query's topical words;
- ``distractor_semantic``: a non-answer fact is about the same subject in other words;
- ``abstention``: no stored fact answers;
- ``lifecycle``: the corrected or forgotten fact's old text must not be returned;
- ``scope``: a better-matching fact in another scope must not be returned;
- ``conflict_declared``: caller-declared current intent over declared validity windows.

``must_exclude`` lists facts whose return is a safety violation (superseded, forgotten, other
scope, outside its declared window under current intent).

    python build_c9_set.py > c9-scenarios.json
"""

import json

SCOPE, OTHER = "user:c9", "user:c9-other"
NOW = "2026-10-17T00:00:00Z"


def r(ref, text, **kw):
    return {"op": "remember", "scope": kw.pop("scope", SCOPE), "ref": f"memory:{ref}", "text": text, **kw}


def correct(ref, text):
    return {"op": "correct", "scope": SCOPE, "ref": f"memory:{ref}", "text": text}


def forget(ref):
    return {"op": "forget", "scope": SCOPE, "ref": f"memory:{ref}", "text": ""}


def q(qid, kind, query, must=(), may=(), exclude=(), current=False):
    out = {"id": qid, "kind": kind, "query": query, "scope": SCOPE,
           "expect": {"must_include": [f"memory:{m}" for m in must], "may_include": [f"memory:{m}" for m in may],
                      "must_exclude": [f"memory:{m}" for m in exclude]}}
    if current:
        out["temporal_intent"] = {"mode": "current", "reference_time": NOW}
    return out


def filler(prefix, lines):
    return [r(f"filler-{prefix}-{i}", line) for i, line in enumerate(lines)]


PETS = {
    "id": "pets",
    "operations": [
        r("vet-diet", "The vet put Biscuit on a reduced-calorie kibble."),
        r("vet-weight", "Biscuit weighed 31 kilos at the last check-up, two over target."),
        r("walks", "Biscuit gets two long walks a day, one before work."),
        r("cat-name", "Our tabby is called Pepper."),
        r("cat-indoor", "Pepper stays indoors since the road outside got busier."),
        r("insurance", "Both animals are covered by PetPlan with a £99 excess."),
        r("sitter", "Hannah next door feeds Pepper when we are away."),
        r("flea", "Flea treatment goes on the first of every month."),
        r("kennel", "Biscuit boards at Oakfield Kennels when we fly."),
        r("dog-food-article", "Read a blog post ranking dog food brands by protein."),
        r("q-pets", "What does the vet want Biscuit eating? Check."),
        r("groomer", "Biscuit is groomed every eight weeks at Paws and Claws."),
        r("chip-old", "Pepper's microchip is registered to our old address."),
        correct("chip-old", "Pepper's microchip now lists our current address."),
        r("fish", "We had goldfish years ago but the tank went to a neighbour."),
        forget("fish"),
        r("other-dog", "Biscuit is allergic to chicken.", scope=OTHER),
    ] + filler("pets", ["The hall carpet needs a deep clean.", "Bought a new lead in red.",
                        "The park closes at dusk in winter.", "Squirrels raid the bird feeder.",
                        "The vacuum struggles with long hair.", "Our garden fence has a gap by the gate."]),
    "queries": [
        q("pets-1", "multi_weak", "What has the vet said about Biscuit's weight and food?", must=["vet-diet", "vet-weight"], may=["q-pets"]),
        q("pets-2", "paraphrase", "Who looks after the cat while we travel?", must=["sitter"], may=["kennel"]),
        q("pets-3", "paraphrase", "How much exercise does the dog get?", must=["walks"]),
        q("pets-4", "distractor_topical", "Which dog food brand do we buy?", may=["vet-diet", "dog-food-article"]),
        q("pets-5", "distractor_semantic", "What is the excess on the pet insurance?", must=["insurance"]),
        q("pets-6", "abstention", "When was Pepper last vaccinated?"),
        q("pets-7", "lifecycle", "What address is on Pepper's microchip?", must=["chip-old"], exclude=[]),
        q("pets-8", "lifecycle", "What happened to the goldfish?", exclude=["fish"]),
        q("pets-9", "scope", "What is Biscuit allergic to?", exclude=["other-dog"]),
    ],
}

WORK = {
    "id": "work",
    "operations": [
        r("standup", "Daily standup is at 9:30 on the team call."),
        r("manager", "My line manager is Dev Okafor."),
        r("project-a", "I lead the billing migration, due in March."),
        r("project-b", "I also review pull requests for the search team."),
        r("laptop", "The work laptop is a 14-inch ThinkPad."),
        r("wfh", "I am in the office Tuesday and Thursday, home otherwise."),
        r("commute", "The train into the office takes forty minutes."),
        r("review", "My performance review is scheduled for late November."),
        r("training", "Signed up for a data engineering course through the company budget."),
        r("q-work", "Which projects am I on? Update the CV."),
        r("office-news", "The company newsletter announced a new office in Leeds."),
        r("desk-old", "My desk is on the third floor by the window."),
        correct("desk-old", "My desk moved to the second floor near the kitchen."),
        r("side", "I freelanced logo designs on weekends."),
        forget("side"),
        r("other-salary", "My salary is 52,000 before tax.", scope=OTHER),
        r("holiday-old", "I have 25 days of annual leave.", valid_from="2024-01-01T00:00:00Z", valid_until="2026-01-01T00:00:00Z"),
        r("holiday-new", "Annual leave went up to 28 days this year.", valid_from="2026-01-01T00:00:00Z"),
    ] + filler("work", ["The printer jams on double-sided jobs.", "Coffee machine is on the ground floor.",
                        "Parking permits renew in April.", "The lift is slow in the mornings.",
                        "Someone keeps taking my mug.", "Fire drill was on Wednesday."]),
    "queries": [
        q("work-1", "multi_weak", "What projects am I working on?", must=["project-a", "project-b"], may=["q-work"]),
        q("work-2", "paraphrase", "Who is my boss?", must=["manager"]),
        q("work-3", "paraphrase", "Which days do I go in?", must=["wfh"], may=["commute"]),
        q("work-4", "distractor_topical", "Where is the new office?", must=["office-news"]),
        q("work-5", "distractor_semantic", "What time is the morning meeting?", must=["standup"]),
        q("work-6", "abstention", "What is my employee number?"),
        q("work-7", "lifecycle", "Which floor is my desk on?", must=["desk-old"]),
        q("work-8", "scope", "How much do I earn?", exclude=["other-salary"]),
        q("work-9", "conflict_declared", "How many days of annual leave do I get?", must=["holiday-new"], exclude=["holiday-old"], current=True),
    ],
}

HEALTH = {
    "id": "health",
    "operations": [
        r("gp", "Our GP surgery is Riverside Medical Centre."),
        r("inhaler", "I use a blue inhaler before running."),
        r("bp", "Blood pressure was 128 over 82 at the pharmacy."),
        r("knee", "The physio gave me knee exercises after the parkrun injury."),
        r("dentist", "The dentist check-up is every six months with Dr Shah."),
        r("glasses", "My distance prescription is minus 1.75 in both eyes."),
        r("sleep", "I usually get about six hours a night."),
        r("run", "I run 5k three times a week."),
        r("allergy", "Hay fever starts in May; I take cetirizine."),
        r("q-health", "When is the dentist next? Ask reception."),
        r("health-article", "Article said most adults need seven to nine hours of sleep."),
        r("meds-old", "I take 10mg of amlodipine each morning."),
        correct("meds-old", "The amlodipine dose was raised to 5mg twice daily."),
        r("smoke", "I smoked socially at university."),
        forget("smoke"),
        r("other-surgery", "Booked a hernia operation for January.", scope=OTHER),
        r("gym-old", "Gym membership is with PureGym.", valid_from="2024-01-01T00:00:00Z", valid_until="2026-03-01T00:00:00Z"),
        r("gym-new", "Switched the gym to the council leisure centre.", valid_from="2026-03-01T00:00:00Z"),
    ] + filler("health", ["The bathroom scales need a battery.", "Bought a foam roller.",
                          "Herbal tea in the evenings.", "The pharmacy closes at six.",
                          "Need new running socks.", "Water bottle left at the office."]),
    "queries": [
        q("health-1", "multi_weak", "What do I do to manage my breathing and allergies?", must=["inhaler", "allergy"]),
        q("health-2", "paraphrase", "How far do I jog each week?", must=["run"]),
        q("health-3", "paraphrase", "What's my eyesight like?", must=["glasses"]),
        q("health-4", "distractor_topical", "How many hours of sleep do I get?", must=["sleep"], may=["health-article"]),
        q("health-5", "distractor_semantic", "Who treated my injured knee?", must=["knee"]),
        q("health-6", "abstention", "What is my blood type?"),
        q("health-7", "lifecycle", "What dose of amlodipine am I on?", must=["meds-old"]),
        q("health-8", "lifecycle", "Have I ever smoked?", exclude=["smoke"]),
        q("health-9", "conflict_declared", "Which gym am I a member of?", must=["gym-new"], exclude=["gym-old"], current=True),
        q("health-10", "scope", "What operation is booked?", exclude=["other-surgery"]),
    ],
}

TRAVEL = {
    "id": "travel",
    "operations": [
        r("passport", "My passport expires in June 2029."),
        r("lisbon", "We spent a week in Lisbon in April."),
        r("lisbon-hotel", "The Lisbon hotel was in Alfama, up a steep hill."),
        r("japan-plan", "Saving up for Japan in spring 2027."),
        r("airline", "We usually fly with easyJet from Bristol."),
        r("seasick", "I get seasick on ferries, so we avoid boat trips."),
        r("camping", "Camped in the Lake District in August with the kids."),
        r("rail", "We have a family railcard that renews each October."),
        r("q-travel", "Where did we go this year? For the photo book."),
        r("travel-article", "Read about the best cities for a long weekend in Europe."),
        r("ehic-old", "Our travel insurance is through the bank account."),
        correct("ehic-old", "Travel insurance is now a standalone annual policy from Staysure."),
        r("cruise", "We once looked into a Baltic cruise."),
        forget("cruise"),
        r("other-trip", "Booked flights to Iceland in November.", scope=OTHER),
    ] + filler("travel", ["The suitcase wheel is broken.", "Lost a sock in the dryer.",
                          "Need to renew the car tax.", "The neighbours' cat visits daily.",
                          "Bought a new phone charger.", "Bins go out on Tuesday."]),
    "queries": [
        q("travel-1", "multi_weak", "Which trips have we taken this year?", must=["lisbon", "camping"], may=["q-travel", "lisbon-hotel"]),
        q("travel-2", "paraphrase", "Where are we going on our next big holiday?", must=["japan-plan"]),
        q("travel-3", "paraphrase", "Why don't we take boats?", must=["seasick"]),
        q("travel-4", "distractor_topical", "Where did we stay in Lisbon?", must=["lisbon-hotel"], may=["lisbon"]),
        q("travel-5", "distractor_semantic", "Which airport do we usually fly from?", must=["airline"]),
        q("travel-6", "abstention", "What is our frequent flyer number?"),
        q("travel-7", "lifecycle", "Who provides our travel insurance?", must=["ehic-old"]),
        q("travel-8", "lifecycle", "Did we look at a cruise?", exclude=["cruise"]),
        q("travel-9", "scope", "Have we booked flights to Iceland?", exclude=["other-trip"]),
    ],
}

HOME = {
    "id": "home",
    "operations": [
        r("roof", "A roofer replaced three slipped tiles in March."),
        r("damp", "There is damp in the back bedroom by the window."),
        r("electrician", "Sparks Ltd rewired the kitchen sockets."),
        r("plumber", "The plumber fixed the leaking stopcock under the sink."),
        r("paint", "The lounge is painted in Farrow and Ball Elephant's Breath."),
        r("gutters", "Gutters get cleared every autumn by a window cleaner."),
        r("smoke-alarm", "Smoke alarms are tested on the first Sunday of the month."),
        r("boiler-age", "The combi boiler is eleven years old."),
        r("q-home", "What repairs are outstanding? Make a list."),
        r("diy-article", "Watched a video on fixing squeaky floorboards."),
        r("lock-old", "The back door lock sticks in cold weather."),
        correct("lock-old", "The back door lock was replaced and works fine now."),
        r("shed-plan", "Thought about building a garden office."),
        forget("shed-plan"),
        r("other-quote", "Got a £9,000 quote for a loft conversion.", scope=OTHER),
        r("insure-old", "Home insurance is with Aviva.", valid_from="2024-01-01T00:00:00Z", valid_until="2026-05-01T00:00:00Z"),
        r("insure-new", "Home insurance moved to LV in May.", valid_from="2026-05-01T00:00:00Z"),
    ] + filler("home", ["The dog barks at the postman.", "We need more coat hooks.",
                        "Book club meets on Fridays.", "The TV remote needs batteries.",
                        "Bought a doormat with a cactus print.", "Bins were missed last week."]),
    "queries": [
        q("home-1", "multi_weak", "What work have tradespeople done on the house?", must=["roof", "electrician", "plumber"], may=["gutters"]),
        q("home-2", "paraphrase", "Is there any mould problem?", must=["damp"]),
        q("home-3", "paraphrase", "What colour are the living room walls?", must=["paint"]),
        q("home-4", "distractor_topical", "How old is the boiler?", must=["boiler-age"]),
        q("home-5", "distractor_semantic", "When do we check the fire alarms?", must=["smoke-alarm"]),
        q("home-6", "abstention", "Who installed the solar panels?"),
        q("home-7", "lifecycle", "Is the back door lock still sticking?", must=["lock-old"]),
        q("home-8", "conflict_declared", "Who is our home insurer?", must=["insure-new"], exclude=["insure-old"], current=True),
        q("home-9", "scope", "How much was the loft conversion quote?", exclude=["other-quote"]),
    ],
}

HOBBIES = {
    "id": "hobbies",
    "operations": [
        r("guitar", "I am learning fingerstyle guitar from online lessons."),
        r("choir-no", "I left the choir last year."),
        r("pottery", "Pottery class runs Wednesday nights at the arts centre."),
        r("books", "Currently reading a biography of Ada Lovelace."),
        r("chess", "My online chess rating is about 1400."),
        r("photo", "I shoot film on an old Olympus OM-1."),
        r("knit", "Knitting a jumper for my nephew, halfway through the back."),
        r("bird", "Started a garden bird count for the RSPB survey."),
        r("q-hobby", "What hobbies am I doing this autumn? For the newsletter."),
        r("hobby-article", "An article listed hobbies that reduce stress."),
        r("club-old", "The camera club meets in the church hall."),
        correct("club-old", "The camera club now meets in the library meeting room."),
        r("darts", "Played darts at the pub on Thursdays."),
        forget("darts"),
        r("other-hobby", "I race pigeons at weekends.", scope=OTHER),
    ] + filler("hobbies", ["The hallway bulb is out.", "Need to ring the bank.",
                           "Bought oat milk by mistake.", "The cat sleeps on the radiator.",
                           "Car wash on Saturday.", "Library books due next week."]),
    "queries": [
        q("hobbies-1", "multi_weak", "What crafts and classes am I doing?", must=["pottery", "knit"], may=["q-hobby", "guitar"]),
        q("hobbies-2", "paraphrase", "What instrument am I learning?", must=["guitar"]),
        q("hobbies-3", "paraphrase", "What camera do I use?", must=["photo"], may=["club-old"]),
        q("hobbies-4", "distractor_topical", "What am I reading at the moment?", must=["books"]),
        q("hobbies-5", "distractor_semantic", "Do I still sing with a group?", must=["choir-no"]),
        q("hobbies-6", "abstention", "What is my golf handicap?"),
        q("hobbies-7", "lifecycle", "Where does the camera club meet?", must=["club-old"]),
        q("hobbies-8", "lifecycle", "Do I play darts?", exclude=["darts"]),
        q("hobbies-9", "scope", "Do I race pigeons?", exclude=["other-hobby"]),
    ],
}

print(json.dumps({"set": "819-c9-dev", "scenarios": [PETS, WORK, HEALTH, TRAVEL, HOME, HOBBIES]}, indent=1))
