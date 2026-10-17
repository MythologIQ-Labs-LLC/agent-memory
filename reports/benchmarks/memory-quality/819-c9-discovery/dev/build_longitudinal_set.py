#!/usr/bin/env python3
"""Self-authored longitudinal development set for the #819 C9-D discovery lane.

Each scenario is one user's store: 30 stable everyday memories, a theme of five "living" memories
that the user corrects three times each (four versions, the last current), two theme memories the
user later forgets, and three theme memories written in another scope. Queries ask about the
theme in the user's own words (aggregate and single), name a living memory's words directly,
ask about a stable memory, and ask about something never stored.

Written from the mechanism (bounded semantic slots shared with superseded versions), not from
any cohort: no e4/e5/e6 content, no benchmark gold. Texts were written before any cosine was
computed. Deterministic: the output depends only on this file.

    python build_longitudinal_set.py > longitudinal-scenarios.json
"""

import json

SCOPE, OTHER = "user:c9d", "user:c9d-other"

STABLE = [
    "Our neighbour Priya waters the plants when we are away.",
    "The car insurance renews every March.",
    "I prefer window seats on long flights.",
    "My sister lives in Galway with her two dogs.",
    "The wifi password is on a card inside the hall cupboard.",
    "We get the vegetable box delivered on Thursdays.",
    "I can't stand coriander.",
    "The spare house key is with the people at number 12.",
    "Dad's birthday is on the 3rd of November.",
    "I keep my passport in the blue folder in the study.",
    "The recycling goes out every other Monday.",
    "My dentist is Dr Okafor on Mill Lane.",
    "I usually take the 7:40 train into town.",
    "Our cat is called Pepper and she is fourteen.",
    "I learned to sail at a summer camp in Wales.",
    "The bank changed my sort code after the merger.",
    "We painted the living room a pale green last spring.",
    "My favourite pizza place is Luigi's on the corner.",
    "I'm allergic to penicillin.",
    "The broadband contract ends in January.",
    "I play five-a-side football with old university friends.",
    "Grandma's recipe book is on the top kitchen shelf.",
    "I switched my phone plan to the cheaper monthly one.",
    "We have a standing dinner with the Harrisons on the first Friday of the month.",
    "The bike lock code is the same as the garage code.",
    "My library card expires next summer.",
    "I support the local rugby club.",
    "The council tax is paid by direct debit.",
    "I wear reading glasses for screens now.",
    "The kids' school uniform comes from the shop on Bridge Street.",
]

