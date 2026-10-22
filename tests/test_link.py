import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "skill repo"
        self.repo.mkdir()
        self.dest = self.root / "installed skills"
        self.dest.mkdir()
        shutil.copy(Path(__file__).resolve().parents[1] / "link.sh", self.repo)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)

    def skill(self, path):
        folder = self.repo / path
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text("---\nname: example\n---\n")
        return folder

    def run_link(self):
        subprocess.run(
            ["bash", str(self.repo / "link.sh"), str(self.dest)],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_links_tracked_and_new_skills_only(self):
        tracked = self.skill("research/tracked")
        new = self.skill("tools/new")
        self.skill("tools/ignored")
        self.skill("tools/new/examples/nested")
        self.skill("deprecated/old")
        self.skill("other/external")
        (self.repo / ".gitignore").write_text("tools/ignored/\nother/\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "research"], check=True)
        self.run_link()
        self.run_link()
        self.assertEqual({p.name for p in self.dest.iterdir()}, {"tracked", "new"})
        self.assertEqual((self.dest / "tracked").resolve(), tracked)
        self.assertEqual((self.dest / "new").resolve(), new)

    def test_preserves_other_owners_and_prunes_retired_links(self):
        self.skill("tools/directory")
        self.skill("tools/external")
        retired = self.skill("tools/retired")
        subprocess.run(["git", "-C", str(self.repo), "add", "tools"], check=True)
        (self.dest / "directory").mkdir()
        marker = self.dest / "directory" / "keep"
        marker.write_text("upstream")
        outside = self.root / "outside"
        outside.mkdir()
        (self.dest / "external").symlink_to(outside, target_is_directory=True)
        (self.dest / "retired").symlink_to(retired, target_is_directory=True)
        foreign_broken = self.dest / "foreign-broken"
        foreign_broken.symlink_to(self.root / "missing")
        (self.repo / "deprecated").mkdir()
        retired.rename(self.repo / "deprecated" / "retired")
        self.run_link()
        self.assertEqual(marker.read_text(), "upstream")
        self.assertEqual((self.dest / "external").resolve(), outside)
        self.assertFalse(os.path.lexists(self.dest / "retired"))
        self.assertTrue(foreign_broken.is_symlink())


if __name__ == "__main__":
    unittest.main()
