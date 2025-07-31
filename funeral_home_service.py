from typing import List
from models import ConversationSession, FuneralHome
from api_client import EazewellAPIClient

class FuneralHomeService:
    """Service for managing funeral home search and display logic"""
    
    def __init__(self):
        self.api_client = EazewellAPIClient()
    
    async def get_recommendations(self, session: ConversationSession) -> List[FuneralHome]:
        """
        Get exactly 3 funeral home recommendations for the user
        Excludes previously shown funeral homes
        """
        if not session.requirements.is_complete():
            raise ValueError("All requirements must be collected before getting recommendations")
        
        try:
            # Update quote first (this is expected by the API)
            await self._update_quote_if_needed(session)
            
            # Get funeral homes, excluding already shown ones
            funeral_homes_data = await self.api_client.get_multiple_funeral_homes(
                requirements=session.requirements,
                count=3,
                excluded_ids=session.shown_funeral_homes
            )
            
            # Convert to FuneralHome objects
            funeral_homes = []
            for home_data in funeral_homes_data:
                funeral_home = FuneralHome(
                    id=home_data["id"],
                    name=home_data["name"],
                    location=home_data["location"],
                    rating=home_data["rating"],
                    price=home_data["price"]
                )
                funeral_homes.append(funeral_home)
            
            # Mark these funeral homes as shown
            for funeral_home in funeral_homes:
                if funeral_home.id not in session.shown_funeral_homes:
                    session.shown_funeral_homes.append(funeral_home.id)
            
            return funeral_homes
            
        except Exception as e:
            print(f"Error getting funeral home recommendations: {e}")
            # Return empty list if API fails
            return []
    
    async def _update_quote_if_needed(self, session: ConversationSession) -> bool:
        """Update quote via API if requirements have changed"""
        try:
            result = await self.api_client.update_quote(session.requirements)
            
            if "error" in result and result["error"] == "user_not_found":
                print("Development mode: Test user not found in staging database")
                return False
            
            print(f"Quote updated successfully: {result}")
            return True
            
        except Exception as e:
            print(f"Error updating quote: {e}")
            return False
    

    
    def _extract_city(self, location: str) -> str:
        """Extract city from location string"""
        if "," in location:
            return location.split(",")[0].strip()
        return location.strip()
    
    def _extract_state(self, location: str) -> str:
        """Extract state from location string"""
        if "," in location:
            state_part = location.split(",")[-1].strip()
            return state_part
        return ""
    
    def has_more_options(self, session: ConversationSession) -> bool:
        """
        Check if there are likely more funeral home options available
        This is used to determine if we should offer to show more options
        """
        # If we've shown less than 6 funeral homes, there are likely more options
        return len(session.shown_funeral_homes) < 6
    
    async def get_more_recommendations(self, session: ConversationSession) -> List[FuneralHome]:
        """
        Get additional funeral home recommendations
        Used when user wants to see more options without changing criteria
        """
        if not session.requirements.is_complete():
            raise ValueError("All requirements must be collected before getting more recommendations")
        
        try:
            print(f"DEBUG: Getting more recommendations for session {session.session_id}")
            print(f"DEBUG: Already shown homes: {session.shown_funeral_homes}")
            
            # Get additional funeral homes from API, excluding already shown ones
            funeral_homes_data = await self.api_client.get_multiple_funeral_homes(
                requirements=session.requirements,
                count=3,
                excluded_ids=session.shown_funeral_homes
            )
            
            print(f"DEBUG: API returned {len(funeral_homes_data)} homes")
            
            # Convert to FuneralHome objects
            funeral_homes = []
            for home_data in funeral_homes_data:
                funeral_home = FuneralHome(
                    id=home_data["id"],
                    name=home_data["name"],
                    location=home_data["location"],
                    rating=home_data["rating"],
                    price=home_data["price"]
                )
                funeral_homes.append(funeral_home)
                # Add to shown homes immediately
                if home_data["id"] not in session.shown_funeral_homes:
                    session.shown_funeral_homes.append(home_data["id"])
                print(f"DEBUG: Added funeral home {home_data['id']} to shown list")
            
            print(f"DEBUG: Returning {len(funeral_homes)} funeral homes")
            print(f"DEBUG: Updated shown homes: {session.shown_funeral_homes}")
            return funeral_homes
            
        except Exception as e:
            print(f"Error getting more funeral home recommendations: {e}")
            # Return empty list if API fails
            return []
    

    
    def reset_recommendations(self, session: ConversationSession):
        """
        Reset shown funeral homes when user changes preferences significantly
        This allows them to see previously shown homes again with new criteria
        """
        session.shown_funeral_homes = []
        session.current_page = 1