"""
Demo showcasing enhanced location filtering capabilities
"""
from main import LinkedInCandidateSystem
from models import (
    CandidateProfile,
    Experience,
    Education,
    LocationRequirement
)
from scoring_engine import ScoringEngine
from datetime import datetime


def create_location_critical_job():
    """Create a job with strict location requirements"""
    return """
    Senior Software Engineer - On-Site Required

    We are looking for a Senior Software Engineer for our San Francisco headquarters.

    LOCATION REQUIREMENTS:
    - MUST be located in San Francisco Bay Area
    - Local candidates only - no remote work
    - Must be able to commute to downtown SF office daily
    - On-site collaboration is critical for this role

    Requirements:
    - 5+ years of experience in software development
    - Strong proficiency in Python and JavaScript
    - Experience with React and Django
    - Bachelor's degree in Computer Science

    This is an on-site position with no remote work options.
    Location: San Francisco, CA (ON-SITE REQUIRED)
    """


def create_hybrid_job():
    """Create a job with flexible location requirements"""
    return """
    Senior Software Engineer - Hybrid

    Join our growing team for this hybrid position.

    Requirements:
    - 5+ years of software development experience
    - Python, JavaScript, React experience
    - Bachelor's degree preferred

    Location: Within 25 miles of Austin, TX (Hybrid work available)
    We offer flexible work arrangements with 2-3 days in office.
    """


def create_remote_job():
    """Create a fully remote job"""
    return """
    Senior Software Engineer - Remote

    Fully remote position open to candidates anywhere in the US.

    Requirements:
    - 5+ years of software development experience
    - Python, JavaScript, React
    - Strong communication skills for remote work

    Location: Remote (US timezones preferred)
    """


def create_test_candidates():
    """Create candidates with various locations"""
    candidates = []

    # Candidate 1: Perfect SF match
    candidates.append(CandidateProfile(
        linkedin_id="sf_local",
        linkedin_url="https://linkedin.com/in/sf-local",
        name="Alice Chen",
        headline="Senior Software Engineer at SF Tech",
        location="San Francisco, CA",
        summary="Experienced software engineer based in downtown SF",
        current_position="Senior Software Engineer",
        current_company="SF Tech",
        experiences=[
            Experience(
                title="Senior Software Engineer",
                company="SF Tech",
                location="San Francisco, CA",
                start_date=datetime(2020, 1, 1),
                is_current=True,
                description="Building scalable web applications with Python and React"
            )
        ],
        education=[
            Education(
                degree="Bachelor of Science",
                field="Computer Science",
                school="UC Berkeley"
            )
        ],
        skills=["Python", "JavaScript", "React", "Django", "PostgreSQL"]
    ))

    # Candidate 2: Bay Area (San Jose)
    candidates.append(CandidateProfile(
        linkedin_id="san_jose",
        linkedin_url="https://linkedin.com/in/san-jose",
        name="Bob Martinez",
        headline="Full Stack Developer in Silicon Valley",
        location="San Jose, CA",
        summary="Software engineer in the heart of Silicon Valley",
        current_position="Full Stack Developer",
        current_company="Silicon Valley Startup",
        experiences=[
            Experience(
                title="Full Stack Developer",
                company="Silicon Valley Startup",
                location="San Jose, CA",
                start_date=datetime(2019, 6, 1),
                is_current=True,
                description="Full stack development with Python and React"
            )
        ],
        education=[
            Education(
                degree="Bachelor of Science",
                field="Computer Science",
                school="Stanford University"
            )
        ],
        skills=["Python", "JavaScript", "React", "Django", "MongoDB"]
    ))

    # Candidate 3: Within radius of Austin
    candidates.append(CandidateProfile(
        linkedin_id="austin_nearby",
        linkedin_url="https://linkedin.com/in/austin-nearby",
        name="Carol Johnson",
        headline="Software Engineer in Round Rock",
        location="Round Rock, TX",  # ~20 miles from Austin
        summary="Software engineer in the Austin metro area",
        current_position="Software Engineer",
        current_company="Texas Tech Corp",
        experiences=[
            Experience(
                title="Software Engineer",
                company="Texas Tech Corp",
                location="Round Rock, TX",
                start_date=datetime(2020, 3, 1),
                is_current=True,
                description="Backend development with Python and databases"
            )
        ],
        education=[
            Education(
                degree="Bachelor of Science",
                field="Computer Science",
                school="UT Austin"
            )
        ],
        skills=["Python", "JavaScript", "React", "Flask", "MySQL"]
    ))

    # Candidate 4: Remote worker
    candidates.append(CandidateProfile(
        linkedin_id="remote_worker",
        linkedin_url="https://linkedin.com/in/remote-worker",
        name="David Kim",
        headline="Remote Software Engineer",
        location="Remote",
        summary="Experienced remote software engineer",
        current_position="Remote Software Engineer",
        current_company="Distributed Team Inc",
        experiences=[
            Experience(
                title="Remote Software Engineer",
                company="Distributed Team Inc",
                location="Remote",
                start_date=datetime(2019, 1, 1),
                is_current=True,
                description="Remote full-stack development with modern technologies"
            )
        ],
        education=[
            Education(
                degree="Bachelor of Science",
                field="Computer Science",
                school="University of Washington"
            )
        ],
        skills=["Python", "JavaScript", "React", "Django", "AWS"]
    ))

    # Candidate 5: Wrong location
    candidates.append(CandidateProfile(
        linkedin_id="wrong_location",
        linkedin_url="https://linkedin.com/in/wrong-location",
        name="Eva Rodriguez",
        headline="Software Engineer in Miami",
        location="Miami, FL",
        summary="Software engineer based in Miami",
        current_position="Software Engineer",
        current_company="Miami Tech",
        experiences=[
            Experience(
                title="Software Engineer",
                company="Miami Tech",
                location="Miami, FL",
                start_date=datetime(2020, 1, 1),
                is_current=True,
                description="Web development with modern frameworks"
            )
        ],
        education=[
            Education(
                degree="Bachelor of Science",
                field="Computer Science",
                school="University of Miami"
            )
        ],
        skills=["Python", "JavaScript", "React", "Django", "PostgreSQL"]
    ))

    return candidates


