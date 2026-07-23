import os
import tempfile
import unittest

from wordlist_generator.generator import export_wordlist, generate_wordlist


class GeneratorTests(unittest.TestCase):
    def test_generate_wordlist_includes_expected_patterns(self):
        candidates = generate_wordlist(name="Rahul", dob="1998", interests=["bike"])

        self.assertIn("rahul123", candidates)
        self.assertIn("bike1998", candidates)
        self.assertIn("rahul@98", candidates)

    def test_generate_wordlist_supports_custom_suffixes_and_separators(self):
        candidates = generate_wordlist(
            name="Rahul",
            dob="1998",
            interests=["bike"],
            suffixes=["123"],
            separators=["-"],
        )

        self.assertIn("rahul-123", candidates)
        self.assertIn("rahul-98", candidates)

    def test_generate_wordlist_respects_requested_count(self):
        candidates = generate_wordlist(name="Rahul", dob="1998", interests=["bike"], count=3)

        self.assertEqual(len(candidates), 3)
        self.assertTrue(all(candidate for candidate in candidates))

    def test_generate_wordlist_can_extend_to_exact_requested_count(self):
        candidates = generate_wordlist(name="Rahul", dob="1998", interests=["bike"], count=100)

        self.assertEqual(len(candidates), 100)
        self.assertTrue(all(candidate for candidate in candidates))

    def test_export_wordlist_writes_text_file(self):
        candidates = generate_wordlist(name="Rahul", dob="1998", interests=["bike"])

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "wordlist.txt")
            export_wordlist(candidates, output_path)

            self.assertTrue(os.path.exists(output_path))
            with open(output_path, "r", encoding="utf-8") as handle:
                saved = handle.read().splitlines()

            self.assertGreaterEqual(len(saved), 1)
            self.assertIn("rahul123", saved)


if __name__ == "__main__":
    unittest.main()
