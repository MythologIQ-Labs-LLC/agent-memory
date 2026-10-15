"""Reviewer-authored generalisation scenarios (never seen by the candidate's calibration)."""
import json
import sys

NOISE = [
    "The boiler service is booked for 14 November.",
    "The bathroom tap drips when the hot water is on.",
    "I prefer aisle seats on long flights.",
    "Grandma's birthday is on 2 February.",
    "We get the veg box delivered on Fridays.",
    "The office is closed between Christmas and New Year.",
    "I'm reading a novel about Antarctic explorers.",
    "The hedge needs trimming before the neighbours complain.",
    "Our recycling bins are collected fortnightly.",
    "The dentist reminder came for the 9th.",
    "The loft ladder squeaks and needs oil.",
    "Book club meets at Priya's flat on the last Thursday.",
    "The smoke alarm battery was changed in June.",
    "We left the spare duvet at the holiday cottage.",
    "The blue folder in the study has the warranty papers.",
    "Our street has a summer party every July.",
    "The neighbour's cat sometimes sleeps in our shed.",
    "I want to learn Portuguese before the trip to Lisbon.",
    "The hallway light switch is wired backwards.",
    "We donated the old pram to the charity shop.",
    "The garden tap was lagged for winter.",
    "I'm meant to call the council about the pothole.",
]


def scen(sid, scope, mems, queries, ops_extra=(), noise=()):
    ops = [{"op": "remember", "scope": scope, "ref": r, "text": t} for r, t in mems]
    ops += [{"op": "remember", "scope": scope, "ref": f"{sid}-n{i}", "text": t} for i, t in enumerate(noise)]
    ops += list(ops_extra)
    qs = []
    for i, q in enumerate(queries):
        text, kind, must, may, excl = (list(q) + [[], [], []])[:5]
        item = {"id": f"{sid}-{i + 1}", "scope": scope, "query": text, "kind": kind,
                "expect": {"must_include": must, "may_include": may,
                           "must_exclude": [{"ref": r, "reason": why} for r, why in excl]}}
        if kind == "historical":
            item["temporal_intent"] = {"mode": "historical"}
        qs.append(item)
    return {"id": sid, "category": "reviewer-gen", "operations": ops, "queries": qs}


S = []
S.append(scen("fin", "user:fin", [
    ("sub-netflix", "Netflix renews on the 3rd of each month at 15.49."),
    ("sub-gym", "The climbing gym membership is 62 a month."),
    ("sub-cloud", "Photo backups go to a 2 TB iCloud plan."),
    ("sub-news", "The Guardian digital edition costs me 12 a month."),
    ("mortgage", "Mortgage is fixed at 4.1% until August 2027 with Nationwide."),
    ("isa", "I put 300 into the stocks and shares ISA on payday."),
    ("accountant", "Helen Brooks files our self-assessment return each January."),
    ("pension", "My workplace pension contribution is 8% with a 5% employer match."),
    ("car-ins", "Admiral renewed the car cover at 540 for the year."),
    ("home-ins", "Contents insurance is with Aviva and covers the bikes up to 2,000."),
    ("groceries", "We try to keep groceries under 450 a month."),
    ("sofa", "The sofa is on 0% finance until next March."),
    ("crypto", "I sold the last of the Ethereum in 2023."),
    ("mia-bike", "Mia wants a purple bike for her birthday."),
], [
    ("What subscriptions am I paying for?", "aggregate", ["sub-netflix", "sub-gym", "sub-cloud", "sub-news"], []),
    ("What do we spend money on every month?", "aggregate", ["sub-netflix", "sub-gym", "sub-news", "groceries"],
     ["sub-cloud", "sofa", "isa", "pension"]),
    ("Who does our taxes?", "paraphrase", ["accountant"]),
    ("When does the fixed rate on the house loan end?", "paraphrase", ["mortgage"]),
    ("How much does my employer put into my retirement savings?", "paraphrase", ["pension"]),
    ("What is my credit card limit?", "no-answer", []),
    ("How much did the kitchen extension cost?", "no-answer", []),
    ("Which insurance policies do we have?", "aggregate", ["car-ins", "home-ins"]),
    ("Are the bikes insured?", "distractor", ["home-ins"]),
], noise=NOISE[:16]))

