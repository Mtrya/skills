import fcntl
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class SyncTests(unittest.TestCase):
    """Exercise the real sync script, Git transport, rebases and linker."""

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
        shutil.copy(REPO / "link.sh", seed / "link.sh")
        self._git("-C", str(seed), "add", "-A")
        self._git("-C", str(seed), "commit", "-q", "-m", "init")
        self._git("-C", str(seed), "push", "-q", "origin", "main")
        self.work = self.root / "work"
        self._git("clone", "-q", str(self.origin), str(self.work))
        self._git("-C", str(self.work), "config", "user.name", "tester")
        self._git("-C", str(self.work), "config", "user.email", "tester@example.com")

    def _env(self):
        env = dict(os.environ, SYNC_ID="tester", HOME=str(self.root))
        if hasattr(self, "github"):
            env["SYNC_TEST_GITHUB"] = str(self.github)
            env["PATH"] = str(REPO / "tests" / "fixtures") + os.pathsep + env["PATH"]
        for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY"):
            env.pop(var, None)
        return env

    def _git(self, *args):
        subprocess.run(["git", *args], check=True, capture_output=True, text=True, env=self._env())

    def _git_out(self, *args):
        return subprocess.run(
            ["git", *args], check=True, capture_output=True, text=True, env=self._env()
        ).stdout

    def run_sync(self, *args):
        return subprocess.run(
            ["bash", str(self.work / "scripts" / "sync.sh"), *args],
            capture_output=True,
            text=True,
            env=self._env(),
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
        self._git("-C", str(peer), "config", "user.name", "browser editor")
        self._git("-C", str(peer), "config", "user.email", "browser@example.com")
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


    def enable_github(self):
        self.github = self.root / "github.json"
        self.github.write_text(json.dumps({"origin": str(self.origin), "prs": []}))
        self._git("-C", str(self.work), "remote", "set-url", "origin", "https://github.com/test/skills.git")
        self._git("-C", str(self.work), "config", f"url.{self.origin}.insteadOf", "https://github.com/test/skills.git")

    def github_data(self):
        return json.loads(self.github.read_text())

    def set_pr(self, state, **fields):
        data = self.github_data()
        data["prs"][0].update(state=state, **fields)
        self.github.write_text(json.dumps(data))

    def on_lookup(self, offset, event):
        data = self.github_data()
        data.setdefault("events", {})[str(data["reads"] + offset)] = event
        self.github.write_text(json.dumps(data))

    def assert_sync(self, *args):
        result = self.run_sync(*args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def publish(self, content="local\n"):
        (self.work / "README.md").write_text(content)
        self.assert_sync()
        return self.work_sha()

    def commit_peer(self, peer, filename, content, target="main", force=False):
        path = peer / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        self._git("-C", str(peer), "add", "-A")
        self._git("-C", str(peer), "commit", "-q", "-m", "peer edit")
        self._git("-C", str(peer), "push", "-q", "origin", f"{'+' if force else ''}HEAD:{target}")

    def test_idle_cycle_is_silent(self):
        self.enable_github()
        self.assert_sync()
        result = self.assert_sync()
        self.assertEqual(result.stdout + result.stderr, "")

    def test_published_but_unchanged_cycle_is_silent(self):
        self.enable_github()
        self.publish()
        before = len(self.github_data()["calls"])
        result = self.assert_sync()
        self.assertEqual(result.stdout + result.stderr, "")
        self.assertTrue(all(call[1] == "list" for call in self.github_data()["calls"][before:]))

    def test_pull_only_reconciles_added_and_removed_skill_links(self):
        self.assert_sync()
        peer = self.peer()
        self.commit_peer(peer, "tools/new/SKILL.md", "new skill\n")
        self.assert_sync()
        link = self.root / ".agents/skills/new"
        self.assertEqual(link.resolve(), self.work / "tools/new")
        self._git("-C", str(peer), "rm", "-r", "tools/new")
        self._git("-C", str(peer), "commit", "-q", "-m", "remove skill")
        self._git("-C", str(peer), "push", "-q", "origin", "main")
        self.assert_sync()
        self.assertFalse(link.is_symlink())

    def test_rejection_is_acknowledged_and_future_edits_create_a_new_pr(self):
        self.enable_github()
        skill = self.work / "tools/new/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("skill\n")
        self.publish()
        self.set_pr("CLOSED")
        self.assert_sync()
        self.assertFalse((self.root / ".agents/skills/new").is_symlink())
        self.assertIsNone(self.origin_sha("sync/tester"))
        self.assertEqual(self.work_sha(), self.work_sha("main"))
        self.assert_sync()
        self.publish("new unrelated work\n")
        self.assertEqual((self.work / "README.md").read_text(), "new unrelated work\n")
        self.assertEqual([p["state"] for p in self.github_data()["prs"]], ["OPEN", "CLOSED"])
        self.assert_sync()
        self.assertEqual((self.work / "README.md").read_text(), "new unrelated work\n")

    def test_failed_rejection_recheck_preserves_dirty_work_and_remote(self):
        self.enable_github()
        tip = self.publish()
        self.set_pr("CLOSED")
        (self.work / "README.md").write_text("still editing\n")
        self.on_lookup(2, "fail")
        result = self.run_sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.origin_sha("sync/tester"), tip)
        self.assertEqual((self.work / "README.md").read_text(), "still editing\n")
        self.assertFalse((self.work / ".git/skills-sync.state").exists())

    def test_reopen_at_final_recheck_cancels_rejection(self):
        self.enable_github()
        self.publish()
        self.set_pr("CLOSED")
        self.on_lookup(2, "OPEN")
        self.assert_sync()
        self.assertEqual((self.work / "README.md").read_text(), "local\n")
        self.assertIsNotNone(self.origin_sha("sync/tester"))
        self.assertEqual(len(self.github_data()["prs"]), 1)

    def test_close_while_publishing_does_not_recreate_pr(self):
        self.enable_github()
        self.publish()
        (self.work / "README.md").write_text("next edit\n")
        self.on_lookup(3, "CLOSED")
        self.assertNotEqual(self.run_sync().returncode, 0)
        self.assertEqual(len(self.github_data()["prs"]), 1)
        self.assert_sync()
        self.assertEqual((self.work / "README.md").read_text(), "seed\n")
        self.assertIsNone(self.origin_sha("sync/tester"))

    def squash_merge(self, delete_branch=False, peer=None):
        peer = peer or self.peer()
        self._git("-C", str(peer), "fetch", "-q", "origin", "sync/tester")
        tip = self._git_out("-C", str(peer), "rev-parse", "FETCH_HEAD").strip()
        self._git("-C", str(peer), "merge", "--squash", "FETCH_HEAD")
        self._git("-C", str(peer), "commit", "-q", "-m", "squash PR")
        self._git("-C", str(peer), "push", "-q", "origin", "main")
        merged = self.origin_sha("main")
        self.set_pr("MERGED", headRefOid=tip, mergeCommit={"oid": merged})
        self._git("--git-dir", str(self.origin), "update-ref", "refs/pull/1/head", tip)
        if delete_branch:
            self._git("-C", str(peer), "push", "-q", "origin", "--delete", "sync/tester")
        return merged

    def test_squash_merge_drops_multiple_edits_to_the_same_lines(self):
        self.enable_github()
        self.publish("first\n")
        self.publish("second\n")
        merged = self.squash_merge()
        self.assert_sync()
        self.assertEqual(self.work_sha(), merged)
        self.assertIsNone(self.origin_sha("sync/tester"))
        self.assertEqual((self.work / "README.md").read_text(), "second\n")
        self.assert_sync()
        self.assertEqual(len(self.github_data()["prs"]), 1)

    def test_squash_merge_preserves_later_work_with_deleted_remote_branch(self):
        self.enable_github()
        self.publish("first\n")
        self.publish("second\n")
        merged = self.squash_merge(delete_branch=True)
        (self.work / "README.md").write_text("third\n")
        self.assert_sync()
        self.assertEqual((self.work / "README.md").read_text(), "third\n")
        self._git("-C", str(self.work), "merge-base", "--is-ancestor", merged, "HEAD")
        self.assertEqual(self._git_out("-C", str(self.work), "rev-list", "--count", "main..HEAD").strip(), "1")
        self.assertEqual([p["state"] for p in self.github_data()["prs"]], ["OPEN", "MERGED"])

    def test_hostname_collision_with_same_git_author_is_rejected_before_adoption(self):
        self.enable_github()
        original_tip = self.publish()
        other = self.peer()
        self._git("-C", str(other), "remote", "set-url", "origin", "https://github.com/test/skills.git")
        self._git("-C", str(other), "config", f"url.{self.origin}.insteadOf", "https://github.com/test/skills.git")
        self.work = other
        (other / "README.md").write_text("other machine\n")
        self.assertNotEqual(self.run_sync().returncode, 0)
        self.assertEqual(self.work_branch(), "main")
        self.assertEqual((other / "README.md").read_text(), "other machine\n")
        self.assertEqual(self.origin_sha("sync/tester"), original_tip)

    def test_changed_ownership_is_checked_even_when_local_identity_is_unchanged(self):
        self.publish()
        identity = (self.work / ".git/skills-sync.identity").read_text()
        peer = self.peer()
        self._git("-C", str(peer), "checkout", "-q", "-b", "collision", "origin/sync/tester")
        self._git("-C", str(peer), "commit", "-q", "--allow-empty", "-m", "Skills-Sync-Owner: tester foreign")
        self._git("-C", str(peer), "push", "-q", "origin", "HEAD:sync/tester")
        (self.work / "README.md").write_text("uncommitted\n")
        self.assertNotEqual(self.run_sync().returncode, 0)
        self.assertEqual((self.work / ".git/skills-sync.identity").read_text(), identity)
        self.assertEqual((self.work / "README.md").read_text(), "uncommitted\n")

    def test_remote_rewrite_preserves_unpublished_local_commits(self):
        base = self.publish()
        self.publish("second\n")
        peer = self.peer()
        self._git("-C", str(peer), "checkout", "-q", "-b", "adjust", base)
        self.commit_peer(peer, "web-adjustment.md", "rewritten\n", "sync/tester", force=True)
        (self.work / "local.md").write_text("unpublished\n")
        self.assert_sync()
        self.assertEqual((self.work / "README.md").read_text(), "local\n")
        self.assertEqual((self.work / "web-adjustment.md").read_text(), "rewritten\n")
        self.assertEqual((self.work / "local.md").read_text(), "unpublished\n")

    def test_conflict_publishes_pr_and_comments_once_per_main_sha(self):
        self.enable_github()
        self.assert_sync()
        peer = self.peer()
        self.commit_peer(peer, "README.md", "upstream\n")
        (self.work / "README.md").write_text("local conflict\n")
        self.assertNotEqual(self.run_sync().returncode, 0)
        self.assertEqual(self.github_data()["prs"][0]["state"], "OPEN")
        self.assertEqual(len(self.github_data()["comments"]), 1)
        self.assertEqual(self.origin_sha("sync/tester"), self.work_sha())
        self.assertEqual((self.work / "README.md").read_text(), "local conflict\n")
        self.assertNotEqual(self.run_sync().returncode, 0)
        self.assertEqual(len(self.github_data()["comments"]), 1)
        self.commit_peer(peer, "unrelated.md", "advance main\n")
        self.assertNotEqual(self.run_sync().returncode, 0)
        self.assertEqual(len(self.github_data()["comments"]), 2)
        self.set_pr("CLOSED")
        self.assert_sync()
        self.assertEqual((self.work / "README.md").read_text(), "upstream\n")

    def test_lock_prevents_overlapping_cycle(self):
        self.assert_sync()
        (self.work / "README.md").write_text("pending\n")
        with (self.work / ".git/skills-sync.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.assert_sync()
        self.assertEqual(result.stdout + result.stderr, "")
        self.assertFalse(self.work_clean())
        self.assertIsNone(self.origin_sha("sync/tester"))


    def test_failed_lookup_with_historical_rejection_and_new_open_pr_is_safe(self):
        self.enable_github()
        self.publish()
        self.set_pr("CLOSED")
        self.assert_sync()
        tip = self.publish("new PR\n")
        (self.work / "README.md").write_text("unfinished\n")
        self.on_lookup(1, "fail")
        self.assertNotEqual(self.run_sync().returncode, 0)
        self.assertEqual(self.origin_sha("sync/tester"), tip)
        self.assertEqual((self.work / "README.md").read_text(), "unfinished\n")
        self.assert_sync()
        self.set_pr("CLOSED")
        self.assert_sync()
        self.assertEqual(self.work_sha(), self.work_sha("main"))
        self.assertEqual([p["state"] for p in self.github_data()["prs"]], ["CLOSED", "CLOSED"])

    def test_squash_merge_falls_back_to_pull_ref_when_head_is_deleted(self):
        self.enable_github()
        self.publish("first\n")
        tip = self.publish("second\n")
        merged = self.squash_merge(delete_branch=True)
        self._git("--git-dir", str(self.origin), "update-ref", "refs/pull/1/head", tip)
        self.set_pr("MERGED", headRefOid="")
        self.assert_sync()
        self.assertEqual(self.work_sha(), merged)

    def test_link_failure_is_retried_on_next_idle_cycle(self):
        self.assert_sync()
        peer = self.peer()
        self.commit_peer(peer, "tools/new/SKILL.md", "new skill\n")
        destination = self.root / ".agents/skills"
        destination.rmdir()
        destination.write_text("blocks linking\n")
        self.assertNotEqual(self.run_sync().returncode, 0)
        destination.unlink()
        self.assert_sync()
        self.assertTrue((destination / "new").is_symlink())

    def test_remote_adjustment_conflict_does_not_overwrite_remote_or_local(self):
        self.enable_github()
        self.publish()
        peer = self.peer()
        self._git("-C", str(peer), "checkout", "-q", "-b", "adjust", "origin/sync/tester")
        self.commit_peer(peer, "README.md", "web edit\n", "sync/tester")
        remote = self.origin_sha("sync/tester")
        (self.work / "README.md").write_text("local edit\n")
        self.assertNotEqual(self.run_sync().returncode, 0)
        self.assertEqual(self.origin_sha("sync/tester"), remote)
        self.assertEqual((self.work / "README.md").read_text(), "local edit\n")
        self.assertEqual(len(self.github_data()["comments"]), 1)

    def test_no_cycle_pushes_main(self):
        before = self.origin_sha("main")
        self.publish()
        self.assert_sync("discard")
        self.assertEqual(self.origin_sha("main"), before)


    def test_squash_merge_adopts_unseen_web_edit_after_branch_deletion(self):
        self.enable_github()
        self.publish()
        peer = self.peer()
        self._git("-C", str(peer), "checkout", "-q", "-b", "adjust", "origin/sync/tester")
        self.commit_peer(peer, "web.md", "web adjustment\n", "sync/tester")
        self._git("-C", str(peer), "checkout", "-q", "main")
        self.squash_merge(delete_branch=True, peer=peer)
        (self.work / "later.md").write_text("later work\n")
        self.assert_sync()
        self.assertEqual((self.work / "web.md").read_text(), "web adjustment\n")
        self.assertEqual((self.work / "later.md").read_text(), "later work\n")
        self.assertEqual(self._git_out("-C", str(self.work), "diff", "--name-only", "main..HEAD").strip(), "later.md")

    def test_post_merge_work_conflict_gets_a_new_pr_and_comment(self):
        self.enable_github()
        self.publish("first\n")
        self.publish("second\n")
        self.squash_merge(delete_branch=True)
        peer = self.root / "peer"
        self.commit_peer(peer, "README.md", "upstream after merge\n")
        (self.work / "README.md").write_text("local after merge\n")
        self.assertNotEqual(self.run_sync().returncode, 0)
        self.assertEqual([p["state"] for p in self.github_data()["prs"]], ["OPEN", "MERGED"])
        self.assertEqual(len(self.github_data()["comments"]), 1)
        self.assertEqual((self.work / "README.md").read_text(), "local after merge\n")
        self.assertEqual(self.origin_sha("sync/tester"), self.work_sha())


if __name__ == "__main__":
    unittest.main()
