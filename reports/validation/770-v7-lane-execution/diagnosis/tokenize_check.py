import hashlib, json, sys, tokenizers
tok = tokenizers.Tokenizer.from_file(sys.argv[1])
texts = json.load(open(sys.argv[2]))["texts"]
enc = tok.encode_batch(texts)
ids = [e.ids for e in enc]
json.dump(ids, open(sys.argv[3], "w"))
print(tokenizers.__version__, len(ids), hashlib.sha256(json.dumps(ids).encode()).hexdigest())
