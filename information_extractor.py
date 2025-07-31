import json
import re
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from models import (
    UserRequirements, ServiceType, Timeframe, Preference,
    SERVICE_TYPE_KEYWORDS, TIMEFRAME_KEYWORDS, PREFERENCE_KEYWORDS
)

class InformationExtractor:
    """Enhanced information extraction using OpenAI with validation and context awareness"""
    
    def __init__(self, openai_client: OpenAI):
        self.openai_client = openai_client
        self.us_states = {
            'texas', 'tx', 'california', 'ca', 'florida', 'fl', 'new york', 'ny',
            'illinois', 'il', 'pennsylvania', 'pa', 'ohio', 'oh', 'georgia', 'ga',
            'north carolina', 'nc', 'michigan', 'mi', 'new jersey', 'nj', 'virginia', 'va',
            'washington', 'wa', 'arizona', 'az', 'massachusetts', 'ma', 'tennessee', 'tn',
            'indiana', 'in', 'maryland', 'md', 'missouri', 'mo', 'wisconsin', 'wi',
            'colorado', 'co', 'minnesota', 'mn', 'south carolina', 'sc', 'alabama', 'al'
        }
    
    def extract_comprehensive_info(self, user_message: str, current_requirements: UserRequirements, conversation_context: List[str] = None) -> Tuple[UserRequirements, Dict[str, any]]:
        """
        Extract all possible information from user message with context awareness
        Returns: (updated_requirements, extraction_metadata)
        """
        
        # Build context for OpenAI
        context_messages = []
        if conversation_context:
            context_messages = conversation_context[-3:]  # Last 3 messages for context
        
        # Try OpenAI extraction first
        try:
            extracted_data, confidence = self._openai_extraction(user_message, current_requirements, context_messages)
            
            # Validate extracted data
            validated_data = self._validate_extracted_data(extracted_data)
            
            # Update requirements with validated data
            updated_requirements = self._update_requirements(current_requirements, validated_data)
            
            # Prepare metadata for response generation
            metadata = {
                "extraction_method": "openai",
                "confidence": confidence,
                "extracted_fields": list(validated_data.keys()),
                "validation_issues": validated_data.get("_validation_issues", []),
                "ambiguous_fields": validated_data.get("_ambiguous_fields", [])
            }
            
            return updated_requirements, metadata
            
        except Exception as e:
            print(f"OpenAI extraction failed: {e}")
            # Fallback to keyword extraction
            return self._fallback_keyword_extraction(user_message, current_requirements)
    
    def detect_preference_adjustment_intent(self, user_message: str, current_requirements: UserRequirements) -> dict:
        """
        Detect if user wants to adjust specific preferences and what they want to change
        Returns dict with change intent details
        """
        try:
            system_prompt = f"""You are analyzing a user message to detect preference adjustment intent for a funeral home search.

CURRENT USER REQUIREMENTS:
- Location: {current_requirements.location or "Not set"}
- Service Type: {current_requirements.service_type.value if current_requirements.service_type else "Not set"}  
- Timeframe: {current_requirements.timeframe.value if current_requirements.timeframe else "Not set"}
- Preference: {current_requirements.preference.value if current_requirements.preference else "Not set"}

TASK: Analyze if the user wants to change any of their current preferences and identify what specifically they want to change.

RETURN JSON FORMAT:
{{
    "intent_type": "none|partial|complete",
    "fields_to_change": ["location", "service_type", "timeframe", "preference"],
    "keep_existing": true|false,
    "confidence": 0.0-1.0,
    "reason": "explanation of detected intent"
}}

INTENT TYPES:
- "none": No preference changes detected
- "partial": User wants to change specific fields while keeping others
- "complete": User wants to start over completely

EXAMPLES:
"Change location to Miami" → {{"intent_type": "partial", "fields_to_change": ["location"], "keep_existing": true}}
"I want cheapest instead" → {{"intent_type": "partial", "fields_to_change": ["preference"], "keep_existing": true}}
"Start over completely" → {{"intent_type": "complete", "fields_to_change": [], "keep_existing": false}}
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this message: '{user_message}'"}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            
        except Exception as e:
            print(f"Preference adjustment detection failed: {e}")
        
        # Fallback to keyword-based detection
        return self._fallback_preference_detection(user_message)
    
    def _fallback_preference_detection(self, user_message: str) -> dict:
        """Fallback preference adjustment detection using keywords"""
        user_lower = user_message.lower()
        
        # Default result
        result = {
            "intent_type": "none",
            "fields_to_change": [],
            "keep_existing": True,
            "confidence": 0.6,
            "reason": "Keyword-based detection"
        }
        
        # Check for complete reset
        reset_phrases = ["start over", "completely different", "all different", "reset", "new search"]
        if any(phrase in user_lower for phrase in reset_phrases):
            result.update({
                "intent_type": "complete",
                "keep_existing": False,
                "reason": "Complete reset requested"
            })
            return result
        
        # Check for specific field changes
        field_keywords = {
            "location": ["location", "city", "place", "area", "move to", "change location", "different city"],
            "service_type": ["service", "cremation", "burial", "funeral", "different service", "change service"],
            "timeframe": ["timeframe", "timeline", "when", "time", "urgency", "immediately", "later", "change time"],
            "preference": ["preference", "cheapest", "nearest", "budget", "price", "cost", "distance", "affordable"]
        }
        
        fields_mentioned = []
        for field, keywords in field_keywords.items():
            if any(keyword in user_lower for keyword in keywords):
                fields_mentioned.append(field)
        
        if fields_mentioned:
            result.update({
                "intent_type": "partial",
                "fields_to_change": fields_mentioned,
                "reason": f"Detected changes for: {', '.join(fields_mentioned)}"
            })
        
        return result
    
    def _openai_extraction(self, user_message: str, current_requirements: UserRequirements, context_messages: List[str]) -> Tuple[Dict, float]:
        """Enhanced OpenAI extraction with context awareness"""
        
        # Build conversation context
        context_str = ""
        if context_messages:
            context_str = "\n".join([f"- {msg}" for msg in context_messages])
        
        system_prompt = f"""
