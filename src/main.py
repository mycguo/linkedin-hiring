"""Streamlit app for resume-based candidate scoring."""
import os
import uuid
from typing import List, Dict, Optional
from datetime import datetime
import json
from dataclasses import asdict

import requests
import streamlit as st

from models import (
    ParsedJobDescription,
    CandidateProfile,
    SearchSession,
    RankedCandidate,
    LinkedInSearchFilters,
)
from job_parser import JobDescriptionParser
from filter_generator import LinkedInFilterGenerator
from scoring_engine import ScoringEngine
from resume_loader import ResumeCandidateFetcher


class LinkedInCandidateSystem:
    """
    Main system orchestrator for LinkedIn candidate processing
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        candidate_fetcher: Optional[ResumeCandidateFetcher] = None,
    ) -> None:
        """
        Initialize the system with all components

        Args:
            openai_api_key: Optional OpenAI API key for enhanced job parsing
        """
        self.job_parser = JobDescriptionParser(openai_api_key)
        self.filter_generator = LinkedInFilterGenerator()
        self.scoring_engine = ScoringEngine()
        self.candidate_fetcher = candidate_fetcher

        # Track active sessions
        self.sessions: Dict[str, SearchSession] = {}

    def process_job_description(self, job_text: str, company_name: Optional[str] = None) -> str:
        """
        Process a job description and create a new search session

        Args:
            job_text: Raw job description text
            company_name: Optional company name

        Returns:
            Session ID for tracking the search
        """
        # Create session
        session_id = str(uuid.uuid4())

        try:
            # Parse job description
            parsed_job = self.job_parser.parse(job_text)
            if company_name:
                parsed_job.company_name = company_name

            # Generate LinkedIn search filters
            search_filters = self.filter_generator.generate_filters(parsed_job)
            optimized_filters = self.filter_generator.optimize_for_api_limits(search_filters)

            # Create search session
            session = SearchSession(
                session_id=session_id,
                job_description_id=session_id,  # Using same ID for simplicity
                parsed_job=parsed_job,
                search_filters=optimized_filters,
                status="ready_for_search"
            )

            self.sessions[session_id] = session

            print(f"✓ Job description processed successfully")
            print(f"✓ Generated {len(optimized_filters.skills)} skill filters")
            print(f"✓ Generated {len(optimized_filters.title_current)} title filters")
            print(f"✓ Search keywords: {optimized_filters.keywords}")

            return session_id

        except Exception as e:
            # Create failed session
            session = SearchSession(
                session_id=session_id,
                job_description_id=session_id,
                parsed_job=ParsedJobDescription(role_title="Parse Failed", job_description_text=job_text),
                search_filters=LinkedInSearchFilters(keywords=""),
                status="failed",
                error_message=str(e)
            )
            self.sessions[session_id] = session
            raise Exception(f"Failed to process job description: {str(e)}")

    def fetch_candidates(
        self,
        session_id: str,
        max_candidates: int = 50,
    ) -> List[CandidateProfile]:
        """Retrieve candidates from the configured source for a given session."""
        if not self.candidate_fetcher:
            raise RuntimeError("Candidate fetcher is not configured.")

        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.sessions[session_id]
        session.status = "searching"

        candidates = self.candidate_fetcher.search_candidates(
            session.search_filters,
            limit=max_candidates,
        )

        session.total_candidates_found = len(candidates)
        session.status = "ready_for_scoring"
        return candidates

    def get_search_filters(self, session_id: str) -> Dict:
        """
        Get the generated LinkedIn search filters for a session

        Args:
            session_id: Session ID

        Returns:
            Dictionary with search filters
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.sessions[session_id]
        return asdict(session.search_filters)

    def score_candidates(
        self,
        session_id: str,
        candidates: List[CandidateProfile]
    ) -> List[RankedCandidate]:
        """
        Score and rank candidates for a job

        Args:
            session_id: Session ID
            candidates: List of candidate profiles

        Returns:
            List of ranked candidates with scores
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.sessions[session_id]

        try:
            # Update session status
            session.status = "scoring"
            session.total_candidates_found = max(
                session.total_candidates_found,
                len(candidates),
            )

            # Score and rank candidates
            ranked_candidates = self.scoring_engine.rank_candidates(
                session.parsed_job,
                candidates
            )

            # Update session
            session.candidates_processed = len(candidates)
            session.candidates_scored = len(ranked_candidates)
            session.status = "completed"
            session.completed_at = datetime.now()

            print(f"✓ Scored {len(ranked_candidates)} candidates")

            return ranked_candidates

        except Exception as e:
            session.status = "failed"
            session.error_message = str(e)
            raise Exception(f"Failed to score candidates: {str(e)}")

    def get_session_status(self, session_id: str) -> Dict:
        """
        Get the status of a search session

        Args:
            session_id: Session ID

        Returns:
            Dictionary with session status
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.sessions[session_id]
        return {
            "session_id": session.session_id,
            "status": session.status,
            "job_title": session.parsed_job.role_title,
            "total_candidates_found": session.total_candidates_found,
            "candidates_processed": session.candidates_processed,
            "candidates_scored": session.candidates_scored,
            "created_at": session.created_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "error_message": session.error_message
        }

    def export_results(
        self,
        ranked_candidates: List[RankedCandidate],
        format: str = "json"
    ) -> str:
        """
        Export results in specified format

        Args:
            ranked_candidates: List of ranked candidates
            format: Export format ('json', 'csv')

        Returns:
            Formatted results string
        """
        if format == "json":
            return self._export_json(ranked_candidates)
        elif format == "csv":
            return self._export_csv(ranked_candidates)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_json(self, ranked_candidates: List[RankedCandidate]) -> str:
        """Export as JSON"""
        export_data = []

        for candidate in ranked_candidates:
            export_data.append({
                "rank": candidate.rank,
                "percentile": candidate.percentile,
                "overall_score": candidate.score.overall_score,
                "name": candidate.profile.name,
                "linkedin_url": candidate.profile.linkedin_url,
                "headline": candidate.profile.headline,
                "location": candidate.profile.location,
                "current_position": candidate.profile.current_position,
                "current_company": candidate.profile.current_company,
                "skills": candidate.profile.skills,
                "score_breakdown": {
                    comp.name: {
                        "raw_score": comp.raw_score,
                        "weight": comp.weight,
                        "weighted_score": comp.weighted_score
                    }
                    for comp in candidate.score.components
                },
                "match_explanation": candidate.score.match_explanation,
                "missing_requirements": candidate.score.missing_requirements,
                "additional_strengths": candidate.score.additional_strengths,
                "recommendations": candidate.score.recommendations
            })

        return json.dumps(export_data, indent=2, default=str)

    def _export_csv(self, ranked_candidates: List[RankedCandidate]) -> str:
        """Export as CSV"""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            'Rank', 'Name', 'Score', 'Percentile', 'LinkedIn URL', 'Headline',
            'Location', 'Current Position', 'Current Company', 'Skills',
            'Match Explanation', 'Missing Requirements'
        ])

        # Write data
        for candidate in ranked_candidates:
            writer.writerow([
                candidate.rank,
                candidate.profile.name,
                f"{candidate.score.overall_score:.1f}",
                f"{candidate.percentile:.1f}",
                candidate.profile.linkedin_url,
                candidate.profile.headline,
                candidate.profile.location,
                candidate.profile.current_position or "",
                candidate.profile.current_company or "",
                "; ".join(candidate.profile.skills[:10]),
                candidate.score.match_explanation,
                "; ".join(candidate.score.missing_requirements)
            ])

        return output.getvalue()

