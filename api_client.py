import httpx
import os
from typing import Dict, List, Optional
from models import UserRequirements, ServiceType, Timeframe, Preference

class EazewellAPIClient:
    """Client for integrating with Eazewell staging API endpoints"""
    
    def __init__(self):
        self.base_url = os.getenv("EAZEWELL_API_BASE_URL", "https://staging.eazewell.com/api")
        self.test_phone = os.getenv("TEST_PHONE_NUMBER", "+16197302760")
        self.timeout = 30.0
        
        # Service type mapping for API
        self.service_type_mapping = {
            ServiceType.CREMATION_MEMORIAL: "cremation_memorial",
            ServiceType.TRADITIONAL_FUNERAL: "traditional_funeral", 
            ServiceType.DIRECT_BURIAL: "direct_burial",
            ServiceType.DIRECT_CREMATION: "direct_cremation"
        }
        
        # Timeframe mapping for API
        self.timeframe_mapping = {
            Timeframe.IMMEDIATELY: "immediately",
            Timeframe.WITHIN_NEXT_FOUR_WEEKS: "within_next_four_weeks",
            Timeframe.LIKELY_WITHIN_SIX_MONTHS: "likely_within_six_months", 
            Timeframe.PLANNING_FOR_THE_FUTURE: "planning_for_the_future"
        }
    
    async def update_quote(self, requirements: UserRequirements) -> Dict:
        """
        Update quote information using the /api/ai-assistant/quote endpoint
        """
        if not requirements.is_complete():
            raise ValueError("Requirements must be complete before updating quote")
        
        # Prepare request data
        quote_data = {
            "call": {
                "retell_llm_dynamic_variables": {
                    "user_number": self.test_phone
                }
            },
            "args": {
                "service_type": self.service_type_mapping[requirements.service_type],
                "timeframe": self.timeframe_mapping[requirements.timeframe],
                "city": self._extract_city(requirements.location),
                "state": self._extract_state(requirements.location),
                "contact_preference": "phone"  # Default preference
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/ai-assistant/quote",
                    json=quote_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    # User not found, this is expected in development
                    return {"error": "user_not_found", "message": "Test user not found in database"}
                else:
                    response.raise_for_status()
                    
        except httpx.TimeoutException:
            raise Exception("API request timed out")
        except httpx.RequestError as e:
            raise Exception(f"API request failed: {str(e)}")
    
    async def search_funeral_homes(self, requirements: UserRequirements, page: int = 1, excluded_ids: List[str] = None) -> Dict:
        """
        Search for funeral homes using the /api/ai-assistant/funeral-homes endpoint
        """
        if not requirements.location or not requirements.service_type or not requirements.preference:
            raise ValueError("Location, service type, and preference are required for funeral home search")
        
        # Prepare request data
        search_data = {
            "call": {
                "retell_llm_dynamic_variables": {
                    "user_number": self.test_phone
                }
            },
            "args": {
                "location": requirements.location,
                "service_type": self.service_type_mapping[requirements.service_type],
                "page": page,
                "get_cheapest": requirements.preference == Preference.CHEAPEST
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/ai-assistant/funeral-homes",
                    json=search_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    # User not found, return mock data for development
                    return self._generate_mock_funeral_homes(requirements, page)
                else:
                    response.raise_for_status()
                    
        except httpx.TimeoutException:
            raise Exception("API request timed out")
        except httpx.RequestError as e:
            raise Exception(f"API request failed: {str(e)}")
    
    async def get_multiple_funeral_homes(self, requirements: UserRequirements, count: int = 3, excluded_ids: List[str] = None) -> List[Dict]:
        """
        Get multiple funeral homes by making multiple API calls if necessary
        Returns exactly 'count' funeral homes or fewer if not available
        """
        funeral_homes = []
        excluded_ids = excluded_ids or []
        
        # Start from page 1 if no exclusions, otherwise start from page based on excluded count
        start_page = len(excluded_ids) + 1 if excluded_ids else 1
        page = start_page
        max_pages = start_page + 10  # Safety limit
        
        while len(funeral_homes) < count and page <= max_pages:
            try:
                result = await self.search_funeral_homes(requirements, page)
                
                # Handle different response formats
                if isinstance(result, dict):
                    if "new_funeral_home" in result:
                        # Parse the funeral home info from the response string
                        funeral_home = self._parse_funeral_home_response(result["new_funeral_home"])
                        if funeral_home and funeral_home["id"] not in excluded_ids:
                            funeral_homes.append(funeral_home)
                    elif "location" in result and not result.get("new_funeral_home"):
                        # Empty result, no more funeral homes
                        break
                elif isinstance(result, list):
                    # Direct list of funeral homes
                    for home in result:
                        if home.get("id") not in excluded_ids:
                            funeral_homes.append(home)
                            if len(funeral_homes) >= count:
                                break
                
                page += 1
                
            except Exception as e:
                print(f"Error fetching funeral homes page {page}: {e}")
                # If API fails, stop trying and return what we have
                break
        
        return funeral_homes[:count]
    
    def _extract_city(self, location: str) -> str:
        """Extract city from location string"""
        if "," in location:
            return location.split(",")[0].strip()
        return location.strip()
    
    def _extract_state(self, location: str) -> str:
        """Extract state from location string"""
        if "," in location:
            state_part = location.split(",")[-1].strip()
            # Handle common state abbreviations
            state_mapping = {
                "TX": "TX", "Texas": "TX",
                "FL": "FL", "Florida": "FL", 
                "CA": "CA", "California": "CA",
                "NY": "NY", "New York": "NY",
                "IL": "IL", "Illinois": "IL"
            }
            return state_mapping.get(state_part, state_part)
        return ""
    
    def _parse_funeral_home_response(self, response_string: str) -> Optional[Dict]:
        """Parse funeral home info from API response string"""
        try:
            # Expected format: "ID - 123 | ABC Funeral Home In City, rating: 4.5, and estimated price of $3,500"
            parts = response_string.split(" | ")
            if len(parts) < 2:
                return None
            
            # Extract ID
            id_part = parts[0].strip()
            funeral_home_id = id_part.replace("ID - ", "").strip()
            
            # Extract name and details
            details_part = parts[1].strip()
            name_location = details_part.split(", rating:")[0].strip()
            
            # Extract name (everything before " In ")
            if " In " in name_location:
                name = name_location.split(" In ")[0].strip()
                location = name_location.split(" In ")[1].strip()
            else:
                name = name_location
                location = "Unknown"
            
            # Extract rating
            rating = 0.0
            if ", rating:" in details_part:
                rating_part = details_part.split(", rating:")[1].split(",")[0].strip()
                try:
                    rating = float(rating_part)
                except ValueError:
                    rating = 0.0
            
            # Extract price
            price = "N/A"
            if "estimated price of " in details_part:
                price = details_part.split("estimated price of ")[1].strip()
            
            return {
                "id": funeral_home_id,
                "name": name,
                "location": location,
                "rating": rating,
                "price": price
            }
            
        except Exception as e:
            print(f"Error parsing funeral home response: {e}")
            return None
    
    def _generate_mock_funeral_homes(self, requirements: UserRequirements, page: int) -> Dict:
        """Generate mock funeral home data for development/testing"""
        city = self._extract_city(requirements.location)
        
        mock_homes = [
            f"ID - {page}01 | {city} Memorial Services In {city}, rating: 4.5, and estimated price of $3,200",
            f"ID - {page}02 | Peaceful Rest Funeral Home In {city}, rating: 4.2, and estimated price of $2,800", 
            f"ID - {page}03 | Eternal Care Services In {city}, rating: 4.7, and estimated price of $3,500"
        ]
        
        if page <= len(mock_homes):
            return {
                "location": requirements.location,
                "new_funeral_home": mock_homes[page - 1]
            }
        else:
            # No more mock data
            return {"location": requirements.location}
    
