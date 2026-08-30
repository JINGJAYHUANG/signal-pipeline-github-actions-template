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


if __name__ == "__main__":
    unittest.main()