def _load_job_description(job_url: str, job_text: str) -> str:
    if job_text.strip():
        return job_text.strip()

    if not job_url:
        raise ValueError("Provide a job description URL or paste the job description text.")

    response = requests.get(job_url, timeout=10)
    response.raise_for_status()
    return response.text


def _build_candidate_fetcher(uploaded_file, fallback_path: str) -> ResumeCandidateFetcher:
    if uploaded_file is not None:
        data = uploaded_file.getvalue()
        return ResumeCandidateFetcher(data)

    return ResumeCandidateFetcher(fallback_path)


def _display_filters(filters: Dict):
    st.subheader("Generated Search Filters")
    normalized = {}
    for key, value in filters.items():
        if isinstance(value, list):
            normalized[key] = [str(v) for v in value]
        else:
            normalized[key] = str(value) if value is not None else ""

    cols = st.columns(2)
    with cols[0]:
        st.json(normalized)

    with cols[1]:
        for key, value in normalized.items():
            if isinstance(value, list):
                preview = ", ".join(value[:5])
                if len(value) > 5:
                    preview += " …"
                st.markdown(f"**{key.replace('_', ' ').title()}**: {preview or '—'}")
            else:
                st.markdown(f"**{key.replace('_', ' ').title()}**: {value or '—'}")


