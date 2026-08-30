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

    def test_release_workflow_configures_annotated_tag_identity(self):
        text = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn('git config user.name "github-actions[bot]"', text)
        self.assertIn('git config user.email "41898282+github-actions[bot]@users.noreply.github.com"', text)
        self.assertIn('git tag -a "$VERSION"', text)

    def test_release_workflow_repairs_only_unreleased_stale_tag(self):
        text = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn('if gh release view "$VERSION"', text)
        self.assertIn('refusing to move released tag $VERSION', text)
        self.assertIn('git push origin ":refs/tags/$VERSION"', text)
        self.assertIn('test "$(git rev-list -n 1 "$VERSION")" = "$head_sha"', text)

    def test_release_archives_are_verified_inside_dist(self):
        text = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn("cd dist", text)
        self.assertIn("sha256sum -c SHA256SUMS.txt", text)
        self.assertNotIn("sha256sum -c dist/SHA256SUMS.txt", text)
        self.assertIn('gzip -n "dist/signal-pipeline-$VERSION.tar"', text)


if __name__ == "__main__":
    unittest.main()