# theme -> (living memories: ref -> four versions, forgotten, other-scope, queries)
THEMES = {
    "health": {
        "living": {
            "bp": ["I take 5mg of amlodipine every morning for blood pressure.",
                   "The doctor raised my amlodipine to 10mg each morning.",
                   "My amlodipine is back down to 5mg, taken at night now.",
                   "I now take 5mg of amlodipine at bedtime for my blood pressure."],
            "inhaler": ["I use the blue inhaler only when wheezy.",
                        "I use the brown preventer inhaler twice a day.",
                        "The preventer inhaler is down to once a day in the evening.",
                        "I take one puff of the preventer inhaler each evening."],
            "vitd": ["I take a vitamin D tablet in winter.",
                     "I take vitamin D all year round now.",
                     "I take a double dose of vitamin D on Mondays.",
                     "Vitamin D is now a weekly 20,000 unit capsule on Mondays."],
            "allergy": ["I take cetirizine for hay fever in June.",
                        "I take cetirizine from May to July.",
                        "I switched from cetirizine to loratadine for hay fever.",
                        "Loratadine every morning from April to August for hay fever."],
            "eyedrops": ["I use lubricating eye drops when my eyes feel dry.",
                         "I use the eye drops three times a day.",
                         "The optician changed my eye drops to a gel at night.",
                         "Eye gel goes in at night; drops during the day only if needed."],
        },
        "forgotten": {"old-statin": "I used to take a statin but stopped.",
                      "old-iron": "I took iron tablets for a month after the blood test."},
        "other": ["I take metformin twice a day.", "I use a steroid nasal spray.",
                  "I take omega-3 capsules with breakfast."],
        "queries": [
            ("aggregate", "What medication am I on these days?", ["bp", "inhaler", "vitd", "allergy", "eyedrops"]),
            ("single", "How do I manage my blood pressure?", ["bp"]),
            ("lexical", "When do I use the preventer inhaler?", ["inhaler"]),
            ("stable", "Which antibiotic must I avoid?", ["s18"]),
            ("absent", "How much insulin do I inject?", []),
        ],
    },
    "kids": {
        "living": {
            "swim": ["Maya has swimming lessons on Tuesdays at 5.",
                     "Maya's swimming moved to Wednesdays at 5.",
                     "Maya's swimming is now Wednesdays at 6 at the leisure centre.",
                     "Maya swims on Wednesday evenings at 6:15 at the leisure centre."],
            "piano": ["Leo starts piano with Mrs Grant on Mondays.",
                      "Leo's piano lesson is Mondays at 4:30.",
                      "Leo's piano lesson moved to Thursdays at 4:30.",
                      "Leo has piano with Mrs Grant on Thursdays at 4:45."],
            "football": ["Leo trains with the under-10s on Saturday mornings.",
                         "Under-10s football training is Saturdays at 9.",
                         "Leo's football training moved to Friday after school.",
                         "Leo has football training on Fridays at 4 on the school field."],
            "coding": ["Maya joined the coding club at the library.",
                       "Coding club meets every second Saturday.",
                       "Coding club is now every Saturday at 11.",
                       "Maya goes to coding club at the library every Saturday at 11:30."],
            "art": ["Both kids do an art class in the holidays.",
                    "The art class runs on Sunday afternoons in term time.",
                    "Art class moved to Sunday mornings.",
                    "The kids' art class is Sunday mornings at 10 in the church hall."],
        },
        "forgotten": {"old-drama": "Maya did a drama club last year.",
                      "old-chess": "Leo tried chess club for a term."},
        "other": ["Sam goes to gymnastics on Mondays.", "Ava has ballet on Saturdays.",
                  "The twins do judo on Thursdays."],
        "queries": [
            ("aggregate", "What clubs and lessons do the children have each week?",
             ["swim", "piano", "football", "coding", "art"]),
            ("single", "When does my son practise with his team?", ["football"]),
            ("lexical", "What time is Maya's swimming?", ["swim"]),
            ("stable", "Where do we buy school clothes?", ["s29"]),
            ("absent", "When is Leo's karate grading?", []),
        ],
    },
    "work": {
        "living": {
            "migration": ["The database migration is planned for the spring.",
                          "The database migration slipped to June.",
                          "The database migration is in testing with two tables left.",
                          "The database migration is in final testing and goes live in July."],
            "hiring": ["We are hiring two backend engineers.",
                       "We made one offer for the backend roles.",
                       "One backend engineer accepted; the second role is open.",
                       "The second backend role is down to two final candidates."],
            "report": ["The quarterly report is due at the end of the month.",
                       "The quarterly report needs sign-off from finance first.",
                       "Finance signed off; the quarterly report needs the sales figures.",
                       "The quarterly report is waiting only on the sales figures from Dana."],
            "vendor": ["The cloud vendor contract is up for renewal.",
                       "We asked the cloud vendor for a discount on renewal.",
                       "The vendor offered 8% off a two-year renewal.",
                       "Legal is reviewing the vendor's two-year renewal at 8% off."],
            "onboarding": ["I'm writing the onboarding guide for new starters.",
                           "The onboarding guide has a first draft.",
                           "The onboarding guide is with the team for comments.",
                           "I'm folding the team's comments into the onboarding guide."],
        },
        "forgotten": {"old-offsite": "I was organising the team offsite.",
                      "old-audit": "I helped with last year's security audit."},
        "other": ["The payments API rewrite is in progress.", "We are hiring a designer.",
                  "The annual budget is due next week."],
        "queries": [
            ("aggregate", "What am I busy with at the office right now?",
             ["migration", "hiring", "report", "vendor", "onboarding"]),
            ("single", "Where are we with recruiting?", ["hiring"]),
            ("lexical", "When does the database migration go live?", ["migration"]),
            ("stable", "Which train do I catch to get into town?", ["s12"]),
            ("absent", "Who is my mentor at work?", []),
        ],
    },
    "house": {
        "living": {
            "tap": ["The kitchen tap is dripping.",
                    "The kitchen tap needs a new washer.",
                    "The washer didn't fix it; the kitchen tap needs replacing.",
                    "A new kitchen tap is ordered and the plumber fits it on Friday."],
            "roof": ["A roof tile slipped in the storm.",
                     "The roofer will look at the slipped tile next week.",
                     "The roofer says three tiles need replacing.",
                     "Three roof tiles are booked to be replaced after the rain."],
            "boiler": ["The boiler service is due in October.",
                       "The boiler service was moved to November.",
                       "The engineer found a faulty pressure valve on the boiler.",
                       "The boiler's pressure valve part is on back order."],
            "fence": ["A fence panel blew down at the back.",
                      "We bought a replacement fence panel.",
                      "The fence post is rotten too, so the panel can't go up yet.",
                      "We need a new fence post before the panel goes back up."],
            "latch": ["The bedroom window latch is stiff.",
                      "The bedroom window latch has snapped.",
                      "I ordered a replacement window latch online.",
                      "The replacement window latch arrived but is the wrong size."],
        },
        "forgotten": {"old-gutter": "The gutter over the porch was blocked.",
                      "old-damp": "There was a damp patch in the bathroom."},
        "other": ["The garage door sticks.", "The loft hatch needs a ladder.",
                  "The shed roof leaks."],
        "queries": [
            ("aggregate", "What jobs around the house are still outstanding?",
             ["tap", "roof", "boiler", "fence", "latch"]),
            ("single", "What's wrong with the heating?", ["boiler"]),
            ("lexical", "When is the plumber fitting the kitchen tap?", ["tap"]),
            ("stable", "What colour did we paint the lounge?", ["s16"]),
            ("absent", "When is the chimney being swept?", []),
        ],
    },
    "travel": {
        "living": {
            "lisbon": ["We are thinking about Lisbon in May.",
                       "Flights to Lisbon are booked for the 12th of May.",
                       "The Lisbon flight moved to the 14th of May.",
                       "We fly to Lisbon on the 14th of May and stay in Alfama."],
            "wedding": ["Tom's wedding is in York in the summer.",
                        "Tom's wedding in York is on the 2nd of August.",
                        "We booked a hotel near the minster for Tom's wedding.",
                        "For Tom's wedding we take the train to York on the 1st of August."],
            "ski": ["We might go skiing in February.",
                    "The ski week is booked for half term in Austria.",
                    "The ski chalet changed to one in Söll.",
                    "Our ski week in Söll starts on the 15th of February."],
            "berlin": ["I may present at a conference in Berlin.",
                       "My Berlin conference talk was accepted.",
                       "The Berlin conference is the 9th and 10th of October.",
                       "I'm flying to Berlin for the conference on the 8th of October."],
            "camping": ["We want a camping weekend in the Lakes.",
                        "The camping weekend is pencilled in for June.",
                        "We booked a pitch at Great Langdale for June.",
                        "Our Great Langdale camping weekend is the 20th to 22nd of June."],
        },
        "forgotten": {"old-paris": "We talked about a weekend in Paris.",
                      "old-cruise": "Mum suggested a cruise."},
        "other": ["We are going to Crete in July.", "A road trip to Scotland in April.",
                  "A weekend in Bruges in March."],
        "queries": [
            ("aggregate", "Where are we going away this year?",
             ["lisbon", "wedding", "ski", "berlin", "camping"]),
            ("single", "When is my work trip to Germany?", ["berlin"]),
            ("lexical", "When do we fly to Lisbon?", ["lisbon"]),
            ("stable", "Where do I keep my passport?", ["s9"]),
            ("absent", "Which hotel did we book in Rome?", []),
        ],
    },
    "fitness": {
        "living": {
            "squat": ["I'm aiming to squat 80kg.",
                      "I squatted 80kg; the next goal is 90kg.",
                      "I'm squatting 85kg for sets of five.",
                      "I'm working up to 90kg squats for sets of five."],
            "run": ["My long run is 8km on Sundays.",
                    "My Sunday long run is up to 12km.",
                    "The Sunday long run is 15km at an easy pace.",
                    "I run 18km slowly on Sunday mornings to build for the half marathon."],
            "swim": ["I swim once a week at lunchtime.",
                     "I swim twice a week, Tuesday and Thursday lunchtimes.",
                     "Swimming dropped to Thursdays only.",
                     "I swim 40 lengths on Thursday lunchtimes."],
            "rest": ["Friday is my rest day.",
                     "I take Wednesdays and Fridays off training.",
                     "Wednesday is now a yoga day instead of a rest day.",
                     "Only Friday is a full rest day; Wednesday is yoga."],
            "cycle": ["I'd like to cycle to work.",
                      "I cycle to work on Mondays.",
                      "I cycle to work on Mondays and Wednesdays.",
                      "I cycle the 9km to work three days a week."],
        },
        "forgotten": {"old-tennis": "I played tennis on Saturdays.",
                      "old-boxing": "I tried a boxing class."},
        "other": ["I do pilates on Mondays.", "I row 5km on the machine.",
                  "I climb at the wall on Fridays."],
        "queries": [
            ("aggregate", "What does my weekly exercise routine look like?",
             ["squat", "run", "swim", "rest", "cycle"]),
            ("single", "How far am I going on my weekend jog?", ["run"]),
            ("lexical", "How many lengths do I swim?", ["swim"]),
            ("stable", "How old is our cat?", ["s13"]),
            ("absent", "What is my marathon personal best?", []),
        ],
    },
}