def _display_candidates(ranked_candidates: List[RankedCandidate]):
    st.subheader("Ranked Candidates")
    if not ranked_candidates:
        st.info("No candidates matched the criteria.")
        return

    for candidate in ranked_candidates:
        profile = candidate.profile
        score = candidate.score

        with st.container():
            st.markdown(f"### Rank #{candidate.rank}: {profile.name}")
            st.markdown(
                f"**Score:** {score.overall_score:.1f}/100  \
**Percentile:** {candidate.percentile:.1f}%  \
**Current Role:** {profile.current_position or 'N/A'} at {profile.current_company or 'N/A'}  \
**Location:** {profile.location or 'N/A'}"
            )

            st.markdown(f"**Match Summary:** {score.match_explanation}")

            if score.missing_requirements:
                st.markdown("**Missing Requirements:** " + ", ".join(score.missing_requirements[:5]))

            if score.additional_strengths:
                st.markdown("**Strengths:** " + ", ".join(score.additional_strengths[:5]))

            if score.recommendations:
                st.markdown("**Recommendation:** " + score.recommendations[0])


def main():
    st.set_page_config(page_title="Resume Scoring Engine", layout="wide")
    st.title("📄 Resume-Based Candidate Scoring")
    st.caption("Parse a job description and rank resume PDFs in a zip archive.")

    st.subheader("Job Description")
    job_url = st.text_input("Job Description URL", placeholder="https://...", key="job_url_input")
    job_text = st.text_area(
        "Or Paste Job Description",
        height=220,
        placeholder="Paste the job description text here...",
        key="job_text_input",
    )

    with st.sidebar:
        st.header("Run Options")
        company_name = st.text_input("Company Name", value="TechCorp Inc")
        max_candidates = st.slider("Max Candidates", min_value=1, max_value=100, value=25, step=1)
        uploaded_zip = st.file_uploader("Resume Archive (.zip)", type="zip")
        fallback_path = os.getenv("RESUME_ARCHIVE_PATH", "download.zip")
        run_button = st.button("Run Scoring")

    if not run_button:
        st.info("Enter a job description and provide a resume archive to get started.")
        return

    try:
        with st.spinner("Loading job description..."):
            job_description_text = _load_job_description(job_url, job_text)

        with st.spinner("Preparing candidate loader..."):
            candidate_fetcher = _build_candidate_fetcher(uploaded_zip, fallback_path)

        openai_key = os.getenv("OPENAI_API_KEY")
        system = LinkedInCandidateSystem(openai_key, candidate_fetcher)

        with st.spinner("Processing job description..."):
            session_id = system.process_job_description(job_description_text, company_name or None)

        filters = system.get_search_filters(session_id)
        _display_filters(filters)

        with st.spinner("Loading resumes and extracting candidates..."):
            candidates = system.fetch_candidates(session_id, max_candidates=max_candidates)

        st.success(f"Loaded {len(candidates)} candidate profiles from resumes.")

        with st.spinner("Scoring candidates..."):
            ranked_candidates = system.score_candidates(session_id, candidates)

        _display_candidates(ranked_candidates)

        json_export = system.export_results(ranked_candidates, "json")
        csv_export = system.export_results(ranked_candidates, "csv")

        st.download_button(
            label="Download JSON Results",
            data=json_export,
            file_name="candidate_rankings.json",
            mime="application/json",
        )

        st.download_button(
            label="Download CSV Results",
            data=csv_export,
            file_name="candidate_rankings.csv",
            mime="text/csv",
        )

        status = system.get_session_status(session_id)
        st.caption(
            f"Session {status['session_id']} completed. Candidates processed: {status['candidates_processed']}."
        )

    except Exception as exc:
        st.error(f"Failed to complete scoring: {exc}")


if __name__ == "__main__":
    main()
