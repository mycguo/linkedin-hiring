"""
Candidate Scoring and Ranking Engine
Multi-factor scoring algorithm for ranking candidates
"""
import math
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from models import (
    ParsedJobDescription,
    CandidateProfile,
    CandidateScore,
    ScoreComponent,
    RankedCandidate,
    Experience,
    Education,
    EducationLevel,
    SeniorityLevel
)
from location_service import LocationService, LocationMatchType


class ScoringEngine:
    """
    Advanced scoring engine for candidate evaluation
    """

    # Default scoring weights
    DEFAULT_WEIGHTS = {
        'skill_match': 0.30,
        'experience_match': 0.20,
        'education_match': 0.15,
        'industry_match': 0.15,
        'location_match': 0.10,
        'career_trajectory': 0.05,
        'keyword_density': 0.05
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize scoring engine

        Args:
            weights: Custom scoring weights (must sum to 1.0)
        """
        self.weights = weights or self.DEFAULT_WEIGHTS
        self._validate_weights()

        # Initialize location service
        self.location_service = LocationService()

        # Initialize TF-IDF vectorizer for text similarity
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2)
        )

        # Skill similarity thresholds
        self.EXACT_MATCH_SCORE = 100
        self.SYNONYM_MATCH_SCORE = 80
        self.RELATED_MATCH_SCORE = 60
        self.PARTIAL_MATCH_SCORE = 40

    def _validate_weights(self):
        """Validate that weights sum to 1.0"""
        weight_sum = sum(self.weights.values())
        if not 0.99 <= weight_sum <= 1.01:  # Allow small floating-point errors
            raise ValueError(f"Weights must sum to 1.0, got {weight_sum}")

    def should_filter_candidate(
        self,
        job: ParsedJobDescription,
        candidate: CandidateProfile
    ) -> Tuple[bool, str]:
        """
        Determine if candidate should be filtered out before scoring

        Args:
            job: Job description with requirements
            candidate: Candidate profile

        Returns:
            Tuple of (should_filter, reason)
        """
        # Strict location filtering
        if job.location and job.location.strict_location_filter:
            location_match = self.location_service.match_location(
                candidate.location,
                job.location.cities + job.location.states + job.location.countries,
                remote_allowed=job.location.remote,
                hybrid_allowed=job.location.hybrid,
                max_distance_miles=job.location.max_distance_miles
            )

            # Define minimum acceptable match types for strict filtering
            acceptable_types = {
                LocationMatchType.EXACT_CITY,
                LocationMatchType.METRO_AREA,
                LocationMatchType.WITHIN_RADIUS,
                LocationMatchType.REMOTE
            }

            if location_match.match_type not in acceptable_types:
                return True, f"Location mismatch: {location_match.details}"

            # Even for acceptable types, filter if confidence is too low
            if location_match.confidence < 60:
                return True, f"Location confidence too low: {location_match.confidence}%"

        return False, ""

    def score_candidate(
        self,
        job: ParsedJobDescription,
        candidate: CandidateProfile,
        job_id: Optional[str] = None
    ) -> CandidateScore:
        """
        Score a single candidate against job requirements

        Args:
            job: Parsed job description
            candidate: Candidate profile
            job_id: Optional job ID for tracking

        Returns:
            CandidateScore object with detailed scoring breakdown
        """
        components = []

        # Calculate individual component scores
        skill_score = self._score_skills(job, candidate)
        components.append(skill_score)

        experience_score = self._score_experience(job, candidate)
        components.append(experience_score)

        education_score = self._score_education(job, candidate)
        components.append(education_score)

        industry_score = self._score_industry(job, candidate)
        components.append(industry_score)

        location_score = self._score_location(job, candidate)
        components.append(location_score)

        trajectory_score = self._score_career_trajectory(job, candidate)
        components.append(trajectory_score)

        keyword_score = self._score_keyword_density(job, candidate)
        components.append(keyword_score)

        # Calculate overall score
        overall_score = sum(comp.weighted_score for comp in components)

        # Generate insights
        match_explanation = self._generate_match_explanation(components, job, candidate)
        missing_requirements = self._identify_missing_requirements(job, candidate)
        additional_strengths = self._identify_additional_strengths(job, candidate)
        recommendations = self._generate_recommendations(components, job, candidate)

        return CandidateScore(
            candidate_id=candidate.linkedin_id,
            job_description_id=job_id or "unknown",
            overall_score=min(overall_score, 100),  # Cap at 100
            components=components,
            match_explanation=match_explanation,
            missing_requirements=missing_requirements,
            additional_strengths=additional_strengths,
            recommendations=recommendations,
            confidence_level=self._calculate_confidence(candidate)
        )

    def _score_skills(self, job: ParsedJobDescription, candidate: CandidateProfile) -> ScoreComponent:
        """Score candidate's skill match"""
        required_skills = set(s.lower() for s in job.required_skills)
        preferred_skills = set(s.lower() for s in job.preferred_skills)
        candidate_skills = set(s.lower() for s in candidate.skills)

        # Also extract skills from experience descriptions
        extracted_skills = self._extract_skills_from_experience(candidate)
        candidate_skills.update(extracted_skills)

        # Score required skills
        required_matches = 0
        required_partials = 0
        for req_skill in required_skills:
            if req_skill in candidate_skills:
                required_matches += 1
            elif any(self._is_related_skill(req_skill, c_skill) for c_skill in candidate_skills):
                required_partials += 0.6
            elif any(req_skill in c_skill or c_skill in req_skill for c_skill in candidate_skills):
                required_partials += 0.4

        # Score preferred skills
        preferred_matches = 0
        for pref_skill in preferred_skills:
            if pref_skill in candidate_skills:
                preferred_matches += 0.5
            elif any(self._is_related_skill(pref_skill, c_skill) for c_skill in candidate_skills):
                preferred_matches += 0.3

        # Calculate score
        if required_skills:
            required_score = ((required_matches + required_partials) / len(required_skills)) * 80
        else:
            required_score = 80

        if preferred_skills:
            preferred_score = (preferred_matches / len(preferred_skills)) * 20
        else:
            preferred_score = 0

        raw_score = required_score + preferred_score
        weighted_score = raw_score * self.weights['skill_match']

        return ScoreComponent(
            name='skill_match',
            weight=self.weights['skill_match'],
            raw_score=raw_score,
            weighted_score=weighted_score,
            details={
                'required_matches': required_matches,
                'required_total': len(required_skills),
                'preferred_matches': preferred_matches,
                'preferred_total': len(preferred_skills),
                'candidate_skills': list(candidate_skills)[:20]
            }
        )

    def _score_experience(self, job: ParsedJobDescription, candidate: CandidateProfile) -> ScoreComponent:
        """Score candidate's experience relevance and duration"""
        # Calculate total years of experience
        total_years = self._calculate_total_experience(candidate)

        # Score years of experience
        years_score = 0
        if job.experience:
            if job.experience.min_years <= total_years:
                if job.experience.max_years and total_years <= job.experience.max_years:
                    years_score = 100
                elif job.experience.max_years and total_years > job.experience.max_years:
                    # Slightly penalize over-qualification
                    over_years = total_years - job.experience.max_years
                    years_score = max(70, 100 - (over_years * 5))
                else:
                    years_score = 100
            else:
                # Under-qualified
                shortfall = job.experience.min_years - total_years
                years_score = max(0, 100 - (shortfall * 20))
        else:
            years_score = 80  # No specific requirement

        # Score relevance of experience
        relevance_score = self._calculate_experience_relevance(job, candidate)

        # Score recency (recent experience is more valuable)
        recency_score = self._calculate_experience_recency(candidate)

        # Score seniority progression
        progression_score = self._calculate_career_progression(candidate)

        # Combine scores
        raw_score = (
            years_score * 0.4 +
            relevance_score * 0.35 +
            recency_score * 0.15 +
            progression_score * 0.10
        )
        weighted_score = raw_score * self.weights['experience_match']

        return ScoreComponent(
            name='experience_match',
            weight=self.weights['experience_match'],
            raw_score=raw_score,
            weighted_score=weighted_score,
            details={
                'total_years': total_years,
                'required_min': job.experience.min_years if job.experience else None,
                'required_max': job.experience.max_years if job.experience else None,
                'relevance_score': relevance_score,
                'recency_score': recency_score
            }
        )

    def _score_education(self, job: ParsedJobDescription, candidate: CandidateProfile) -> ScoreComponent:
        """Score candidate's education match"""
        if not job.education:
            # No education requirement
            return ScoreComponent(
                name='education_match',
                weight=self.weights['education_match'],
                raw_score=100,
                weighted_score=100 * self.weights['education_match'],
                details={'status': 'no_requirement'}
            )

        # Map education levels to numeric values
        education_hierarchy = {
            EducationLevel.HIGH_SCHOOL: 1,
            EducationLevel.ASSOCIATE: 2,
            EducationLevel.BACHELOR: 3,
            EducationLevel.MASTER: 4,
            EducationLevel.PHD: 5,
            EducationLevel.PROFESSIONAL: 4
        }

        # Get candidate's highest education level
        candidate_level = self._get_highest_education_level(candidate)
        required_level = job.education.level

        # Score education level
        level_score = 0
        if candidate_level:
            candidate_value = education_hierarchy.get(candidate_level, 0)
            required_value = education_hierarchy.get(required_level, 3)

            if candidate_value >= required_value:
                level_score = 100
            else:
                shortfall = required_value - candidate_value
                level_score = max(0, 100 - (shortfall * 25))
        else:
            level_score = 0 if job.education.required else 50

        # Score field of study match
        field_score = self._score_education_field(job.education.fields, candidate.education)

        # Combine scores
        raw_score = level_score * 0.6 + field_score * 0.4
        weighted_score = raw_score * self.weights['education_match']

        return ScoreComponent(
            name='education_match',
            weight=self.weights['education_match'],
            raw_score=raw_score,
            weighted_score=weighted_score,
            details={
                'candidate_level': candidate_level.value if candidate_level else None,
                'required_level': required_level.value,
                'field_match': field_score > 50
            }
        )

    def _score_industry(self, job: ParsedJobDescription, candidate: CandidateProfile) -> ScoreComponent:
        """Score candidate's industry experience"""
        if not job.industry_experience:
            return ScoreComponent(
                name='industry_match',
                weight=self.weights['industry_match'],
                raw_score=100,
                weighted_score=100 * self.weights['industry_match'],
                details={'status': 'no_requirement'}
            )

        # Extract industries from candidate's experience
        candidate_industries = self._extract_industries(candidate)

        # Check for matches
        matches = 0
        for required_industry in job.industry_experience:
            if any(required_industry.lower() in ci.lower() for ci in candidate_industries):
                matches += 1

        raw_score = (matches / len(job.industry_experience)) * 100 if job.industry_experience else 100
        weighted_score = raw_score * self.weights['industry_match']

        return ScoreComponent(
            name='industry_match',
            weight=self.weights['industry_match'],
            raw_score=raw_score,
            weighted_score=weighted_score,
            details={
                'required_industries': job.industry_experience,
                'candidate_industries': candidate_industries,
                'matches': matches
            }
        )

    def _score_location(self, job: ParsedJobDescription, candidate: CandidateProfile) -> ScoreComponent:
        """Score candidate's location match using enhanced location service"""
        if not job.location:
            return ScoreComponent(
                name='location_match',
                weight=self.weights['location_match'],
                raw_score=100,
                weighted_score=100 * self.weights['location_match'],
                details={'status': 'no_requirement'}
            )

        # Use enhanced location matching
        all_required_locations = job.location.cities + job.location.states + job.location.countries
        location_match = self.location_service.match_location(
            candidate.location,
            all_required_locations,
            remote_allowed=job.location.remote,
            hybrid_allowed=job.location.hybrid,
            max_distance_miles=job.location.max_distance_miles
        )

        # Base score from location match
        raw_score = location_match.confidence

        # Apply location weight multiplier for location-critical roles
        if job.location.location_weight_multiplier != 1.0:
            # Amplify the score difference for location-critical roles
            if raw_score >= 80:
                raw_score = min(100, raw_score * job.location.location_weight_multiplier)
            elif raw_score <= 40:
                raw_score = max(0, raw_score / job.location.location_weight_multiplier)

        # Calculate weighted score with potentially adjusted weight
        effective_weight = self.weights['location_match']
        if job.location.location_weight_multiplier > 1.0:
            # For location-critical roles, increase the weight itself
            effective_weight = min(0.5, effective_weight * job.location.location_weight_multiplier)

        weighted_score = raw_score * effective_weight

        # Prepare detailed information
        details = {
            'candidate_location': candidate.location,
            'required_locations': all_required_locations,
            'match_type': location_match.match_type.value,
            'match_confidence': location_match.confidence,
            'distance_miles': location_match.distance_miles,
            'remote_allowed': job.location.remote,
            'hybrid_allowed': job.location.hybrid,
            'max_distance_miles': job.location.max_distance_miles,
            'location_weight_multiplier': job.location.location_weight_multiplier,
            'effective_weight': effective_weight,
            'match_details': location_match.details
        }

        if location_match.matched_location:
            details['matched_location'] = {
                'name': location_match.matched_location.name,
                'city': location_match.matched_location.city,
                'state': location_match.matched_location.state,
                'country': location_match.matched_location.country
            }

        return ScoreComponent(
            name='location_match',
            weight=effective_weight,
            raw_score=raw_score,
            weighted_score=weighted_score,
            details=details
        )

    def _score_career_trajectory(self, job: ParsedJobDescription, candidate: CandidateProfile) -> ScoreComponent:
        """Score candidate's career growth pattern"""
        trajectory_points = []

        # Analyze job progression
        for i in range(len(candidate.experiences) - 1):
            current = candidate.experiences[i]
            previous = candidate.experiences[i + 1]

            # Check for promotion or advancement
            if self._is_advancement(previous, current):
                trajectory_points.append(20)
            else:
                trajectory_points.append(10)

        # Check for consistent employment
        gaps = self._calculate_employment_gaps(candidate)
        if gaps < 6:  # Less than 6 months total gaps
            trajectory_points.append(30)
        elif gaps < 12:
            trajectory_points.append(20)
        else:
            trajectory_points.append(10)

        # Check for stability (not too many job changes)
        avg_tenure = self._calculate_average_tenure(candidate)
        if avg_tenure >= 2:  # Average 2+ years per job
            trajectory_points.append(30)
        elif avg_tenure >= 1:
            trajectory_points.append(20)
        else:
            trajectory_points.append(10)

        raw_score = sum(trajectory_points) if trajectory_points else 50
        raw_score = min(raw_score, 100)
        weighted_score = raw_score * self.weights['career_trajectory']

        return ScoreComponent(
            name='career_trajectory',
            weight=self.weights['career_trajectory'],
            raw_score=raw_score,
            weighted_score=weighted_score,
            details={
                'employment_gaps_months': gaps,
                'average_tenure_years': avg_tenure,
                'shows_progression': raw_score > 70
            }
        )

    def _score_keyword_density(self, job: ParsedJobDescription, candidate: CandidateProfile) -> ScoreComponent:
        """Score based on keyword matching in candidate's profile text"""
        # Combine all candidate text
        candidate_text = self._get_candidate_text(candidate)

        # Extract keywords from job description
        job_keywords = self._extract_keywords(job.job_description_text)

        # Count keyword matches
        matches = 0
        for keyword in job_keywords:
            if keyword.lower() in candidate_text.lower():
                matches += 1

        raw_score = (matches / len(job_keywords)) * 100 if job_keywords else 50
        weighted_score = raw_score * self.weights['keyword_density']

        return ScoreComponent(
            name='keyword_density',
            weight=self.weights['keyword_density'],
            raw_score=raw_score,
            weighted_score=weighted_score,
            details={
                'keywords_found': matches,
                'keywords_total': len(job_keywords)
            }
        )

    # Helper methods
    def _is_related_skill(self, skill1: str, skill2: str) -> bool:
        """Check if two skills are related"""
        skill_relations = {
            'javascript': ['typescript', 'node.js', 'react', 'angular', 'vue'],
            'python': ['django', 'flask', 'fastapi', 'pandas', 'numpy'],
            'java': ['spring', 'hibernate', 'maven', 'gradle'],
            'cloud': ['aws', 'azure', 'gcp', 'devops'],
            'machine learning': ['tensorflow', 'pytorch', 'scikit-learn', 'deep learning', 'ai']
        }

        for base, related in skill_relations.items():
            if (skill1 == base and skill2 in related) or (skill2 == base and skill1 in related):
                return True

        return False

    def _extract_skills_from_experience(self, candidate: CandidateProfile) -> set:
        """Extract skills mentioned in experience descriptions"""
        skills = set()
        skill_keywords = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular',
            'node.js', 'django', 'flask', 'spring', 'docker', 'kubernetes',
            'aws', 'azure', 'gcp', 'sql', 'nosql', 'mongodb', 'postgresql'
        ]

        for exp in candidate.experiences:
            exp_text = exp.description.lower()
            for skill in skill_keywords:
                if skill in exp_text:
                    skills.add(skill)

        return skills

    def _calculate_total_experience(self, candidate: CandidateProfile) -> float:
        """Calculate total years of experience"""
        if not candidate.experiences:
            return 0

        total_months = 0
        for exp in candidate.experiences:
            if exp.start_date:
                end = exp.end_date or datetime.now()
                months = (end.year - exp.start_date.year) * 12 + (end.month - exp.start_date.month)
                total_months += max(0, months)

        return total_months / 12

    def _calculate_experience_relevance(self, job: ParsedJobDescription, candidate: CandidateProfile) -> float:
        """Calculate relevance of candidate's experience using TF-IDF"""
        if not candidate.experiences:
            return 0

        try:
            # Combine all experience descriptions
            candidate_exp_text = " ".join([exp.description for exp in candidate.experiences])

            if not candidate_exp_text or not job.job_description_text:
                return 50

            # Fit and transform texts
            texts = [job.job_description_text, candidate_exp_text]
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)

            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

            return similarity * 100
        except:
            return 50  # Default score on error

    def _calculate_experience_recency(self, candidate: CandidateProfile) -> float:
        """Score based on how recent the experience is"""
        if not candidate.experiences:
            return 0

        # Check if currently employed
        if any(exp.is_current for exp in candidate.experiences):
            return 100

        # Find most recent experience
        most_recent = None
        for exp in candidate.experiences:
            if exp.end_date:
                if not most_recent or exp.end_date > most_recent:
                    most_recent = exp.end_date

        if not most_recent:
            return 50

        # Calculate months since last job
        months_gap = (datetime.now() - most_recent).days / 30

        if months_gap < 3:
            return 95
        elif months_gap < 6:
            return 85
        elif months_gap < 12:
            return 70
        else:
            return max(30, 100 - (months_gap * 2))

    def _calculate_career_progression(self, candidate: CandidateProfile) -> float:
        """Analyze career progression"""
        if len(candidate.experiences) < 2:
            return 50

        progression_score = 50
        seniority_keywords = {
            'junior': 1, 'associate': 2, 'mid': 3, 'senior': 4,
            'lead': 5, 'principal': 6, 'manager': 7, 'director': 8
        }

        for i in range(len(candidate.experiences) - 1):
            current = candidate.experiences[i].title.lower()
            previous = candidate.experiences[i + 1].title.lower()

            current_level = max([v for k, v in seniority_keywords.items() if k in current], default=3)
            previous_level = max([v for k, v in seniority_keywords.items() if k in previous], default=3)

            if current_level > previous_level:
                progression_score += 10

        return min(progression_score, 100)

    def _get_highest_education_level(self, candidate: CandidateProfile) -> Optional[EducationLevel]:
        """Get candidate's highest education level"""
        education_keywords = {
            'phd': EducationLevel.PHD,
            'doctorate': EducationLevel.PHD,
            'master': EducationLevel.MASTER,
            'mba': EducationLevel.MASTER,
            'bachelor': EducationLevel.BACHELOR,
            'associate': EducationLevel.ASSOCIATE
        }

        highest = None
        hierarchy_values = {
            EducationLevel.ASSOCIATE: 2,
            EducationLevel.BACHELOR: 3,
            EducationLevel.MASTER: 4,
            EducationLevel.PHD: 5
        }

        for edu in candidate.education:
            degree_lower = edu.degree.lower()
            for keyword, level in education_keywords.items():
                if keyword in degree_lower:
                    if not highest or hierarchy_values.get(level, 0) > hierarchy_values.get(highest, 0):
                        highest = level

        return highest

    def _score_education_field(self, required_fields: List[str], education: List[Education]) -> float:
        """Score field of study match"""
        if not required_fields or not education:
            return 75

        for edu in education:
            field_lower = edu.field.lower()
            for req_field in required_fields:
                if req_field.lower() in field_lower or field_lower in req_field.lower():
                    return 100

        return 30

    def _extract_industries(self, candidate: CandidateProfile) -> List[str]:
        """Extract industries from candidate's experience"""
        industries = []
        industry_keywords = [
            'fintech', 'healthcare', 'e-commerce', 'saas', 'education',
            'gaming', 'social media', 'cybersecurity', 'ai', 'blockchain'
        ]

        for exp in candidate.experiences:
            exp_text = (exp.company + " " + exp.description).lower()
            for keyword in industry_keywords:
                if keyword in exp_text:
                    industries.append(keyword)

        return list(set(industries))

    def _is_advancement(self, previous: Experience, current: Experience) -> bool:
        """Check if current position is advancement from previous"""
        seniority_keywords = ['senior', 'lead', 'principal', 'manager', 'director', 'vp']

        prev_title = previous.title.lower()
        curr_title = current.title.lower()

        prev_seniority = sum(1 for k in seniority_keywords if k in prev_title)
        curr_seniority = sum(1 for k in seniority_keywords if k in curr_title)

        return curr_seniority > prev_seniority

    def _calculate_employment_gaps(self, candidate: CandidateProfile) -> int:
        """Calculate total employment gaps in months"""
        if len(candidate.experiences) < 2:
            return 0

        total_gap_months = 0
        for i in range(len(candidate.experiences) - 1):
            current = candidate.experiences[i]
            next_exp = candidate.experiences[i + 1]

            if current.start_date and next_exp.end_date:
                gap = (current.start_date - next_exp.end_date).days / 30
                if gap > 1:  # More than 1 month gap
                    total_gap_months += gap

        return int(total_gap_months)

    def _calculate_average_tenure(self, candidate: CandidateProfile) -> float:
        """Calculate average job tenure in years"""
        if not candidate.experiences:
            return 0

        total_months = 0
        job_count = 0

        for exp in candidate.experiences:
            if exp.start_date:
                end = exp.end_date or datetime.now()
                months = (end.year - exp.start_date.year) * 12 + (end.month - exp.start_date.month)
                total_months += max(0, months)
                job_count += 1

        return (total_months / 12 / job_count) if job_count > 0 else 0

    def _get_candidate_text(self, candidate: CandidateProfile) -> str:
        """Get all text from candidate profile"""
        texts = [
            candidate.headline,
            candidate.summary
        ]

        for exp in candidate.experiences:
            texts.append(exp.title)
            texts.append(exp.description)

        return " ".join(texts)

    def _extract_keywords(self, text: str, top_n: int = 20) -> List[str]:
        """Extract important keywords from text"""
        # Simple keyword extraction - would use more sophisticated NLP in production
        import re
        words = re.findall(r'\b[a-z]+\b', text.lower())

        # Filter common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were'}
        words = [w for w in words if w not in stopwords and len(w) > 2]

        # Count frequency
        from collections import Counter
        word_freq = Counter(words)

        return [word for word, _ in word_freq.most_common(top_n)]

    def _generate_match_explanation(
        self, components: List[ScoreComponent], job: ParsedJobDescription, candidate: CandidateProfile
    ) -> str:
        """Generate human-readable match explanation"""
        overall_score = sum(c.weighted_score for c in components)

        if overall_score >= 85:
            strength = "Excellent"
        elif overall_score >= 70:
            strength = "Strong"
        elif overall_score >= 55:
            strength = "Good"
        elif overall_score >= 40:
            strength = "Fair"
        else:
            strength = "Weak"

        # Find strongest component
        best_component = max(components, key=lambda c: c.raw_score)

        explanation = f"{strength} match ({overall_score:.0f}/100). "
        explanation += f"Strongest area: {best_component.name.replace('_', ' ').title()} "
        explanation += f"({best_component.raw_score:.0f}/100)."

        return explanation

    def _identify_missing_requirements(
        self, job: ParsedJobDescription, candidate: CandidateProfile
    ) -> List[str]:
        """Identify key missing requirements"""
        missing = []

        # Check required skills
        candidate_skills = set(s.lower() for s in candidate.skills)
        for skill in job.required_skills:
            if skill.lower() not in candidate_skills:
                missing.append(f"Required skill: {skill}")

        # Check experience
        if job.experience:
            total_years = self._calculate_total_experience(candidate)
            if total_years < job.experience.min_years:
                shortfall = job.experience.min_years - total_years
                missing.append(f"Experience: {shortfall:.1f} years short of requirement")

        # Check education
        if job.education and job.education.required:
            candidate_level = self._get_highest_education_level(candidate)
            if not candidate_level:
                missing.append(f"Education: {job.education.level.value} degree required")

        return missing[:5]  # Limit to top 5

    def _identify_additional_strengths(
        self, job: ParsedJobDescription, candidate: CandidateProfile
    ) -> List[str]:
        """Identify candidate's additional strengths"""
        strengths = []

        # Check for extra skills
        candidate_skills = set(s.lower() for s in candidate.skills)
        valuable_extra_skills = ['leadership', 'mentoring', 'agile', 'scrum', 'architecture']
        for skill in valuable_extra_skills:
            if skill in candidate_skills and skill not in str(job.required_skills).lower():
                strengths.append(f"Additional skill: {skill}")

        # Check for certifications
        if candidate.certifications:
            strengths.append(f"{len(candidate.certifications)} professional certification(s)")

        # Check for publications/projects
        if candidate.publications:
            strengths.append(f"{len(candidate.publications)} publication(s)")

        return strengths[:3]

    def _generate_recommendations(
        self, components: List[ScoreComponent], job: ParsedJobDescription, candidate: CandidateProfile
    ) -> List[str]:
        """Generate recommendations for the candidate"""
        recommendations = []
        overall_score = sum(c.weighted_score for c in components)

        if overall_score >= 70:
            recommendations.append("Strong candidate - recommend interview")
        elif overall_score >= 55:
            recommendations.append("Promising candidate - consider for interview")
        else:
            recommendations.append("May not meet minimum requirements")

        # Find weakest area for improvement suggestion
        weakest = min(components, key=lambda c: c.raw_score)
        if weakest.raw_score < 60:
            recommendations.append(f"Assess {weakest.name.replace('_', ' ')} carefully in interview")

        return recommendations

    def _calculate_confidence(self, candidate: CandidateProfile) -> float:
        """Calculate confidence level based on data completeness"""
        confidence = 1.0

        # Penalize for missing data
        if not candidate.summary:
            confidence -= 0.1
        if not candidate.experiences:
            confidence -= 0.3
        if not candidate.skills:
            confidence -= 0.2
        if not candidate.education:
            confidence -= 0.1

        return max(0.3, confidence)

    def rank_candidates(
        self, job: ParsedJobDescription, candidates: List[CandidateProfile]
    ) -> List[RankedCandidate]:
        """
        Rank multiple candidates with optional pre-filtering

        Args:
            job: Job description
            candidates: List of candidates to rank

        Returns:
            List of RankedCandidate objects sorted by score
        """
        # Pre-filter candidates if strict filtering is enabled
        filtered_candidates = []
        filtered_out_count = 0

        for candidate in candidates:
            should_filter, filter_reason = self.should_filter_candidate(job, candidate)
            if should_filter:
                filtered_out_count += 1
                print(f"Filtered out {candidate.name}: {filter_reason}")
            else:
                filtered_candidates.append(candidate)

        if filtered_out_count > 0:
            print(f"Pre-filtered {filtered_out_count} candidates due to strict requirements")

        # Score remaining candidates
        scored_candidates = []
        for candidate in filtered_candidates:
            score = self.score_candidate(job, candidate)
            scored_candidates.append((candidate, score))

        # Sort by overall score
        scored_candidates.sort(key=lambda x: x[1].overall_score, reverse=True)

        # Create ranked candidates with percentile
        ranked = []
        total = len(scored_candidates)
        for i, (candidate, score) in enumerate(scored_candidates):
            percentile = ((total - i - 1) / total * 100) if total > 1 else 100
            ranked.append(RankedCandidate(
                profile=candidate,
                score=score,
                rank=i + 1,
                percentile=percentile
            ))

        return ranked