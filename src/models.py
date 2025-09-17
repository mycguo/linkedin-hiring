"""
Data models for LinkedIn candidate filtering and ranking system
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class SeniorityLevel(Enum):
    INTERNSHIP = "internship"
    ENTRY_LEVEL = "entry_level"
    MID_LEVEL = "mid_level"
    SENIOR = "senior"
    LEAD = "lead"
    MANAGER = "manager"
    DIRECTOR = "director"
    EXECUTIVE = "executive"


class EducationLevel(Enum):
    HIGH_SCHOOL = "high_school"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"
    PROFESSIONAL = "professional"


class CompanySize(Enum):
    STARTUP = "1-10"
    SMALL = "11-50"
    MEDIUM = "51-200"
    LARGE = "201-1000"
    ENTERPRISE = "1001-5000"
    MEGA = "5000+"


@dataclass
class ExperienceRequirement:
    min_years: int
    max_years: Optional[int] = None
    required_domains: List[str] = field(default_factory=list)


@dataclass
class EducationRequirement:
    level: EducationLevel
    fields: List[str] = field(default_factory=list)
    required: bool = True


@dataclass
class LocationRequirement:
    cities: List[str] = field(default_factory=list)
    states: List[str] = field(default_factory=list)
    countries: List[str] = field(default_factory=list)
    remote: bool = False
    hybrid: bool = False
    on_site: bool = True
    max_distance_miles: Optional[int] = None  # Distance radius for proximity matching
    strict_location_filter: bool = False  # Hard exclude non-matching candidates
    location_weight_multiplier: float = 1.0  # Multiplier for location importance


@dataclass
class ParsedJobDescription:
    """Structured representation of a parsed job description"""
    role_title: str
    company_name: Optional[str] = None
    seniority_level: Optional[SeniorityLevel] = None
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    experience: Optional[ExperienceRequirement] = None
    education: Optional[EducationRequirement] = None
    certifications: List[str] = field(default_factory=list)
    location: Optional[LocationRequirement] = None
    industry_experience: List[str] = field(default_factory=list)
    company_size_preference: Optional[CompanySize] = None
    salary_range: Optional[Dict[str, int]] = None
    job_description_text: str = ""
    key_responsibilities: List[str] = field(default_factory=list)
    parsed_at: datetime = field(default_factory=datetime.now)


@dataclass
class LinkedInSearchFilters:
    """LinkedIn search parameters generated from job requirements"""
    keywords: str
    title_current: List[str] = field(default_factory=list)
    title_past: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    experience_years_min: Optional[int] = None
    experience_years_max: Optional[int] = None
    location_names: List[str] = field(default_factory=list)
    location_geo_urn: Optional[str] = None
    radius_miles: int = 25
    industries: List[str] = field(default_factory=list)
    current_companies: List[str] = field(default_factory=list)
    past_companies: List[str] = field(default_factory=list)
    school_names: List[str] = field(default_factory=list)
    company_sizes: List[CompanySize] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)


@dataclass
class Experience:
    title: str
    company: str
    location: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_current: bool = False
    description: str = ""
    skills_used: List[str] = field(default_factory=list)


@dataclass
class Education:
    degree: str
    field: str
    school: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    gpa: Optional[float] = None
    activities: List[str] = field(default_factory=list)


@dataclass
class CandidateProfile:
    """LinkedIn candidate profile data"""
    linkedin_id: str
    linkedin_url: str
    name: str
    headline: str
    location: str
    summary: str = ""
    current_position: Optional[str] = None
    current_company: Optional[str] = None
    experiences: List[Experience] = field(default_factory=list)
    education: List[Education] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    publications: List[str] = field(default_factory=list)
    projects: List[Dict[str, Any]] = field(default_factory=list)
    recommendations_count: int = 0
    connections_count: Optional[int] = None
    profile_picture_url: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)


@dataclass
class ScoreComponent:
    """Individual scoring component result"""
    name: str
    weight: float
    raw_score: float  # 0-100
    weighted_score: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateScore:
    """Complete scoring result for a candidate"""
    candidate_id: str
    job_description_id: str
    overall_score: float  # 0-100
    components: List[ScoreComponent] = field(default_factory=list)
    match_explanation: str = ""
    missing_requirements: List[str] = field(default_factory=list)
    additional_strengths: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    confidence_level: float = 1.0  # 0-1
    scored_at: datetime = field(default_factory=datetime.now)


@dataclass
class RankedCandidate:
    """Candidate with ranking information"""
    profile: CandidateProfile
    score: CandidateScore
    rank: int
    percentile: float  # 0-100


@dataclass
class SearchSession:
    """Search session tracking"""
    session_id: str
    job_description_id: str
    parsed_job: ParsedJobDescription
    search_filters: LinkedInSearchFilters
    total_candidates_found: int = 0
    candidates_processed: int = 0
    candidates_scored: int = 0
    status: str = "initialized"
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)