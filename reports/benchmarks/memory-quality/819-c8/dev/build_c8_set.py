"""Build the #819 C8 development set: fresh multi-evidence and conflict cases (self-authored, synthetic).

It is new content, written after C7 stopped, and shares no text with the C6 or C7 sets. There
are six stores, one per life domain, each of about 40 memories:
- the domain's evidence;
- topically related non-answers;
- a question-shaped note;
- ordinary filler.

Query kinds:
- ``multi``: 2-4 needed memories, worded differently from the question and each other;
- ``corroborate``: one fact matches the question's words; others support it in other words;
- ``distractor``: one answer among topical non-answers sharing the question's words;
- ``deep``: one answer sharing only weak words with the question;
- ``conflict``: older and newer statements, both remembered, no correction, unspecified intent.
  Newer-first is measured, not gated;
- ``conflict_declared``: older and newer statements with declared validity windows, queried with
  caller-declared ``current`` or ``as_of`` intent. The order is decided by the temporal
  applicability stage and is gated (restated I4);
- ``abstention``: nothing in the store answers.

No benchmark data, gold or wording is used. Expectations are fixed here, before any C8
runtime change.

    python build_c8_set.py > c8-scenarios.json
"""

import json

SCOPE = "user:c8"
OLD = {"valid_from": "2024-01-01T00:00:00Z", "valid_until": "2026-01-01T00:00:00Z"}
NEW = {"valid_from": "2026-01-01T00:00:00Z"}
CURRENT = {"mode": "current", "reference_time": "2026-10-16T00:00:00Z"}  # current intent needs a reference time
AS_OF_2025 = {"mode": "as_of", "reference_time": "2025-06-01T00:00:00Z", "target_start": "2025-06-01T00:00:00Z"}

FILLER = [
    "The hallway clock runs five minutes fast.",
    "A spare phone charger is in the glovebox.",
    "Recycling collection moved to Thursdays.",
    "I like my tea with a splash of milk.",
    "The front gate squeaks when it rains.",
    "Stamps are kept in the blue tin.",
    "My reading glasses live on the bedside table.",
    "The doorbell battery was replaced in spring.",
    "There is a parcel locker at the corner shop.",
    "I keep receipts in a shoebox under the desk.",
    "The radiator in the study takes ages to warm up.",
    "Our street gets gritted only after the main road.",
    "The blender lid cracked but still works.",
    "I prefer window seats on trains.",
    "Laundry day is usually Sunday.",
    "The spare duvet is in the loft.",
    "The torch in the kitchen drawer needs new batteries.",
    "I tend to wake up around half six.",
]


def store(sid, facts, queries, filler):
    ops = []
    for ref, text, extra in facts:
        ops.append({"op": "remember", "scope": SCOPE, "ref": f"memory:{ref}", "text": text, **(extra or {})})
    ops += [{"op": "remember", "scope": SCOPE, "ref": f"memory:filler-{sid}-{i}", "text": t} for i, t in enumerate(filler)]
    qs = []
    for n, (kind, query, must, may, intent) in enumerate(queries, start=1):
        q = {"id": f"{sid}-{n}", "kind": kind, "query": query, "scope": SCOPE,
             "expect": {"must_include": [f"memory:{r}" for r in must],
                        "may_include": [f"memory:{r}" for r in may], "must_exclude": []}}
        if intent:
            q["temporal_intent"] = intent
        qs.append(q)
    return {"id": sid, "category": "c8-development", "operations": ops, "queries": qs}


def F(ref, text, **extra):
    return (ref, text, extra)


GARDEN = store("garden", [
    F("plot", "We rent plot 14 at the Elm Road allotments."),
    F("beans", "Runner beans are climbing the canes by the shed."),
    F("spuds", "Two rows of early potatoes went in during April."),
    F("squash", "The butternut squash is sprawling over the path."),
    F("slugs", "Slugs ate every lettuce seedling in May."),
    F("copper", "Copper tape round the raised bed keeps the slugs off."),
    F("water-butt", "A water butt collects rain from the shed roof."),
    F("hose-ban", "There is a hosepipe ban until the end of August."),
    F("seed-wish", "Maybe try growing asparagus one year."),
    F("garden-mag", "A gardening magazine piece listed plants that attract bees."),
    F("fee-old", "The allotment rent is £45 a year.", observed_at="2024-03-01T00:00:00Z"),
    F("fee-new", "The council has raised allotment rent to £60 annually.", observed_at="2026-02-10T00:00:00Z"),
    F("shed-old", "The shed key is with Malcolm on plot 12.", **OLD),
    F("shed-new", "The shed key now hangs on the hook inside the gate.", **NEW),
    F("stuff-grow", "What am I growing this year? Remind me."),
    F("compost", "The compost bins are at the far end of the site."),
    F("neighbour", "Rosa on plot 15 swaps courgettes for our beans."),
    F("tools", "Borrowed a strimmer from the site committee."),
    F("frost", "Fleece went over the tender plants during the late frost."),
    F("chair", "A folding chair lives in the shed for tea breaks."),
], [
    ("multi", "What vegetables have I planted?", ["beans", "spuds", "squash"], ["stuff-grow"], None),
    ("multi", "How do we deal with pests on the plot?", ["copper"], ["slugs"], None),
    ("multi", "Where does our water come from given the restrictions?", ["water-butt", "hose-ban"], [], None),
    ("corroborate", "What happened to the lettuces and what did we do about it?", ["slugs", "copper"], [], None),
    ("distractor", "Which plot number is ours?", ["plot"], ["neighbour"], None),
    ("deep", "Who do we trade produce with?", ["neighbour"], [], None),
    ("conflict", "How much is the allotment rent?", ["fee-new"], ["fee-old"], None),
    ("conflict_declared", "Where is the shed key?", ["shed-new"], ["shed-old"], CURRENT),
    ("abstention", "What variety of tomato did we buy?", [], [], None),
], FILLER[0:18])

