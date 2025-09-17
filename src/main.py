"""
Main orchestrator for LinkedIn candidate filtering and ranking system
"""
import uuid
from typing import List, Dict, Optional
from datetime import datetime
import json
from dataclasses import asdict

from models import (
    ParsedJobDescription,
    CandidateProfile,
    SearchSession,
    RankedCandidate,
    Experience,
    Education
)
from job_parser import JobDescriptionParser
from filter_generator import LinkedInFilterGenerator
from scoring_engine import ScoringEngine


class LinkedInCandidateSystem:
    """
    Main system orchestrator for LinkedIn candidate processing
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize the system with all components

        Args:
            openai_api_key: Optional OpenAI API key for enhanced job parsing
        """
        self.job_parser = JobDescriptionParser(openai_api_key)
        self.filter_generator = LinkedInFilterGenerator()
        self.scoring_engine = ScoringEngine()

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
            session.total_candidates_found = len(candidates)

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


def create_sample_candidates() -> List[CandidateProfile]:
    """Create sample candidate data for testing"""
    candidates = []

    # Candidate 1: Strong match
    candidate1 = CandidateProfile(
        linkedin_id="sample1",
        linkedin_url="https://linkedin.com/in/sample1",
        name="John Doe",
        headline="Senior Software Engineer at Tech Corp",
        location="San Francisco, CA",
        summary="Experienced full-stack developer with 6 years building scalable web applications",
        current_position="Senior Software Engineer",
        current_company="Tech Corp",
        experiences=[
            Experience(
                title="Senior Software Engineer",
                company="Tech Corp",
                location="San Francisco, CA",
                start_date=datetime(2021, 1, 1),
                is_current=True,
                description="Led development of microservices using Python, React, and AWS. Mentored junior developers.",
                skills_used=["Python", "React", "AWS", "Docker", "PostgreSQL"]
            ),
            Experience(
                title="Software Engineer",
                company="Startup Inc",
                location="San Francisco, CA",
                start_date=datetime(2019, 6, 1),
                end_date=datetime(2020, 12, 31),
                description="Built REST APIs with Django and React frontend. Implemented CI/CD pipelines.",
                skills_used=["Python", "Django", "React", "JavaScript", "MySQL"]
            )
        ],
        education=[
            Education(
                degree="Bachelor of Science",
                field="Computer Science",
                school="UC Berkeley",
                start_date=datetime(2015, 9, 1),
                end_date=datetime(2019, 5, 1)
            )
        ],
        skills=["Python", "JavaScript", "React", "Django", "AWS", "Docker", "PostgreSQL", "Git", "Agile"],
        certifications=["AWS Certified Solutions Architect"]
    )

    # Candidate 2: Medium match
    candidate2 = CandidateProfile(
        linkedin_id="sample2",
        linkedin_url="https://linkedin.com/in/sample2",
        name="Jane Smith",
        headline="Full Stack Developer at Digital Agency",
        location="New York, NY",
        summary="Passionate developer with 4 years experience in web development",
        current_position="Full Stack Developer",
        current_company="Digital Agency",
        experiences=[
            Experience(
                title="Full Stack Developer",
                company="Digital Agency",
                location="New York, NY",
                start_date=datetime(2020, 3, 1),
                is_current=True,
                description="Developed e-commerce platforms using Node.js and React. Worked with MongoDB.",
                skills_used=["JavaScript", "Node.js", "React", "MongoDB", "Express"]
            ),
            Experience(
                title="Junior Developer",
                company="Small Business",
                location="New York, NY",
                start_date=datetime(2019, 1, 1),
                end_date=datetime(2020, 2, 28),
                description="Built websites with HTML, CSS, JavaScript and PHP.",
                skills_used=["HTML", "CSS", "JavaScript", "PHP", "MySQL"]
            )
        ],
        education=[
            Education(
                degree="Bachelor of Arts",
                field="Information Systems",
                school="NYU",
                start_date=datetime(2015, 9, 1),
                end_date=datetime(2018, 12, 1)
            )
        ],
        skills=["JavaScript", "React", "Node.js", "MongoDB", "Express", "HTML", "CSS", "Git"],
        certifications=[]
    )

    # Candidate 3: Lower match
    candidate3 = CandidateProfile(
        linkedin_id="sample3",
        linkedin_url="https://linkedin.com/in/sample3",
        name="Bob Johnson",
        headline="Data Analyst at Finance Corp",
        location="Chicago, IL",
        summary="Data analyst with some programming experience looking to transition to software development",
        current_position="Data Analyst",
        current_company="Finance Corp",
        experiences=[
            Experience(
                title="Data Analyst",
                company="Finance Corp",
                location="Chicago, IL",
                start_date=datetime(2021, 6, 1),
                is_current=True,
                description="Analyzed financial data using Python and SQL. Built dashboards with Tableau.",
                skills_used=["Python", "SQL", "Tableau", "Excel", "Statistics"]
            ),
            Experience(
                title="Junior Data Analyst",
                company="Consulting Firm",
                location="Chicago, IL",
                start_date=datetime(2020, 8, 1),
                end_date=datetime(2021, 5, 31),
                description="Performed data analysis and reporting using Excel and SQL.",
                skills_used=["Excel", "SQL", "PowerBI"]
            )
        ],
        education=[
            Education(
                degree="Master of Science",
                field="Statistics",
                school="University of Chicago",
                start_date=datetime(2018, 9, 1),
                end_date=datetime(2020, 6, 1)
            )
        ],
        skills=["Python", "SQL", "Tableau", "Excel", "Statistics", "Data Analysis"],
        certifications=["Google Data Analytics Certificate"]
    )

    return [candidate1, candidate2, candidate3]


