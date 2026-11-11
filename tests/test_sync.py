import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class SyncTests(unittest.TestCase):
    """Exercise scripts/sync.sh against a real bare origin. The GitHub PR
    paths (upsert, rejection detection, comments) are thin gh call sites and
    are exercised in real rollout; everything git-side is covered here."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.origin = self.root / "origin.git"
        self._git("init", "-q", "--bare", "--initial-branch", "main", str(self.origin))
        seed = self.root / "seed"
        self._git("clone", "-q", str(self.origin), str(seed))
        self._git("-C", str(seed), "config", "user.name", "tester")
        self._git("-C", str(seed), "config", "user.email", "tester@example.com")
        (seed / "README.md").write_text("seed\n")
        (seed / ".gitignore").write_text("ignored/\n__pycache__/\n")
        (seed / "scripts").mkdir()
        shutil.copy(REPO / "scripts" / "sync.sh", seed / "scripts" / "sync.sh")
        self._git("-C", str(seed), "add", "-A")
        self._git("-C", str(seed), "commit", "-q", "-m", "init")
        self._git("-C", str(seed), "push", "-q", "origin", "main")
        self.work = self.root / "work"
        self._git("clone", "-q", str(self.origin), str(self.work))
        self._git("-C", str(self.work), "config", "user.name", "tester")
        self._git("-C", str(self.work), "config", "user.email", "tester@example.com")

    def _git(self, *args):
        subprocess.run(["git", *args], check=True, capture_output=True, text=True)

    def _git_out(self, *args):
        return subprocess.run(
            ["git", *args], check=True, capture_output=True, text=True
        ).stdout

    def run_sync(self, *args):
        return subprocess.run(
            ["bash", str(self.work / "scripts" / "sync.sh"), *args],
            capture_output=True,
            text=True,
            env=dict(os.environ, SYNC_ID="tester", HOME=str(self.root)),
        )

    def peer(self):
        peer = self.root / "peer"
        self._git("clone", "-q", str(self.origin), str(peer))
        self._git("-C", str(peer), "config", "user.name", "tester")
        self._git("-C", str(peer), "config", "user.email", "tester@example.com")
        return peer

    def origin_sha(self, ref):
        out = self._git_out("-C", str(self.work), "ls-remote", "origin", ref)
        return out.split()[0] if out.strip() else None

    def work_sha(self, ref="HEAD"):
        return self._git_out("-C", str(self.work), "rev-parse", ref).strip()

    def work_branch(self):
        return self._git_out("-C", str(self.work), "branch", "--show-current").strip()

    def work_clean(self):
        return not self._git_out("-C", str(self.work), "status", "--porcelain").strip()

    def committed_files(self):
        out = self._git_out("-C", str(self.work), "ls-tree", "-r", "--name-only", "HEAD")
        return set(out.splitlines())

    def test_fresh_clone_is_branched_and_stays_clean(self):
        result = self.run_sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.work_branch(), "sync/tester")
        self.assertTrue(self.work_clean())
        self.assertIsNone(self.origin_sha("sync/tester"))

    def test_publishes_dirty_work_on_the_machine_branch(self):
        (self.work / "README.md").write_text("edited\n")
        skill = self.work / "new-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("new\n")
        ignored = self.work / "ignored"
        ignored.mkdir()
        (ignored / "x").write_text("kept out\n")
        result = self.run_sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.origin_sha("sync/tester"), self.work_sha())
        self.assertTrue(self.work_clean())
        files = self.committed_files()
        self.assertIn("new-skill/SKILL.md", files)
        self.assertNotIn("ignored/x", files)
        subject = self._git_out(
            "-C", str(self.work), "log", "-1", "--format=%s"
        ).strip()
        self.assertTrue(subject.startswith("sync(tester):"), subject)

    def test_converges_when_upstream_merges_the_pr(self):
        (self.work / "README.md").write_text("edited\n")
        result = self.run_sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        peer = self.peer()
        self._git("-C", str(peer), "fetch", "-q", "origin", "sync/tester")
        self._git("-C", str(peer), "merge", "--ff-only", "FETCH_HEAD")
        self._git("-C", str(peer), "push", "-q", "origin", "main")
        result = self.run_sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.work_sha(), self.work_sha("main"))
        self.assertTrue(self.work_clean())

    def test_conflicting_upstream_change_is_surfaced_not_lost(self):
        self.run_sync()
        (self.work / "README.md").write_text("local\n")
        self._git("-C", str(self.work), "add", "-A")
        self._git("-C", str(self.work), "commit", "-q", "-m", "local edit")
        peer = self.peer()
        (peer / "README.md").write_text("upstream\n")
        self._git("-C", str(peer), "add", "-A")
        self._git("-C", str(peer), "commit", "-q", "-m", "upstream edit")
        self._git("-C", str(peer), "push", "-q", "origin", "main")
        result = self.run_sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(self.work_sha(), self.work_sha("main"))
        self.assertTrue(self.work_clean())
        self.assertEqual((self.work / "README.md").read_text(), "local\n")

    def test_discard_restores_main_and_removes_published_state(self):
        (self.work / "README.md").write_text("edited\n")
        skill = self.work / "new-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("new\n")
        ignored = self.work / "ignored"
        ignored.mkdir()
        (ignored / "x").write_text("kept out\n")
        result = self.run_sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_sync("discard")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.work / "README.md").read_text(), "seed\n")
        self.assertFalse((self.work / "new-skill").exists())
        self.assertTrue((self.work / "ignored" / "x").exists())
        self.assertIsNone(self.origin_sha("sync/tester"))
        self.assertTrue(self.work_clean())

    def test_adopts_remote_branch_updates_made_elsewhere(self):
        (self.work / "README.md").write_text("a\n")
        result = self.run_sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        peer = self.peer()
        self._git("-C", str(peer), "fetch", "-q", "origin", "sync/tester")
        self._git("-C", str(peer), "checkout", "-q", "-b", "adjust", "FETCH_HEAD")
        (peer / "web-adjustment.md").write_text("from the PR page\n")
        self._git("-C", str(peer), "add", "-A")
        self._git("-C", str(peer), "commit", "-q", "-m", "web adjustment")
        self._git("-C", str(peer), "push", "-q", "origin", "adjust:sync/tester")
        (self.work / "README.md").write_text("b\n")
        result = self.run_sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.origin_sha("sync/tester"), self.work_sha())
        self.assertEqual((self.work / "README.md").read_text(), "b\n")
        self.assertEqual((self.work / "web-adjustment.md").read_text(), "from the PR page\n")


if __name__ == "__main__":
    unittest.main()
