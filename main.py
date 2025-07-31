from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv
from openai import OpenAI
import uvicorn

# Import our conversation management modules
from session_store import session_store
from conversation_manager import ConversationManager

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Funeral Home Chatbot Agent",
    description="Multi-turn chatbot for finding the best funeral homes",
    version="1.0.0"
)

# CORS middleware for frontend integration
# Configure CORS for both local and production environments
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # "development" or "production"
FRONTEND_URL = os.getenv("FRONTEND_URL", "")  # Set this in production

if ENVIRONMENT == "production":
    # Production environment - specific origins
    cors_origins = []
    if FRONTEND_URL:
        cors_origins.append(FRONTEND_URL)
    # Always allow Netlify domains in production
    cors_origins.extend([
        "https://*.netlify.app",
        "https://netlify.app",
    ])
else:
    # Development environment - allow local origins
    cors_origins = [
        "http://localhost:8000",    # Local development
        "http://127.0.0.1:8000",    # Local development  
        "http://localhost:3000",    # Alternative local port
        "http://127.0.0.1:3000",    # Alternative local port
        "http://localhost:5173",    # Vite default port
        "http://127.0.0.1:5173",    # Vite default port
        "*"  # Allow all in development
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize conversation manager
conversation_manager = ConversationManager(openai_client)

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models for request/response
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    is_complete: bool = False
    funeral_homes: Optional[List[dict]] = None
    requirements_status: Optional[dict] = None

# Basic health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "funeral-home-chatbot"}

# Debug endpoint for session monitoring
@app.get("/debug/sessions")
async def debug_sessions():
    """
    Debug endpoint to view all active sessions
    """
    return {
        "total_sessions": session_store.get_session_count(),
        "sessions": session_store.list_sessions()
    }

# Cleanup endpoint
@app.post("/admin/cleanup")
async def cleanup_sessions():
    """
    Admin endpoint to cleanup old sessions
    """
    deleted_count = session_store.cleanup_old_sessions()
    return {
        "message": f"Cleaned up {deleted_count} old sessions",
        "remaining_sessions": session_store.get_session_count()
    }

# Main chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatMessage):
    """
    Main chat endpoint for the funeral home chatbot
    """
    try:
        # Get or create conversation session
        session = session_store.get_or_create_session(chat_message.session_id)
        
        # Store user message in conversation history
        session.add_message("user", chat_message.message)
        
        # Extract information from user message with conversation context
        old_requirements = session.requirements.model_copy()
        session.requirements, extraction_metadata = conversation_manager.extract_user_info(
            chat_message.message, 
            session.requirements,
            session.conversation_history
        )
        
        # Check if we need to reset funeral home search due to significant changes
        if conversation_manager.should_reset_search(old_requirements, session.requirements):
            session.reset_funeral_home_search()
        
        # Generate appropriate response with extraction metadata
        bot_response = conversation_manager.generate_response(
            session, 
            chat_message.message,
            extraction_metadata
        )
        
        # Store bot response in conversation history
        session.add_message("bot", bot_response)
        
        # Get funeral homes if all requirements are complete and state is showing results
        funeral_homes = []
        if session.requirements.is_complete() and session.state.value == "showing_results":
            funeral_homes = await conversation_manager.get_funeral_homes_if_ready(session, chat_message.message)
            
            # If no funeral homes found, update the response message
            if not funeral_homes and not any(keyword in chat_message.message.lower() for keyword in ["more options", "show more", "see more"]):
                bot_response = conversation_manager.response_generator.generate_no_results_message(session.requirements)
                session.add_message("bot", bot_response)  # Update conversation history
        
        # Update session in store
        session_store.update_session(session)
        
        # Prepare response
        response = ChatResponse(
            response=bot_response,
            session_id=session.session_id,
            is_complete=session.requirements.is_complete(),
            funeral_homes=funeral_homes if funeral_homes else None,
            requirements_status={
                "location": session.requirements.location,
                "service_type": session.requirements.service_type.value if session.requirements.service_type else None,
                "timeframe": session.requirements.timeframe.value if session.requirements.timeframe else None,
                "preference": session.requirements.preference.value if session.requirements.preference else None,
                "missing_fields": session.requirements.missing_fields(),
                "state": session.state.value,
                "shown_homes_count": len(session.shown_funeral_homes)
            }
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}") from e

# Serve the frontend
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """
    Serve the main HTML page
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Funeral Home Finder</title>
        <script>
            window.location.href = '/static/index.html';
        </script>
    </head>
    <body>
        <p>Redirecting to chat interface...</p>
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=False  # Set to False for production
    )