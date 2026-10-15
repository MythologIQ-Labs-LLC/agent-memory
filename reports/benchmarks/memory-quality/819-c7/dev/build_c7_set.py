"""Build the #819 C7 diagnostic set: multi-evidence ranking cases (self-authored, synthetic).

Six stores, one per life domain. Each store has about 45 memories:
- the domain's evidence;
- topically related non-answers;
- ordinary filler from other parts of life, which shares only function words with most
  questions.

Query kinds:
- ``multi``: 2-4 facts, all needed, worded differently from the question and from each other;
- ``corroborate``: one fact matches the question's words, and the others support it in other
  words;
- ``distractor``: one answer, plus several topical non-answers that share the question's words;
- ``deep``: one answer that shares only weak words with the question;
- ``conflict``: an older and a newer statement of the same thing, both remembered, with
  no correction. The newer one is needed, and the older one is allowed;
- ``abstention``: nothing in the store answers;
- ``stuffing``: a question-shaped note sits beside the real answer.

No benchmark data, gold or wording is used. Expectations are fixed here, before any C7 runtime
change.

    python build_c7_set.py > c7-scenarios.json
"""

import json

SCOPE = "user:c7"

FILLER = [
    "Bins go out on Tuesday nights.",
    "The spare key is under the blue flowerpot.",
    "Wi-Fi password is on a sticky note inside the cupboard.",
    "I prefer oat milk in coffee.",
    "The car's MOT is due in November.",
    "Library books are due back on the 14th.",
    "My shoe size is 9.",
    "The plumber's number is saved as 'Dave pipes'.",
    "We keep batteries in the second kitchen drawer.",
    "The smoke alarm chirps when its battery is low.",
    "I don't like coriander.",
    "Parking at the station costs £6 a day.",
    "The router reboots itself every Sunday at 4am.",
    "There is a dentist check-up booked for the spring.",
    "The good scissors live in the desk organiser.",
    "I switched my phone plan to a SIM-only deal.",
    "Our postcode was mistyped on the council letter.",
    "The neighbours' cat sometimes sleeps in our shed.",
    "I usually go to bed around eleven.",
    "The umbrella with the broken spoke should be thrown away.",
]


def store(sid, facts, queries, filler_slice):
    ops = [{"op": "remember", "scope": SCOPE, "ref": f"memory:{ref}", "text": text,
            **({"observed_at": when} if when else {})} for ref, text, when in facts]
    ops += [{"op": "remember", "scope": SCOPE, "ref": f"memory:filler-{sid}-{i}", "text": text}
            for i, text in enumerate(filler_slice)]
    qs = []
    for n, (kind, query, must, may) in enumerate(queries, start=1):
        qs.append({"id": f"{sid}-{n}", "kind": kind, "query": query, "scope": SCOPE,
                   "expect": {"must_include": [f"memory:{r}" for r in must],
                              "may_include": [f"memory:{r}" for r in may], "must_exclude": []}})
    return {"id": sid, "category": "c7-diagnostic", "operations": ops, "queries": qs}


def F(ref, text, when=None):
    return (ref, text, when)


TRAVEL = store("travel", [
    F("lisbon", "Spent four days in Lisbon in March eating pastéis de nata.", "2026-03-20T00:00:00Z"),
    F("kyoto", "The Kyoto visit in May was rainy but the temples were worth it.", "2026-05-18T00:00:00Z"),
    F("highlands", "Drove up to the Highlands for a long weekend in August.", "2026-08-30T00:00:00Z"),
    F("peru-wish", "One day I want to hike to Machu Picchu."),
    F("rome-sister", "My sister went to Rome for her honeymoon."),
    F("passport", "My passport expires in February 2028."),
    F("insurance", "Annual travel insurance renews every January with the bank."),
    F("lounge", "The credit card gives two free airport lounge passes a year."),
    F("seat", "I always book an aisle seat on long flights."),
    F("jetlag", "Melatonin helps me adjust after crossing time zones."),
    F("airline-old", "Our usual airline for holidays is TAP.", "2024-02-01T00:00:00Z"),
    F("airline-new", "We now mostly fly easyJet because it serves our local airport.", "2026-04-02T00:00:00Z"),
    F("trip-budget", "We set aside about £3,000 a year for holidays."),
    F("packing", "A packing list template lives in my notes app."),
    F("travel-trip-word", "Trip planning spreadsheets never get finished."),
    F("trip-blog", "I read a blog about trips to Iceland last week."),
    F("visa", "Japan did not require a visa for our stay."),
    F("adapter", "We bought a universal plug adapter for the Kyoto visit."),
    F("camera", "The old camera's battery barely lasts a day now."),
    F("souvenir", "The ceramic bowl on the shelf came from a market in Lisbon."),
    F("stuff-trips", "Question for later: which trips did I take this year?"),
    F("ferry", "The ferry to the islands got cancelled because of wind."),
    F("hotel-pref", "Small guesthouses suit us better than big hotels."),
    F("map-app", "Offline maps saved us when there was no signal."),
    F("rail-card", "A railcard knocks a third off train fares."),
], [
    ("multi", "Which trips did I take this year?", ["lisbon", "kyoto", "highlands"], ["stuff-trips", "adapter", "souvenir", "ferry"]),
    ("multi", "Where have I been on holiday recently?", ["lisbon", "kyoto", "highlands"], ["souvenir", "adapter"]),
    ("corroborate", "What did we bring back or buy for the Japan holiday?", ["adapter"], ["kyoto", "visa"]),
    ("distractor", "When does my passport run out?", ["passport"], []),
    ("deep", "How do I cope with jet lag?", ["jetlag"], []),
    ("conflict", "Which airline do we usually fly with?", ["airline-new"], ["airline-old"]),
    ("abstention", "What was the name of the hotel in Paris?", [], []),
    ("multi", "What perks or discounts do I have for travelling?", ["lounge", "rail-card"], ["insurance"]),
], FILLER[0:20])

