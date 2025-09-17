"""Tests for resume loader helper behaviour."""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from resume_loader import ResumeCandidateFetcher


class ResumeLoaderHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fetcher = ResumeCandidateFetcher(PROJECT_ROOT / "download.zip")

    def test_derive_name_prefers_filename_parts(self) -> None:
        lines = ["Random Heading", "Engineer"]
        name = self.fetcher._derive_name("Jane_Doe_resume.pdf", lines)
        self.assertEqual(name, "Jane Doe")

    def test_extract_skills_merges_job_requirements(self) -> None:
        text = """
        Experienced engineer with strong Python background and Terraform automation.
        Also familiar with machine learning workflows.
        """
        skills = self.fetcher._extract_skills(text, ["Python", "Terraform", "Go"])
        self.assertIn("python", skills)
        self.assertIn("terraform", skills)
        self.assertNotIn("go", skills)

    def test_extract_experiences_returns_entries(self) -> None:
        lines = [
            "PROFESSIONAL EXPERIENCE",
            "Senior Software Engineer at Tech Corp 2021 - Present",
            "Led backend development and cloud migrations.",
            "Software Engineer at Startup 2018 - 2021",
            "Built APIs in Python and React.",
        ]
        experiences = self.fetcher._extract_experiences(lines)
        self.assertGreaterEqual(len(experiences), 2)
        self.assertEqual(experiences[0].company.lower(), "tech corp")
        self.assertTrue(experiences[0].is_current)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
