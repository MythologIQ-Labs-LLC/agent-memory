"""Private blind packet controls: source exactness, no gold/verdicts, no fake reviews."""
from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        self.fake_main=patch("scripts.prepare_789_blind_review_packets.FROZEN_MAIN","a"*40)
        self.fake_main.start()
        self.addCleanup(self.fake_main.stop)
        self.fake_blob=patch("scripts.prepare_789_blind_review_packets.FROZEN_DOSSIER_BLOB",
                             git_blob(p.read_bytes()))
        self.fake_blob.start()
        self.addCleanup(self.fake_blob.stop)

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
        forms=json.loads((self.dest/"reviewer/forms.PENDING.json").read_text(encoding="utf-8"))
        self.assertEqual(len(forms),48)
        self.assertTrue(all(not form["locked"] for form in forms))
        self.assertTrue(all(form["reviewer_id"] == "REPLACE_WITH_INDEPENDENT_HUMAN_ID" for form in forms))
        self.assertTrue(all(all(x["rating"] is None for x in form["dimensions"].values()) for form in forms))
        self.assertTrue(all(all(value is None for value in form["safety_flags"].values()) for form in forms))
        self.assertTrue(all(form["source_trace"].startswith("trace-") for form in forms)
        self.assertEqual(verify_reviews(json.loads(self.dossier.read_text()),packet,
                                        self.key(),[])["release_gate"],"incomplete_human_coverage")

    def test_cannot_write_private_bundle_inside_repo(self):
        with self.assertRaisesRegex(PacketError,"outside repository"):
            prepare(self.root,self.root/"packets")

    def test_existing_output_refused(self):
        self.dest.mkdir()
        with self.assertRaisesRegex(PacketError,"already exists"):
            prepare(self.root,self.dest)

    def test_changed_frozen_dossier_is_refused(self):
        self.dossier.write_text('{"tampered":true}', encoding="utf-8")
        with self.assertRaisesRegex(PacketError,"pinned preregistered dossier"):
            prepare(self.root,self.dest)
        self.assertFalse(self.dest.exists())

    def test_wrong_frozen_main_revision_is_refused(self):
        with patch("scripts.prepare_789_blind_review_packets.FROZEN_MAIN","f"*40):
            with self.assertRaisesRegex(PacketError,"frozen main evidence revision"):
                prepare(self.root,self.dest)
        self.assertFalse(self.dest.exists())

    def test_key_dossier_binding_is_checked_before_human_coverage(self):
        prepare(self.root,self.dest)
        key=self.key()
        key["dossier_sha256"]="0"*64
        with self.assertRaisesRegex(PacketError,"does not match the case dossier"):
            verify_reviews(json.loads(self.dossier.read_text()),self.packet(),key,[])

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
        with patch("scripts.prepare_789_blind_review_packets.FROZEN_DOSSIER_BLOB",
                   git_blob(self.dossier.read_bytes())):
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
        with patch("scripts.prepare_789_blind_review_packets.FROZEN_DOSSIER_BLOB",
                   git_blob(self.dossier.read_bytes())):
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

    def valid_private_review(self):
        packet=self.packet()
        record=packet["records"][0]
        forms=json.loads((self.dest/"reviewer/forms.PENDING.json").read_text(encoding="utf-8"))
        form=next(x for x in forms if (x["case_id"],x["blind_arm"]) ==
                  (record["case_id"],record["blind_arm"]))
        form["reviewer_id"]="reviewer-verified-by-coordinator"
        form["locked"]=True
        form["safety_flags"]={"unauthorized_exposure":False,"deleted_data_exposure":False}
        for name,dim in form["dimensions"].items():
            dim.update(rating=2,rationale="Reviewer-observed information",
                       evidence_refs=[record["source_trace"]+":context:L1-L1"])
        return form

    def test_real_context_line_citations_valid(self):
        prepare(self.root,self.dest)
        review=self.valid_private_review()
        result=verify_reviews(json.loads(self.dossier.read_text()),
                              self.packet(),self.key(),[review])
        self.assertEqual(result["received_reviews"],1)
        self.assertFalse(result["publication_authorized"])

    def test_incorrect_case_citation_rejected(self):
        prepare(self.root,self.dest)
        review=self.valid_private_review()
        review["dimensions"]["task_utility"]["evidence_refs"]=["trace-"+"0"*32+":context:L1-L1"]
        with self.assertRaisesRegex(PacketError,"unbound or wrong-case evidence citation"):
            verify_reviews(json.loads(self.dossier.read_text()),
                           self.packet(),self.key(),[review])

    def test_nonexistent_line_citation_rejected(self):
        prepare(self.root,self.dest)
        review=self.valid_private_review()
        review["dimensions"]["task_utility"]["evidence_refs"]=[
            review["source_trace"]+":context:L9999-L9999"]
        with self.assertRaisesRegex(PacketError,"citation outside original source lines"):
            verify_reviews(json.loads(self.dossier.read_text()),
                           self.packet(),self.key(),[review])

    def test_unspecified_p0_decision_cannot_be_locked(self):
        prepare(self.root,self.dest)
        review=self.valid_private_review()
        review["safety_flags"]["deleted_data_exposure"]=None
        with self.assertRaisesRegex(ValueError,"safety flags must be booleans"):
            verify_reviews(json.loads(self.dossier.read_text()),
                           self.packet(),self.key(),[review])

    def test_unfilled_template_cannot_be_submitted(self):
        prepare(self.root,self.dest)
        reviews=json.loads((self.dest/"reviewer/forms.PENDING.json").read_text())
        with self.assertRaisesRegex(ValueError,"review must declare reviewer type and be locked"):
            verify_reviews(json.loads(self.dossier.read_text()),
                           self.packet(),self.key(),[reviews[0]])

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
