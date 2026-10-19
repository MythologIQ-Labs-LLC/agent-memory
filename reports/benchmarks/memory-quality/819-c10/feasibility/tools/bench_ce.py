import json, time, statistics, sys, random
import numpy as np, onnxruntime as ort
from tokenizers import Tokenizer
S = sys.argv[1]; M = f"{S}/models/cross-encoder_qnli-electra-base"
data = json.load(open(f"{S}/fx/819-c8_dev_c8-scenarios.json")); scen = data["scenarios"]
pairs = []
for s in scen:
    texts = [op["text"] for op in s["operations"] if op["op"] == "remember"]
    for q in s["queries"]: pairs.append((q["query"], texts[:8]))
random.Random(1).shuffle(pairs); pairs = pairs[:40]
def mk(opt, threads, f="model.onnx"):
    o = ort.SessionOptions(); o.intra_op_num_threads = threads; o.inter_op_num_threads = 1; o.graph_optimization_level = opt
    return ort.InferenceSession(f"{M}/onnx/{f}", o, providers=["CPUExecutionProvider"])
def run(sess, maxlen, batched=True):
    t = Tokenizer.from_file(f"{M}/tokenizer.json"); t.enable_truncation(maxlen)
    if batched: t.enable_padding()
    out = []; lat = []
    for q, docs in pairs:
        t0 = time.perf_counter()
        if batched:
            enc = t.encode_batch([(q, d) for d in docs])
            v = sess.run(None, {"input_ids": np.array([e.ids for e in enc]), "attention_mask": np.array([e.attention_mask for e in enc]), "token_type_ids": np.array([e.type_ids for e in enc])})[0][:, 0]
        else:
            v = []
            for d in docs:
                e = t.encode(q, d)
                v.append(sess.run(None, {"input_ids": np.array([e.ids]), "attention_mask": np.array([e.attention_mask]), "token_type_ids": np.array([e.type_ids])})[0][0, 0])
        lat.append((time.perf_counter() - t0) * 1000); out.extend(float(x) for x in v)
    return np.array(out), lat
t0 = time.perf_counter(); base = mk(ort.GraphOptimizationLevel.ORT_ENABLE_BASIC, 1); init = time.perf_counter() - t0
ref, lat = run(base, 512)
print(f"init {init:.2f}s  basic/1t/512 batched  p50 {statistics.median(lat):.0f}ms p95 {sorted(lat)[int(.95*len(lat))]:.0f}ms per 8 pairs")
for name, sess, ml, b in [("basic/1t/512 single", base, 512, False), ("all/1t/512 batched", mk(ort.GraphOptimizationLevel.ORT_ENABLE_ALL, 1), 512, True),
                          ("all/1t/512 single", mk(ort.GraphOptimizationLevel.ORT_ENABLE_ALL, 1), 512, False),
                          ("basic/4t/512 batched", mk(ort.GraphOptimizationLevel.ORT_ENABLE_BASIC, 4), 512, True),
                          ("all/4t/512 single", mk(ort.GraphOptimizationLevel.ORT_ENABLE_ALL, 4), 512, False),
                          ("basic/1t/128 batched", base, 128, True)]:
    v, lat = run(sess, ml, b)
    print(f"{name:24s} p50 {statistics.median(lat):.0f}ms p95 {sorted(lat)[int(.95*len(lat))]:.0f}ms  max|d| {np.abs(v-ref).max():.2e} flips {(np.sign(v)!=np.sign(ref)).sum()}/{len(v)}")
import resource; print("maxrss MiB", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024)
