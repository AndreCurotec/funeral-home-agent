from typing import Dict, Optional
import uuid
from datetime import datetime, timedelta
from models import ConversationSession, ConversationState, UserRequirements
import os

class SessionStore:
    """In-memory session store for conversation state management"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
        self.cleanup_interval = timedelta(hours=24)  # Clean up sessions after 24 hours
        self.test_phone = os.getenv("TEST_PHONE_NUMBER", "+16197302760")
    
    def create_session(self, session_id: Optional[str] = None) -> ConversationSession:
        """Create a new conversation session"""
        if not session_id:
            session_id = f"session_{uuid.uuid4().hex}"
        
        session = ConversationSession(
            session_id=session_id,
            user_phone=self.test_phone,  # Using test phone number for development
            state=ConversationState.COLLECTING_INFO,
            requirements=UserRequirements()
        )
        
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get existing session by ID"""
        return self.sessions.get(session_id)
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> ConversationSession:
        """Get existing session or create new one"""
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            # Update last activity
            session.updated_at = datetime.now()
            return session
        else:
            return self.create_session(session_id)
    
    def update_session(self, session: ConversationSession):
        """Update session in store"""
        session.updated_at = datetime.now()
        self.sessions[session.session_id] = session
    
    def delete_session(self, session_id: str):
        """Delete session from store"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def cleanup_old_sessions(self):
        """Remove sessions older than cleanup_interval"""
        cutoff_time = datetime.now() - self.cleanup_interval
        to_delete = [
            session_id for session_id, session in self.sessions.items()
            if session.updated_at < cutoff_time
        ]
        
        for session_id in to_delete:
            del self.sessions[session_id]
        
        return len(to_delete)
    
    def get_session_count(self) -> int:
        """Get total number of active sessions"""
        return len(self.sessions)
    
    def list_sessions(self) -> Dict[str, dict]:
        """List all sessions with basic info (for debugging)"""
        return {
            session_id: {
                "state": session.state,
                "has_complete_info": session.requirements.is_complete(),
                "shown_homes_count": len(session.shown_funeral_homes),
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            }
            for session_id, session in self.sessions.items()
        }

# Global session store instance
session_store = SessionStore()