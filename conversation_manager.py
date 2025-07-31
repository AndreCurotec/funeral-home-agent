from openai import OpenAI
from models import (
    ConversationSession, ConversationState, UserRequirements
)
from information_extractor import InformationExtractor
from response_generator import ResponseGenerator
from funeral_home_service import FuneralHomeService

class ConversationManager:
    """Enhanced conversation manager with intelligent extraction and contextual responses"""
    
    def __init__(self, openai_client: OpenAI):
        self.openai_client = openai_client
        self.extractor = InformationExtractor(openai_client)
        self.response_generator = ResponseGenerator()
        self.funeral_home_service = FuneralHomeService()
    
    def extract_user_info(self, user_message: str, current_requirements: UserRequirements, conversation_history: list = None) -> tuple[UserRequirements, dict]:
        """
        Extract user information with enhanced context awareness
        Returns: (updated_requirements, extraction_metadata)
        """
        
        # Handle special cases
        if self._is_help_request(user_message):
            return current_requirements, {"special_response": "help"}
        
        if self._is_greeting(user_message) and not any([current_requirements.location, current_requirements.service_type]):
            return current_requirements, {"special_response": "welcome"}
        
        # Check if this is a "show more options" request (should not extract any info)
        user_message_lower = user_message.lower()
        more_options_keywords = ["more options", "show more", "see more", "other options", "more choices", "additional", "what else"]
        if any(keyword in user_message_lower for keyword in more_options_keywords):
            return current_requirements, {"special_response": "show_more"}
        
        # Check for preference adjustment intent (only if user already has some requirements)
        has_existing_requirements = any([
            current_requirements.location, 
            current_requirements.service_type, 
            current_requirements.timeframe, 
            current_requirements.preference
        ])
        
        if has_existing_requirements:
            adjustment_intent = self.extractor.detect_preference_adjustment_intent(user_message, current_requirements)
            if adjustment_intent["intent_type"] != "none":
                return current_requirements, {
                    "special_response": "preference_adjustment", 
                    "adjustment_intent": adjustment_intent
                }
        
        # Detect correction intent
        correction_detected = self.extractor.detect_correction_intent(user_message)
        if correction_detected:
            # Reset relevant fields for corrections
            current_requirements = self._handle_correction(current_requirements)
        
        # Build conversation context for better extraction
        context_messages = []
        if conversation_history:
            context_messages = [msg["content"] for msg in conversation_history[-6:] if msg["role"] == "user"]
        
        # Extract information with enhanced logic
        updated_requirements, metadata = self.extractor.extract_comprehensive_info(
            user_message, 
            current_requirements, 
            context_messages
        )
        
        return updated_requirements, metadata
    
    def _is_help_request(self, message: str) -> bool:
        """Detect help requests"""
        help_keywords = ["help", "what can you do", "how does this work", "what do you need", "confused"]
        return any(keyword in message.lower() for keyword in help_keywords)
    
    def _is_greeting(self, message: str) -> bool:
        """Detect greeting messages"""
        greeting_keywords = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
        return any(keyword in message.lower() for keyword in greeting_keywords)
    
    def _handle_correction(self, current_requirements: UserRequirements) -> UserRequirements:
        """Handle correction intent by resetting relevant fields"""
        # For now, let the extraction logic handle it naturally
        # In future versions, we could be more sophisticated about which fields to reset
        return current_requirements
    
    def generate_response(self, session: ConversationSession, user_message: str, extraction_metadata: dict = None) -> str:
        """Generate appropriate response based on conversation state and extracted information"""
        
        # Handle special responses
        if extraction_metadata and "special_response" in extraction_metadata:
            special_type = extraction_metadata["special_response"]
            if special_type == "help":
                return self.response_generator.generate_help_message()
            elif special_type == "welcome":
                return self.response_generator.generate_welcome_message()
            elif special_type == "show_more":
                # For show more requests, keep state as showing_results but don't return early
                # Let the flow continue to fetch funeral homes
                if session.state == ConversationState.SHOWING_RESULTS:
                    # Generate the response but don't return yet - let it continue to fetch homes
                    pass
                else:
                    # If not in showing results state, treat as regular flow
                    pass
            elif special_type == "preference_adjustment":
                # Handle intelligent preference adjustment
                adjustment_intent = extraction_metadata.get("adjustment_intent", {})
                return self._handle_preference_adjustment(session, user_message, adjustment_intent)
        
        # Route to appropriate response generator based on conversation state
        if session.state == ConversationState.COLLECTING_INFO:
            return self.response_generator.generate_collection_response(session, extraction_metadata)
        elif session.state == ConversationState.SHOWING_RESULTS:
            # Check if this is a show_more request
            if extraction_metadata and extraction_metadata.get("special_response") == "show_more":
                return self.response_generator._generate_more_options_response(session)
            else:
                return self.response_generator.generate_results_response(session, user_message)
        elif session.state == ConversationState.ADJUSTING_PREFERENCES:
            return self.response_generator.generate_adjustment_response(session)
        else:
            return "Thank you for using our funeral home finder service!"
    
    async def get_funeral_homes_if_ready(self, session: ConversationSession, user_message: str = "") -> list:
        """
        Get funeral home recommendations if all requirements are complete
        Returns empty list if not ready or if there's an error
        """
        if not session.requirements.is_complete():
            return []
        
        if session.state != ConversationState.SHOWING_RESULTS:
            return []
        
        # Check if user is asking for more options
        user_message_lower = user_message.lower()
        more_options_keywords = ["more options", "show more", "see more", "other options", "more choices", "additional", "what else"]
        is_more_request = any(keyword in user_message_lower for keyword in more_options_keywords)
        
        try:
            if is_more_request:
                # Get more recommendations without changing preferences
                funeral_homes = await self.funeral_home_service.get_more_recommendations(session)
            else:
                # Initial recommendations or after preference change
                funeral_homes = await self.funeral_home_service.get_recommendations(session)
            
            return [fh.model_dump() for fh in funeral_homes]
        except Exception as e:
            print(f"Error getting funeral homes: {e}")
            return []
    
    def should_reset_search(self, old_requirements: UserRequirements, new_requirements: UserRequirements) -> bool:
        """Determine if funeral home search should be reset due to significant changes"""
        # Reset if location or service type changed
        if (old_requirements.location != new_requirements.location or 
            old_requirements.service_type != new_requirements.service_type):
            return True
        
        # Reset if preference changed (cheapest vs nearest)
        if old_requirements.preference != new_requirements.preference:
            return True
        
        return False
    
    def _handle_preference_adjustment(self, session: ConversationSession, user_message: str, adjustment_intent: dict) -> str:
        """
        Handle intelligent preference adjustment based on detected intent
        """
        intent_type = adjustment_intent.get("intent_type", "none")
        fields_to_change = adjustment_intent.get("fields_to_change", [])
        
        if intent_type == "complete":
            # Complete reset - clear everything and start over
            session.requirements = UserRequirements()
            session.reset_funeral_home_search()
            session.state = ConversationState.COLLECTING_INFO
            
            return """I understand you'd like to start completely fresh! Let me help you find new funeral homes.

I'll need to collect your requirements again:
• **📍 Location** - Which city or area?
• **⚱️ Service Type** - What type of service do you need?
• **⏰ Timeframe** - When do you need this?
• **💰 Preference** - Do you prefer the cheapest or nearest options?

What's your location?"""

        elif intent_type == "partial":
            # Partial adjustment - smart handling of specific field changes
            return self._handle_partial_adjustment(session, user_message, fields_to_change)
        
        else:
            # Fallback to general adjustment response
            session.state = ConversationState.ADJUSTING_PREFERENCES
            return self.response_generator.generate_adjustment_response(session)
    
    def _handle_partial_adjustment(self, session: ConversationSession, user_message: str, fields_to_change: list) -> str:
        """
        Handle partial preference adjustments by extracting new values for specific fields
        """
        # Extract new information for the changed fields
        updated_requirements, _ = self.extractor.extract_comprehensive_info(
            user_message, 
            session.requirements, 
            session.conversation_history
        )
        
        # Only update the fields the user wants to change
        changes_made = []
        old_requirements = session.requirements.model_copy()
        
        for field in fields_to_change:
            if field == "location" and updated_requirements.location and updated_requirements.location != session.requirements.location:
                session.requirements.location = updated_requirements.location
                changes_made.append(f"📍 Location → {updated_requirements.location}")
            
            elif field == "service_type" and updated_requirements.service_type and updated_requirements.service_type != session.requirements.service_type:
                session.requirements.service_type = updated_requirements.service_type
                changes_made.append(f"⚱️ Service → {updated_requirements.service_type.value.replace('_', ' ')}")
            
            elif field == "timeframe" and updated_requirements.timeframe and updated_requirements.timeframe != session.requirements.timeframe:
                session.requirements.timeframe = updated_requirements.timeframe
                changes_made.append(f"⏰ Timeframe → {updated_requirements.timeframe.value.replace('_', ' ')}")
            
            elif field == "preference" and updated_requirements.preference and updated_requirements.preference != session.requirements.preference:
                session.requirements.preference = updated_requirements.preference
                changes_made.append(f"💰 Preference → {updated_requirements.preference.value}")
        
        # Check if we should reset the search based on significant changes
        if self.should_reset_search(old_requirements, session.requirements):
            session.reset_funeral_home_search()
        
        # Generate appropriate response
        if changes_made:
            session.state = ConversationState.SHOWING_RESULTS if session.requirements.is_complete() else ConversationState.COLLECTING_INFO
            
            changes_text = "\n".join([f"• {change}" for change in changes_made])
            current_info = self.response_generator._format_current_info(session.requirements)
            
            if session.requirements.is_complete():
                return f"""Perfect! I've updated your preferences:

{changes_text}

{current_info}

Let me find new funeral homes with your updated criteria. I'll show you 3 options that match your new preferences..."""
            else:
                missing = session.requirements.missing_fields()
                missing_text = ", ".join(missing).replace("_", " ")
                
                return f"""Great! I've updated:

{changes_text}

{current_info}

I still need: **{missing_text}**

Could you provide the missing information so I can find the perfect funeral homes for you?"""
        
        else:
            # No changes detected, ask for clarification
            session.state = ConversationState.ADJUSTING_PREFERENCES
            return f"""I'd like to help you adjust your preferences, but I'm not sure exactly what you'd like to change.

{self.response_generator._format_current_info(session.requirements)}

Could you be more specific? For example:
• "Change location to Miami"
• "I want traditional funeral instead"  
• "Switch to nearest options"
• "I need it immediately"

What would you like to adjust?"""