import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from runtime_skills import owned_skills


class OwnedSkillsTests(unittest.TestCase):
    def test_missing_records_are_not_owned(self):
        entries = [{"name": "lark-doc", "source": "larksuite/cli", "path": None, "status": "missing"},
                   {"name": "lark-im", "source": "larksuite/cli", "path": "/x/lark-im", "status": "tracked"}]
        self.assertEqual(owned_skills("lark", entries), {"lark-im"})

    def test_pathless_entry_does_not_crash_hf_probe(self):
        entries = [{"name": "unrelated", "source": "stablyai/orca", "path": None, "status": "untracked"}]
        self.assertEqual(owned_skills("hf", entries), set())

    def test_source_match_is_case_insensitive(self):
        entries = [{"name": "inspire", "source": "RealZillionX/InspireSkill", "path": "/x/inspire", "status": "tracked"}]
        self.assertEqual(owned_skills("inspire", entries), {"inspire"})

    def test_untracked_entries_are_not_owned(self):
        entries = [{"name": "inspire", "source": None, "path": "/x/inspire", "status": "untracked"}]
        self.assertEqual(owned_skills("inspire", entries), set())

    def test_hf_manifest_fallback_claims_marketplace_copies(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / ".hf-skill-manifest.json").touch()
            entries = [{"name": "hf-cli", "source": "someone-else/repo", "path": temp, "status": "tracked"}]
            self.assertEqual(owned_skills("hf", entries), {"hf-cli"})


if __name__ == "__main__":
    unittest.main()
