"""
Job Description Parser Module
Extracts structured information from unstructured job descriptions
"""
import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import asdict

try:
    import openai
except ImportError:  # pragma: no cover - optional dependency
    openai = None
from models import (
    ParsedJobDescription,
    SeniorityLevel,
    ExperienceRequirement,
    EducationRequirement,
    EducationLevel,
    LocationRequirement,
    CompanySize
)


class JobDescriptionParser:
    """
    Parses job descriptions using NLP and pattern matching
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key
        self._ai_available = bool(openai_api_key and openai)

        if openai_api_key and not openai:
            raise ImportError(
                "OpenAI support requested but the 'openai' package is not installed. "
                "Install the optional dependency or omit the API key to use regex parsing."
            )

        if self._ai_available:
            openai.api_key = openai_api_key

        # Compile regex patterns
        self._compile_patterns()

        # Initialize skill keywords
        self._initialize_skill_keywords()

    def _compile_patterns(self):
        """Compile regex patterns for extraction"""
        self.patterns = {
            'years_experience': re.compile(
                r'(\d+)[\+\-]?\s*(?:to|\-)?\s*(\d+)?\s*years?\s*(?:of\s*)?experience',
                re.IGNORECASE
            ),
            'education': re.compile(
                r'(?:bachelor|master|phd|doctorate|associate|diploma|degree)',
                re.IGNORECASE
            ),
            'salary': re.compile(
                r'\$?\s*(\d+)k?\s*(?:to|\-)?\s*\$?\s*(\d+)k?',
                re.IGNORECASE
            ),
            'remote': re.compile(
                r'\b(?:remote|work from home|wfh|distributed|telecommute)\b',
                re.IGNORECASE
            ),
            'hybrid': re.compile(
                r'\b(?:hybrid|flexible work|partial remote)\b',
                re.IGNORECASE
            ),
            'email': re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ),
            'url': re.compile(
                r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            )
        }

    def _initialize_skill_keywords(self):
        """Initialize common skill keywords for extraction"""
        self.skill_keywords = {
            'programming_languages': [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby',
                'go', 'rust', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl',
                'php', 'objective-c', 'dart', 'lua', 'haskell', 'clojure'
            ],
            'web_frameworks': [
                'react', 'angular', 'vue', 'django', 'flask', 'fastapi', 'express',
                'spring', 'rails', 'laravel', 'asp.net', 'node.js', 'next.js',
                'nuxt.js', 'svelte', 'ember', 'backbone'
            ],
            'databases': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
                'cassandra', 'oracle', 'sql server', 'dynamodb', 'neo4j',
                'influxdb', 'mariadb', 'sqlite', 'couchdb'
            ],
            'cloud_platforms': [
                'aws', 'azure', 'gcp', 'google cloud', 'heroku', 'digitalocean',
                'alibaba cloud', 'ibm cloud', 'oracle cloud'
            ],
            'devops_tools': [
                'docker', 'kubernetes', 'jenkins', 'gitlab', 'github actions',
                'circleci', 'travis ci', 'ansible', 'terraform', 'puppet',
                'chef', 'vagrant', 'prometheus', 'grafana', 'elk stack'
            ],
            'data_science': [
                'machine learning', 'deep learning', 'tensorflow', 'pytorch',
                'scikit-learn', 'pandas', 'numpy', 'keras', 'nlp', 'computer vision',
                'data analysis', 'statistics', 'data visualization', 'tableau',
                'power bi', 'looker', 'datadog'
            ]
        }

    def parse(self, job_description: str) -> ParsedJobDescription:
        """
        Main parsing method - combines AI and pattern matching

        Args:
            job_description: Raw job description text

        Returns:
            ParsedJobDescription object with extracted information
        """
        # Try AI parsing first if API key available
        if self._ai_available:
            try:
                return self._parse_with_ai(job_description)
            except Exception as e:
                print(f"AI parsing failed, falling back to pattern matching: {e}")

        # Fallback to pattern matching
        return self._parse_with_patterns(job_description)

    def _parse_with_ai(self, job_description: str) -> ParsedJobDescription:
        """Use OpenAI GPT to parse job description"""

        if not openai:
            raise RuntimeError("OpenAI client not available; cannot perform AI parsing.")

        prompt = f"""
        Extract structured information from this job description.
        Return a JSON object with these fields:
        - role_title: string
        - seniority_level: one of [internship, entry_level, mid_level, senior, lead, manager, director, executive]
        - required_skills: array of technical skills that are mandatory
        - preferred_skills: array of nice-to-have skills
        - min_years_experience: number or null
        - max_years_experience: number or null
        - education_level: one of [high_school, associate, bachelor, master, phd, professional] or null
        - education_fields: array of study fields
        - location_cities: array of city names
        - location_states: array of state names (if applicable)
        - remote_allowed: boolean
        - hybrid_allowed: boolean
        - max_distance_miles: number for radius-based matching (if mentioned)
        - location_critical: boolean (true if location is emphasized as critical)
        - industry_experience: array of industries
        - key_responsibilities: array of main job duties (max 5)

        Job Description:
        {job_description}

        Return only valid JSON, no additional text.
        """

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a job description parser. Extract structured data from job postings."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )

        # Parse AI response
        ai_result = json.loads(response.choices[0].message.content)

        # Convert to ParsedJobDescription
        return self._ai_result_to_parsed_job(ai_result, job_description)

    def _ai_result_to_parsed_job(self, ai_result: Dict, original_text: str) -> ParsedJobDescription:
        """Convert AI parsing result to ParsedJobDescription"""

        # Parse seniority level
        seniority = None
        if ai_result.get('seniority_level'):
            try:
                seniority = SeniorityLevel(ai_result['seniority_level'])
            except ValueError:
                pass

        # Parse experience requirement
        experience = None
        if ai_result.get('min_years_experience') is not None:
            experience = ExperienceRequirement(
                min_years=ai_result['min_years_experience'],
                max_years=ai_result.get('max_years_experience')
            )

        # Parse education requirement
        education = None
        if ai_result.get('education_level'):
            try:
                education = EducationRequirement(
                    level=EducationLevel(ai_result['education_level']),
                    fields=ai_result.get('education_fields', [])
                )
            except ValueError:
                pass

        # Parse location with enhanced features
        location = LocationRequirement(
            cities=ai_result.get('location_cities', []),
            states=ai_result.get('location_states', []),
            remote=ai_result.get('remote_allowed', False),
            hybrid=ai_result.get('hybrid_allowed', False),
            max_distance_miles=ai_result.get('max_distance_miles'),
            strict_location_filter=ai_result.get('location_critical', False),
            location_weight_multiplier=2.0 if ai_result.get('location_critical', False) else 1.0
        )

        return ParsedJobDescription(
            role_title=ai_result.get('role_title', 'Unknown Role'),
            seniority_level=seniority,
            required_skills=ai_result.get('required_skills', []),
            preferred_skills=ai_result.get('preferred_skills', []),
            experience=experience,
            education=education,
            location=location,
            industry_experience=ai_result.get('industry_experience', []),
            key_responsibilities=ai_result.get('key_responsibilities', []),
            job_description_text=original_text
        )

    def _parse_with_patterns(self, job_description: str) -> ParsedJobDescription:
        """Fallback pattern-based parsing"""

        # Extract basic information
        title = self._extract_title(job_description)
        seniority = self._extract_seniority(job_description)
        skills = self._extract_skills(job_description)
        experience = self._extract_experience(job_description)
        education = self._extract_education(job_description)
        location = self._extract_location(job_description)

        return ParsedJobDescription(
            role_title=title,
            seniority_level=seniority,
            required_skills=skills['required'],
            preferred_skills=skills['preferred'],
            experience=experience,
            education=education,
            location=location,
            job_description_text=job_description
        )

    def _extract_title(self, text: str) -> str:
        """Extract job title from text"""
        # Common title patterns
        title_keywords = [
            'engineer', 'developer', 'architect', 'analyst', 'manager',
            'designer', 'scientist', 'consultant', 'specialist', 'coordinator',
            'lead', 'director', 'vp', 'president', 'intern'
        ]

        # Look for title in first few lines
        lines = text.split('\n')[:5]
        for line in lines:
            line_lower = line.lower()
            for keyword in title_keywords:
                if keyword in line_lower and len(line) < 100:
                    return line.strip()

        return "Software Engineer"  # Default fallback

    def _extract_seniority(self, text: str) -> Optional[SeniorityLevel]:
        """Extract seniority level from text"""
        text_lower = text.lower()

        seniority_keywords = {
            SeniorityLevel.INTERNSHIP: ['intern', 'internship', 'co-op'],
            SeniorityLevel.ENTRY_LEVEL: ['entry level', 'junior', 'graduate', 'new grad'],
            SeniorityLevel.MID_LEVEL: ['mid-level', 'mid level', 'intermediate'],
            SeniorityLevel.SENIOR: ['senior', 'sr.', 'experienced'],
            SeniorityLevel.LEAD: ['lead', 'principal', 'staff'],
            SeniorityLevel.MANAGER: ['manager', 'management'],
            SeniorityLevel.DIRECTOR: ['director', 'head of'],
            SeniorityLevel.EXECUTIVE: ['vp', 'vice president', 'cto', 'ceo', 'executive']
        }

        for level, keywords in seniority_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return level

        return None

    def _extract_skills(self, text: str) -> Dict[str, List[str]]:
        """Extract required and preferred skills"""
        text_lower = text.lower()
        required_skills = []
        preferred_skills = []

        # Find all mentioned skills
        all_skills = []
        for category, skills in self.skill_keywords.items():
            for skill in skills:
                if skill in text_lower:
                    all_skills.append(skill)

        # Determine if required or preferred based on context
        required_section = False
        preferred_section = False

        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower()

            if any(word in line_lower for word in ['required', 'must have', 'mandatory', 'essential']):
                required_section = True
                preferred_section = False
            elif any(word in line_lower for word in ['preferred', 'nice to have', 'bonus', 'desired']):
                preferred_section = True
                required_section = False

            # Check for skills in current line
            for skill in all_skills:
                if skill in line_lower:
                    if preferred_section:
                        preferred_skills.append(skill)
                    else:
                        required_skills.append(skill)

        # Remove duplicates while preserving order
        required_skills = list(dict.fromkeys(required_skills))
        preferred_skills = list(dict.fromkeys(preferred_skills))

        return {
            'required': required_skills,
            'preferred': preferred_skills
        }

    def _extract_experience(self, text: str) -> Optional[ExperienceRequirement]:
        """Extract years of experience requirement"""
        matches = self.patterns['years_experience'].findall(text)

        if matches:
            match = matches[0]
            min_years = int(match[0])
            max_years = int(match[1]) if match[1] else None

            return ExperienceRequirement(
                min_years=min_years,
                max_years=max_years
            )

        return None

    def _extract_education(self, text: str) -> Optional[EducationRequirement]:
        """Extract education requirements"""
        text_lower = text.lower()

        education_mapping = {
            'bachelor': EducationLevel.BACHELOR,
            'master': EducationLevel.MASTER,
            'phd': EducationLevel.PHD,
            'doctorate': EducationLevel.PHD,
            'associate': EducationLevel.ASSOCIATE
        }

        for keyword, level in education_mapping.items():
            if keyword in text_lower:
                # Extract field of study if mentioned nearby
                fields = self._extract_education_fields(text_lower, keyword)
                return EducationRequirement(
                    level=level,
                    fields=fields
                )

        return None

    def _extract_education_fields(self, text: str, education_keyword: str) -> List[str]:
        """Extract fields of study mentioned near education requirement"""
        fields = []
        common_fields = [
            'computer science', 'software engineering', 'information technology',
            'mathematics', 'physics', 'engineering', 'data science', 'statistics',
            'business', 'economics', 'finance'
        ]

        # Look for fields mentioned within 50 characters of education keyword
        keyword_pos = text.find(education_keyword)
        if keyword_pos != -1:
            context = text[max(0, keyword_pos-100):keyword_pos+100]
            for field in common_fields:
                if field in context:
                    fields.append(field)

        return fields

    def _extract_location(self, text: str) -> LocationRequirement:
        """Extract enhanced location requirements"""
        location = LocationRequirement()

        # Check for remote/hybrid
        if self.patterns['remote'].search(text):
            location.remote = True
        if self.patterns['hybrid'].search(text):
            location.hybrid = True

        # Check for location criticality indicators
        location_critical_phrases = [
            'must be located', 'required to be based', 'location is critical',
            'must be local', 'local candidates only', 'no remote', 'on-site required',
            'must commute', 'in-person required'
        ]

        text_lower = text.lower()
        location_critical = any(phrase in text_lower for phrase in location_critical_phrases)

        location.strict_location_filter = location_critical
        location.location_weight_multiplier = 2.0 if location_critical else 1.0

        # Extract distance/radius requirements
        distance_pattern = re.compile(r'within\s+(\d+)\s*(?:miles?|mi|km)', re.IGNORECASE)
        distance_match = distance_pattern.search(text)
        if distance_match:
            miles = int(distance_match.group(1))
            # Convert km to miles if needed
            if 'km' in distance_match.group(0).lower():
                miles = int(miles * 0.621371)
            location.max_distance_miles = miles

        # Expanded city database for pattern matching
        major_cities = [
            'San Francisco', 'New York', 'Los Angeles', 'Chicago', 'Boston',
            'Seattle', 'Austin', 'Denver', 'Portland', 'San Jose', 'Atlanta',
            'Washington DC', 'Dallas', 'Houston', 'Miami', 'Philadelphia',
            'Phoenix', 'San Diego', 'Nashville', 'Charlotte', 'Detroit',
            'Minneapolis', 'Tampa', 'Orlando', 'Pittsburgh', 'Cleveland',
            'Sacramento', 'Las Vegas', 'Kansas City', 'Indianapolis',
            'Toronto', 'Vancouver', 'Montreal', 'London', 'Berlin',
            'Paris', 'Amsterdam', 'Dublin', 'Sydney', 'Melbourne'
        ]

        for city in major_cities:
            if city.lower() in text.lower():
                location.cities.append(city)

        # Extract US states
        us_states = [
            'California', 'New York', 'Texas', 'Florida', 'Illinois', 'Pennsylvania',
            'Ohio', 'Georgia', 'North Carolina', 'Michigan', 'New Jersey', 'Virginia',
            'Washington', 'Arizona', 'Massachusetts', 'Tennessee', 'Indiana', 'Missouri',
            'Maryland', 'Wisconsin', 'Colorado', 'Minnesota', 'South Carolina', 'Alabama',
            'Louisiana', 'Kentucky', 'Oregon', 'Oklahoma', 'Connecticut', 'Utah',
            'Iowa', 'Nevada', 'Arkansas', 'Mississippi', 'Kansas', 'New Mexico',
            'Nebraska', 'West Virginia', 'Idaho', 'Hawaii', 'New Hampshire', 'Maine',
            'Rhode Island', 'Montana', 'Delaware', 'South Dakota', 'North Dakota',
            'Alaska', 'Vermont', 'Wyoming'
        ]

        for state in us_states:
            if state.lower() in text.lower():
                location.states.append(state)

        # Check for country mentions
        countries = ['United States', 'USA', 'Canada', 'United Kingdom', 'UK', 'Germany', 'France']
        for country in countries:
            if country.lower() in text.lower():
                location.countries.append(country)

        return location


# Example usage
if __name__ == "__main__":
    parser = JobDescriptionParser()

    sample_job = """
    Senior Software Engineer - Full Stack

    We are looking for an experienced Senior Software Engineer to join our team.

    Requirements:
    - 5+ years of experience in software development
    - Strong proficiency in Python, JavaScript, and React
    - Experience with AWS and Docker
    - Bachelor's degree in Computer Science or related field
    - Experience with PostgreSQL and MongoDB

    Nice to have:
    - Experience with machine learning
    - Knowledge of Kubernetes
    - Master's degree preferred

    Location: San Francisco, CA (Remote work available)
    Salary: $150k - $200k
    """

    result = parser.parse(sample_job)
    print(json.dumps(asdict(result), default=str, indent=2))
