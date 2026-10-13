"""#779 static frontier viewer: browser qualification with the real projection.

Runs the committed static page in headless Chromium through Playwright
against the projection built from the accepted F1 catalog, then feeds it
adversarial projections. Skips cleanly when Playwright or Chromium is not
installed. Set ``FRONTIER_UI_EVIDENCE_DIR`` to keep screenshots.
"""
from __future__ import annotations

from copy import deepcopy
from functools import partial
import http.server
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import unittest

from agentmem_ref.evaluation.ui_frontier_leaderboard import build_frontier_leaderboard

try:  # pragma: no cover - availability depends on the environment
    from playwright.sync_api import sync_playwright
except Exception:  # noqa: BLE001
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[2]
UI_DIR = ROOT / "reports/benchmarks/ui"
CATALOG = UI_DIR / "catalog.json"
DESKTOP = {"width": 1366, "height": 900}
MOBILE = {"width": 390, "height": 844}


def _launch(playwright):
    try:
        return playwright.chromium.launch()
    except Exception:  # noqa: BLE001
        for candidate in ("/opt/pw-browsers/chromium", "/usr/bin/chromium", "/usr/bin/chromium-browser"):
            if Path(candidate).exists():
                return playwright.chromium.launch(executable_path=candidate)
        raise


def _draft_registry():
    return {
        "schema_version": "1.0.0",
        "claims_policy": {"universal_score": None, "authority_effect": "none"},
        "capability_groups": {
            "A": "Ingestion and representation", "B": "Retrieval and relevance",
            "C": "Temporal memory", "D": "Lifecycle and metabolism",
            "E": "Governance and safety", "F": "Operational durability",
            "G": "Cognition and task utility", "H": "Multi-source / multi-agent / multimodal",
            "I": "Evaluator quality",
        },
        "objectives": [{
            "id": "B01", "group": "B", "capability": "Deep recall at k=50",
            "benchmark": "LongMemEval_S turn", "metric": "recall_all@50",
            "source_kind": "ledger", "owners": [673, 669, 644],
            "deficit_selector": "longmemeval-s-turn-deep-recall-2026-10-07",
        }],
    }


