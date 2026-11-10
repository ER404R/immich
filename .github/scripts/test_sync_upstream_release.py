import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from sync_upstream_release import build_passed, stable_releases, synchronize


def release(tag, **overrides):
    return {"tag_name": tag, "draft": False, "prerelease": False, **overrides}


class ReleaseSelectionTest(unittest.TestCase):
    def test_only_successful_build_of_current_commit_allows_an_update(self):
        run = {"head_sha": "current", "status": "completed", "conclusion": "success"}
        self.assertTrue(build_passed([run], "current"))
        self.assertFalse(build_passed([], "current"))
        self.assertFalse(build_passed([run], "different"))
        self.assertFalse(build_passed([{**run, "status": "in_progress"}], "current"))
        self.assertFalse(build_passed([{**run, "conclusion": "failure"}], "current"))

    def test_only_stable_versions_are_selected_in_numeric_order(self):
        releases = [
            release("v3.10.0"),
            release("v3.4.0"),
            release("v3.5.0-rc.1", prerelease=True),
            release("v3.6.0", draft=True),
            release("v3.7.0", prerelease=True),
            release("--upload-pack=unexpected"),
        ]
        self.assertEqual(stable_releases(releases), [((3, 4, 0), "v3.4.0"), ((3, 10, 0), "v3.10.0")])


class GitSynchronizationTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.upstream = root / "upstream"
        self.origin = root / "origin.git"
        self.work = root / "work"
        self.run_git(root, "init", "--initial-branch=main", str(self.upstream))
        self.configure(self.upstream)
        (self.upstream / "mobile").mkdir()
        (self.upstream / "mobile/pubspec.yaml").write_text("version: 3.4.0-rc.0+3040000\n")
        (self.upstream / "upstream.txt").write_text("original\n")
        self.commit(self.upstream, "Initial upstream")
        self.run_git(root, "clone", "--bare", str(self.upstream), str(self.origin))
        self.run_git(root, "clone", str(self.origin), str(self.work))
        self.configure(self.work)
        self.run_git(self.work, "switch", "--create", "personal")
        (self.work / "fork.txt").write_text("Immich-E\n")
        self.commit(self.work, "Personal customization")
        self.run_git(self.work, "push", "origin", "personal")
        self.previous_directory = Path.cwd()
        os.chdir(self.work)
        self.addCleanup(os.chdir, self.previous_directory)

    def run_git(self, directory, *args):
        return subprocess.run(["git", "-C", str(directory), *args], check=True, text=True, capture_output=True).stdout.strip()

    def configure(self, directory):
        self.run_git(directory, "config", "user.name", "Sync Test")
        self.run_git(directory, "config", "user.email", "sync-test@example.com")

    def commit(self, directory, message):
        self.run_git(directory, "add", ".")
        self.run_git(directory, "commit", "-m", message)

    def upstream_release(self, version="3.4.0"):
        (self.upstream / "mobile/pubspec.yaml").write_text(f"version: {version}+3040000\n")
        (self.upstream / "upstream.txt").write_text(f"release {version}\n")
        self.commit(self.upstream, f"Release {version}")
        tag = f"v{version}"
        self.run_git(self.upstream, "tag", "-a", tag, "-m", tag)
        return release(tag)

    def remote_heads(self):
        return tuple(self.run_git(self.origin, "rev-parse", ref) for ref in ["main", "personal"])

    def test_sync_updates_both_branches_and_preserves_customizations(self):
        official = self.upstream_release()
        message = synchronize([official], str(self.upstream))
        self.assertIn("v3.4.0", message)
        self.assertEqual(self.run_git(self.origin, "show", "main:upstream.txt"), "release 3.4.0")
        self.assertEqual(self.run_git(self.origin, "show", "personal:upstream.txt"), "release 3.4.0")
        self.assertEqual(self.run_git(self.origin, "show", "personal:fork.txt"), "Immich-E")
        self.assertNotEqual(*self.remote_heads())

    def test_repeated_sync_does_not_push_or_rebuild(self):
        official = self.upstream_release()
        synchronize([official], str(self.upstream))
        before = self.remote_heads()
        self.assertIn("No newer", synchronize([official], str(self.upstream)))
        self.assertEqual(self.remote_heads(), before)

    def test_older_stable_release_does_not_downgrade_prerelease_checkout(self):
        before = self.remote_heads()
        self.assertIn("No newer", synchronize([release("v3.3.6")], str(self.upstream)))
        self.assertEqual(self.remote_heads(), before)

    def test_pending_build_leaves_both_branches_unchanged(self):
        official = self.upstream_release()
        before = self.remote_heads()
        run = {"head_sha": before[1], "status": "in_progress", "conclusion": None}
        self.assertIn("Waiting for Fork Android", synchronize([official], str(self.upstream), build_runs=[run]))
        self.assertEqual(self.remote_heads(), before)

    def test_merge_conflict_leaves_both_remote_branches_unchanged(self):
        (self.work / "upstream.txt").write_text("personal change\n")
        self.commit(self.work, "Personal conflicting customization")
        self.run_git(self.work, "push", "origin", "personal")
        official = self.upstream_release()
        before = self.remote_heads()
        with self.assertRaises(subprocess.CalledProcessError):
            synchronize([official], str(self.upstream))
        self.assertEqual(self.remote_heads(), before)

    def test_divergent_main_is_not_overwritten(self):
        self.run_git(self.work, "switch", "main")
        (self.work / "main-only.txt").write_text("preserve this commit\n")
        self.commit(self.work, "Main-only work")
        self.run_git(self.work, "push", "origin", "main")
        official = self.upstream_release()
        before = self.remote_heads()
        with self.assertRaises(subprocess.CalledProcessError):
            synchronize([official], str(self.upstream))
        self.assertEqual(self.remote_heads(), before)

    def test_push_rejection_updates_neither_branch(self):
        official = self.upstream_release()
        hook = self.origin / "hooks/update"
        hook.write_text('#!/bin/sh\nif [ "$1" = refs/heads/personal ]; then exit 1; fi\n')
        hook.chmod(0o755)
        before = self.remote_heads()
        with self.assertRaises(subprocess.CalledProcessError):
            synchronize([official], str(self.upstream))
        self.assertEqual(self.remote_heads(), before)

    def test_missed_releases_are_processed_oldest_first(self):
        first = self.upstream_release("3.4.0")
        second = self.upstream_release("3.5.0")
        self.assertIn("v3.4.0", synchronize([second, first], str(self.upstream)))
        self.assertEqual(self.run_git(self.origin, "show", "personal:upstream.txt"), "release 3.4.0")


if __name__ == "__main__":
    unittest.main()
