from __future__ import annotations

import unittest
from pathlib import Path

from scripts.repo_audit import scan, unpinned_actions

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_public_tree_is_clean(self):
        self.assertEqual(scan(ROOT), [])

    def test_external_actions_are_pinned(self):
        self.assertEqual(unpinned_actions(ROOT), [])

    def test_release_workflow_supports_create_and_push_retry(self):
        text = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn("create:", text)
        self.assertIn("push:", text)
        self.assertIn("github.event.ref", text)
        self.assertIn("github.ref_name", text)
        self.assertIn("gh release upload", text)
        self.assertIn("--clobber", text)
        self.assertIn("git rev-list -n 1", text)
        self.assertNotIn("startsWith(github.ref, 'release/v')", text)


if __name__ == "__main__":
    unittest.main()