You are an expert at extracting funeral home service requirements from natural language.

CURRENT INFORMATION ALREADY COLLECTED:
- Location: {current_requirements.location or "NOT SET"}
- Service Type: {current_requirements.service_type.value if current_requirements.service_type else "NOT SET"}
- Timeframe: {current_requirements.timeframe.value if current_requirements.timeframe else "NOT SET"}
- Preference: {current_requirements.preference.value if current_requirements.preference else "NOT SET"}

RECENT CONVERSATION CONTEXT:
{context_str}

EXTRACTION RULES:
1. Location: Extract city, state, or full address. Examples: "Austin TX", "Miami Florida", "New York", "Los Angeles, California"
2. Service Type: Must be exactly one of:
   - "cremation_memorial" (cremation with memorial service)
   - "traditional_funeral" (full funeral service with burial)
   - "direct_burial" (simple burial without ceremony)  
   - "direct_cremation" (simple cremation without ceremony)
3. Timeframe: Must be exactly one of:
   - "immediately" (urgent, ASAP, right away)
   - "within_next_four_weeks" (soon, within a month)
   - "likely_within_six_months" (planning ahead, this year)
   - "planning_for_the_future" (just exploring, not urgent)
4. Preference: Must be exactly one of:
   - "cheapest" (budget-focused, affordable, low cost)
   - "nearest" (location-focused, convenient, close by)

SPECIAL INSTRUCTIONS:
- If user is correcting previous information, extract the correction
- If multiple values are mentioned for same field, pick the most recent/emphasized one
- Mark ambiguous extractions with confidence score
- Don't extract if information is unclear or contradictory
- ONLY extract fields that are clearly mentioned by the user
- Do NOT include fields with "NOT_SET", "null", or empty values
- If a field is not mentioned, simply omit it from the response