def build() -> dict:
    scenarios = []
    for name, theme in THEMES.items():
        ops = [{"op": "remember", "scope": SCOPE, "ref": f"memory:s{i}", "text": text}
               for i, text in enumerate(STABLE)]
        living = theme["living"]
        ops += [{"op": "remember", "scope": SCOPE, "ref": f"memory:{ref}", "text": versions[0]}
                for ref, versions in living.items()]
        ops += [{"op": "remember", "scope": SCOPE, "ref": f"memory:{ref}", "text": text}
                for ref, text in theme["forgotten"].items()]
        ops += [{"op": "remember", "scope": OTHER, "ref": f"memory:o{i}", "text": text}
                for i, text in enumerate(theme["other"])]
        for version in (1, 2, 3):  # the user's corrections arrive in rounds
            ops += [{"op": "correct", "scope": SCOPE, "ref": f"memory:{ref}", "text": versions[version]}
                    for ref, versions in living.items()]
        ops += [{"op": "forget", "scope": SCOPE, "ref": f"memory:{ref}"} for ref in theme["forgotten"]]
        excluded = ([{"ref": f"memory:{ref}", "reason": "forgotten"} for ref in theme["forgotten"]]
                    + [{"ref": f"{OTHER}#memory:o{i}", "reason": "other_scope"} for i in range(len(theme["other"]))])
        queries = [{"id": f"{name}-{kind}", "scope": SCOPE, "query": text, "family": kind,
                    "expect": {"must_include": [f"memory:{ref}" for ref in needed], "may_include": [],
                               "must_exclude": excluded}}
                   for kind, text, needed in theme["queries"]]
        scenarios.append({"id": name, "category": "c9d-longitudinal", "operations": ops, "queries": queries})
    return {"cohort": "819-c9d-longitudinal-dev", "authored_by": "runtime engineer (self-authored development data)",
            "scenarios": scenarios}


if __name__ == "__main__":
    print(json.dumps(build(), indent=1, ensure_ascii=False))