S.append(scen("fam", "user:fam", [
    ("mia-school", "Mia is in Year 4 at Hillcrest Primary."),
    ("leo-school", "Leo started at Oakfield Secondary this September."),
    ("mia-teacher", "Mr. Hughes teaches Mia's class."),
    ("leo-tutor", "Leo sees a maths tutor, Raj, on Tuesday evenings."),
    ("mia-allergy", "Mia can't eat peanuts; the office keeps her EpiPen."),
    ("leo-band", "Leo plays the trumpet in the junior brass band."),
    ("mia-gym", "Mia does gymnastics on Wednesdays after lessons finish."),
    ("leo-bus", "The 47 bus picks Leo up at 7:50."),
    ("mia-pickup", "Grandad collects Mia on Fridays."),
    ("parents-eve", "Parents' evening is on 21 November at 6pm."),
    ("blazer", "Leo's blazer needs replacing, he's grown out of it."),
    ("inset", "There's an inset day on 3 January."),
    ("mia-friend", "Mia's best friend is Zara from next door."),
    ("leo-friends", "Leo hangs out with Sam and Kofi from the band."),
    ("leo-phone", "Leo got his first phone for his twelfth birthday."),
], [
    ("Who teaches Mia?", "governance", ["mia-teacher-new"], [], [("mia-teacher", "superseded")]),
    ("What instruments does Leo play?", "paraphrase", ["leo-band"]),
    ("What after-school activities do the kids do?", "aggregate", ["leo-band", "mia-gym"], ["leo-tutor"]),
    ("Is there any food Mia must avoid?", "paraphrase", ["mia-allergy"]),
    ("How does Leo get to school?", "paraphrase", ["leo-bus"], ["leo-school"]),
    ("Who are Leo's friends?", "paraphrase", ["leo-friends"]),
    ("What did Mia get on her spelling test?", "no-answer", []),
    ("When is the school trip to the zoo?", "no-answer", []),
    ("Does Leo have a mobile?", "governance", [], [], [("leo-phone", "forgotten")]),
], ops_extra=[
    {"op": "correct", "scope": "user:fam", "ref": "mia-teacher", "as": "mia-teacher-new",
     "text": "Mrs. Adeyemi took over Mia's class after half term."},
    {"op": "forget", "scope": "user:fam", "ref": "leo-phone", "text": ""},
], noise=NOISE[4:20]))

S.append(scen("car", "user:car", [
    ("car-model", "We drive a grey 2019 Skoda Octavia estate."),
    ("car-mot", "The MOT is due in May."),
    ("tyres", "Front tyres were replaced at Kwik Fit in August."),
    ("charger", "We're getting quotes for a home charger from Pod Point."),
    ("commute", "I cycle to the office on dry days and take the tram when it rains."),
    ("parking", "The station car park costs 6.50 a day."),
    ("bike", "My commuter bike is a Brompton with a dynamo light."),
    ("car-ins", "Admiral covers the car; the excess is 250."),
    ("breakdown", "Green Flag is our breakdown cover."),
    ("garage", "Steve at Hilltop Motors does the servicing."),
    ("mpg", "It averages about 52 miles per gallon on the motorway."),
], [
    ("What vehicle do we own?", "governance", ["car-model-new"], ["charger"], [("car-model", "superseded")]),
    ("Who services the car?", "paraphrase", ["garage"]),
    ("What happens if we break down on the motorway?", "paraphrase", ["breakdown"], ["car-ins"]),
    ("How do I get to work?", "paraphrase", ["commute"], ["bike"]),
    ("How much is parking at the station?", "lexical", ["parking"]),
    ("What is the car's registration number?", "no-answer", []),
    ("How much did the Brompton cost?", "no-answer", []),
    ("Which car did we have before?", "historical", ["car-model"], ["car-model-new"]),
    ("What do we pay to cover the car?", "aggregate", ["car-ins", "breakdown"]),
], ops_extra=[
    {"op": "correct", "scope": "user:car", "ref": "car-model", "as": "car-model-new", "replacement_kind": "state_change",
     "text": "We sold the Octavia and now drive a white Kia Niro EV."},
], noise=NOISE[:18]))