Return JSON with ONLY the fields that are clearly provided:
{{"location": "Austin TX", "confidence": 0.9, "notes": "user provided location only"}}
"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Using newer model for better extraction
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract requirements from: '{user_message}'"}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group())
                confidence = extracted_data.pop("confidence", 0.8)
                extracted_data.pop("notes", "")  # Remove notes but don't store
                
                return extracted_data, confidence
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"OpenAI API error: {e}")
            raise
        
        return {}, 0.0
    
    def _validate_extracted_data(self, extracted_data: Dict) -> Dict:
        """Validate and clean extracted data"""
        validated = {}
        validation_issues = []
        ambiguous_fields = []
        
        # Validate location
        if "location" in extracted_data:
            location = extracted_data["location"].strip()
            if self._is_valid_location(location):
                validated["location"] = self._normalize_location(location)
            else:
                validation_issues.append(f"Invalid location format: {location}")
        
        # Validate service type - only if provided and not empty/None/NOT_SET
        if "service_type" in extracted_data and extracted_data["service_type"]:
            service_type = extracted_data["service_type"]
            if service_type.upper() not in ["NOT_SET", "NONE", "NULL", ""]:
                try:
                    ServiceType(service_type)
                    validated["service_type"] = service_type
                except ValueError:
                    validation_issues.append(f"Invalid service type: {service_type}")
        
        # Validate timeframe - only if provided and not empty/None/NOT_SET
        if "timeframe" in extracted_data and extracted_data["timeframe"]:
            timeframe = extracted_data["timeframe"]
            if timeframe.upper() not in ["NOT_SET", "NONE", "NULL", ""]:
                try:
                    Timeframe(timeframe)
                    validated["timeframe"] = timeframe
                except ValueError:
                    validation_issues.append(f"Invalid timeframe: {timeframe}")
        
        # Validate preference - only if provided and not empty/None/NOT_SET
        if "preference" in extracted_data and extracted_data["preference"]:
            preference = extracted_data["preference"]
            if preference.upper() not in ["NOT_SET", "NONE", "NULL", ""]:
                try:
                    Preference(preference)
                    validated["preference"] = preference
                except ValueError:
                    validation_issues.append(f"Invalid preference: {preference}")
        
        # Add metadata
        if validation_issues:
            validated["_validation_issues"] = validation_issues
        if ambiguous_fields:
            validated["_ambiguous_fields"] = ambiguous_fields
        
        return validated
    
    def _is_valid_location(self, location: str) -> bool:
        """Check if location format seems valid"""
        location_lower = location.lower().strip()
        
        # Check if it contains at least a city name (2+ characters)
        if len(location_lower) < 2:
            return False
        
        # Exclude common non-location phrases
        non_location_phrases = [
            "show me more", "more options", "see more", "other options", 
            "different", "change", "adjust", "help", "what can you",
            "hello", "hi", "thanks", "thank you", "yes", "no",
            "i want", "i need", "looking for", "cremation", "burial",
            "funeral", "immediately", "asap", "cheapest", "nearest",
            "budget", "affordable", "convenient"
        ]
        
        if any(phrase in location_lower for phrase in non_location_phrases):
            return False
        
        # Check if it contains state information or common city patterns
        has_state = any(state in location_lower for state in self.us_states)
        has_comma = ',' in location
        has_multiple_words = len(location.split()) >= 2
        
        # Must have state, comma, or be a recognizable city pattern
        return has_state or has_comma or has_multiple_words
    
    def _normalize_location(self, location: str) -> str:
        """Normalize location format"""
        location = location.strip()
        
        # Common normalizations
        normalizations = {
            'austin texas': 'Austin, TX',
            'austin tx': 'Austin, TX',
            'miami florida': 'Miami, FL', 
            'miami fl': 'Miami, FL',
            'new york': 'New York, NY',
            'los angeles': 'Los Angeles, CA',
            'chicago illinois': 'Chicago, IL',
            'chicago il': 'Chicago, IL'
        }
        
        location_lower = location.lower()
        if location_lower in normalizations:
            return normalizations[location_lower]
        
        return location.title()  # Basic title case
    
    def _update_requirements(self, current: UserRequirements, validated_data: Dict) -> UserRequirements:
        """Update requirements with validated extracted data"""
        updated = current.model_copy()
        
        if "location" in validated_data:
            updated.location = validated_data["location"]
        
        if "service_type" in validated_data:
            updated.service_type = ServiceType(validated_data["service_type"])
        
        if "timeframe" in validated_data:
            updated.timeframe = Timeframe(validated_data["timeframe"])
        
        if "preference" in validated_data:
            updated.preference = Preference(validated_data["preference"])
        
        return updated
    
    def _fallback_keyword_extraction(self, user_message: str, current_requirements: UserRequirements) -> Tuple[UserRequirements, Dict]:
        """Fallback extraction using keyword matching"""
        updated_requirements = current_requirements.model_copy()
        extracted_fields = []
        
        user_message_lower = user_message.lower()
        
        # Extract location (improved patterns)
        if not updated_requirements.location:
            location_patterns = [
                r'(?:in|at|near|from|live in|located in)\s+([a-zA-Z][a-zA-Z\s,.-]+?)(?:\s|$|[,.])',
                r'^([a-zA-Z][a-zA-Z\s,.-]+?)\s*(?:area|region)?\s*$',
                r'([a-zA-Z]+\s*,\s*[a-zA-Z]{2,})',
                r'([a-zA-Z]{3,}\s+(?:texas|tx|california|ca|florida|fl|new york|ny))\b'
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, user_message, re.IGNORECASE)
                if match:
                    location = match.group(1).strip()
                    if self._is_valid_location(location):
                        updated_requirements.location = self._normalize_location(location)
                        extracted_fields.append("location")
                        break
        
        # Extract service type
        if not updated_requirements.service_type:
            for service_type, keywords in SERVICE_TYPE_KEYWORDS.items():
                if any(keyword in user_message_lower for keyword in keywords):
                    updated_requirements.service_type = service_type
                    extracted_fields.append("service_type")
                    break
        
        # Extract timeframe
        if not updated_requirements.timeframe:
            for timeframe, keywords in TIMEFRAME_KEYWORDS.items():
                if any(keyword in user_message_lower for keyword in keywords):
                    updated_requirements.timeframe = timeframe
                    extracted_fields.append("timeframe")
                    break
        
        # Extract preference
        if not updated_requirements.preference:
            for preference, keywords in PREFERENCE_KEYWORDS.items():
                if any(keyword in user_message_lower for keyword in keywords):
                    updated_requirements.preference = preference
                    extracted_fields.append("preference")
                    break
        
        metadata = {
            "extraction_method": "keyword_fallback",
            "confidence": 0.6,
            "extracted_fields": extracted_fields,
            "validation_issues": [],
            "ambiguous_fields": []
        }
        
        return updated_requirements, metadata
    
    def detect_correction_intent(self, user_message: str) -> Optional[str]:
        """Detect if user is trying to correct previously provided information"""
        correction_patterns = [
            r'(?:actually|wait|no|sorry|i meant|let me correct|change that to|instead of)',
            r'(?:not|it\'s not|that\'s wrong|that\'s incorrect)',
            r'(?:i said|i want|i need) (.+?) (?:not|instead)'
        ]
        
        for pattern in correction_patterns:
            if re.search(pattern, user_message.lower()):
                return "correction_detected"
        
        return None
    
    def extract_multiple_fields(self, user_message: str) -> Dict[str, str]:
        """Extract multiple fields from a single comprehensive message"""
        # This handles cases like "I'm in Austin Texas, need cremation, ASAP, cheapest option"
        
        fields = {}
        
        # Location extraction
        location_match = re.search(r'(?:in|at|from)\s+([^,]+(?:,\s*[A-Z]{2})?)', user_message, re.IGNORECASE)
        if location_match:
            fields["location"] = location_match.group(1).strip()
        
        # Service type extraction
        for service_type, keywords in SERVICE_TYPE_KEYWORDS.items():
            if any(keyword in user_message.lower() for keyword in keywords):
                fields["service_type"] = service_type.value
                break
        
        # Timeframe extraction
        for timeframe, keywords in TIMEFRAME_KEYWORDS.items():
            if any(keyword in user_message.lower() for keyword in keywords):
                fields["timeframe"] = timeframe.value
                break
        
        # Preference extraction
        for preference, keywords in PREFERENCE_KEYWORDS.items():
            if any(keyword in user_message.lower() for keyword in keywords):
                fields["preference"] = preference.value
                break
        
        return fields