@unittest.skipUnless(sync_playwright is not None, "playwright is not installed")
@unittest.skipUnless(CATALOG.exists(), "accepted F1 catalog is not present")
class FrontierViewerBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="frontier-ui-"))
        cls.evidence = Path(os.environ.get("FRONTIER_UI_EVIDENCE_DIR", cls.tmp / "evidence"))
        cls.evidence.mkdir(parents=True, exist_ok=True)
        shutil.copy(UI_DIR / "index.html", cls.tmp / "index.html")
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        cls.projection = build_frontier_leaderboard(catalog)
        (cls.tmp / "frontier-leaderboards.json").write_text(
            json.dumps(cls.projection, sort_keys=True), encoding="utf-8")
        cls.draft = build_frontier_leaderboard(
            catalog, objectives=_draft_registry(), objectives_status="draft",
            objectives_source="synthetic draft registry")
        (cls.tmp / "draft.json").write_text(json.dumps(cls.draft, sort_keys=True), encoding="utf-8")
        handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(cls.tmp))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}/"
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = _launch(cls.playwright)
        except Exception as exc:  # noqa: BLE001
            cls.playwright.stop()
            cls.server.shutdown()
            raise unittest.SkipTest(f"chromium is not launchable: {exc}")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def _page(self, viewport=DESKTOP, fragment=""):
        context = self.browser.new_context(viewport=viewport)
        page = context.new_page()
        self.errors = []
        page.on("pageerror", lambda e: self.errors.append(str(e)))
        page.on("console", lambda m: self.errors.append(m.text) if m.type == "error" else None)
        page.goto(self.base + "index.html" + fragment)
        page.wait_for_function("document.getElementById('counts').children.length > 0")
        self.addCleanup(context.close)
        return page

    def _shot(self, page, name, full=True):
        page.screenshot(path=str(self.evidence / name), full_page=full)

    def test_desktop_renders_real_snapshot_and_known_rows(self):
        page = self._page(fragment="#profile=longmemeval-s-retrieval-parity-v2%3Aturn&metric=recall_all%4050")
        self.assertIn(self.projection["snapshot_id"], page.locator("#snapshot").inner_text())
        self.assertIn("Historical snapshot", page.locator("#stale").inner_text())
        rows = page.locator("#rows tr.row")
        self.assertEqual(rows.count(), 1)
        text = rows.first.inner_text()
        self.assertIn("mem0-oss · 89.50%", text)
        self.assertIn("85.92% · rank 2 of 3", text)
        self.assertIn("3.58 pp", text)
        self.assertIn("Behind external peer", text)
        self.assertIn("Newer unaccepted evidence", text)
        self.assertIn("Adequacy unknown", text)
        bar = rows.first.locator("[role='img']")
        self.assertIn("3.58 pp", bar.get_attribute("aria-label"))
        self._shot(page, "desktop-known-row-behind-external.png")
        self.assertEqual(self.errors, [])

    def test_tie_and_control_leader_are_labelled_not_celebrated(self):
        page = self._page(fragment="#profile=longmemeval-s-retrieval-parity-v2%3Asession&metric=latest_gold_ranked_first")
        text = page.locator("#rows tr.row").first.inner_text()
        self.assertIn("Tie: agent-memory = lexical_overlap", text)
        self.assertIn("Tied for lead", text)
        self.assertIn("0.00 pp", text)
        page = self._page(fragment="#profile=longmemeval-s-retrieval-parity-v2%3Aturn&metric=latest_gold_ranked_first")
        text = page.locator("#rows tr.row").first.inner_text()
        self.assertIn("lexical_overlap · 61.43%", text)
        self.assertIn("Behind a control", text)
        self.assertIn("5.71 pp", text)
        self._shot(page, "desktop-behind-control.png")

    def test_non_comparable_rows_show_no_number_and_explain_why(self):
        page = self._page(fragment="#profile=longmemeval-s-retrieval-parity-v6%3Aturn&metric=recall_all%4050")
        row = page.locator("#rows tr.row").first
        text = row.inner_text()
        self.assertIn("Non-comparable", text)
        self.assertIn("No numeric gap", text)
        self.assertIn("Not established", text)
        self.assertNotIn("%", row.locator("td[data-label='Gap to leader']").inner_text())
        row.get_by_role("button", name="Details").click()
        detail = page.locator("#rows tr.detail").first.inner_text()
        self.assertIn("Why no numeric gap?", detail)
        self.assertIn("not an accepted same-harness lane", detail)
        self.assertIn("excluded", detail)
        self._shot(page, "desktop-non-comparable-why-not.png")
        self.assertEqual(self.errors, [])

    def test_keyboard_navigation_expands_details_and_keeps_focus(self):
        page = self._page(fragment="#profile=longmemeval-s-retrieval-parity-v2%3Aturn&metric=recall_all%4050")
        page.keyboard.press("Tab")
        self.assertEqual(page.evaluate("document.activeElement.className"), "skip")
        page.keyboard.press("Enter")
        for _ in range(60):
            page.keyboard.press("Tab")
            tag = page.evaluate("document.activeElement.textContent")
            if tag == "Details":
                break
        else:
            self.fail("Details button not reachable by keyboard")
        page.keyboard.press("Enter")
        page.wait_for_selector("#rows tr.detail")
        button = page.locator("#rows button.toggle").first
        self.assertEqual(button.get_attribute("aria-expanded"), "true")
        self.assertEqual(page.evaluate("document.activeElement.textContent"), "Details")
        detail = page.locator("#rows tr.detail").first
        self.assertIn("Why comparable?", detail.inner_text())
        self.assertIn("All systems in this comparison set", detail.inner_text())
        self.assertEqual(detail.locator("table.inner tbody tr").count(), 3)
        self.assertEqual(detail.locator("table.inner tbody tr td").first.inner_text(), "1")
        self.assertIn("Control baseline", detail.inner_text())
        self.assertIn("External system", detail.inner_text())
        self.assertIn("run ", detail.inner_text())
        self.assertIn("sha256", detail.inner_text())
        self._shot(page, "desktop-details-expanded-keyboard.png")
        page.keyboard.press("Enter")
        self.assertEqual(page.locator("#rows tr.detail").count(), 0)
        self.assertEqual(self.errors, [])

    def test_filters_navigate_benchmarks_and_update_url(self):
        page = self._page()
        page.select_option("#f-benchmark", "amb-precisionmembench")
        page.select_option("#f-state", "ranked")
        page.wait_for_function("location.hash.includes('benchmark=amb-precisionmembench')")
        count = page.locator("#rows tr.row").count()
        self.assertEqual(count, 10)
        self.assertTrue(all("amb-precisionmembench" in t for t in page.locator("#rows tr.row").all_inner_texts()))
        self.assertIn("Chronology undetermined", page.locator("#rows").inner_text())
        page.select_option("#f-currency", "stale")
        page.select_option("#f-comp", "behind_external")
        self.assertEqual(page.locator("#rows tr.row").count(), 2)
        self.assertIn("1 count", page.locator("#rows").inner_text())
        page.click("#f-reset")
        self.assertEqual(page.locator("#rows tr.row").count(), len(self.projection["leaderboards"]) + len(
            [c for c in self.projection["metric_coverage"] if c["best_ranking_state"] == "no_comparison_row"]))
        self._shot(page, "desktop-overview.png", full=False)

    def test_published_references_are_isolated_from_rankings(self):
        page = self._page(fragment="#state=ranked")
        published = page.locator("#published").inner_text()
        for system in ("Cognee", "Hindsight", "Mem0 managed platform", "Supermemory", "Zep"):
            self.assertIn(system, published)
            self.assertNotIn(system, page.locator("#rows").inner_text())
        self.assertIn("not comparable", published)
        self.assertIn("registry: ABSENT", page.locator("#obj-state").inner_text())
        self.assertEqual(page.locator("#families .family").count(), 9)

    def test_mobile_viewport_has_no_horizontal_overflow_and_stacks_cells(self):
        page = self._page(viewport=MOBILE, fragment="#profile=longmemeval-s-retrieval-parity-v2%3Aturn&dimension=retrieval")
        scroll_w = page.evaluate("document.scrollingElement.scrollWidth")
        inner_w = page.evaluate("window.innerWidth")
        self.assertLessEqual(scroll_w, inner_w)
        display = page.evaluate("getComputedStyle(document.querySelector('#rows tr.row td')).display")
        self.assertEqual(display, "block")
        label = page.evaluate("getComputedStyle(document.querySelector('#rows tr.row td'), '::before').content")
        self.assertIn("Benchmark / metric", label)
        page.locator("#rows button.toggle").first.click()
        self.assertLessEqual(page.evaluate("document.scrollingElement.scrollWidth"), inner_w)
        self._shot(page, "mobile-details.png")
        self.assertEqual(self.errors, [])

    def test_draft_registry_is_labelled_and_links_ownership(self):
        page = self._page()
        page.set_input_files("#upload", str(self.tmp / "draft.json"))
        page.wait_for_function("document.getElementById('obj-state').textContent.includes('DRAFT')")
        self.assertIn("DRAFT registry read from an unmerged source", page.locator("#obj-note").inner_text())
        self.assertIn("B01", page.locator("#families").inner_text())
        page.select_option("#f-family", "B")
        rows = page.locator("#rows tr.row")
        # Eight comparison rows carry recall_all@50 on a turn plane (two
        # currentness-v1 inputs plus parity v1..v6); seven distinct metric keys.
        self.assertEqual(rows.count(), 8)
        rows.first.get_by_role("button", name="Details").click()
        detail = page.locator("#rows tr.detail").first.inner_text()
        self.assertIn("#673", detail)
        self.assertIn("DRAFT registry", detail)
        self._shot(page, "desktop-draft-objectives.png")

    def _upload(self, page, name, payload):
        path = self.tmp / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        page.set_input_files("#upload", str(path))
        page.wait_for_timeout(150)

    def test_adversarial_projections_are_refused_or_rendered_without_numbers(self):
        page = self._page()
        base = deepcopy(self.projection)
        refused = [
            ("aggregate", dict(base, aggregate_score=0.93), "aggregate score"),
            ("schema", dict(base, schema_version="0.1.0"), "Unsupported projection schema"),
            ("authority", dict(base, authority_effect="grant"), "claims authority"),
            ("shape", {"schema_version": "0.2.0", "aggregate_score": None, "authority_effect": "none"}, "Invalid projection"),
        ]
        for name, payload, needle in refused:
            with self.subTest(name=name):
                self._upload(page, name + ".json", payload)
                self.assertIn(needle, page.locator("#error").inner_text())
        self._shot(page, "desktop-refused-aggregate-score.png", full=False)

        known = next(r for r in base["leaderboards"] if r["metric_id"] == "recall_all@50"
                     and r["task_profile"] == "longmemeval-s-retrieval-parity-v2:turn")
        tampered = []
        bad = deepcopy(known); bad["leader"]["value"] = "0.99"; tampered.append(("string_leader", bad))
        bad = deepcopy(known); bad["gap_to_leader_native"] = -0.5; tampered.append(("negative_gap", bad))
        bad = deepcopy(known); bad["leader"]["value"] = 1.7; tampered.append(("ratio_over_one", bad))
        bad = deepcopy(known); bad["ranking"] = []; tampered.append(("empty_ranking", bad))
        bad = deepcopy(known); bad["ranking_state"] = "best_in_class"; tampered.append(("unknown_state", bad))
        bad = deepcopy(known); bad["ranking_state"] = "non_comparable"; tampered.append(("non_comparable_with_leader", bad))
        bad = deepcopy(known); bad["direction"] = "descriptive"; tampered.append(("descriptive_ranked", bad))
        bad = deepcopy(known); bad["leader"] = None; tampered.append(("missing_leader", bad))
        payload = deepcopy(base)
        payload["leaderboards"] = [dict(row, metric_key=row["metric_key"] + ":" + name, comparison_set_id=row["comparison_set_id"] + ":" + name)
                                   for name, row in tampered]
        payload["metric_coverage"] = []
        self._upload(page, "tampered.json", payload)
        self.assertEqual(page.locator("#error").inner_text(), "")
        rows = page.locator("#rows tr.row")
        self.assertEqual(rows.count(), len(tampered))
        for i in range(len(tampered)):
            text = rows.nth(i).inner_text()
            with self.subTest(case=tampered[i][0]):
                self.assertIn("Invalid row, refused", text)
                self.assertIn("No numeric gap", text)
                self.assertNotIn("%", rows.nth(i).locator("td[data-label='Gap to leader']").inner_text())
                self.assertNotIn("Leading", text)
                self.assertNotIn("rank", rows.nth(i).locator("td[data-label='Agent Memory']").inner_text())
        self.assertEqual(page.locator("#rows [role='img']").count(), 0)
        self._shot(page, "desktop-tampered-rows-refused.png")
        self.assertEqual(self.errors, [])


if __name__ == "__main__":
    unittest.main()
