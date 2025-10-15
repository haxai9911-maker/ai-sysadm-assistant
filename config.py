import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for environment variables"""
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Yandex GPT
    YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')
    YANDEX_FOLDER_ID = os.getenv('YANDEX_FOLDER_ID')
    
    # Security
    ALLOWED_USERS = os.getenv('ALLOWED_USERS', '').strip()
    
    # Bot settings
    COMMAND_TIMEOUT = 30
    MAX_MESSAGE_LENGTH = 4000
    MAX_HISTORY_LENGTH = 10
    
    # Bot command settings
    BOT_COMMANDS = [
        ('start', 'Start the bot and show welcome message'),
        ('help', 'Show help information and usage guide'),
        ('status', 'Show bot status and active sessions'),
        ('system', 'Display detailed system information'),
        ('clear', 'Clear conversation history and reset state'),
        ('cancel', 'Cancel current operation or plan execution'),
    ]
    
    @classmethod
    def validate_config(cls):
        """Validate that all required environment variables are set"""
        required_vars = ['TELEGRAM_BOT_TOKEN', 'YANDEX_API_KEY', 'YANDEX_FOLDER_ID']
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True

