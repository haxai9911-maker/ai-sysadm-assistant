import logging
from typing import Optional
import telebot
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException

logger = logging.getLogger(__name__)

class MessageSender:
    """Helper class for safely sending messages with Markdown formatting"""
    
    def __init__(self, bot: AsyncTeleBot):
        self.bot = bot
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape special Markdown characters"""
        if not text:
            return text
            
        # List of characters that need to be escaped in Markdown
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    @staticmethod
    def safe_truncate(text: str, max_length: int = 4000) -> str:
        """Safely truncate text to avoid Telegram message limits"""
        if len(text) <= max_length:
            return text
        return text[:max_length-100] + "\n\n... (message truncated due to length limitations)"
    
    async def send_safe_message(self, chat_id: int, text: str, reply_to_message_id: int = None, 
                              parse_mode: str = 'Markdown') -> bool:
        """
        Safely send message with fallback strategies
        Returns True if successful, False otherwise
        """
        if not text or not text.strip():
            return False
            
        try:
            # First attempt: Send with Markdown
            await self.bot.send_message(
                chat_id, 
                text, 
                reply_to_message_id=reply_to_message_id,
                parse_mode=parse_mode
            )
            return True
            
        except ApiTelegramException as e:
            if "can't parse entities" in str(e):
                logger.warning(f"Markdown parsing failed, trying with escaped text: {e}")
                try:
                    # Second attempt: Escape Markdown and try again
                    escaped_text = self.escape_markdown(text)
                    await self.bot.send_message(
                        chat_id,
                        escaped_text,
                        reply_to_message_id=reply_to_message_id,
                        parse_mode=parse_mode
                    )
                    return True
                except ApiTelegramException as e2:
                    logger.warning(f"Escaped Markdown also failed, trying without formatting: {e2}")
                    try:
                        # Third attempt: Send without Markdown
                        await self.bot.send_message(
                            chat_id,
                            text,
                            reply_to_message_id=reply_to_message_id,
                            parse_mode=None
                        )
                        return True
                    except ApiTelegramException as e3:
                        logger.error(f"All message sending attempts failed: {e3}")
                        # Final attempt: Send error message
                        try:
                            error_msg = "❌ Failed to send message due to formatting issues. Please try again."
                            await self.bot.send_message(chat_id, error_msg)
                            return False
                        except:
                            return False
            else:
                logger.error(f"Telegram API error: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
            return False
    
    async def reply_safe(self, message, text: str, parse_mode: str = 'Markdown') -> bool:
        """Safely reply to a message with proper error handling"""
        return await self.send_safe_message(
            message.chat.id, 
            text, 
            reply_to_message_id=message.message_id,
            parse_mode=parse_mode
        )