HEALTH = store("health", [
    F("bp-med", "I take amlodipine every morning for blood pressure."),
    F("vit-d", "A vitamin D tablet with breakfast during winter."),
    F("allergy-med", "Cetirizine in hay fever season."),
    F("statin", "Atorvastatin at night to keep cholesterol down."),
    F("gp", "Dr Okafor at the Riverside practice is my GP."),
    F("physio", "Physio for the left knee is on Thursday afternoons."),
    F("knee", "I twisted my left knee playing five-a-side in June."),
    F("dentist", "My dentist is Ms Patel on Station Road."),
    F("blood-test", "The last blood test showed slightly low iron."),
    F("iron", "Eating more spinach and lentils since the iron result."),
    F("sleep", "I have been sleeping badly since the new job started."),
    F("eyes", "New glasses prescription: -2.25 in both eyes."),
    F("gym-old", "The gym membership costs £35 a month.", "2025-01-10T00:00:00Z"),
    F("gym-new", "The gym put the monthly fee up to £42.", "2026-03-05T00:00:00Z"),
    F("health-article", "I read an article about blood pressure monitors."),
    F("bp-cuff-wish", "Maybe buy a home monitor for checking pressure."),
    F("flu-jab", "Had the flu jab at the pharmacy in October."),
    F("run", "Running three times a week, about 5k each."),
    F("stuff-meds", "Remind me which medicines I take."),
    F("water", "Trying to drink two litres of water a day."),
    F("caffeine", "Cutting down to one coffee after lunch."),
    F("health-podcast", "A podcast episode said walking after dinner helps digestion."),
    F("insurance-h", "Private health cover comes through work."),
    F("mole", "The dermatologist said the mole on my back is fine."),
    F("pharmacy", "Repeat prescriptions are collected from Boots on the high street."),
], [
    ("multi", "What medications am I on?", ["bp-med", "vit-d", "allergy-med", "statin"], ["stuff-meds", "pharmacy"]),
    ("multi", "Who looks after my health?", ["gp", "dentist"], ["physio", "mole", "pharmacy"]),
    ("corroborate", "What is going on with my knee?", ["knee", "physio"], []),
    ("corroborate", "What did the blood test show and what am I doing about it?", ["blood-test", "iron"], []),
    ("distractor", "Do I have a blood pressure monitor?", ["bp-cuff-wish"], ["health-article"]),
    ("deep", "Why am I so tired lately?", ["sleep"], []),
    ("conflict", "How much does the gym cost each month?", ["gym-new"], ["gym-old"]),
    ("abstention", "What is my blood type?", [], []),
], FILLER[1:20])

