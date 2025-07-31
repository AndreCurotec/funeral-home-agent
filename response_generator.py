from typing import Dict, List
from models import (
    ConversationSession, ConversationState, UserRequirements,
    SERVICE_TYPE_DISPLAY, TIMEFRAME_DISPLAY
)

class ResponseGenerator:
    """Generates contextual and intelligent responses based on conversation state"""
    
    def __init__(self):
        self.location_examples = [
            "Austin, TX", "Miami, FL", "New York, NY", "Los Angeles, CA", 
            "Chicago, IL", "Dallas, TX", "Phoenix, AZ", "Philadelphia, PA"
        ]
    
    def generate_collection_response(self, session: ConversationSession, extraction_metadata: Dict = None) -> str:
        """Generate response during information collection phase"""
        requirements = session.requirements
        missing = requirements.missing_fields()
        metadata = extraction_metadata or {}
        
        # Handle validation issues - check both possible keys
        validation_issues = metadata.get("validation_issues") or metadata.get("_validation_issues")
        if validation_issues:
            # Filter out empty/NOT_SET related issues
            real_issues = [issue for issue in validation_issues if "NOT_SET" not in issue and "none" not in issue.lower()]
            if real_issues:
                return self._handle_validation_issues(requirements, real_issues)
        
        # All information collected
        if not missing:
            session.state = ConversationState.SHOWING_RESULTS
            return self._generate_completion_response(requirements)
        
        # Generate specific prompts for missing information
        if "location" in missing:
            return self._prompt_for_location(requirements)
        elif "service_type" in missing:
            return self._prompt_for_service_type(requirements)
        elif "timeframe" in missing:
            return self._prompt_for_timeframe(requirements)
        elif "preference" in missing:
            return self._prompt_for_preference(requirements)
        
        return "I need a bit more information. Could you please provide more details about your funeral home needs?"
    
    def generate_results_response(self, session: ConversationSession, user_message: str) -> str:
        """Generate response when showing results or asking for satisfaction"""
        user_message_lower = user_message.lower()
        
        # Check if user wants to see more options (without changing preferences)
        more_options_keywords = ["more options", "show more", "see more", "other options", "more choices", "additional", "what else"]
        if any(keyword in user_message_lower for keyword in more_options_keywords):
            return self._generate_more_options_response(session)
        
        # Check if user wants to adjust preferences (changing criteria)
        adjustment_keywords = ["different", "change", "adjust", "modify", "not satisfied", "no", "not really", "try something else"]
        if any(keyword in user_message_lower for keyword in adjustment_keywords):
            session.state = ConversationState.ADJUSTING_PREFERENCES
            return self._generate_adjustment_prompt()
        
        # Check if user is satisfied
        satisfied_keywords = ["yes", "satisfied", "good", "great", "perfect", "thanks", "thank you", "looks good", "that works"]
        if any(keyword in user_message_lower for keyword in satisfied_keywords):
            session.state = ConversationState.COMPLETED
            return "Wonderful! I'm glad I could help you find suitable funeral home options. If you need any more assistance in the future, feel free to ask!"
        
        # Ask for clarification with clear options
        return """Are you satisfied with these funeral home options? You can:

• **"Yes, these look good"** - If you're happy with the options
• **"Show me more options"** - To see additional funeral homes with the same criteria  
• **"I want different options"** - To change your location, service type, or preferences

What would you prefer?"""
    
    def generate_adjustment_response(self, session: ConversationSession) -> str:
        """Generate response when user wants to adjust preferences"""
        session.state = ConversationState.COLLECTING_INFO
        current_info = self._format_current_info(session.requirements)
        
        return f"""I'd be happy to help you find different options! {current_info}

What would you like to change?
• **Location** - Different city or area
• **Service type** - Different type of service  
• **Timeframe** - Different timeline
• **Preference** - Switch between cheapest vs nearest

Just let me know what you'd like to adjust, and I'll find new recommendations for you."""
    
    def _generate_more_options_response(self, session: ConversationSession) -> str:
        """Generate response when user wants to see more options with same criteria"""
        current_info = self._format_current_info(session.requirements)
        
        # Check if we've shown funeral homes before
        shown_count = len(session.shown_funeral_homes)
        
        if shown_count >= 9:  # Reasonable limit
            return f"""I've already shown you {shown_count} funeral homes matching your criteria. {current_info}

I recommend either:
• **"These look good"** - If any of the previous options work for you
• **"I want different options"** - To change your location, service type, or preferences for fresh results

What would you prefer?"""
        
        return f"""Perfect! Let me find more funeral homes that match your criteria. {current_info}

I'll show you additional options that I haven't shown you yet..."""
    
    def _prompt_for_location(self, requirements: UserRequirements) -> str:
        """Generate location prompt"""
        examples = ", ".join(self.location_examples[:4])
        
        return f"""I'd be happy to help you find funeral homes! First, could you please tell me your location? 

You can provide:
• City and state (e.g., {examples})
• Just a city name (e.g., "Austin" or "Miami")
• Your zip code or neighborhood

Where are you located?"""
    
    def _prompt_for_service_type(self, requirements: UserRequirements) -> str:
        """Generate service type prompt with current info"""
        current_info = self._format_current_info(requirements)
        
        return f"""Great! {current_info}

Now, what type of service are you looking for?

🕊️ **Cremation Memorial** - Cremation with memorial service
⚰️ **Traditional Funeral** - Full funeral service with burial  
🏺 **Direct Burial** - Simple burial without ceremony
🔥 **Direct Cremation** - Simple cremation without ceremony

Which option interests you, or would you like me to explain any of these in more detail?"""
    
    def _prompt_for_timeframe(self, requirements: UserRequirements) -> str:
        """Generate timeframe prompt with current info"""
        current_info = self._format_current_info(requirements)
        
        return f"""Thank you! {current_info}

When do you need these services?

⚡ **Immediately** - Right away or within days (urgent situation)
📅 **Within the next 4 weeks** - Soon but not urgent
🗓️ **Likely within 6 months** - Planning ahead for this year
🔮 **Planning for the future** - Just exploring options for future planning

What timeframe works for your situation?"""
    
    def _prompt_for_preference(self, requirements: UserRequirements) -> str:
        """Generate preference prompt with current info"""
        current_info = self._format_current_info(requirements)
        
        return f"""Perfect! {current_info}

Finally, what's most important to you when choosing a funeral home?

💰 **Cheapest options** - Focus on affordability and budget-friendly choices
📍 **Nearest locations** - Focus on convenience and proximity to you

Which would you prefer, or is there a balance of both you're looking for?"""
    
    def _generate_completion_response(self, requirements: UserRequirements) -> str:
        """Generate response when all information is collected"""
        current_info = self._format_current_info(requirements, show_emoji=True)
        
        return f"""Perfect! I have all the information I need. Here's what I'm searching for:

{current_info}

Let me find the best funeral homes that match your criteria..."""
    
    def _generate_adjustment_prompt(self) -> str:
        """Generate prompt for adjusting preferences"""
        return """I understand you'd like to see different options. What would you like to change?

You can modify any of these:
• **Location** - Different city or area
• **Service type** - Different type of service
• **Timeframe** - Different timeline  
• **Preference** - Switch between cheapest vs nearest

Or you can give me completely new requirements. What would you like to adjust?"""
    
    def _handle_validation_issues(self, requirements: UserRequirements, issues: List[str]) -> str:
        """Handle validation issues in user input"""
        current_info = self._format_current_info(requirements)
        
        issue_text = ". ".join(issues)
        
        return f"""I had trouble understanding part of your request: {issue_text}

{current_info}

Could you please clarify or rephrase your request? I'm here to help!"""
    
    def _format_current_info(self, requirements: UserRequirements, show_emoji: bool = True) -> str:
        """Format currently collected information for display"""
        info_parts = []
        
        if requirements.location:
            emoji = "📍 " if show_emoji else ""
            info_parts.append(f"{emoji}**Location:** {requirements.location}")
        
        if requirements.service_type:
            emoji = "⚱️ " if show_emoji else ""
            info_parts.append(f"{emoji}**Service:** {SERVICE_TYPE_DISPLAY[requirements.service_type]}")
        
        if requirements.timeframe:
            emoji = "⏰ " if show_emoji else ""
            info_parts.append(f"{emoji}**Timeframe:** {TIMEFRAME_DISPLAY[requirements.timeframe]}")
        
        if requirements.preference:
            emoji = "💰 " if show_emoji else ""
            pref_display = "Cheapest options" if requirements.preference.value == "cheapest" else "Nearest locations"
            info_parts.append(f"{emoji}**Preference:** {pref_display}")
        
        if info_parts:
            return "Here's what I have so far:\n\n" + "\n".join(info_parts)
        
        return ""
    
    def generate_error_response(self, error_type: str = "general") -> str:
        """Generate appropriate error responses"""
        error_responses = {
            "general": "I apologize, but I encountered an issue processing your request. Could you please try again?",
            "extraction": "I had trouble understanding your message. Could you please rephrase your request?",
            "validation": "Some of the information provided doesn't seem to be in the right format. Could you please clarify?",
            "timeout": "It seems like our conversation has been inactive for a while. Feel free to start fresh with your funeral home needs."
        }
        
        return error_responses.get(error_type, error_responses["general"])
    
    def generate_welcome_message(self) -> str:
        """Generate initial welcome message"""
        return """Hello, I'm here to help you find the perfect funeral home for your needs.

To provide you with the best recommendations, I'll need to gather some information:

📍 **Your location** - So I can find nearby options
⚱️ **Type of service** - What kind of service you're looking for  
⏰ **Timeframe** - When you need these services
💰 **Your preference** - Whether you prioritize cost or convenience

You can provide all this information at once, or we can go step by step. How would you like to get started?"""
    
    def generate_help_message(self) -> str:
        """Generate help message for confused users"""
        return """I'm here to help you find funeral homes! I can assist you with:

✅ **Finding funeral homes** in your area
✅ **Comparing options** based on your preferences  
✅ **Different service types** (cremation, burial, etc.)
✅ **Budget and location** considerations

Just tell me what you're looking for, like:
• "I need funeral homes in Austin, Texas"
• "Looking for affordable cremation services"  
• "Need immediate funeral arrangements in Miami"

What can I help you with today?"""
    
    def generate_no_results_message(self, requirements: UserRequirements) -> str:
        """Generate message when no funeral homes are found"""
        current_info = self._format_current_info(requirements, show_emoji=True)
        
        # Suggest alternative locations with known data
        suggested_locations = [
            "Houston, TX", "Dallas, TX", "San Antonio, TX",
            "Miami, FL", "Los Angeles, CA", "Chicago, IL",
            "Philadelphia, PA", "New York, NY"
        ]
        
        suggestions = ", ".join(suggested_locations[:4])
        
        return f"""I'm sorry, but I couldn't find any funeral homes matching your criteria:

{current_info}

This might be because:
• **Limited coverage** - Our database may not have funeral homes in this specific area
• **Service availability** - The requested service type might not be available locally

**Suggestions:**
• Try a **nearby major city** like {suggestions}
• **Modify your location** to include surrounding areas
• **Change your service type** to see if other options are available

Would you like to try a different location or modify your search criteria?"""