MONEY = store("money", [
    F("isa", "Saving £200 a month into a stocks and shares ISA."),
    F("emergency", "Three months of expenses sit in an easy-access account."),
    F("mortgage", "The mortgage overpayment is £150 each month."),
    F("streaming", "Paying for two streaming services, one with ads."),
    F("gym-sub", "The climbing wall membership comes out on the 3rd."),
    F("phone-sub", "Mobile contract is £18 a month until next spring."),
    F("budget-app", "I track spending in a budgeting app every Sunday."),
    F("tax-return", "Self-assessment is due by the end of January."),
    F("accountant", "Hannah, a friend who is an accountant, checks my return."),
    F("money-article", "Read an article comparing savings accounts and interest rates."),
    F("lottery-wish", "If we ever win the lottery we'll buy a campervan."),
    F("bank-old", "Our joint account is with Northern Building Society.", observed_at="2024-05-01T00:00:00Z"),
    F("bank-new", "We moved the joint account to a high-street bank with better app support.", observed_at="2026-03-12T00:00:00Z"),
    F("rate-old", "The ISA fund charges 0.45% a year.", **OLD),
    F("rate-new", "After switching platforms the fund fee dropped to 0.22% a year.", **NEW),
    F("stuff-subs", "Which subscriptions am I paying for? Check later."),
    F("pension", "My workplace pension gets a 5% employer contribution."),
    F("loan", "The car loan finishes in August next year."),
    F("charity", "A monthly donation goes to the local food bank."),
    F("cashback", "The credit card gives 1% cashback on groceries."),
], [
    ("multi", "What regular subscriptions come out of my account?", ["streaming", "gym-sub", "phone-sub"], ["stuff-subs", "charity"], None),
    ("multi", "How am I saving for the future?", ["isa", "emergency", "pension"], ["mortgage"], None),
    ("multi", "What debts am I still paying off?", ["mortgage", "loan"], [], None),
    ("corroborate", "Who helps with my tax and when is it due?", ["accountant", "tax-return"], [], None),
    ("distractor", "When is my self-assessment tax return due?", ["tax-return"], ["accountant"], None),
    ("deep", "How do I keep an eye on what I spend?", ["budget-app"], [], None),
    ("conflict", "Which bank holds our joint account?", ["bank-new"], ["bank-old"], None),
    ("conflict_declared", "What does the ISA fund cost each year?", ["rate-new"], ["rate-old", "isa"], CURRENT),
    ("abstention", "What is my credit score?", [], [], None),
], FILLER[1:18])

