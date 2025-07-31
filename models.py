from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class ServiceType(str, Enum):
    CREMATION_MEMORIAL = "cremation_memorial"
    TRADITIONAL_FUNERAL = "traditional_funeral"
    DIRECT_BURIAL = "direct_burial"
    DIRECT_CREMATION = "direct_cremation"

class Timeframe(str, Enum):
    IMMEDIATELY = "immediately"
    WITHIN_NEXT_FOUR_WEEKS = "within_next_four_weeks"
    LIKELY_WITHIN_SIX_MONTHS = "likely_within_six_months"
    PLANNING_FOR_THE_FUTURE = "planning_for_the_future"

class Preference(str, Enum):
    CHEAPEST = "cheapest"
    NEAREST = "nearest"

class ConversationState(str, Enum):
    COLLECTING_INFO = "collecting_info"
    SHOWING_RESULTS = "showing_results"
    ADJUSTING_PREFERENCES = "adjusting_preferences"
    COMPLETED = "completed"

class UserRequirements(BaseModel):
    location: Optional[str] = None
    service_type: Optional[ServiceType] = None
    timeframe: Optional[Timeframe] = None
    preference: Optional[Preference] = None
    
    def is_complete(self) -> bool:
        """Check if all required information has been collected"""
        return all([
            self.location is not None,
            self.service_type is not None,
            self.timeframe is not None,
            self.preference is not None
        ])
    
    def missing_fields(self) -> List[str]:
        """Return list of missing required fields"""
        missing = []
        if not self.location:
            missing.append("location")
        if not self.service_type:
            missing.append("service_type")
        if not self.timeframe:
            missing.append("timeframe")
        if not self.preference:
            missing.append("preference")
        return missing

class FuneralHome(BaseModel):
    id: str
    name: str
    location: str
    rating: float
    price: str

class ConversationSession(BaseModel):
    session_id: str
    user_phone: str
    state: ConversationState = ConversationState.COLLECTING_INFO
    requirements: UserRequirements = UserRequirements()
    shown_funeral_homes: List[str] = []  # List of funeral home IDs already shown
    current_page: int = 1
    conversation_history: List[Dict[str, Any]] = []
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        self.updated_at = datetime.now()
    
    def reset_funeral_home_search(self):
        """Reset funeral home search when preferences change significantly"""
        self.shown_funeral_homes = []
        self.current_page = 1
        self.state = ConversationState.COLLECTING_INFO
    
    def mark_funeral_homes_as_shown(self, funeral_home_ids: List[str]):
        """Mark funeral homes as already shown to user"""
        self.shown_funeral_homes.extend(funeral_home_ids)
        self.updated_at = datetime.now()

# Service type mappings for user-friendly display
SERVICE_TYPE_DISPLAY = {
    ServiceType.CREMATION_MEMORIAL: "Cremation Memorial",
    ServiceType.TRADITIONAL_FUNERAL: "Traditional Funeral",
    ServiceType.DIRECT_BURIAL: "Direct Burial",
    ServiceType.DIRECT_CREMATION: "Direct Cremation"
}

TIMEFRAME_DISPLAY = {
    Timeframe.IMMEDIATELY: "Immediately",
    Timeframe.WITHIN_NEXT_FOUR_WEEKS: "Within the next 4 weeks",
    Timeframe.LIKELY_WITHIN_SIX_MONTHS: "Likely within 6 months",
    Timeframe.PLANNING_FOR_THE_FUTURE: "Planning for the future"
}

# Keywords for natural language processing
SERVICE_TYPE_KEYWORDS = {
    ServiceType.CREMATION_MEMORIAL: ["cremation memorial", "memorial service", "cremation with service"],
    ServiceType.TRADITIONAL_FUNERAL: ["traditional funeral", "full service", "funeral service", "burial"],
    ServiceType.DIRECT_BURIAL: ["direct burial", "simple burial", "burial without service"],
    ServiceType.DIRECT_CREMATION: ["direct cremation", "simple cremation", "cremation without service"]
}

TIMEFRAME_KEYWORDS = {
    Timeframe.IMMEDIATELY: ["immediately", "asap", "right away", "urgent", "now"],
    Timeframe.WITHIN_NEXT_FOUR_WEEKS: ["soon", "few weeks", "month", "4 weeks", "within weeks"],
    Timeframe.LIKELY_WITHIN_SIX_MONTHS: ["6 months", "half year", "few months", "this year"],
    Timeframe.PLANNING_FOR_THE_FUTURE: ["future", "planning ahead", "not urgent", "someday"]
}

PREFERENCE_KEYWORDS = {
    Preference.CHEAPEST: ["cheapest", "affordable", "budget", "low cost", "inexpensive", "cheap"],
    Preference.NEAREST: ["nearest", "close", "nearby", "closest", "convenient", "near"]
}