import os
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class UserWhitelist:
    """Class to manage user whitelist"""
    
    def __init__(self, allowed_users_str: str = ''):
        self.allowed_users = self._load_whitelist(allowed_users_str)
    
    def _load_whitelist(self, allowed_users_str: str) -> List[str]:
        """Load whitelist from environment variable"""
        if not allowed_users_str:
            logger.warning("No ALLOWED_USERS environment variable set. All users will be allowed.")
            return []
        
        # Parse comma-separated list of usernames
        users = [username.strip().lstrip('@') for username in allowed_users_str.split(',') if username.strip()]
        logger.info(f"Loaded {len(users)} allowed users: {', '.join(users)}")
        return users
    
    def is_user_allowed(self, username: Optional[str], user_id: int) -> bool:
        """
        Check if user is allowed to use the bot
        
        Args:
            username: Telegram username (without @)
            user_id: Telegram user ID
            
        Returns:
            bool: True if user is allowed, False otherwise
        """
        # If no whitelist is configured, allow all users
        if not self.allowed_users:
            return True
            
        # Check if username is in whitelist
        if username and username in self.allowed_users:
            return True
            
        # Log unauthorized access attempt
        logger.warning(f"Unauthorized access attempt: username='{username}', user_id={user_id}")
        return False
    
    def get_whitelist_info(self) -> str:
        """Get whitelist information for status"""
        if not self.allowed_users:
            return "Whitelist: Disabled (all users allowed)"
        return f"Whitelist: Enabled ({len(self.allowed_users)} users)"