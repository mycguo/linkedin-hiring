"""Candidate loader for resume archives."""
from __future__ import annotations

import re
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set, Union

from pypdf import PdfReader

from models import CandidateProfile, Education, Experience, LinkedInSearchFilters


DEFAULT_SKILL_KEYWORDS: Set[str] = {
    # Languages
    "python",
    "java",
    "javascript",
    "typescript",
    "c",
    "c++",
    "c#",
    "go",
    "golang",
    "rust",
    "ruby",
    "swift",
    "kotlin",
    "scala",
    "php",
    "r",
    "sql",
    "nosql",
    "html",
    "css",
    "bash",
    "shell",
    "powershell",
    "matlab",
    "perl",
    "lua",
    "haskell",
    "clojure",
    # Frameworks & libraries
    "react",
    "angular",
    "vue",
    "svelte",
    "django",
    "flask",
    "fastapi",
    "spring",
    "hibernate",
    "express",
    "next.js",
    "node.js",
    ".net",
    "asp.net",
    "laravel",
    "rails",
    "redux",
    # Data & ML
    "pandas",
    "numpy",
    "scikit-learn",
    "sklearn",
    "tensorflow",
    "pytorch",
    "keras",
    "spark",
    "hadoop",
    "airflow",
    "databricks",
    "snowflake",
    "bigquery",
    "redshift",
    "tableau",
    "power bi",
    "looker",
    # Cloud & DevOps
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "terraform",
    "ansible",
    "chef",
    "puppet",
    "jenkins",
    "circleci",
    "github actions",
    "gitlab",
    "ci/cd",
    "prometheus",
    "grafana",
    "splunk",
    "elk",
    "elasticsearch",
    "kibana",
    # Databases
    "postgres",
    "postgresql",
    "mysql",
    "mariadb",
    "sqlite",
    "oracle",
    "sql server",
    "mongodb",
    "dynamodb",
    "cassandra",
    "redis",
    "neo4j",
    "couchbase",
    # Misc
    "microservices",
    "rest",
    "graphql",
    "grpc",
    "event-driven",
    "agile",
    "scrum",
    "tdd",
    "bdd",
    "pytest",
    "jest",
    "webpack",
    "babel",
    "lint",
}


STATE_ABBREVIATIONS = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
}


ArchiveSource = Union[str, Path, bytes, BytesIO]


