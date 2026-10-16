"""Second reviewer-authored multi-evidence set (distinct wording and domains from every engineering set)."""
import json
from pathlib import Path
S = "user:rvm"
def rem(ref, text): return {"op": "remember", "scope": S, "ref": ref, "text": text}
FILL = [
 "The bathroom grout needs redoing.", "There is a fox that visits the garden at night.", "We buy coffee beans from the roastery on Dalry Road.",
 "The kids' bikes are in the garage.", "My laptop is a 2021 ThinkPad.", "We get a veg box delivered on Tuesdays.",
 "The hall carpet was replaced in 2022.", "Our street has a bake sale every June.", "I listen to podcasts on the commute.",
 "The dishwasher salt runs out quickly.", "We have a standing order for the window cleaner.", "The attic is full of old toys.",
 "Grandad grows tomatoes in his greenhouse.", "The bus stop moved further down the road.", "We watch a film together on Friday nights.",
 "There are two smoke alarms upstairs.", "The fridge magnet from Lisbon fell off.", "My reading glasses are by the bed.",
 "The neighbours have a new trampoline.", "We switched to oat milk.", "The garden tap freezes in winter.",
 "I renewed my library card last month.", "Our cat sleeps on the radiator shelf.", "The postman comes around eleven.",
]
ops = [rem(f"memory:x{i}", t) for i, t in enumerate(FILL)]
facts = {
 # Q1 count over time: how many times did the boiler break
 "b1": "The boiler broke down in January 2024 and Gavin replaced the pump.",
 "b2": "No heating again last November; the boiler's fan had failed.",
 "b3": "In March the boiler lost pressure and needed a new valve.",
 # Q2 three-hop: what car does my wife's boss drive
 "w1": "My wife, Laura, works at a design studio in Glasgow.",
 "w2": "Laura's boss at the studio is called Fergus.",
 "w3": "Fergus drives an old green Land Rover Defender.",
 # Q3 constraint: what can Ella eat at the party (allergy + menu)
 "e1": "Ella is coeliac and must avoid gluten.",
 "e2": "The party menu has pizza, rice salad and fruit skewers.",
 # Q4 set difference: which grandparents are still alive
 "g1": "Granny Rose died in 2019.",
 "g2": "Grandpa Alan still lives in Inverness.",
 "g3": "Nana Joyce turned ninety this year.",
 "g4": "Grandpa Bill passed away before I was born.",
 # Q5 who is responsible for which chore (list)
 "c1": "Sam empties the dishwasher after school.",
 "c2": "Ella feeds Mango in the mornings.",
 "c3": "I do the ironing on Sunday evenings.",
 # Q6 timeline: order of jobs
 "j1": "My first job out of university was at a call centre.",
 "j2": "Then I spent five years teaching maths at Leith Academy.",
 "j3": "I retrained as a software tester in 2019.",
 # Q7 total spend: holiday costs
 "h1": "Flights to Crete cost us 640 pounds.",
 "h2": "The villa in Crete was 1,100 pounds for the week.",
 "h3": "We spent about 300 pounds on car hire in Crete.",
 # Q8 compare two people: who is older, Sam or Freya
 "a1": "Sam was born in May 2014.",
 "a2": "Freya, my cousin's daughter, was born in 2012.",
}
ops += [rem(f"memory:{k}", v) for k, v in facts.items()]
# near distractors for each
ops += [rem("memory:d1", "The boiler service is booked for October."), rem("memory:d2", "Laura's sister drives a Mini."),
        rem("memory:d3", "Ella loves the bouncy castle at parties."), rem("memory:d4", "We visit Grandpa Alan every Easter."),
        rem("memory:d5", "Chores chart is on the fridge."), rem("memory:d6", "I want to learn Spanish eventually."),
        rem("memory:d7", "We are thinking about Crete again next year."), rem("memory:d8", "Sam's birthday party will be at the climbing wall.")]
qs = [
 ("mx-boiler-count", "How many times has the boiler broken down?", ["b1", "b2", "b3"], "count"),
 ("mx-3hop", "What car does my wife's boss drive?", ["w1", "w2", "w3"], "three_hop"),
 ("mx-constraint", "What can Ella eat at the party?", ["e1", "e2"], "constraint"),
 ("mx-alive", "Which of my grandparents are still alive?", ["g1", "g2", "g3", "g4"], "set_difference"),
 ("mx-chores", "Who does which chores at home?", ["c1", "c2", "c3"], "list"),
 ("mx-jobs", "What jobs have I had, in order?", ["j1", "j2", "j3"], "sequence"),
 ("mx-holiday", "How much did the Crete holiday cost in total?", ["h1", "h2", "h3"], "sum"),
 ("mx-older", "Who is older, Sam or Freya?", ["a1", "a2"], "compare"),
]
queries = [{"id": i, "kind": "multi_" + k, "query": q, "scope": S,
            "expect": {"must_include": [f"memory:{x}" for x in need], "may_include": []}} for i, q, need, k in qs]
Path(__file__).with_name("review-multi.json").write_text(json.dumps({"author": "independent reviewer", "scenarios": [{"id": "multi", "operations": ops, "queries": queries}]}, indent=1))
print(len(queries), "queries", len(ops), "ops")
