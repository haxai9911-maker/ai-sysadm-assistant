import logging
import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot.types import BotCommand

from config import Config
from models.user_session import SessionManager
from models.whitelist import UserWhitelist
from services.yandex_gpt import YandexGPTClient
from services.command_executor import CommandExecutor
from services.message_sender import MessageSender
from services.system_info import SystemInfo
from bot.handlers import BotHandlers

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def setup_bot_commands(bot: AsyncTeleBot):
    """Set up bot commands for the menu"""
    commands = [
        BotCommand('start', 'Start the bot and show welcome message'),
        BotCommand('help', 'Show help information and usage guide'),
        BotCommand('status', 'Show bot status and active sessions'),
        BotCommand('system', 'Display detailed system information'),
        BotCommand('clear', 'Clear conversation history and reset state'),
        BotCommand('cancel', 'Cancel current operation or plan execution'),
    ]
    
    try:
        await bot.set_my_commands(commands)
        logger.info("Bot commands menu set successfully")
        print("✅ Bot commands menu configured")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")
        print("❌ Failed to set bot commands menu")

async def main():
    """Main function to run the bot."""
    # Validate configuration
    try:
        Config.validate_config()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return

    # Initialize components
    bot = AsyncTeleBot(Config.TELEGRAM_BOT_TOKEN)
    session_manager = SessionManager()
    whitelist = UserWhitelist(Config.ALLOWED_USERS)
    yandex_gpt = YandexGPTClient(Config.YANDEX_API_KEY, Config.YANDEX_FOLDER_ID)
    command_executor = CommandExecutor(Config.COMMAND_TIMEOUT)
    message_sender = MessageSender(bot)

    # Set up bot commands menu
    await setup_bot_commands(bot)

    # Initialize and register handlers
    bot_handlers = BotHandlers(bot, session_manager, whitelist, yandex_gpt, command_executor, message_sender)

    print("🤖 Bot is starting...")
    
    # Display system and security information on startup
    try:
        system_info = await SystemInfo.get_system_info()
        print(f"🖥️ System Information:\n{system_info}")
    except Exception as e:
        print(f"⚠️ Could not gather system information: {e}")
    
    # Display whitelist status
    print(f"🔐 {whitelist.get_whitelist_info()}")
    print("🔄 Multi-step planning feature: ENABLED")
    print("🎯 Smart complexity analysis: ENABLED")
    
    try:
        await bot.polling(none_stop=True)
    except Exception as e:
        logger.error(f"Bot polling failed: {e}")
        print("❌ Bot stopped due to an error.")

if __name__ == '__main__':
    asyncio.run(main())