class ResumeCandidateFetcher:
    """Load and transform resume PDFs into candidate profiles."""

    def __init__(
        self,
        archive: ArchiveSource,
        skill_keywords: Optional[Iterable[str]] = None,
    ) -> None:
        self.archive_source: ArchiveSource = archive
        if skill_keywords:
            self.skill_keywords = {skill.lower() for skill in skill_keywords}
        else:
            self.skill_keywords = {skill.lower() for skill in DEFAULT_SKILL_KEYWORDS}

    def search_candidates(
        self,
        filters: LinkedInSearchFilters,
        limit: int = 50,
    ) -> List[CandidateProfile]:
        candidates: List[CandidateProfile] = []

        with self._open_archive() as archive:
            for filename in sorted(archive.namelist()):
                if not filename.lower().endswith(".pdf"):
                    continue

                with archive.open(filename) as file_handle:
                    pdf_bytes = file_handle.read()

                profile = self._parse_resume(filename, pdf_bytes, filters)
                if profile:
                    candidates.append(profile)

                if len(candidates) >= limit:
                    break

        return candidates

    def _open_archive(self) -> zipfile.ZipFile:
        source = self.archive_source

        if isinstance(source, (str, Path)):
            archive_path = Path(source)
            if not archive_path.exists():
                raise FileNotFoundError(f"Resume archive not found: {archive_path}")
            return zipfile.ZipFile(archive_path, "r")

        if isinstance(source, bytes):
            return zipfile.ZipFile(BytesIO(source), "r")

        if hasattr(source, "read"):
            data = source.read()
            return zipfile.ZipFile(BytesIO(data), "r")

        raise ValueError("Unsupported archive source type")

    def _parse_resume(
        self,
        filename: str,
        pdf_bytes: bytes,
        filters: LinkedInSearchFilters,
    ) -> Optional[CandidateProfile]:
        text = self._extract_text(pdf_bytes)
        if not text:
            return None

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None

        name = self._derive_name(filename, lines)
        linkedin_url = self._extract_linkedin_url(text)

        location = self._extract_location(lines)
        summary = self._extract_summary(lines)
        headline = self._extract_headline(lines)

        skills = self._extract_skills(text, filters.skills)
        experiences = self._extract_experiences(lines)
        education = self._extract_education(lines)

        current_position = experiences[0].title if experiences else None
        current_company = experiences[0].company if experiences else None

        return CandidateProfile(
            linkedin_id=Path(filename).stem,
            linkedin_url=linkedin_url or f"resume:{Path(filename).stem}",
            name=name,
            headline=headline,
            location=location,
            summary=summary,
            current_position=current_position,
            current_company=current_company,
            experiences=experiences,
            education=education,
            skills=sorted(skills),
            certifications=[],
        )

    @staticmethod
    def _extract_text(pdf_bytes: bytes) -> str:
        buffer = BytesIO(pdf_bytes)
        reader = PdfReader(buffer)
        text_parts: List[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
        return "\n".join(text_parts)

    @staticmethod
    def _derive_name(filename: str, lines: Sequence[str]) -> str:
        base = Path(filename).stem
        parts = [part for part in base.split("_") if part]
        if parts:
            guess = " ".join(parts[:2])
            if len(guess.strip()) > 2:
                return guess.replace("-", " ")

        first_line = lines[0]
        if len(first_line.split()) <= 6:
            return first_line

        return base.replace("_", " ")

    @staticmethod
    def _extract_headline(lines: Sequence[str]) -> str:
        if len(lines) >= 2:
            second_line = lines[1]
            if len(second_line.split()) > 2:
                return second_line
        return ""

    @staticmethod
    def _extract_summary(lines: Sequence[str]) -> str:
        summary_lines: List[str] = []
        for line in lines[1:6]:
            if ResumeCandidateFetcher._looks_like_section_header(line):
                break
            summary_lines.append(line)
        return " ".join(summary_lines[:3])

    @staticmethod
    def _looks_like_section_header(line: str) -> bool:
        upper = line.upper()
        return upper in {"SUMMARY", "PROFILE", "PROFESSIONAL SUMMARY", "OBJECTIVE"}

    @staticmethod
    def _extract_linkedin_url(text: str) -> Optional[str]:
        match = re.search(r"https://www\.linkedin\.com/in/[A-Za-z0-9\-_/]+", text)
        return match.group(0) if match else None

    def _extract_skills(self, text: str, job_skills: Iterable[str]) -> Set[str]:
        keywords = set(self.skill_keywords)
        for skill in job_skills:
            keywords.add(skill.lower())

        text_lower = text.lower()
        found: Set[str] = set()
        for skill in keywords:
            if not skill:
                continue
            pattern = re.compile(rf"\b{re.escape(skill)}\b")
            if pattern.search(text_lower):
                found.add(skill)

        return found

    def _extract_location(self, lines: Sequence[str]) -> str:
        for line in lines[:8]:
            match = re.search(r"([A-Za-z .]+),\s*([A-Z]{2})", line)
            if match and match.group(2) in STATE_ABBREVIATIONS:
                return match.group(0)
        return ""

    def _extract_experiences(self, lines: Sequence[str]) -> List[Experience]:
        experiences: List[Experience] = []
        for idx, line in enumerate(lines):
            if not line or len(line.split()) < 2:
                continue

            if re.search(r"(19|20)\d{2}", line):
                title, company = self._split_title_company(line)
                description = line
                for offset in range(1, 4):
                    if idx + offset >= len(lines):
                        break
                    next_line = lines[idx + offset]
                    if re.search(r"(19|20)\d{2}", next_line):
                        break
                    if self._looks_like_section_header(next_line):
                        break
                    if len(next_line) < 4:
                        continue
                    description += " " + next_line

                experiences.append(
                    Experience(
                        title=title or "Professional Experience",
                        company=company,
                        description=description,
                        is_current="present" in line.lower(),
                    )
                )

            if len(experiences) >= 5:
                break

        if not experiences:
            snippet = " ".join(lines[:20])
            experiences.append(
                Experience(
                    title="Professional Experience",
                    company="",
                    description=snippet,
                )
            )

        return experiences

    @staticmethod
    def _split_title_company(line: str) -> tuple[str, str]:
        normalized = line.replace(" @ ", " at ")
        if " at " in normalized.lower():
            parts = re.split(r"\s+at\s+", normalized, flags=re.IGNORECASE)
            if len(parts) >= 2:
                return parts[0].strip(), parts[1].split(" - ")[0].strip()

        tokens = re.split(r"\s+-\s+", line)
        if len(tokens) >= 2:
            return tokens[0].strip(), tokens[1].strip()

        return line.split(",")[0].strip(), ""

    def _extract_education(self, lines: Sequence[str]) -> List[Education]:
        educations: List[Education] = []
        for line in lines:
            match = re.search(
                r"(Bachelor|Master|B\.Sc|M\.Sc|B\.S\.|M\.S\.|Ph\.D|Doctor|Associate)",
                line,
                re.IGNORECASE,
            )
            if match:
                degree = match.group(0)
                educations.append(
                    Education(
                        degree=degree,
                        field="",
                        school=line.strip(),
                    )
                )

            if len(educations) >= 3:
                break

        return educations
