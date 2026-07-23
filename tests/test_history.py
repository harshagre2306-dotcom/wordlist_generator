import json
import tempfile
import unittest
from pathlib import Path

from wordlist_generator.history import SessionHistory


class HistoryTests(unittest.TestCase):
    def test_history_persists_structured_export_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history = SessionHistory(history_path, max_entries=5)
            history.append(
                action="export",
                target="C:/out/wordlist.txt",
                candidates=25,
                user="admin",
                generation_time=1.25,
                total_passwords=25,
                export_type="txt",
                output_file="C:/out/wordlist.txt",
            )

            persisted = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual(len(persisted), 1)
            entry = persisted[0]
            self.assertIn("date", entry)
            self.assertIn("time", entry)
            self.assertEqual(entry["total_passwords"], 25)
            self.assertEqual(entry["generation_time"], 1.25)
            self.assertEqual(entry["export_type"], "txt")
            self.assertEqual(entry["output_file"], "C:/out/wordlist.txt")


if __name__ == "__main__":
    unittest.main()
