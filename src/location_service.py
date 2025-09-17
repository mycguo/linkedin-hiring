"""
Enhanced Location Service with Geocoding and Distance Calculations
Provides comprehensive location matching for candidate filtering
"""
import math
import re
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import json


class LocationMatchType(Enum):
    EXACT_CITY = "exact_city"
    METRO_AREA = "metro_area"
    STATE_MATCH = "state_match"
    COUNTRY_MATCH = "country_match"
    WITHIN_RADIUS = "within_radius"
    REMOTE = "remote"
    NO_MATCH = "no_match"


@dataclass
class Coordinates:
    latitude: float
    longitude: float


@dataclass
class LocationData:
    name: str
    city: str
    state: str
    country: str
    coordinates: Coordinates
    metro_area: Optional[str] = None
    aliases: List[str] = None
    population: Optional[int] = None

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


@dataclass
class LocationMatch:
    match_type: LocationMatchType
    confidence: float  # 0-100
    distance_miles: Optional[float] = None
    matched_location: Optional[LocationData] = None
    details: str = ""


class LocationService:
    """
    Comprehensive location service for candidate filtering
    """

    def __init__(self):
        """Initialize location service with comprehensive location database"""
        self.locations: Dict[str, LocationData] = {}
        self.metro_areas: Dict[str, List[str]] = {}
        self.state_abbreviations: Dict[str, str] = {}
        self.country_data: Dict[str, str] = {}

        self._initialize_location_database()
        self._initialize_metro_areas()
        self._initialize_state_abbreviations()
        self._initialize_country_data()

    def _initialize_location_database(self):
        """Initialize comprehensive US and international location database"""

        # Major US Cities with coordinates
        us_cities = [
            # West Coast
            ("San Francisco", "CA", "USA", 37.7749, -122.4194, 875000, "San Francisco Bay Area"),
            ("Los Angeles", "CA", "USA", 34.0522, -118.2437, 4000000, "Los Angeles Metro"),
            ("San Diego", "CA", "USA", 32.7157, -117.1611, 1400000, "San Diego Metro"),
            ("Seattle", "WA", "USA", 47.6062, -122.3321, 750000, "Seattle Metro"),
            ("Portland", "OR", "USA", 45.5152, -122.6784, 650000, "Portland Metro"),
            ("San Jose", "CA", "USA", 37.3382, -121.8863, 1000000, "San Francisco Bay Area"),

            # East Coast
            ("New York", "NY", "USA", 40.7128, -74.0060, 8400000, "New York Metro"),
            ("Boston", "MA", "USA", 42.3601, -71.0589, 685000, "Boston Metro"),
            ("Washington", "DC", "USA", 38.9072, -77.0369, 700000, "Washington DC Metro"),
            ("Philadelphia", "PA", "USA", 39.9526, -75.1652, 1600000, "Philadelphia Metro"),
            ("Miami", "FL", "USA", 25.7617, -80.1918, 470000, "Miami Metro"),
            ("Atlanta", "GA", "USA", 33.7490, -84.3880, 500000, "Atlanta Metro"),

            # Central
            ("Chicago", "IL", "USA", 41.8781, -87.6298, 2700000, "Chicago Metro"),
            ("Dallas", "TX", "USA", 32.7767, -96.7970, 1300000, "Dallas-Fort Worth Metro"),
            ("Houston", "TX", "USA", 29.7604, -95.3698, 2300000, "Houston Metro"),
            ("Austin", "TX", "USA", 30.2672, -97.7431, 950000, "Austin Metro"),
            ("Denver", "CO", "USA", 39.7392, -104.9903, 715000, "Denver Metro"),
            ("Phoenix", "AZ", "USA", 33.4484, -112.0740, 1700000, "Phoenix Metro"),
            ("Las Vegas", "NV", "USA", 36.1699, -115.1398, 650000, "Las Vegas Metro"),
            ("Salt Lake City", "UT", "USA", 40.7608, -111.8910, 200000, "Salt Lake City Metro"),

            # Additional Major Cities
            ("Nashville", "TN", "USA", 36.1627, -86.7816, 695000, "Nashville Metro"),
            ("Orlando", "FL", "USA", 28.5383, -81.3792, 310000, "Orlando Metro"),
            ("Tampa", "FL", "USA", 27.9506, -82.4572, 385000, "Tampa Bay Metro"),
            ("Charlotte", "NC", "USA", 35.2271, -80.8431, 875000, "Charlotte Metro"),
            ("Raleigh", "NC", "USA", 35.7796, -78.6382, 470000, "Raleigh-Durham Metro"),
            ("Richmond", "VA", "USA", 37.5407, -77.4360, 230000, "Richmond Metro"),
            ("Baltimore", "MD", "USA", 39.2904, -76.6122, 585000, "Baltimore Metro"),
            ("Pittsburgh", "PA", "USA", 40.4406, -79.9959, 300000, "Pittsburgh Metro"),
            ("Cleveland", "OH", "USA", 41.4993, -81.6944, 385000, "Cleveland Metro"),
            ("Detroit", "MI", "USA", 42.3314, -83.0458, 670000, "Detroit Metro"),
            ("Columbus", "OH", "USA", 39.9612, -82.9988, 900000, "Columbus Metro"),
            ("Indianapolis", "IN", "USA", 39.7684, -86.1581, 875000, "Indianapolis Metro"),
            ("Milwaukee", "WI", "USA", 43.0389, -87.9065, 590000, "Milwaukee Metro"),
            ("Minneapolis", "MN", "USA", 44.9778, -93.2650, 430000, "Minneapolis-St. Paul Metro"),
            ("Kansas City", "MO", "USA", 39.0997, -94.5786, 495000, "Kansas City Metro"),
            ("St. Louis", "MO", "USA", 38.6270, -90.1994, 300000, "St. Louis Metro"),
            ("New Orleans", "LA", "USA", 29.9511, -90.0715, 390000, "New Orleans Metro"),
            ("San Antonio", "TX", "USA", 29.4241, -98.4936, 1500000, "San Antonio Metro"),
            ("Oklahoma City", "OK", "USA", 35.4676, -97.5164, 695000, "Oklahoma City Metro"),
            ("Tulsa", "OK", "USA", 36.1540, -95.9928, 415000, "Tulsa Metro"),
            ("Little Rock", "AR", "USA", 34.7465, -92.2896, 198000, "Little Rock Metro"),
            ("Memphis", "TN", "USA", 35.1495, -90.0490, 650000, "Memphis Metro"),
            ("Birmingham", "AL", "USA", 33.5186, -86.8104, 210000, "Birmingham Metro"),
            ("Jacksonville", "FL", "USA", 30.3322, -81.6557, 950000, "Jacksonville Metro"),
            ("Buffalo", "NY", "USA", 42.8864, -78.8784, 255000, "Buffalo Metro"),
            ("Rochester", "NY", "USA", 43.1566, -77.6088, 206000, "Rochester Metro"),
            ("Albany", "NY", "USA", 42.6526, -73.7562, 98000, "Albany Metro"),
            ("Providence", "RI", "USA", 41.8240, -71.4128, 180000, "Providence Metro"),
            ("Hartford", "CT", "USA", 41.7658, -72.6734, 122000, "Hartford Metro"),
            ("Bridgeport", "CT", "USA", 41.1865, -73.1952, 145000, "Bridgeport Metro"),
        ]

        # International Cities
        international_cities = [
            ("Toronto", "ON", "Canada", 43.6532, -79.3832, 2930000, "Greater Toronto Area"),
            ("Vancouver", "BC", "Canada", 49.2827, -123.1207, 675000, "Metro Vancouver"),
            ("Montreal", "QC", "Canada", 45.5017, -73.5673, 1780000, "Montreal Metro"),
            ("London", "", "United Kingdom", 51.5074, -0.1278, 9000000, "Greater London"),
            ("Berlin", "", "Germany", 52.5200, 13.4050, 3700000, "Berlin Metro"),
            ("Paris", "", "France", 48.8566, 2.3522, 2100000, "Île-de-France"),
            ("Amsterdam", "", "Netherlands", 52.3676, 4.9041, 870000, "Amsterdam Metro"),
            ("Dublin", "", "Ireland", 53.3498, -6.2603, 555000, "Dublin Metro"),
            ("Sydney", "NSW", "Australia", -33.8688, 151.2093, 5300000, "Greater Sydney"),
            ("Melbourne", "VIC", "Australia", -37.8136, 144.9631, 5000000, "Greater Melbourne"),
            ("Tel Aviv", "", "Israel", 32.0853, 34.7818, 460000, "Tel Aviv Metro"),
            ("Tokyo", "", "Japan", 35.6762, 139.6503, 14000000, "Greater Tokyo"),
            ("Singapore", "", "Singapore", 1.3521, 103.8198, 5900000, "Singapore"),
            ("Hong Kong", "", "Hong Kong", 22.3193, 114.1694, 7500000, "Hong Kong"),
            ("Bangalore", "KA", "India", 12.9716, 77.5946, 8400000, "Bangalore Metro"),
            ("Mumbai", "MH", "India", 19.0760, 72.8777, 12400000, "Mumbai Metro"),
            ("Hyderabad", "TG", "India", 17.3850, 78.4867, 6900000, "Hyderabad Metro"),
            ("Pune", "MH", "India", 18.5204, 73.8567, 3100000, "Pune Metro"),
            ("Chennai", "TN", "India", 13.0827, 80.2707, 4600000, "Chennai Metro"),
        ]

        # Add all cities to database
        for city_data in us_cities + international_cities:
            city, state, country, lat, lon, population, metro = city_data

            location = LocationData(
                name=city,
                city=city,
                state=state,
                country=country,
                coordinates=Coordinates(lat, lon),
                metro_area=metro,
                population=population,
                aliases=self._generate_aliases(city, state, country)
            )

            # Store with multiple keys for flexible lookup
            self.locations[city.lower()] = location
            self.locations[f"{city.lower()}, {state.lower()}"] = location
            if state:
                self.locations[f"{city.lower()}, {state}".lower()] = location

    def _generate_aliases(self, city: str, state: str, country: str) -> List[str]:
        """Generate common aliases for a location"""
        aliases = []

        # Common abbreviations and variations
        alias_map = {
            "San Francisco": ["SF", "San Fran", "The City"],
            "New York": ["NYC", "New York City", "Manhattan"],
            "Los Angeles": ["LA", "Los Angeles"],
            "Washington": ["DC", "Washington DC", "Washington D.C."],
            "Las Vegas": ["Vegas"],
            "Salt Lake City": ["SLC"],
            "Kansas City": ["KC"],
            "St. Louis": ["Saint Louis"],
            "New Orleans": ["NOLA"],
            "San Antonio": ["SA"],
            "Oklahoma City": ["OKC"],
        }

        if city in alias_map:
            aliases.extend(alias_map[city])

        return aliases

    def _initialize_metro_areas(self):
        """Initialize metro area groupings"""
        self.metro_areas = {
            "San Francisco Bay Area": [
                "San Francisco", "San Jose", "Oakland", "Fremont", "Santa Clara",
                "Sunnyvale", "Hayward", "Concord", "Berkeley", "Richmond"
            ],
            "Los Angeles Metro": [
                "Los Angeles", "Long Beach", "Anaheim", "Santa Ana", "Riverside",
                "San Bernardino", "Glendale", "Huntington Beach", "Irvine"
            ],
            "New York Metro": [
                "New York", "Newark", "Jersey City", "Yonkers", "Paterson",
                "Elizabeth", "Bridgeport", "New Haven", "Stamford"
            ],
            "Chicago Metro": [
                "Chicago", "Aurora", "Joliet", "Naperville", "Elgin", "Waukegan",
                "Cicero", "Hammond", "Gary", "Schaumburg"
            ],
            "Dallas-Fort Worth Metro": [
                "Dallas", "Fort Worth", "Arlington", "Plano", "Garland", "Irving",
                "Grand Prairie", "McKinney", "Mesquite", "Carrollton"
            ],
            "Houston Metro": [
                "Houston", "The Woodlands", "Sugar Land", "Conroe", "League City",
                "Baytown", "Missouri City", "Pearland", "Pasadena"
            ],
            "Washington DC Metro": [
                "Washington", "Arlington", "Alexandria", "Rockville", "Bethesda",
                "Silver Spring", "Fairfax", "Gaithersburg", "Frederick"
            ],
            "Boston Metro": [
                "Boston", "Cambridge", "Lowell", "Brockton", "Quincy", "Lynn",
                "Newton", "Lawrence", "Somerville", "Waltham"
            ],
            "Philadelphia Metro": [
                "Philadelphia", "Allentown", "Reading", "Camden", "Wilmington",
                "Atlantic City", "Trenton", "Chester", "Bethlehem"
            ],
            "Phoenix Metro": [
                "Phoenix", "Mesa", "Chandler", "Scottsdale", "Glendale", "Gilbert",
                "Tempe", "Peoria", "Surprise", "Avondale"
            ]
        }

    def _initialize_state_abbreviations(self):
        """Initialize US state abbreviations"""
        self.state_abbreviations = {
            "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
            "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
            "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
            "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
            "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
            "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
            "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
            "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
            "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
            "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"
        }

    def _initialize_country_data(self):
        """Initialize country aliases and data"""
        self.country_data = {
            "USA": ["United States", "US", "America", "United States of America"],
            "Canada": ["CA", "CAN"],
            "United Kingdom": ["UK", "Britain", "Great Britain", "England"],
            "Germany": ["DE", "Deutschland"],
            "France": ["FR"],
            "Netherlands": ["NL", "Holland"],
            "Australia": ["AU", "AUS"],
            "India": ["IN", "IND"],
            "Japan": ["JP", "JPN"],
            "Singapore": ["SG", "SGP"],
        }

    def parse_location(self, location_text: str) -> Optional[LocationData]:
        """
        Parse location text and return best match

        Args:
            location_text: Location string to parse

        Returns:
            LocationData object if found, None otherwise
        """
        if not location_text:
            return None

        location_text = location_text.strip().lower()

        # Direct lookup
        if location_text in self.locations:
            return self.locations[location_text]

        # Try partial matches
        for key, location_data in self.locations.items():
            if location_text in key or key in location_text:
                return location_data

        # Try aliases
        for location_data in self.locations.values():
            for alias in location_data.aliases:
                if alias.lower() in location_text:
                    return location_data

        return None

    def calculate_distance(self, coord1: Coordinates, coord2: Coordinates) -> float:
        """
        Calculate distance between two coordinates using Haversine formula

        Args:
            coord1: First coordinate
            coord2: Second coordinate

        Returns:
            Distance in miles
        """
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [coord1.latitude, coord1.longitude,
                                                     coord2.latitude, coord2.longitude])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        # Radius of earth in miles
        r = 3956

        return c * r

    def match_location(
        self,
        candidate_location: str,
        required_locations: List[str],
        remote_allowed: bool = False,
        hybrid_allowed: bool = False,
        max_distance_miles: Optional[int] = None
    ) -> LocationMatch:
        """
        Match candidate location against job requirements

        Args:
            candidate_location: Candidate's location string
            required_locations: List of required/preferred locations
            remote_allowed: Whether remote work is acceptable
            hybrid_allowed: Whether hybrid work is acceptable
            max_distance_miles: Maximum distance for proximity matching

        Returns:
            LocationMatch object with match details
        """
        if not candidate_location:
            return LocationMatch(LocationMatchType.NO_MATCH, 0, details="No candidate location provided")

        candidate_location = candidate_location.strip()

        # Check for remote work indicators
        remote_keywords = ['remote', 'work from home', 'wfh', 'distributed', 'anywhere', 'global']
        if any(keyword in candidate_location.lower() for keyword in remote_keywords):
            if remote_allowed:
                return LocationMatch(
                    LocationMatchType.REMOTE,
                    100,
                    details="Remote candidate matches remote job"
                )
            else:
                return LocationMatch(
                    LocationMatchType.NO_MATCH,
                    20,
                    details="Remote candidate but remote work not allowed"
                )

        # Parse candidate location
        candidate_loc_data = self.parse_location(candidate_location)
        if not candidate_loc_data:
            return LocationMatch(
                LocationMatchType.NO_MATCH,
                10,
                details=f"Could not parse candidate location: {candidate_location}"
            )

        best_match = LocationMatch(LocationMatchType.NO_MATCH, 0)

        # Check each required location
        for req_location in required_locations:
            if req_location.lower() == "remote" and remote_allowed:
                return LocationMatch(LocationMatchType.REMOTE, 100, details="Remote work allowed")

            req_loc_data = self.parse_location(req_location)
            if not req_loc_data:
                continue

            # Exact city match
            if (candidate_loc_data.city.lower() == req_loc_data.city.lower() and
                candidate_loc_data.state.lower() == req_loc_data.state.lower()):
                return LocationMatch(
                    LocationMatchType.EXACT_CITY,
                    100,
                    matched_location=req_loc_data,
                    details=f"Exact match: {candidate_loc_data.city}, {candidate_loc_data.state}"
                )

            # Metro area match
            if (candidate_loc_data.metro_area and req_loc_data.metro_area and
                candidate_loc_data.metro_area == req_loc_data.metro_area):
                match = LocationMatch(
                    LocationMatchType.METRO_AREA,
                    90,
                    matched_location=req_loc_data,
                    details=f"Metro area match: {candidate_loc_data.metro_area}"
                )
                if match.confidence > best_match.confidence:
                    best_match = match

            # State match (for US locations)
            elif (candidate_loc_data.state and req_loc_data.state and
                  candidate_loc_data.state.lower() == req_loc_data.state.lower() and
                  candidate_loc_data.country == "USA" and req_loc_data.country == "USA"):
                match = LocationMatch(
                    LocationMatchType.STATE_MATCH,
                    70 if hybrid_allowed else 50,
                    matched_location=req_loc_data,
                    details=f"Same state: {candidate_loc_data.state}"
                )
                if match.confidence > best_match.confidence:
                    best_match = match

            # Country match
            elif candidate_loc_data.country == req_loc_data.country:
                match = LocationMatch(
                    LocationMatchType.COUNTRY_MATCH,
                    40 if hybrid_allowed else 30,
                    matched_location=req_loc_data,
                    details=f"Same country: {candidate_loc_data.country}"
                )
                if match.confidence > best_match.confidence:
                    best_match = match

            # Distance-based matching
            if max_distance_miles and candidate_loc_data.coordinates and req_loc_data.coordinates:
                distance = self.calculate_distance(
                    candidate_loc_data.coordinates,
                    req_loc_data.coordinates
                )

                if distance <= max_distance_miles:
                    # Score decreases with distance
                    distance_score = max(60, 100 - (distance / max_distance_miles * 40))
                    match = LocationMatch(
                        LocationMatchType.WITHIN_RADIUS,
                        distance_score,
                        distance_miles=distance,
                        matched_location=req_loc_data,
                        details=f"Within {distance:.1f} miles of {req_loc_data.city}"
                    )
                    if match.confidence > best_match.confidence:
                        best_match = match

        return best_match

    def get_location_suggestions(self, partial_text: str, limit: int = 10) -> List[LocationData]:
        """
        Get location suggestions for autocomplete

        Args:
            partial_text: Partial location text
            limit: Maximum number of suggestions

        Returns:
            List of matching LocationData objects
        """
        if not partial_text:
            return []

        partial_text = partial_text.lower().strip()
        suggestions = []

        for key, location in self.locations.items():
            if partial_text in key:
                suggestions.append(location)
                if len(suggestions) >= limit:
                    break

        # Sort by population (larger cities first)
        suggestions.sort(key=lambda x: x.population or 0, reverse=True)

        return suggestions[:limit]

    def validate_location_requirements(self, locations: List[str]) -> Dict[str, bool]:
        """
        Validate that location requirements can be parsed

        Args:
            locations: List of location strings

        Returns:
            Dictionary mapping location to validity
        """
        results = {}
        for location in locations:
            parsed = self.parse_location(location)
            results[location] = parsed is not None

        return results