SCHOOL = store("school", [
    F("zoe-class", "Zoe is in Year 4 with Mr Adeyemi."),
    F("finn-class", "Finn started reception in September."),
    F("swim", "Zoe has swimming lessons on Tuesday after school."),
    F("cubs", "Finn goes to Beavers at the scout hut on Thursdays."),
    F("piano", "Zoe practises piano for fifteen minutes before dinner."),
    F("reading", "Finn brings home a reading book every Monday."),
    F("nut", "Finn must not have anything containing sesame."),
    F("glasses", "Zoe needs her glasses for the whiteboard."),
    F("trip", "The Year 4 trip to the science museum is in March."),
    F("pta", "I volunteer on the PTA bake sale rota."),
    F("school-news", "The school newsletter covered after-school clubs and fees."),
    F("tutor-wish", "Maybe find a maths tutor next year."),
    F("pickup-old", "Grandad does the Wednesday school pickup.", observed_at="2024-09-01T00:00:00Z"),
    F("pickup-new", "Wednesday collection is now covered by the breakfast-and-after-school club.", observed_at="2026-04-20T00:00:00Z"),
    F("uniform-old", "School uniform comes from the shop in town.", **OLD),
    F("uniform-new", "We now order the uniform online from the school's supplier.", **NEW),
    F("stuff-clubs", "Which clubs do the kids go to? Write it down."),
    F("lunch", "Zoe takes a packed lunch; Finn has school dinners."),
    F("bus", "There is no school bus, so we walk."),
], [
    ("multi", "What activities do the children do after school?", ["swim", "cubs", "piano"], ["stuff-clubs", "pickup-new"], None),
    ("multi", "What health or diet needs do teachers need to know about?", ["nut", "glasses"], [], None),
    ("multi", "What year groups are the kids in?", ["zoe-class", "finn-class"], [], None),
    ("corroborate", "How is Finn getting on with reading and what class is he in?", ["reading", "finn-class"], [], None),
    ("distractor", "When is the museum trip?", ["trip"], ["zoe-class"], None),
    ("deep", "How do I help out at school?", ["pta"], [], None),
    ("conflict", "Who collects the kids on Wednesdays?", ["pickup-new"], ["pickup-old"], None),
    ("conflict_declared", "Where do we get the school uniform from?", ["uniform-new"], ["uniform-old"], CURRENT),
    ("abstention", "What is the head teacher's name?", [], [], None),
], FILLER[2:18])

KITCHEN = store("kitchen", [
    F("oven", "The fan oven runs about ten degrees hot."),
    F("sourdough", "Our sourdough starter is called Doughvid and lives in the fridge."),
    F("knives", "The chef's knife needs sharpening every few weeks."),
    F("allergy-guest", "Our friend Leila cannot eat shellfish."),
    F("vegan", "Marcus has been vegan for two years."),
    F("glutenfree", "Priya avoids gluten."),
    F("signature", "Everyone asks for my lamb tagine."),
    F("weekly-shop", "The big food shop happens on Saturday morning."),
    F("veg-box", "A vegetable box is delivered every Friday."),
    F("freezer", "The chest freezer is in the garage."),
    F("cook-show", "Watched a cookery programme about slow cooking."),
    F("pasta-wish", "I'd like to learn to make fresh pasta someday."),
    F("hob-old", "We cook on a gas hob.", observed_at="2024-01-15T00:00:00Z"),
    F("hob-new", "The gas hob was replaced with an induction one.", observed_at="2026-05-02T00:00:00Z"),
    F("bin-old", "Food waste goes in the green caddy collected Mondays.", **OLD),
    F("bin-new", "Food waste collection is now on Wednesdays in the brown caddy.", **NEW),
    F("stuff-diets", "Note: whose diets do I need to cater for?"),
    F("spices", "Spices are in the drawer left of the cooker."),
    F("kettle", "The kettle is descaled monthly."),
], [
    ("multi", "What dietary requirements do my dinner guests have?", ["allergy-guest", "vegan", "glutenfree"], ["stuff-diets"], None),
    ("multi", "How does our food arrive each week?", ["weekly-shop", "veg-box"], [], None),
    ("multi", "What needs regular maintenance in the kitchen?", ["knives", "kettle"], ["oven"], None),
    ("corroborate", "What should I make when friends come round?", ["signature"], ["allergy-guest", "vegan", "glutenfree"], None),
    ("distractor", "Where is the freezer?", ["freezer"], [], None),
    ("deep", "Is the oven temperature accurate?", ["oven"], [], None),
    ("conflict", "What kind of hob do we have?", ["hob-new"], ["hob-old"], None),
    ("conflict_declared", "When is food waste collected?", ["bin-new"], ["bin-old"], CURRENT),
    ("abstention", "What brand is the dishwasher?", [], [], None),
], FILLER[3:18])

