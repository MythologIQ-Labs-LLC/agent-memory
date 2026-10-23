import json
from transformers import pipeline
qa = pipeline("question-answering", model="deepset/roberta-base-squad2", revision="adc3b06f79f797d1c575d5479d6f5efe54a9e3b4", device=-1)
out = []
for p in json.load(open("pairs.json")):
    r = qa(question=p["question"], context=p["context"], handle_impossible_answer=True)
    out.append(r["answer"] != "")
json.dump(out, open("hf.json", "w"))
print(sum(out), len(out))