WORK = store("work", [
    F("manager-old", "My manager is Priya.", "2025-06-01T00:00:00Z"),
    F("manager-new", "Since the reorg I report to Daniel.", "2026-02-15T00:00:00Z"),
    F("proj-atlas", "Leading the Atlas migration to the new billing platform."),
    F("proj-beacon", "Also reviewing Beacon, the onboarding redesign."),
    F("proj-old", "The Comet project was shelved last year."),
    F("deadline", "Atlas has to be live by the end of November."),
    F("risk", "Data quality in the legacy invoices could delay the cutover."),
    F("hire-1", "Amara joined my team as a data engineer in September."),
    F("hire-2", "We also brought on Tomás, a backend developer, last month."),
    F("colleague", "Lena in finance signs off the billing rules."),
    F("office", "The office is in Manchester and I go in Tuesdays and Thursdays."),
    F("commute", "The 7:42 train gets me to the office by half eight."),
    F("laptop", "My work laptop is a 14-inch ThinkPad."),
    F("review", "Annual review is in January."),
    F("raise", "I am hoping for a promotion to principal next year."),
    F("work-newsletter", "The company newsletter had a piece on teams and projects."),
    F("work-quote", "Someone joked that every project is late by definition."),
    F("standup", "Daily stand-up at 9:30 on video."),
    F("vpn", "The VPN drops whenever the laptop sleeps."),
    F("expenses", "Expenses must be submitted by the 25th of each month."),
    F("stuff-team", "Note to self: who is on my team now?"),
    F("conference", "Speaking at a fintech conference in London next spring."),
    F("training", "Signed up for a leadership course through work."),
    F("pension", "Work matches pension contributions up to 6%."),
], [
    ("multi", "Which projects am I working on?", ["proj-atlas", "proj-beacon"], ["deadline", "risk"]),
    ("multi", "Who are the new people on my team?", ["hire-1", "hire-2"], ["stuff-team"]),
    ("corroborate", "When is the Atlas launch and what could get in the way?", ["deadline", "risk"], ["proj-atlas"]),
    ("distractor", "Who approves the billing rules?", ["colleague"], ["proj-atlas"]),
    ("deep", "How do I get to work?", ["commute"], ["office"]),
    ("conflict", "Who is my manager?", ["manager-new"], ["manager-old"]),
    ("abstention", "What is my employee ID number?", [], []),
    ("multi", "What are the regular deadlines and meetings I need to remember?", ["expenses", "standup", "review"], ["deadline"]),
], FILLER[2:20])

HOME = store("home", [
    F("boiler", "The boiler was serviced in September by HeatRight."),
    F("roof", "A roofer fixed the slipped tiles above the bathroom."),
    F("damp", "There is a damp patch in the back bedroom corner."),
    F("dehumid", "We run a dehumidifier in the back bedroom overnight."),
    F("sofa", "Bought a green corduroy sofa in the summer sale."),
    F("fridge", "The new fridge-freezer arrived in July."),
    F("energy-old", "Electricity is with Octopus on a fixed tariff.", "2025-03-01T00:00:00Z"),
    F("energy-new", "We switched electricity to a variable tracker plan.", "2026-05-20T00:00:00Z"),
    F("council-tax", "Council tax is band C, paid over ten months."),
    F("mortgage", "The fixed rate on the mortgage ends in 2027."),
    F("insurance-home", "Home insurance renews in April."),
    F("garden", "Planted tomatoes and courgettes along the fence."),
    F("home-blog", "Saw a blog post about home renovation costs."),
    F("home-wish", "One day we'd like a loft conversion."),
    F("paint", "Bought two tins of 'Elephant's Breath' for the hallway."),
    F("tap", "The kitchen tap drips if not turned off firmly."),
    F("stuff-repairs", "Which repairs did we have done this year?"),
    F("cleaner", "The window cleaner comes every six weeks."),
    F("alarm", "The burglar alarm code changed after the engineer visit."),
    F("shed", "The shed lock is rusted shut."),
    F("bike-store", "Bikes are kept in the hallway because the shed is full."),
    F("internet", "Broadband is 500Mb fibre."),
    F("ladder", "Borrowed a ladder from next door and haven't returned it."),
], [
    ("multi", "What maintenance work has been done on the house?", ["boiler", "roof"], ["stuff-repairs", "alarm"]),
    ("multi", "What have we bought for the house this year?", ["sofa", "fridge", "paint"], ["dehumid"]),
    ("corroborate", "What are we doing about the damp?", ["damp", "dehumid"], []),
    ("distractor", "When does the home insurance renew?", ["insurance-home"], []),
    ("deep", "Where do the bicycles live?", ["bike-store"], ["shed"]),
    ("conflict", "What electricity tariff are we on?", ["energy-new"], ["energy-old"]),
    ("abstention", "How old is the washing machine?", [], []),
    ("multi", "What regular bills do we pay for the house?", ["council-tax", "mortgage", "internet"], ["insurance-home", "energy-new"]),
], FILLER[3:20])

