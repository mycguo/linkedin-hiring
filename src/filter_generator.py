"""
LinkedIn Filter Generator Module
Converts parsed job requirements into LinkedIn search filters
"""
from typing import List, Dict, Optional
import re
from models import (
    ParsedJobDescription,
    LinkedInSearchFilters,
    SeniorityLevel,
    CompanySize
)


class LinkedInFilterGenerator:
    """
    Generates optimized LinkedIn search filters from job requirements
    """

    def __init__(self):
        # Initialize mappings
        self._init_skill_synonyms()
        self._init_title_variations()
        self._init_industry_mappings()

    def _init_skill_synonyms(self):
        """Initialize skill synonym mappings for better search coverage"""
        self.skill_synonyms = {
            'javascript': ['js', 'javascript', 'ecmascript'],
            'typescript': ['ts', 'typescript'],
            'python': ['python', 'py'],
            'react': ['react', 'reactjs', 'react.js'],
            'angular': ['angular', 'angularjs', 'angular.js'],
            'node.js': ['node', 'nodejs', 'node.js'],
            'machine learning': ['ml', 'machine learning', 'deep learning'],
            'artificial intelligence': ['ai', 'artificial intelligence'],
            'devops': ['devops', 'dev ops', 'development operations'],
            'ci/cd': ['ci/cd', 'cicd', 'continuous integration', 'continuous deployment'],
            'kubernetes': ['k8s', 'kubernetes'],
            'postgresql': ['postgres', 'postgresql'],
            'mongodb': ['mongo', 'mongodb'],
            'amazon web services': ['aws', 'amazon web services'],
            'google cloud platform': ['gcp', 'google cloud', 'google cloud platform'],
            'microsoft azure': ['azure', 'microsoft azure']
        }

    def _init_title_variations(self):
        """Initialize job title variations for comprehensive search"""
        self.title_variations = {
            'software engineer': [
                'software engineer',
                'software developer',
                'programmer',
                'developer',
                'sde'
            ],
            'senior software engineer': [
                'senior software engineer',
                'senior developer',
                'sr software engineer',
                'sr. software engineer',
                'senior sde',
                'sde 2',
                'sde ii'
            ],
            'principal engineer': [
                'principal engineer',
                'principal software engineer',
                'staff engineer',
                'staff software engineer',
                'sde 3',
                'sde iii'
            ],
            'engineering manager': [
                'engineering manager',
                'software engineering manager',
                'development manager',
                'em',
                'sdm'
            ],
            'data scientist': [
                'data scientist',
                'machine learning engineer',
                'ml engineer',
                'data analyst',
                'research scientist'
            ],
            'product manager': [
                'product manager',
                'pm',
                'product owner',
                'po'
            ],
            'devops engineer': [
                'devops engineer',
                'site reliability engineer',
                'sre',
                'infrastructure engineer',
                'platform engineer'
            ]
        }

    def _init_industry_mappings(self):
        """Map common industry terms to LinkedIn industry categories"""
        self.industry_mappings = {
            'tech': ['Computer Software', 'Internet', 'Information Technology and Services'],
            'finance': ['Financial Services', 'Banking', 'Investment Banking', 'Investment Management'],
            'healthcare': ['Hospital & Health Care', 'Medical Devices', 'Pharmaceuticals', 'Biotechnology'],
            'retail': ['Retail', 'E-commerce', 'Consumer Goods'],
            'education': ['Education Management', 'E-Learning', 'Higher Education'],
            'consulting': ['Management Consulting', 'Information Technology and Services'],
            'media': ['Media Production', 'Entertainment', 'Publishing', 'Broadcast Media'],
            'automotive': ['Automotive', 'Transportation', 'Logistics and Supply Chain'],
            'energy': ['Oil & Energy', 'Renewables & Environment', 'Utilities']
        }

    def generate_filters(self, job: ParsedJobDescription) -> LinkedInSearchFilters:
        """
        Generate LinkedIn search filters from parsed job description

        Args:
            job: Parsed job description object

        Returns:
            LinkedInSearchFilters object with optimized search parameters
        """
        filters = LinkedInSearchFilters(
            keywords=self._generate_keywords(job),
            title_current=self._generate_title_filters(job),
            skills=self._expand_skills(job.required_skills[:10]),  # LinkedIn limits skills
            experience_years_min=job.experience.min_years if job.experience else None,
            experience_years_max=job.experience.max_years if job.experience else None,
            location_names=self._process_locations(job),
            industries=self._map_industries(job.industry_experience),
            company_sizes=self._map_company_sizes(job.company_size_preference)
        )

        # Add education filters if specified
        if job.education:
            filters.school_names = self._generate_school_filters(job.education)

        return filters

    def _generate_keywords(self, job: ParsedJobDescription) -> str:
        """
        Generate Boolean search query for LinkedIn

        LinkedIn Boolean search supports:
        - AND (default between terms)
        - OR
        - NOT (minus sign)
        - Quotes for exact phrases
        - Parentheses for grouping
        """
        keywords_parts = []

        # Add role title variations
        if job.role_title:
            title_variations = self._get_title_variations(job.role_title)
            if len(title_variations) > 1:
                # Use OR for title variations
                title_query = '(' + ' OR '.join(f'"{t}"' for t in title_variations[:3]) + ')'
                keywords_parts.append(title_query)
            else:
                keywords_parts.append(f'"{job.role_title}"')

        # Add top required skills
        top_skills = job.required_skills[:3]
        if top_skills:
            # Expand each skill with synonyms
            skill_queries = []
            for skill in top_skills:
                skill_variations = self._get_skill_synonyms(skill)
                if len(skill_variations) > 1:
                    skill_queries.append('(' + ' OR '.join(skill_variations[:2]) + ')')
                else:
                    skill_queries.append(skill)

            if skill_queries:
                keywords_parts.append(' AND '.join(skill_queries))

        # Add industry keywords if specified
        if job.industry_experience:
            industry_keywords = ' OR '.join(job.industry_experience[:2])
            keywords_parts.append(f'({industry_keywords})')

        # Combine all parts
        if keywords_parts:
            # LinkedIn has a character limit, so we need to be selective
            full_query = ' AND '.join(keywords_parts)
            if len(full_query) > 200:
                # Simplify if too long
                full_query = ' '.join([job.role_title] + job.required_skills[:2])

            return full_query

        return job.role_title or "software engineer"

    def _generate_title_filters(self, job: ParsedJobDescription) -> List[str]:
        """Generate current job title filters"""
        if not job.role_title:
            return []

        # Get title variations
        variations = self._get_title_variations(job.role_title.lower())

        # Add seniority-specific variations
        if job.seniority_level:
            variations = self._add_seniority_variations(variations, job.seniority_level)

        # LinkedIn typically allows up to 10 title filters
        return variations[:10]

    def _expand_skills(self, skills: List[str]) -> List[str]:
        """Expand skills list with synonyms and related skills"""
        expanded_skills = []
        seen = set()

        for skill in skills:
            skill_lower = skill.lower()

            # Add original skill
            if skill_lower not in seen:
                expanded_skills.append(skill)
                seen.add(skill_lower)

            # Add synonyms
            synonyms = self._get_skill_synonyms(skill_lower)
            for synonym in synonyms:
                if synonym not in seen and len(expanded_skills) < 20:
                    expanded_skills.append(synonym)
                    seen.add(synonym)

        return expanded_skills

    def _process_locations(self, job: ParsedJobDescription) -> List[str]:
        """Process location requirements into LinkedIn location filters"""
        locations = []

        if job.location:
            # Add specific cities
            locations.extend(job.location.cities)

            # Add states if no cities specified
            if not locations and job.location.states:
                locations.extend(job.location.states)

            # Handle remote work
            if job.location.remote:
                locations.append("Remote")

        return locations[:5]  # LinkedIn typically limits location filters

    def _map_industries(self, industries: List[str]) -> List[str]:
        """Map industry keywords to LinkedIn industry categories"""
        linkedin_industries = []

        for industry in industries:
            industry_lower = industry.lower()

            # Check if we have a mapping
            for key, mapped_industries in self.industry_mappings.items():
                if key in industry_lower:
                    linkedin_industries.extend(mapped_industries)
                    break
            else:
                # Use original if no mapping found
                linkedin_industries.append(industry)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(linkedin_industries))[:10]

    def _map_company_sizes(self, preference: Optional[CompanySize]) -> List[CompanySize]:
        """Map company size preference to LinkedIn filters"""
        if not preference:
            return []

        # Include the preferred size and adjacent sizes
        size_progression = [
            CompanySize.STARTUP,
            CompanySize.SMALL,
            CompanySize.MEDIUM,
            CompanySize.LARGE,
            CompanySize.ENTERPRISE,
            CompanySize.MEGA
        ]

        try:
            index = size_progression.index(preference)
            # Include preferred size and one size up/down
            result = []
            if index > 0:
                result.append(size_progression[index - 1])
            result.append(preference)
            if index < len(size_progression) - 1:
                result.append(size_progression[index + 1])
            return result
        except ValueError:
            return [preference]

    def _generate_school_filters(self, education) -> List[str]:
        """Generate school name filters based on education requirements"""
        # This would ideally connect to a database of schools
        # For now, return top schools for the field
        top_schools = {
            'computer science': [
                'MIT', 'Stanford', 'Carnegie Mellon', 'UC Berkeley',
                'Georgia Tech', 'UIUC', 'Cornell', 'University of Washington'
            ],
            'business': [
                'Harvard', 'Wharton', 'Stanford GSB', 'MIT Sloan',
                'Kellogg', 'Columbia', 'Chicago Booth', 'INSEAD'
            ],
            'engineering': [
                'MIT', 'Stanford', 'Caltech', 'Georgia Tech',
                'UC Berkeley', 'UIUC', 'Michigan', 'Purdue'
            ]
        }

        schools = []
        for field in education.fields:
            field_lower = field.lower()
            for key, school_list in top_schools.items():
                if key in field_lower:
                    schools.extend(school_list[:3])
                    break

        return schools[:5]

    def _get_title_variations(self, title: str) -> List[str]:
        """Get variations of a job title"""
        title_lower = title.lower()

        # Check predefined variations
        for key, variations in self.title_variations.items():
            if key in title_lower:
                return variations

        # Generate basic variations if not found
        variations = [title]

        # Add common abbreviations
        if 'senior' in title_lower:
            variations.append(title.replace('senior', 'sr'))
            variations.append(title.replace('senior', 'sr.'))

        if 'engineer' in title_lower and 'software' not in title_lower:
            variations.append(title.replace('engineer', 'software engineer'))

        return variations

    def _get_skill_synonyms(self, skill: str) -> List[str]:
        """Get synonyms for a skill"""
        skill_lower = skill.lower()

        # Check predefined synonyms
        for key, synonyms in self.skill_synonyms.items():
            if skill_lower == key or skill_lower in synonyms:
                return synonyms

        # Return original if no synonyms found
        return [skill]

    def _add_seniority_variations(self, titles: List[str], seniority: SeniorityLevel) -> List[str]:
        """Add seniority-specific title variations"""
        seniority_prefixes = {
            SeniorityLevel.ENTRY_LEVEL: ['junior', 'jr', 'entry level', 'associate'],
            SeniorityLevel.MID_LEVEL: ['', 'mid-level', 'intermediate'],
            SeniorityLevel.SENIOR: ['senior', 'sr', 'sr.', 'lead'],
            SeniorityLevel.LEAD: ['lead', 'principal', 'staff'],
            SeniorityLevel.MANAGER: ['manager', 'management', 'head of'],
            SeniorityLevel.DIRECTOR: ['director', 'head', 'vp'],
            SeniorityLevel.EXECUTIVE: ['vp', 'vice president', 'chief', 'cto', 'ceo']
        }

        enhanced_titles = list(titles)
        prefixes = seniority_prefixes.get(seniority, [])

        for title in titles[:3]:  # Limit to avoid explosion
            for prefix in prefixes[:2]:
                if prefix and prefix not in title.lower():
                    enhanced_titles.append(f"{prefix} {title}")

        return enhanced_titles

    def optimize_for_api_limits(self, filters: LinkedInSearchFilters) -> LinkedInSearchFilters:
        """
        Optimize filters to work within LinkedIn API/scraping limits

        LinkedIn typically has limits on:
        - Keywords length (< 250 chars)
        - Number of skills (< 20)
        - Number of titles (< 10)
        - Number of locations (< 5)
        """
        # Truncate keywords if too long
        if len(filters.keywords) > 250:
            # Simplify boolean query
            parts = filters.keywords.split(' AND ')
            filters.keywords = ' AND '.join(parts[:2])

        # Limit arrays
        filters.skills = filters.skills[:20]
        filters.title_current = filters.title_current[:10]
        filters.location_names = filters.location_names[:5]
        filters.industries = filters.industries[:10]

        return filters


# Example usage
if __name__ == "__main__":
    from job_parser import JobDescriptionParser

    # Parse a job description first
    parser = JobDescriptionParser()
    job_text = """
    Senior Software Engineer - Full Stack

    Requirements:
    - 5+ years of experience
    - Strong proficiency in Python and JavaScript
    - Experience with React and Node.js
    - AWS experience required
    - Bachelor's degree in Computer Science

    Location: San Francisco, CA (Remote friendly)
    """

    parsed_job = parser.parse(job_text)

    # Generate LinkedIn filters
    generator = LinkedInFilterGenerator()
    filters = generator.generate_filters(parsed_job)
    optimized_filters = generator.optimize_for_api_limits(filters)

    # Print generated filters
    print("Generated LinkedIn Filters:")
    print(f"Keywords: {filters.keywords}")
    print(f"Titles: {filters.title_current}")
    print(f"Skills: {filters.skills}")
    print(f"Experience: {filters.experience_years_min}-{filters.experience_years_max} years")
    print(f"Locations: {filters.location_names}")