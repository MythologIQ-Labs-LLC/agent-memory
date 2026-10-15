"""Closed-grammar plural_answer: false positives / negatives. python3 plural_probe.py <worktree>"""
import sys
sys.path.insert(0, sys.argv[1] + "/reference")
from agentmem_ref.runtime.return_selection import plural_answer
from agentmem_ref.runtime.return_selection import interpret_query as interpret
FP = ["Which does Alice prefer, tea or coffee?", "What news did Mom share?", "What series am I watching?",
      "Which lens do I use for portraits?", "What species is our fish?", "Which canvas did I buy?",
      "What are you doing on Friday?", "Who were you with last night?", "What physics course am I taking?",
      "Which glasses case is mine?", "What was this", "Which means of transport do I use?",
      "What diabetes medication was I prescribed?", "What mumps vaccine did I get?", "Which pants are the blue ones?",
      "What hours does the gym open?", "What does Sam do?", "Which goes first?", "Which comes first?"]
FN = ["Who is in my family?", "What do my children like?", "Which of my friends live in Paris?",
      "What kind of dogs do I have?", "What children do I have?", "What people did I meet at the conference?",
      "Where are my keys?", "Name my siblings.", "List the books I read.", "Tell me my allergies.",
      "What did I buy for the kids?", "Which mice did we adopt?", "What data do we keep?", "Who attended the meeting?",
      "What medicine do I take?", "What hobbies has Ana got?", "What are the kids called?",
      "what're my dogs' names?", "Which 3 cities did I visit?"]
for label, qs in (("plural_answer=True (check for false positives)", FP), ("plural_answer=False? (check for false negatives)", FN)):
    print("==", label)
    for q in qs:
        r = interpret(q) if callable(interpret) else None
        ns = getattr(r, "needs_several", None)
        print(f"  plural={plural_answer(q)!s:5} needs_several={ns!s:5} {q}")