FAMILY = store("family", [
    F("mum-bday", "Mum's birthday is on the 3rd of June."),
    F("dad-bday", "Dad turns seventy in October."),
    F("niece", "My niece Ella started primary school this September."),
    F("brother", "My brother Sam lives in Bristol with his partner Jo."),
    F("gift-mum", "Got Mum a pottery class voucher last year."),
    F("gift-dad", "Dad would love a new set of golf clubs."),
    F("friend-maya", "Maya and I have dinner on the first Friday of each month."),
    F("friend-tom", "Tom is moving to Canada in the new year."),
    F("wedding", "Cousin Ruth is getting married in Cornwall next July."),
    F("allergy-ella", "Ella is allergic to peanuts."),
    F("veg-jo", "Jo is vegetarian."),
    F("grandma", "Grandma moved into a care home in Leeds."),
    F("visit-grandma", "We visit Grandma every other Sunday."),
    F("family-chat", "The family group chat is mostly photos of dogs."),
    F("family-article", "Read an article about family birthdays and gift ideas."),
    F("stuff-bdays", "What birthdays are coming up? Must check."),
    F("dog-sam", "Sam and Jo have a spaniel called Pepper."),
    F("babysit", "I babysit Ella on Wednesday evenings."),
    F("christmas-old", "Christmas is at Mum and Dad's this year.", "2025-11-01T00:00:00Z"),
    F("christmas-new", "Christmas has moved to Sam's house in Bristol.", "2026-09-10T00:00:00Z"),
    F("phone-dad", "Dad's new mobile number is in my contacts."),
    F("recipe-mum", "Mum's lasagne recipe is in the blue folder."),
], [
    ("multi", "Whose birthdays are coming up?", ["mum-bday", "dad-bday"], ["stuff-bdays", "gift-dad", "gift-mum"]),
    ("multi", "What dietary needs should I plan for when the family visits?", ["allergy-ella", "veg-jo"], []),
    ("corroborate", "How is Grandma and when do we see her?", ["grandma", "visit-grandma"], []),
    ("distractor", "What could I get Dad as a present?", ["gift-dad"], ["dad-bday", "gift-mum"]),
    ("deep", "Who is leaving the country soon?", ["friend-tom"], []),
    ("conflict", "Where are we spending Christmas?", ["christmas-new"], ["christmas-old"]),
    ("abstention", "What is Maya's surname?", [], []),
    ("multi", "What do I do regularly with friends and family each week or month?", ["friend-maya", "visit-grandma", "babysit"], []),
], FILLER[4:20])

HOBBY = store("hobby", [
    F("guitar", "Learning fingerpicking on the acoustic guitar."),
    F("lessons", "Guitar lessons with Marcus every Monday evening."),
    F("piano-old", "I used to play piano as a kid."),
    F("spanish", "Doing twenty minutes of Spanish on Duolingo daily."),
    F("course", "Enrolled in an evening pottery course at the community centre."),
    F("climb", "Bouldering on Saturdays with Maya's climbing club."),
    F("swim", "Swimming lengths before work on Wednesdays."),
    F("book-club", "The book club is reading 'The Overstory' this month."),
    F("photo", "Bought a second-hand mirrorless camera for street photography."),
    F("chess", "My online chess rating is about 1400."),
    F("run-race", "Signed up for the Great North Run in September."),
    F("strings", "Need new strings for the acoustic soon."),
    F("hobby-mag", "A magazine article listed fifty new hobbies to try."),
    F("hobby-wish", "Maybe take up sailing someday."),
    F("stuff-hobbies", "List my hobbies for the profile form."),
    F("bike-club-old", "I ride with the Thursday cycling club.", "2025-04-01T00:00:00Z"),
    F("bike-club-new", "I've moved to the Sunday morning cycling group.", "2026-06-12T00:00:00Z"),
    F("sketch", "Sketchbook goes everywhere with me."),
    F("garden-h", "Growing chillies on the windowsill."),
    F("puzzle", "Finished a 1000-piece jigsaw of Venice."),
    F("podcast-h", "Listening to a history podcast on the commute."),
], [
    ("multi", "What am I learning at the moment?", ["guitar", "spanish", "course"], ["lessons", "strings"]),
    ("multi", "Which sports do I do each week?", ["climb", "swim", "bike-club-new"], ["run-race", "bike-club-old"]),
    ("corroborate", "How is the guitar going and who teaches me?", ["guitar", "lessons"], ["strings"]),
    ("distractor", "What race have I entered?", ["run-race"], []),
    ("deep", "What is the reading group doing?", ["book-club"], []),
    ("conflict", "When do I go cycling with the club?", ["bike-club-new"], ["bike-club-old"]),
    ("abstention", "What grade did I get in my piano exam?", [], ["piano-old"]),
    ("multi", "What creative things do I do?", ["photo", "sketch", "course"], ["guitar", "puzzle"]),
], FILLER[5:20])

print(json.dumps({"cohort": "819-c7-diagnostic", "author": "engineering (self-authored, synthetic)",
                  "scenarios": [TRAVEL, HEALTH, WORK, HOME, FAMILY, HOBBY]}, indent=1))