def main():
    """Main demonstration function"""
    print("=== LinkedIn Candidate Filtering & Ranking System ===\n")

    # Initialize system
    system = LinkedInCandidateSystem()

    # Sample job description
    job_description = """
    Senior Software Engineer - Full Stack

    We are looking for an experienced Senior Software Engineer to join our team and help build
    the next generation of our web platform.

    Requirements:
    - 5+ years of experience in software development
    - Strong proficiency in Python and JavaScript
    - Experience with React and modern web frameworks
    - Experience with cloud platforms (AWS preferred)
    - Bachelor's degree in Computer Science or related field
    - Experience with PostgreSQL or similar databases
    - Knowledge of Docker and containerization

    Preferred:
    - Experience with machine learning
    - Knowledge of microservices architecture
    - AWS certifications

    Location: San Francisco, CA (Remote work available)
    Salary: $150k - $200k
    """

    try:
        # Process job description
        print("1. Processing job description...")
        session_id = system.process_job_description(job_description, "TechCorp Inc")

        # Get search filters
        print("\n2. Generated LinkedIn search filters:")
        filters = system.get_search_filters(session_id)
        print(f"   Keywords: {filters['keywords']}")
        print(f"   Skills: {filters['skills'][:5]}...")
        print(f"   Titles: {filters['title_current'][:3]}...")

        # Create sample candidates
        print("\n3. Processing candidate profiles...")
        candidates = create_sample_candidates()

        # Score and rank candidates
        print("\n4. Scoring and ranking candidates...")
        ranked_candidates = system.score_candidates(session_id, candidates)

        # Display results
        print(f"\n5. Results ({len(ranked_candidates)} candidates):")
        print("=" * 80)

        for candidate in ranked_candidates:
            print(f"\nRank #{candidate.rank} - {candidate.profile.name}")
            print(f"Score: {candidate.score.overall_score:.1f}/100 (Top {100-candidate.percentile:.0f}%)")
            print(f"Position: {candidate.profile.current_position} at {candidate.profile.current_company}")
            print(f"Location: {candidate.profile.location}")
            print(f"Match: {candidate.score.match_explanation}")

            if candidate.score.missing_requirements:
                print(f"Missing: {'; '.join(candidate.score.missing_requirements[:2])}")

            if candidate.score.additional_strengths:
                print(f"Strengths: {'; '.join(candidate.score.additional_strengths)}")

            print(f"Recommendation: {candidate.score.recommendations[0]}")

        # Export results
        print("\n6. Exporting results...")
        json_export = system.export_results(ranked_candidates, "json")
        with open("candidate_rankings.json", "w") as f:
            f.write(json_export)

        csv_export = system.export_results(ranked_candidates, "csv")
        with open("candidate_rankings.csv", "w") as f:
            f.write(csv_export)

        print("✓ Results exported to candidate_rankings.json and candidate_rankings.csv")

        # Session status
        print("\n7. Session status:")
        status = system.get_session_status(session_id)
        print(f"   Status: {status['status']}")
        print(f"   Candidates processed: {status['candidates_processed']}")
        print(f"   Duration: {(datetime.fromisoformat(status['completed_at']) - datetime.fromisoformat(status['created_at'])).total_seconds():.1f}s")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1

    print("\n✓ Demo completed successfully!")
    return 0


if __name__ == "__main__":
    exit(main())