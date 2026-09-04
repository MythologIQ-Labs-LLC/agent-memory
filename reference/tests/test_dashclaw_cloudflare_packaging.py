from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PREPARE_PATH = REPO_ROOT / "examples" / "cloudflare-dashclaw-provider" / "prepare.py"


def _load_prepare_module():
    spec = importlib.util.spec_from_file_location("dashclaw_cloudflare_prepare", PREPARE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Cloudflare prepare module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DashClawCloudflarePackagingTests(unittest.TestCase):
    def test_prepared_provider_uses_canonical_sources_and_imports_without_runtime_dependencies(self) -> None:
        prepare = _load_prepare_module()
        rendered, manifest = prepare._render_sources()

        self.assertEqual(
            set(rendered),
            {"policy.py", "dashclaw_external_verdict.py", "dashclaw_authority.py"},
        )
        self.assertEqual(set(manifest), set(rendered))
        self.assertIn("if TYPE_CHECKING:\n    from .adapter import GovernedMemoryAdapter", rendered["dashclaw_external_verdict.py"])
        self.assertNotIn("\nfrom .adapter import GovernedMemoryAdapter\n", rendered["dashclaw_external_verdict.py"])

        with tempfile.TemporaryDirectory(prefix="dashclaw-cf-test-") as temp:
            root = Path(temp)
            prepared_manifest = prepare._write_package(root / "agentmem_ref")
            prepare._import_check(root)

        self.assertEqual(prepared_manifest, manifest)


if __name__ == "__main__":
    unittest.main()
