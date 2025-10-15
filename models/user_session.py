from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Conversation states
NORMAL_STATE = "normal"
PLANNING_STATE = "planning"
EXECUTING_STATE = "executing"

class UserSession:
    """Class to manage user session data"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.conversation_history: List[Dict] = []
        self.waiting_for_followup = False
        self.state = NORMAL_STATE
        self.current_plan: Optional[Dict] = None
        self.current_step = 0
        self.plan_results: List[Dict] = []
    
    def add_message_to_history(self, role: str, text: str):
        """Add a message to conversation history"""
        self.conversation_history.append({"role": role, "text": text})
        
        # Keep history manageable
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-6:]
    
    def reset_plan(self):
        """Reset plan-related data"""
        self.state = NORMAL_STATE
        self.current_plan = None
        self.current_step = 0
        self.plan_results = []
    
    def reset_all(self):
        """Reset all session data"""
        self.conversation_history = []
        self.waiting_for_followup = False
        self.reset_plan()

class SessionManager:
    """Manager for user sessions"""
    
    def __init__(self):
        self.sessions: Dict[int, UserSession] = {}
    
    def get_session(self, user_id: int) -> UserSession:
        """Get or create user session"""
        if user_id not in self.sessions:
            self.sessions[user_id] = UserSession(user_id)
        return self.sessions[user_id]
    
    def get_session_count(self) -> int:
        """Get total number of active sessions"""
        return len(self.sessions)