def demonstrate_location_scenarios():
    """Demonstrate various location filtering scenarios"""
    print("=== Enhanced Location Filtering Demo ===\n")

    # Initialize system
    system = LinkedInCandidateSystem()
    candidates = create_test_candidates()

    scenarios = [
        ("Location-Critical Job (San Francisco ON-SITE)", create_location_critical_job()),
        ("Hybrid Job (Austin +25 miles)", create_hybrid_job()),
        ("Remote Job (US-wide)", create_remote_job())
    ]

    for scenario_name, job_text in scenarios:
        print(f"🏢 {scenario_name}")
        print("=" * 60)

        # Process job
        session_id = system.process_job_description(job_text)
        session = system.sessions[session_id]

        # Show location requirements
        location_req = session.parsed_job.location
        if location_req:
            print(f"📍 Location Requirements:")
            if location_req.cities:
                print(f"   Cities: {', '.join(location_req.cities)}")
            if location_req.states:
                print(f"   States: {', '.join(location_req.states)}")
            print(f"   Remote: {location_req.remote}")
            print(f"   Hybrid: {location_req.hybrid}")
            if location_req.max_distance_miles:
                print(f"   Max Distance: {location_req.max_distance_miles} miles")
            print(f"   Strict Filtering: {location_req.strict_location_filter}")
            print(f"   Location Weight Multiplier: {location_req.location_weight_multiplier}x")
        else:
            print("   No specific location requirements")

        print()

        # Score candidates
        ranked_candidates = system.score_candidates(session_id, candidates)

        print(f"📊 Candidate Rankings:")
        for i, ranked_candidate in enumerate(ranked_candidates, 1):
            candidate = ranked_candidate.profile
            score = ranked_candidate.score

            # Find location component
            location_component = next(
                (c for c in score.components if c.name == 'location_match'), None
            )

            print(f"{i}. {candidate.name}")
            print(f"   Location: {candidate.location}")
            print(f"   Overall Score: {score.overall_score:.1f}/100")

            if location_component:
                details = location_component.details
                print(f"   Location Score: {location_component.raw_score:.1f}/100")
                if 'match_type' in details:
                    print(f"   Match Type: {details['match_type']}")
                if 'distance_miles' in details and details['distance_miles']:
                    print(f"   Distance: {details['distance_miles']:.1f} miles")
                if 'match_details' in details:
                    print(f"   Details: {details['match_details']}")

            print()

        print("-" * 60)
        print()


def demonstrate_custom_weights():
    """Demonstrate custom location weights for location-critical roles"""
    print("🎯 Custom Location Weights Demo")
    print("=" * 50)

    # Create location-critical weights
    location_critical_weights = {
        'skill_match': 0.25,           # Reduced from 30%
        'experience_match': 0.20,
        'education_match': 0.10,       # Reduced from 15%
        'industry_match': 0.10,        # Reduced from 15%
        'location_match': 0.30,        # Increased from 10% to 30%
        'career_trajectory': 0.03,
        'keyword_density': 0.02
    }

    # Initialize systems with different weights
    standard_system = LinkedInCandidateSystem()
    location_critical_system = LinkedInCandidateSystem()
    location_critical_system.scoring_engine = ScoringEngine(weights=location_critical_weights)

    # Use location-critical job
    job_text = create_location_critical_job()
    candidates = create_test_candidates()

    print("Comparing standard vs location-critical scoring weights:\n")

    for system_name, system in [("Standard Weights", standard_system),
                                ("Location-Critical Weights", location_critical_system)]:
        print(f"📊 {system_name}:")

        session_id = system.process_job_description(job_text)
        ranked_candidates = system.score_candidates(session_id, candidates)

        for i, ranked_candidate in enumerate(ranked_candidates[:3], 1):
            candidate = ranked_candidate.profile
            score = ranked_candidate.score

            location_component = next(
                (c for c in score.components if c.name == 'location_match'), None
            )

            print(f"   {i}. {candidate.name} ({candidate.location})")
            print(f"      Overall: {score.overall_score:.1f}")
            if location_component:
                print(f"      Location: {location_component.raw_score:.1f} "
                     f"(weight: {location_component.weight:.1%})")

        print()


def main():
    """Run location filtering demonstrations"""
    try:
        demonstrate_location_scenarios()
        demonstrate_custom_weights()

        print("✅ Location filtering demo completed successfully!")

    except Exception as e:
        print(f"❌ Error in demo: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())