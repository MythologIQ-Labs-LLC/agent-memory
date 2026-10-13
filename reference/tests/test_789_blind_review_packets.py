"""Private blind packet controls: source exactness, no gold/verdicts, no fake reviews."""
from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_789_blind_review_packets import (
    PacketError, prepare, verify_reviews, git_blob, stable_bytes, digest,
)

class BlindPacketTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base=Path(self.temp.name)
        self.root=base/"repo"
        self.root.mkdir()
        self.dest=base/"private-001"
        self.target_ids=["case-%02d" % i for i in range(24)]
        self.sources={}
        report_entries=[]
        for i in range(77):
            cid="case-%02d" % i
            report_entries.append({"case_id":cid,"arms":{
                "agent_memory":{"passed_native_scorer":i%4==0},
                "mem0_oss":{"passed_native_scorer":i%5==0},
            }})
        source_reports=[]
        for system in ("agent_memory","mem0_oss"):
            rows=[]
            for i in range(77):
                rows.append({"query_id":"case-%02d"%i,"query":"Question %d?"%i,
                    "gold_answers":["gold-SECRET-%d"%i],
                    "correct":i%(4 if system=="agent_memory" else 5)==0,
                    "context":"context-%d-%s\nno gold here"%(i,"left" if system=="agent_memory" else "right")})
            doc={"dataset":"precisionmembench","split":"single-turn","mode":"retrieval",
                 "total_queries":77,"correct":sum(x["correct"] for x in rows),"results":rows}
            path="reports/benchmarks/amb/v6/%s/single-turn.json"%system
            file=self.root/path
            file.parent.mkdir(parents=True,exist_ok=True)
            raw=stable_bytes(doc)
            file.write_bytes(raw)
            source_reports.append({"arm":system,"path":path,"git_blob_sha":git_blob(raw)})
            self.sources[system]=file
        source_reports.append({"arm":"bm25_control","path":"reports/benchmarks/amb/v6/bm25/single-turn.json",
                               "git_blob_sha":"0"*40})
        dossier={"schema_version":"competitive-case-dossier/1",
                 "accepted_score_update":False,"qualitative_review_status":"not_started",
                 "source_main_sha":"a"*40,
                 "source_reports":source_reports,
                 "review_selection":{"target_case_ids":self.target_ids},
                 "entries":report_entries}
        p=self.root/"reports/benchmarks/audits/789-amb-v6-case-dossiers.json"
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(stable_bytes(dossier))
        self.dossier=p

    def packet(self):
        return json.loads((self.dest/"reviewer/packet.json").read_text(encoding="utf-8"))

    def key(self):
        return json.loads((self.dest/"coordinator/key.json").read_text(encoding="utf-8"))

    def test_exact_source_builds_private_48_and_withholds_gold_outcomes_and_ids(self):
        report=prepare(self.root,self.dest)
        self.assertEqual(report["records"],48)
        self.assertEqual(report["completed_human_reviews"],0)
        packet=self.packet()
        self.assertEqual(len(packet["records"]),48)
        self.assertEqual(len({(x["case_id"],x["blind_arm"]) for x in packet["records"]}),48)
        self.assertEqual(sum(x["blind_arm"]=="A" for x in packet["records"]),24)
        data=(self.dest/"reviewer/packet.json").read_text(encoding="utf-8")
        self.assertNotIn("gold-SECRET",data)
        self.assertNotIn("passed_native_scorer",data)
        self.assertNotIn("source_reports",data)
        self.assertNotIn("provider_id",data)
        self.assertEqual(digest((self.dest/"reviewer/packet.json").read_bytes()),
                         self.key()["packet_sha256"])
        self.assertEqual(len(self.key()["assignments"]),48)
        self.assertEqual(verify_reviews(json.loads(self.dossier.read_text()),packet,
                                        self.key(),[])["release_gate"],"incomplete_human_coverage")

    def test_cannot_write_private_bundle_inside_repo(self):
        with self.assertRaisesRegex(PacketError,"outside repository"):
            prepare(self.root,self.root/"packets")

    def test_existing_output_refused(self):
        self.dest.mkdir()
        with self.assertRaisesRegex(PacketError,"already exists"):
            prepare(self.root,self.dest)

    def test_bad_pinned_source_refused_without_output(self):
        self.sources["agent_memory"].write_text("{}")
        with self.assertRaisesRegex(PacketError,"source blob mismatch"):
            prepare(self.root,self.dest)
        self.assertFalse(self.dest.exists())

    def test_mismatched_prompt_gold_refused(self):
        p=self.sources["mem0_oss"]
        d=json.loads(p.read_text())
        d["results"][0]["gold_answers"]=["some-other-gold"]
        raw=stable_bytes(d)
        p.write_bytes(raw)
        dossier=json.loads(self.dossier.read_text())
        next(s for s in dossier["source_reports"] if s["arm"]=="mem0_oss")["git_blob_sha"]=git_blob(raw)
        self.dossier.write_bytes(stable_bytes(dossier))
        with self.assertRaisesRegex(PacketError,"source query/gold conflict"):
            prepare(self.root,self.dest)

    def test_obvious_provider_deblinding_refused(self):
        p=self.sources["agent_memory"]
        d=json.loads(p.read_text())
        d["results"][0]["context"]="Mem0 openly declared"
        raw=stable_bytes(d)
        p.write_bytes(raw)
        dossier=json.loads(self.dossier.read_text())
        next(s for s in dossier["source_reports"] if s["arm"]=="agent_memory")["git_blob_sha"]=git_blob(raw)
        self.dossier.write_bytes(stable_bytes(dossier))
        with self.assertRaisesRegex(PacketError,"explicit provider name"):
            prepare(self.root,self.dest)

    def test_review_wrong_trace_or_tampered_packet_refused(self):
        prepare(self.root,self.dest)
        packet=self.packet()
        key=self.key()
        dossier=json.loads(self.dossier.read_text())
        packet["records"][0]["source_trace"]="forged"
        with self.assertRaisesRegex(PacketError,"packet/key mismatch"):
            verify_reviews(dossier,packet,key,[])
        packet=self.packet()
        review={"case_id":packet["records"][0]["case_id"],
                "blind_arm":packet["records"][0]["blind_arm"],
                "source_trace":"forged", "locked":True}
        with self.assertRaisesRegex(PacketError,"review source trace"):
            verify_reviews(dossier,packet,key,[review])

    def test_empty_review_preserves_zero_qualitative_claim(self):
        prepare(self.root,self.dest)
        result=verify_reviews(json.loads(self.dossier.read_text()),
                              self.packet(),self.key(),[])
        self.assertEqual(result["received_reviews"],0)
        self.assertEqual(result["independently_human_reviewed_case_arms"],0)
        self.assertFalse(result["publication_authorized"])
        self.assertEqual(result["status"],"incomplete_not_publishable")

if __name__=="__main__":
    unittest.main()