TECH = store("tech", [
    F("laptop", "My personal laptop is a three-year-old MacBook Air."),
    F("backup", "Photos back up to an external drive every Sunday night."),
    F("cloud", "Documents sync to a cloud folder automatically."),
    F("router", "The mesh Wi-Fi has three nodes upstairs and down."),
    F("printer", "The printer only works over USB now."),
    F("password", "I use a password manager with a long passphrase."),
    F("2fa", "Two-factor codes come from an authenticator app on my phone."),
    F("tv", "The smart TV needs restarting when apps freeze."),
    F("smart-plug", "Smart plugs turn the lamps on at dusk."),
    F("tech-blog", "A tech blog compared mesh routers and backup drives."),
    F("vr-wish", "Thinking about a VR headset for Christmas."),
    F("phone-old", "My phone is an Android from 2021.", observed_at="2024-02-01T00:00:00Z"),
    F("phone-new", "I switched to an iPhone in the summer sale.", observed_at="2026-07-14T00:00:00Z"),
    F("isp-old", "Broadband is a 70Mb copper line.", **OLD),
    F("isp-new", "Broadband is now full-fibre at 900Mb.", **NEW),
    F("stuff-backup", "How are my files backed up? Remind me."),
    F("kindle", "The e-reader charges about once a month."),
    F("speaker", "A speaker in the kitchen plays the radio in the morning."),
    F("cables", "Spare cables are in the labelled box under the stairs."),
], [
    ("multi", "How are my files and photos protected against loss?", ["backup", "cloud"], ["stuff-backup"], None),
    ("multi", "How do I keep my accounts secure?", ["password", "2fa"], [], None),
    ("multi", "What home automation do we have?", ["smart-plug", "speaker"], ["router", "tv"], None),
    ("corroborate", "What is the Wi-Fi setup and what speed is the line?", ["router", "isp-new"], ["isp-old"], None),
    ("distractor", "How do I print documents?", ["printer"], [], None),
    ("deep", "What do I read books on?", ["kindle"], [], None),
    ("conflict", "What phone do I have?", ["phone-new"], ["phone-old"], None),
    ("conflict_declared", "What broadband speed do we get?", ["isp-new"], ["isp-old"], CURRENT),
    ("abstention", "What is the Wi-Fi network name?", [], [], None),
], FILLER[4:18])

COMMUNITY = store("community", [
    F("foodbank", "I sort donations at the food bank on Saturday mornings."),
    F("litter", "The street litter-pick is the first Sunday of the month."),
    F("choir", "Rehearsals for the community choir are on Monday evenings."),
    F("library", "I help at the library's homework club once a fortnight."),
    F("councillor", "Our local councillor is Ms Okonjo."),
    F("petition", "Signed the petition for a zebra crossing on Mill Lane."),
    F("garden-group", "The residents' group planted bulbs along the verge."),
    F("neighbour-help", "I collect Mr Byrne's prescriptions because he can't drive."),
    F("church-hall", "The church hall can be booked for £15 an hour."),
    F("news-local", "The local paper ran a story about volunteering and charities."),
    F("run-wish", "Maybe organise a fun run next summer."),
    F("chair-old", "The residents' association is chaired by Bill Carter.", observed_at="2024-06-01T00:00:00Z"),
    F("chair-new", "Sunita Rao took over as chair of the residents' group.", observed_at="2026-03-30T00:00:00Z"),
    F("meet-old", "Residents' meetings are held in the pub function room.", **OLD),
    F("meet-new", "Residents' meetings now take place in the library annexe.", **NEW),
    F("stuff-vol", "Where do I volunteer? List for the CV."),
    F("defib", "There is a defibrillator outside the post office."),
    F("whatsapp", "The street WhatsApp group shares lost-cat alerts."),
], [
    ("multi", "Where do I volunteer my time?", ["foodbank", "library", "litter"], ["stuff-vol", "neighbour-help"], None),
    ("multi", "What regular community events do I attend?", ["choir", "litter"], ["foodbank", "library"], None),
    ("multi", "How do I help my neighbours?", ["neighbour-help"], ["whatsapp", "litter"], None),
    ("corroborate", "What have residents done to improve the street?", ["garden-group", "petition"], ["litter"], None),
    ("distractor", "Who is our local councillor?", ["councillor"], [], None),
    ("deep", "Where is the nearest defibrillator?", ["defib"], [], None),
    ("conflict", "Who chairs the residents' group?", ["chair-new"], ["chair-old"], None),
    ("conflict_declared", "Where do residents' meetings happen?", ["meet-new"], ["meet-old"], CURRENT),
    ("abstention", "When was the village hall built?", [], [], None),
], FILLER[5:18])

AS_OF = store("asof", [
    F("car-old", "We drive a silver Skoda estate.", **OLD),
    F("car-new", "We now drive a blue electric Kia.", **NEW),
    F("insure-old", "Car insurance was with Direct Line.", **OLD),
    F("insure-new", "Car insurance moved to Admiral.", **NEW),
    F("garage", "The local garage on Station Road does our servicing."),
    F("charger", "A wall charger was fitted on the driveway."),
], [
    ("conflict_declared", "Which car did we have in mid-2025?", ["car-old"], ["car-new"], AS_OF_2025),
    ("conflict_declared", "Who insured the car in mid-2025?", ["insure-old"], ["insure-new"], AS_OF_2025),
    ("conflict_declared", "What car do we drive?", ["car-new"], ["car-old", "charger"], CURRENT),
], FILLER[6:18])

print(json.dumps({"cohort": "819-c8-development", "author": "engineering (self-authored, synthetic; fresh after C7)",
                  "scenarios": [GARDEN, MONEY, SCHOOL, KITCHEN, TECH, COMMUNITY, AS_OF]}, indent=1))
