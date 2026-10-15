import json
facts = {
 "f:car": "We drive a grey 2019 Corolla.",
 "f:dog": "Biscuit, our beagle, is terrified of thunderstorms.",
 "f:cat": "The tabby we adopted in March is called Miso.",
 "f:job": "My employer is Northwind Logistics, where I lead the data team.",
 "f:boss": "My manager at work is Priya Raman.",
 "f:gym": "I go to the climbing gym on Tuesday evenings.",
 "f:meds": "I take levothyroxine every morning.",
 "f:allergy": "I am allergic to penicillin.",
 "f:sister": "My sister Lena lives in Rotterdam.",
 "f:flight": "Our flight to Osaka leaves on 3 May at 09:40.",
 "f:hotel": "The hotel in Osaka is near Namba station.",
 "f:lang": "I am learning Japanese on weekday mornings.",
 "f:budget": "We spend about 400 euros a month on groceries.",
 "f:garden": "The tomatoes failed this year because of a late frost.",
 "f:wifi": "The guest network password is on the fridge magnet."}
unanswerable = ["What is my blood type?", "Which hamster do we have?", "What is my brother's name?",
  "When is my mortgage payment due?", "What colour is our boat?", "Where did I go to university?",
  "What is my shoe size?", "Who is my dentist?", "Which bank do I use?", "What is my favourite film?",
  "When is the company picnic?", "What is the weather in Osaka tomorrow?", "How much is our rent?",
  "What is my cholesterol?", "Which school do the kids attend?", "What instrument do I play?",
  "Who is our landlord?", "What is my daughter allergic to?", "What did I eat yesterday?", "Which car does Lena drive?"]
answerable = {"Which automobile do we own?": ["f:car"], "Which animals live with us?": ["f:dog", "f:cat"],
  "Who pays my salary?": ["f:job"], "Who is my boss?": ["f:boss"], "Where do I exercise?": ["f:gym"],
  "What medicine do I take?": ["f:meds"], "Which drugs must I avoid?": ["f:allergy"],
  "Where does my sibling live?": ["f:sister"], "When do we fly to Japan?": ["f:flight"],
  "Where are we staying in Japan?": ["f:hotel"], "What language am I studying?": ["f:lang"],
  "How much do we spend on food?": ["f:budget"], "How did the vegetable patch do?": ["f:garden"],
  "How do guests get online?": ["f:wifi"], "What pets do we have?": ["f:dog", "f:cat"]}
json.dump([{"name": "abstain", "facts": facts, "queries": unanswerable},
           {"name": "answerable", "facts": facts, "queries": list(answerable)}], open("scen3.json", "w"), indent=1)
json.dump(answerable, open("scen3-gold.json", "w"), indent=1)