ADV_BASE = [
    ("work", "Northwind Logistics hired me as head of analytics in 2021."),
    ("dog", "Biscuit, our beagle, is terrified of thunderstorms."),
    ("cat", "The tabby we adopted in March is called Miso."),
    ("petfood", "Miso only eats the salmon pouches, Biscuit gets kibble."),
    ("gp", "Dr. Mensah at the Elm Street surgery is my GP."),
    ("dentist", "My dentist is on Corporation Road."),
]
ADV_STUFF = [
    ("stuff-work", "Asked the assistant again: where do I work, and who is my employer?"),
    ("stuff-work2", "Employer, company, workplace, job: the questions about my work keep coming up."),
    ("stuff-pets", "Asked which pets we have and what the pets eat."),
    ("stuff-doc", "I keep forgetting who my doctor is."),
]
ADV_Q = [
    ("Who is my employer?", "stuffing", ["work"]),
    ("Where do I work?", "stuffing", ["work"]),
    ("Which pets do we have?", "stuffing", ["dog", "cat"], ["petfood"]),
    ("Who is my doctor?", "stuffing", ["gp"]),
    ("What do the pets eat?", "stuffing", ["petfood"]),
]
S.append(scen("adv", "user:adv", ADV_BASE + ADV_STUFF, ADV_Q, noise=NOISE[:22]))
S.append(scen("advctl", "user:adv", ADV_BASE, ADV_Q, noise=NOISE[:22]))

S.append(scen("home", "user:home", [
    ("dad-allergy", "Dad is allergic to shellfish."),
    ("ines-veg", "My sister Ines is vegetarian."),
    ("sam-spice", "Sam can't handle very spicy food."),
    ("fav-dish", "The family favourite is my lamb tagine with apricots."),
    ("oven", "The oven runs about 15 degrees hot."),
    ("knife", "The good chef's knife was a wedding present from Aunt Rosa."),
    ("starter", "The sourdough starter lives at the back of the fridge and is called Gerald."),
    ("freezer", "The chest freezer in the garage is full of batch-cooked chilli."),
    ("party", "We're hosting eight people for dinner on 12 December."),
    ("wine", "Ines prefers white wine; Dad only drinks bitter."),
    ("cookbook", "Ottolenghi's Simple is the most used cookbook on the shelf."),
    ("dishwasher", "The dishwasher's rinse aid light is on."),
], [
    ("What dietary restrictions should I plan for at the dinner party?", "aggregate",
     ["dad-allergy", "ines-veg", "sam-spice"], ["party", "wine"]),
    ("Does anyone avoid meat?", "paraphrase", ["ines-veg"]),
    ("What's the name of the bread starter?", "lexical", ["starter"]),
    ("Is the oven accurate?", "paraphrase", ["oven"]),
    ("What should I cook that everyone loves?", "paraphrase", ["fav-dish"]),
    ("What is Sam's favourite dessert?", "no-answer", []),
    ("When was the fridge bought?", "no-answer", []),
    ("Who gave us the knife?", "paraphrase", ["knife"]),
    ("What drinks do people like?", "paraphrase", ["wine"]),
], noise=NOISE[2:22]))

S.append(scen("fit", "user:fit", [
    ("race", "I'm training for the Bristol half marathon in April."),
    ("knee", "My left knee aches after runs longer than 10 km."),
    ("physio", "Physio sessions with Joanna are on Monday mornings."),
    ("shoes", "Running shoes are Hoka Clifton 9, replaced every 600 km."),
    ("med-bp", "I take amlodipine 5 mg each morning for blood pressure."),
    ("med-hay", "Cetirizine in spring for hay fever."),
    ("vit-d", "Vitamin D tablets through the winter."),
    ("sleep", "I've been sleeping badly since the clocks changed."),
    ("gp", "Dr. Mensah at Elm Street is my GP."),
    ("bloods", "Blood test results came back normal in September."),
    ("statin", "I take a statin at night."),
], [
    ("What medications am I on?", "aggregate", ["med-bp", "med-hay"], ["vit-d"], [("statin", "forgotten")]),
    ("What do I take every day?", "aggregate", ["med-bp"], ["vit-d"], [("statin", "forgotten")]),
    ("Which race am I preparing for?", "paraphrase", ["race"]),
    ("Do I have any injuries?", "paraphrase", ["knee"], ["physio"]),
    ("When do I see the physiotherapist?", "paraphrase", ["physio"]),
    ("What is my resting heart rate?", "no-answer", []),
    ("How much do I weigh?", "no-answer", []),
    ("Who is my doctor?", "paraphrase", ["gp"]),
    ("Why am I so tired lately?", "paraphrase", ["sleep"]),
], ops_extra=[{"op": "forget", "scope": "user:fit", "ref": "statin", "text": ""}], noise=NOISE[:20]))

json.dump({"scenarios": S}, open(sys.argv[1], "w"), indent=1)
print(sum(len(s["queries"]) for s in S), "queries;", [len(s["operations"]) for s in S])
