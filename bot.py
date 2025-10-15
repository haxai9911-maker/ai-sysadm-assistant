import os
import logging
import subprocess
import json
import asyncio
import re
import html
import platform
import socket
from typing import Dict, Optional, List
from dotenv import load_dotenv
import telebot
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException
import aiohttp

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store user sessions
user_sessions: Dict[int, Dict] = {}

# Initialize bot
bot = AsyncTeleBot(os.getenv('TELEGRAM_BOT_TOKEN'))

# Conversation states
PLANNING_STATE = "planning"
EXECUTING_STATE = "executing"
NORMAL_STATE = "normal"

class UserWhitelist:
    """Class to manage user whitelist"""
    
    def __init__(self):
        self.allowed_users = self._load_whitelist()
    
    def _load_whitelist(self) -> List[str]:
        """Load whitelist from environment variable"""
        whitelist_str = os.getenv('ALLOWED_USERS', '').strip()
        if not whitelist_str:
            logger.warning("No ALLOWED_USERS environment variable set. All users will be allowed.")
            return []
        
        # Parse comma-separated list of usernames
        users = [username.strip().lstrip('@') for username in whitelist_str.split(',') if username.strip()]
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

# Initialize whitelist
user_whitelist = UserWhitelist()

class SystemInfo:
    """Class to gather and format system information"""
    
    @staticmethod
    async def get_system_info() -> str:
        """Get comprehensive system information"""
        try:
            # Basic system info
            system = platform.system()
            release = platform.release()
            version = platform.version()
            machine = platform.machine()
            processor = platform.processor()
            
            # Get hostname
            hostname = socket.gethostname()
            
            # Get distribution info for Linux
            distro_info = ""
            if system == "Linux":
                try:
                    # Try to get distribution info
                    with open('/etc/os-release', 'r') as f:
                        os_release = f.read()
                    for line in os_release.split('\n'):
                        if line.startswith('PRETTY_NAME='):
                            distro_info = line.split('=', 1)[1].strip('"')
                            break
                    if not distro_info:
                        distro_info = "Linux (unknown distribution)"
                except:
                    distro_info = "Linux"
            else:
                distro_info = f"{system} {release}"
            
            # Get current working directory
            cwd = os.getcwd()
            
            # Get user info
            import getpass
            current_user = getpass.getuser()
            
            # Get available memory (Linux/MacOS)
            memory_info = ""
            if system in ["Linux", "Darwin"]:
                try:
                    if system == "Linux":
                        with open('/proc/meminfo', 'r') as f:
                            mem_lines = f.readlines()
                        total_mem = None
                        for line in mem_lines:
                            if line.startswith('MemTotal:'):
                                total_mem_kb = int(line.split()[1])
                                total_mem_gb = round(total_mem_kb / (1024 * 1024), 1)
                                memory_info = f", {total_mem_gb}GB RAM"
                                break
                    else:  # Darwin (macOS)
                        result = await asyncio.create_subprocess_shell(
                            'sysctl hw.memsize',
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True
                        )
                        stdout, stderr = await result.communicate()
                        if stdout:
                            mem_bytes = int(stdout.decode().split(':')[1].strip())
                            total_mem_gb = round(mem_bytes / (1024**3), 1)
                            memory_info = f", {total_mem_gb}GB RAM"
                except:
                    memory_info = ""
            
            # Format system information
            system_info = f"""
Host System Information:
- OS: {distro_info}
- Kernel: {release}
- Architecture: {machine}
- Hostname: {hostname}
- Current User: {current_user}
- Working Directory: {cwd}
- Processor: {processor}{memory_info}
"""
            return system_info.strip()
            
        except Exception as e:
            logger.error(f"Error gathering system info: {e}")
            return "Host System Information: Unable to gather detailed system information"

class MessageSender:
    """Helper class for safely sending messages with Markdown formatting"""
    
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
    
    @classmethod
    async def send_safe_message(cls, chat_id: int, text: str, reply_to_message_id: int = None, 
                              parse_mode: str = 'Markdown') -> bool:
        """
        Safely send message with fallback strategies
        Returns True if successful, False otherwise
        """
        if not text or not text.strip():
            return False
            
        try:
            # First attempt: Send with Markdown
            await bot.send_message(
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
                    escaped_text = cls.escape_markdown(text)
                    await bot.send_message(
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
                        await bot.send_message(
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
                            await bot.send_message(chat_id, error_msg)
                            return False
                        except:
                            return False
            else:
                logger.error(f"Telegram API error: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
            return False
    
    @classmethod
    async def reply_safe(cls, message, text: str, parse_mode: str = 'Markdown') -> bool:
        """Safely reply to a message with proper error handling"""
        return await cls.send_safe_message(
            message.chat.id, 
            text, 
            reply_to_message_id=message.message_id,
            parse_mode=parse_mode
        )

async def check_user_access(message) -> bool:
    """
    Check if user is allowed to use the bot
    Returns True if allowed, False otherwise
    """
    user_id = message.from_user.id
    username = message.from_user.username
    
    if not user_whitelist.is_user_allowed(username, user_id):
        access_denied_msg = (
            "🚫 *Access Denied*\n\n"
            "You are not authorized to use this bot.\n\n"
            "If you believe this is an error, please contact the administrator."
        )
        await MessageSender.reply_safe(message, access_denied_msg)
        return False
    return True

class YandexGPTClient:
    def __init__(self):
        self.api_key = os.getenv('YANDEX_API_KEY')
        self.folder_id = os.getenv('YANDEX_FOLDER_ID')
        self.api_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        self.system_info = None
        
    async def initialize_system_info(self):
        """Initialize system information once"""
        if self.system_info is None:
            self.system_info = await SystemInfo.get_system_info()
        
    async def send_prompt(self, prompt: str, conversation_history: list = None, plan_mode: bool = False) -> dict:
        """
        Send prompt to Yandex GPT and return response
        
        Args:
            prompt: The user prompt
            conversation_history: Previous conversation history
            plan_mode: Whether this is for generating a plan
        """
        # Ensure system info is initialized
        await self.initialize_system_info()
        
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if conversation_history is None:
            conversation_history = []
            
        # Different system prompts for plan mode vs normal mode
        if plan_mode:
            system_message = {
                "role": "system",
                "text": f"""You are an expert system administrator that creates detailed execution plans for complex tasks.

SYSTEM INFORMATION:
{self.system_info}

TASK: Create a step-by-step plan to accomplish the user's request.

RESPONSE FORMAT:
Respond with PURE JSON (without any markdown formatting) containing:
{{
    "plan": [
        {{
            "step_number": 1,
            "description": "Clear description of what this step accomplishes",
            "expected_outcome": "What we expect to achieve in this step"
        }},
        {{
            "step_number": 2,
            "description": "Next step description",
            "expected_outcome": "Expected outcome for this step"
        }}
    ],
    "overview": "Brief overview of the entire plan",
    "estimated_time": "Estimated time to complete all steps",
    "risks": "Any potential risks or considerations"
}}

IMPORTANT GUIDELINES:
- Create practical, safe steps appropriate for {platform.system()} system
- Each step should be clear and actionable
- Consider dependencies between steps
- Include verification steps where appropriate
- NEVER use markdown code blocks (```) in your responses
- ALWAYS respond with pure JSON"""
            }
        else:
            system_message = {
                "role": "system",
                "text": f"""You are a helpful assistant that can generate CLI commands. 
                
SYSTEM INFORMATION:
{self.system_info}

RESPONSE FORMAT:
When you need to run commands, respond with PURE JSON (without any markdown formatting) containing:
{{
    "command": "the CLI command to execute",
    "explanation": "brief explanation of what the command does"
}}

If you need additional information from the user, respond with PURE JSON (without any markdown formatting) containing:
{{
    "question": "the question to ask the user",
    "needed_for": "what the information is needed for"
}}

Otherwise, provide helpful responses in plain text.

IMPORTANT GUIDELINES:
- Generate commands appropriate for the current operating system ({platform.system()})
- NEVER use markdown code blocks (```) in your responses
- ALWAYS respond with pure JSON for structured responses
- Only generate safe commands. Never generate commands that could harm the system.
- For JSON responses, don't include any additional text before or after the JSON.
- Consider the current working directory and user permissions when generating commands."""
            }
        
        messages = [system_message] + conversation_history + [{"role": "user", "text": prompt}]
        
        data = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.3,
                "maxTokens": 2000
            },
            "messages": messages
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        return {"error": f"API request failed: {response.status} - {error_text}"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

class CommandExecutor:
    @staticmethod
    async def execute_command(command: str) -> tuple:
        """
        Execute CLI command and return output
        """
        try:
            # Security check - prevent dangerous commands
            dangerous_patterns = [
                'rm -rf', 'format', 'dd', 'mkfs', '> /dev/sd', ':(){:|:&};:', 
                'chmod 777', 'passwd', 'adduser', 'useradd', 'deluser', 
                'chown root', 'chgrp root', 'visudo', 'crontab -r'
            ]
            if any(pattern in command for pattern in dangerous_patterns):
                return None, "Error: Command contains potentially dangerous operations"
            
            # Execute command with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
            
            output = stdout.decode('utf-8', errors='ignore') if stdout else ""
            error = stderr.decode('utf-8', errors='ignore') if stderr else ""
            
            if process.returncode != 0:
                return None, f"Command failed with return code {process.returncode}: {error}"
                
            return output, None
            
        except asyncio.TimeoutError:
            return None, "Command timed out after 30 seconds"
        except Exception as e:
            return None, f"Error executing command: {str(e)}"

# Initialize clients
yandex_gpt = YandexGPTClient()
command_executor = CommandExecutor()
message_sender = MessageSender()

def get_user_session(user_id: int) -> Dict:
    """Get or create user session"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'conversation_history': [],
            'waiting_for_followup': False,
            'state': NORMAL_STATE,
            'current_plan': None,
            'current_step': 0,
            'plan_results': []
        }
    return user_sessions[user_id]

def extract_json_from_response(response: str) -> Optional[dict]:
    """
    Extract JSON from Markdown code blocks or try to parse directly.
    Handles cases where JSON is wrapped in ```json ... ``` or ``` ... ```
    """
    # Patterns for extracting JSON from Markdown
    patterns = [
        r'```json\s*(.*?)\s*```',  # ```json { ... } ```
        r'```\s*(.*?)\s*```',      # ``` { ... } ```
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
    
    # If not found in Markdown blocks, try to parse the whole string as JSON
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        return None

async def generate_plan(message, user_request: str) -> bool:
    """Generate a plan for complex tasks"""
    session = get_user_session(message.from_user.id)
    
    # Show typing action
    await bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # Send to Yandex GPT in plan mode
        response = await yandex_gpt.send_prompt(
            f"Create a detailed step-by-step plan for: {user_request}",
            plan_mode=True
        )
        
        if "error" in response:
            await message_sender.reply_safe(message, f"❌ Error generating plan: {response['error']}")
            return False
        
        # Extract response text
        result = response.get('result', {})
        alternatives = result.get('alternatives', [])
        
        if not alternatives:
            await message_sender.reply_safe(message, "❌ No response from AI for plan generation")
            return False
            
        ai_response = alternatives[0].get('message', {}).get('text', '')
        
        # Try to parse as JSON
        plan_data = extract_json_from_response(ai_response)
        
        if plan_data and 'plan' in plan_data:
            session['current_plan'] = plan_data
            session['state'] = PLANNING_STATE
            session['current_step'] = 0
            session['plan_results'] = []
            
            # Format and send the plan to user
            plan_message = format_plan_message(plan_data)
            plan_message += "\n\n**Do you want to execute this plan?**\nReply with `yes` to proceed or `no` to cancel."
            
            await message_sender.reply_safe(message, plan_message)
            return True
        else:
            await message_sender.reply_safe(message, "❌ Could not generate a valid plan. Please try a different request.")
            return False
            
    except Exception as e:
        logger.error(f"Error in generate_plan: {str(e)}")
        await message_sender.reply_safe(message, "❌ An error occurred while generating the plan.")
        return False

def format_plan_message(plan_data: dict) -> str:
    """Format plan data into a readable message"""
    plan = plan_data.get('plan', [])
    overview = plan_data.get('overview', 'No overview provided')
    estimated_time = plan_data.get('estimated_time', 'Not specified')
    risks = plan_data.get('risks', 'No significant risks identified')
    
    message = f"📋 **Execution Plan**\n\n"
    message += f"**Overview:** {overview}\n"
    message += f"**Estimated Time:** {estimated_time}\n"
    message += f"**Risks:** {risks}\n\n"
    message += f"**Steps ({len(plan)} total):**\n\n"
    
    for step in plan:
        step_num = step.get('step_number', '?')
        description = step.get('description', 'No description')
        expected_outcome = step.get('expected_outcome', 'Not specified')
        
        message += f"**Step {step_num}:** {description}\n"
        message += f"   _Expected:_ {expected_outcome}\n\n"
    
    return message

async def execute_next_step(message) -> bool:
    """Execute the next step in the plan"""
    session = get_user_session(message.from_user.id)
    plan = session.get('current_plan', {})
    steps = plan.get('plan', [])
    current_step = session.get('current_step', 0)
    
    if current_step >= len(steps):
        # Plan completed
        await finish_plan_execution(message)
        return True
    
    step = steps[current_step]
    step_description = step.get('description', 'Unknown step')
    
    # Show typing action
    await bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # Ask Yandex GPT for command to execute this step
        prompt = f"""
        We are executing step {current_step + 1} of the plan: "{step_description}"
        
        Please provide the CLI command to execute this step.
        Consider the system context and ensure the command is safe and appropriate.
        """
        
        response = await yandex_gpt.send_prompt(prompt)
        
        if "error" in response:
            await message_sender.reply_safe(message, f"❌ Error getting command for step {current_step + 1}: {response['error']}")
            session['current_step'] += 1
            session['plan_results'].append({
                'step': current_step + 1,
                'description': step_description,
                'status': 'error',
                'error': response['error']
            })
            return await execute_next_step(message)
        
        # Extract response
        result = response.get('result', {})
        alternatives = result.get('alternatives', [])
        
        if not alternatives:
            await message_sender.reply_safe(message, f"❌ No response for step {current_step + 1}")
            session['current_step'] += 1
            session['plan_results'].append({
                'step': current_step + 1,
                'description': step_description,
                'status': 'error',
                'error': 'No AI response'
            })
            return await execute_next_step(message)
            
        ai_response = alternatives[0].get('message', {}).get('text', '')
        
        # Try to parse as JSON for command
        command_data = extract_json_from_response(ai_response)
        
        if command_data and 'command' in command_data:
            command = command_data['command']
            explanation = command_data.get('explanation', 'No explanation provided')
            
            # Execute the command
            step_message = f"**🔄 Step {current_step + 1}/{len(steps)}:** {step_description}\n"
            step_message += f"**Command:** `{command}`\n"
            step_message += f"**Explanation:** {explanation}"
            
            await message_sender.reply_safe(message, step_message)
            
            output, error = await command_executor.execute_command(command)
            
            # Store result
            if error:
                result_status = 'error'
                result_message = f"❌ {error}"
                session['plan_results'].append({
                    'step': current_step + 1,
                    'description': step_description,
                    'command': command,
                    'status': 'error',
                    'output': error
                })
            else:
                result_status = 'success'
                # Truncate long output
                output_display = message_sender.safe_truncate(output)
                result_message = f"✅ **Success!**\n```\n{output_display}\n```"
                session['plan_results'].append({
                    'step': current_step + 1,
                    'description': step_description,
                    'command': command,
                    'status': 'success',
                    'output': output
                })
            
            await message_sender.reply_safe(message, result_message)
            
        else:
            # If no command found, mark as skipped
            await message_sender.reply_safe(message, f"⏭️ **Step {current_step + 1}:** {step_description}\n_No command generated - skipping_")
            session['plan_results'].append({
                'step': current_step + 1,
                'description': step_description,
                'status': 'skipped',
                'output': 'No command generated by AI'
            })
        
        # Move to next step
        session['current_step'] += 1
        
        # If there are more steps, continue automatically
        if session['current_step'] < len(steps):
            await asyncio.sleep(1)  # Brief pause between steps
            return await execute_next_step(message)
        else:
            await finish_plan_execution(message)
            return True
            
    except Exception as e:
        logger.error(f"Error in execute_next_step: {str(e)}")
        await message_sender.reply_safe(message, f"❌ Error executing step {current_step + 1}")
        session['current_step'] += 1
        session['plan_results'].append({
            'step': current_step + 1,
            'description': step_description,
            'status': 'error',
            'error': str(e)
        })
        return await execute_next_step(message)

async def finish_plan_execution(message):
    """Finish plan execution and show summary"""
    session = get_user_session(message.from_user.id)
    plan_results = session.get('plan_results', [])
    
    # Calculate statistics
    total_steps = len(plan_results)
    successful_steps = len([r for r in plan_results if r.get('status') == 'success'])
    failed_steps = len([r for r in plan_results if r.get('status') == 'error'])
    skipped_steps = len([r for r in plan_results if r.get('status') == 'skipped'])
    
    summary_message = f"🏁 **Plan Execution Complete**\n\n"
    summary_message += f"**Summary:** {successful_steps} ✅ | {failed_steps} ❌ | {skipped_steps} ⏭️\n\n"
    
    if failed_steps > 0:
        summary_message += "**Failed Steps:**\n"
        for result in plan_results:
            if result.get('status') == 'error':
                summary_message += f"• Step {result['step']}: {result.get('error', 'Unknown error')}\n"
    
    summary_message += "\n**Detailed Results:**\n"
    for result in plan_results:
        status_icon = '✅' if result.get('status') == 'success' else '❌' if result.get('status') == 'error' else '⏭️'
        summary_message += f"{status_icon} Step {result['step']}: {result.get('description', 'Unknown')}\n"
    
    await message_sender.reply_safe(message, summary_message)
    
    # Reset session state
    session['state'] = NORMAL_STATE
    session['current_plan'] = None
    session['current_step'] = 0
    session['plan_results'] = []

async def handle_structured_response(message, session, response_data):
    """Handle structured JSON response from AI."""
    try:
        if 'command' in response_data:
            # Execute command
            command = response_data['command']
            explanation = response_data.get('explanation', 'No explanation provided')
            
            message_text = f"🔧 **Executing:** `{command}`\n📝 **Explanation:** {explanation}"
            await message_sender.reply_safe(message, message_text)
            
            output, error = await command_executor.execute_command(command)
            
            if error:
                await message_sender.reply_safe(message, f"❌ {error}")
            else:
                # Truncate long output
                output = message_sender.safe_truncate(output)
                output_message = f"✅ **Output:**\n```\n{output}\n```"
                await message_sender.reply_safe(message, output_message)
                
        elif 'question' in response_data:
            # Ask follow-up question
            question = response_data['question']
            needed_for = response_data.get('needed_for', 'further processing')
            
            session['waiting_for_followup'] = True
            
            question_message = (
                f"❓ **Question:** {question}\n"
                f"📋 **Needed for:** {needed_for}\n\n"
                f"Please reply with the requested information."
            )
            await message_sender.reply_safe(message, question_message)
            
        else:
            # If it's JSON but doesn't contain expected fields, show as text
            await message_sender.reply_safe(message, str(response_data))
            
    except Exception as e:
        logger.error(f"Error in handle_structured_response: {str(e)}")
        await message_sender.reply_safe(
            message, 
            "❌ An error occurred while processing the structured response."
        )

async def process_ai_response(message, session, ai_response):
    """Process AI response and take appropriate action."""
    try:
        # First try to extract JSON from Markdown code blocks
        json_data = extract_json_from_response(ai_response)
        
        if json_data:
            # If we found JSON, use it
            await handle_structured_response(message, session, json_data)
        else:
            # If no JSON found, show the response as is
            await message_sender.reply_safe(message, ai_response)
            
    except Exception as e:
        logger.error(f"Error in process_ai_response: {str(e)}")
        await message_sender.reply_safe(
            message,
            "❌ An error occurred while processing the AI response."
        )

@bot.message_handler(commands=['start'])
async def start_command(message):
    """Send a message when the command /start is issued."""
    try:
        # Check user access
        if not await check_user_access(message):
            return
            
        user_id = message.from_user.id
        session = get_user_session(user_id)
        
        # Reset any existing state
        session.update({
            'conversation_history': [],
            'waiting_for_followup': False,
            'state': NORMAL_STATE,
            'current_plan': None,
            'current_step': 0,
            'plan_results': []
        })
        
        # Initialize system info and include it in welcome message
        system_info = await SystemInfo.get_system_info()
        
        welcome_text = f"""
🤖 Welcome to Yandex GPT CLI Bot!

I'm running on:
{system_info}

**New Feature:** For complex tasks, I'll create a step-by-step execution plan!

Send me your request and I'll:
1. Generate appropriate CLI commands for this system
2. For complex tasks, create an execution plan for your approval
3. Execute them on the server
4. Ask for additional info if needed

Example: "List all files in current directory" or "Check disk usage"
Complex example: "Set up monitoring for disk space and alert when it's low"

Type /help for more info.
        """
        await message_sender.reply_safe(message, welcome_text)
        
    except Exception as e:
        logger.error(f"Error in start_command: {str(e)}")

@bot.message_handler(commands=['help'])
async def help_command(message):
    """Send a message when the command /help is issued."""
    try:
        # Check user access
        if not await check_user_access(message):
            return
            
        help_text = """
📖 **Available Commands:**

/start - Start the bot
/help - Show this help message
/clear - Clear conversation history
/status - Show bot status
/system - Show detailed system information
/cancel - Cancel current operation

🔧 **How to use:**
1. Send your request in natural language
2. For simple tasks: Bot will execute immediately
3. For complex tasks: Bot will create an execution plan
4. Review and approve the plan
5. Bot executes step by step automatically

⚡ **Plan Execution:**
- Bot generates step-by-step plan for complex tasks
- You can approve or reject the plan
- Each step is executed automatically
- Progress is reported in real-time

⚠️ **Safety Features:**
- Dangerous commands are blocked
- Command execution has timeout
- Only basic operations allowed
- User whitelist support
        """
        await message_sender.reply_safe(message, help_text)
        
    except Exception as e:
        logger.error(f"Error in help_command: {str(e)}")

@bot.message_handler(commands=['cancel'])
async def cancel_command(message):
    """Cancel current operation."""
    try:
        # Check user access
        if not await check_user_access(message):
            return
            
        user_id = message.from_user.id
        session = get_user_session(user_id)
        
        if session['state'] in [PLANNING_STATE, EXECUTING_STATE]:
            session.update({
                'state': NORMAL_STATE,
                'current_plan': None,
                'current_step': 0,
                'plan_results': []
            })
            await message_sender.reply_safe(message, "🛑 Operation cancelled. Back to normal mode.")
        else:
            await message_sender.reply_safe(message, "ℹ️ No active operation to cancel.")
            
    except Exception as e:
        logger.error(f"Error in cancel_command: {str(e)}")

@bot.message_handler(commands=['system'])
async def system_command(message):
    """Show detailed system information."""
    try:
        # Check user access
        if not await check_user_access(message):
            return
            
        system_info = await SystemInfo.get_system_info()
        await message_sender.reply_safe(message, f"🖥️ **System Information:**\n\n{system_info}")
    except Exception as e:
        logger.error(f"Error in system_command: {str(e)}")
        await message_sender.reply_safe(message, "❌ Failed to gather system information")

@bot.message_handler(commands=['clear'])
async def clear_history(message):
    """Clear conversation history."""
    try:
        # Check user access
        if not await check_user_access(message):
            return
            
        user_id = message.from_user.id
        session = get_user_session(user_id)
        session.update({
            'conversation_history': [],
            'waiting_for_followup': False,
            'state': NORMAL_STATE,
            'current_plan': None,
            'current_step': 0,
            'plan_results': []
        })
        await message_sender.reply_safe(message, "✅ Conversation history and state cleared!")
        
    except Exception as e:
        logger.error(f"Error in clear_history: {str(e)}")

@bot.message_handler(commands=['status'])
async def status_command(message):
    """Show bot status."""
    try:
        # Check user access
        if not await check_user_access(message):
            return
            
        user_id = message.from_user.id
        session = get_user_session(user_id)
        history_length = len(session.get('conversation_history', []))
        
        state_display = {
            NORMAL_STATE: "Normal",
            PLANNING_STATE: "Planning",
            EXECUTING_STATE: "Executing Plan"
        }.get(session.get('state', NORMAL_STATE), "Unknown")
        
        status_text = f"""
🤖 **Bot Status**

👤 Active sessions: {len(user_sessions)}
💬 Your message history: {history_length} messages
🔄 Current state: {state_display}
{user_whitelist.get_whitelist_info()}
        """
        await message_sender.reply_safe(message, status_text)
        
    except Exception as e:
        logger.error(f"Error in status_command: {str(e)}")

@bot.message_handler(func=lambda message: True)
async def handle_message(message):
    """Handle all incoming messages."""
    try:
        # Check user access
        if not await check_user_access(message):
            return
            
        user_id = message.from_user.id
        user_message = message.text.strip().lower()
        
        session = get_user_session(user_id)
        current_state = session.get('state', NORMAL_STATE)
        
        # Handle plan confirmation
        if current_state == PLANNING_STATE:
            if user_message in ['yes', 'y', 'confirm', 'ok', 'proceed']:
                session['state'] = EXECUTING_STATE
                await message_sender.reply_safe(message, "🚀 Starting plan execution...")
                await execute_next_step(message)
                return
            elif user_message in ['no', 'n', 'cancel', 'stop']:
                session['state'] = NORMAL_STATE
                session['current_plan'] = None
                await message_sender.reply_safe(message, "❌ Plan execution cancelled.")
                return
            else:
                await message_sender.reply_safe(
                    message, 
                    "❓ Please confirm the plan: reply with `yes` to proceed or `no` to cancel."
                )
                return
        
        # Handle normal message processing
        if session.get('waiting_for_followup'):
            await handle_followup(message, session, user_message)
            return
        
        # Show typing action
        try:
            await bot.send_chat_action(message.chat.id, 'typing')
        except Exception as e:
            logger.warning(f"Failed to send typing action: {e}")
        
        # Check if this is a new conversation (no history) - trigger plan generation
        original_message = message.text  # Keep original case for the request
        if (not session['conversation_history'] and 
            len(original_message.split()) >= 3 and  # At least 3 words (likely a complex request)
            not any(cmd in original_message.lower() for cmd in ['list', 'show', 'display', 'check'])):  # Simple commands
            
            # For complex-looking new requests, generate a plan
            await message_sender.reply_safe(
                message, 
                "🔍 This looks like a complex task. Generating an execution plan..."
            )
            if await generate_plan(message, original_message):
                return
            # If plan generation fails, fall through to normal processing
        
        # Normal message processing
        response = await yandex_gpt.send_prompt(original_message, session['conversation_history'])
        
        if "error" in response:
            await message_sender.reply_safe(message, f"❌ Error: {response['error']}")
            return
        
        # Extract response text
        result = response.get('result', {})
        alternatives = result.get('alternatives', [])
        
        if not alternatives:
            await message_sender.reply_safe(message, "❌ No response from AI")
            return
            
        ai_response = alternatives[0].get('message', {}).get('text', '')
        
        # Update conversation history
        session['conversation_history'].extend([
            {"role": "user", "text": original_message},
            {"role": "assistant", "text": ai_response}
        ])
        
        # Keep history manageable
        if len(session['conversation_history']) > 10:
            session['conversation_history'] = session['conversation_history'][-6:]
        
        # Process the AI response
        await process_ai_response(message, session, ai_response)
            
    except Exception as e:
        logger.error(f"Error in handle_message: {str(e)}")
        await message_sender.reply_safe(
            message, 
            "❌ An error occurred while processing your request."
        )

async def handle_followup(message, session, user_response):
    """Handle follow-up responses from user."""
    session['waiting_for_followup'] = False
    
    # Show typing action
    try:
        await bot.send_chat_action(message.chat.id, 'typing')
    except Exception as e:
        logger.warning(f"Failed to send typing action in followup: {e}")
    
    try:
        # Create follow-up prompt
        followup_prompt = f"User provided the following information: {user_response}. Please continue with the original request."
        
        # Send to Yandex GPT with full history
        response = await yandex_gpt.send_prompt(followup_prompt, session['conversation_history'])
        
        if "error" in response:
            await message_sender.reply_safe(message, f"❌ Error: {response['error']}")
            return
        
        # Process response
        result = response.get('result', {})
        alternatives = result.get('alternatives', [])
        
        if not alternatives:
            await message_sender.reply_safe(message, "❌ No response from AI")
            return
            
        ai_response = alternatives[0].get('message', {}).get('text', '')
        
        # Update conversation history
        session['conversation_history'].extend([
            {"role": "user", "text": followup_prompt},
            {"role": "assistant", "text": ai_response}
        ])
        
        # Process the AI response using the new approach
        await process_ai_response(message, session, ai_response)
            
    except Exception as e:
        logger.error(f"Error in handle_followup: {str(e)}")
        await message_sender.reply_safe(
            message, 
            "❌ An error occurred while processing your response."
        )

async def main():
    """Main function to run the bot."""
    # Check required environment variables
    required_vars = ['TELEGRAM_BOT_TOKEN', 'YANDEX_API_KEY', 'YANDEX_FOLDER_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please create a .env file with these variables:")
        print("TELEGRAM_BOT_TOKEN=your_telegram_bot_token")
        print("YANDEX_API_KEY=your_yandex_gpt_api_key")
        print("YANDEX_FOLDER_ID=your_yandex_folder_id")
        return
    
    print("🤖 Bot is starting...")
    
    # Display system and security information on startup
    try:
        system_info = await SystemInfo.get_system_info()
        print(f"🖥️ System Information:\n{system_info}")
    except Exception as e:
        print(f"⚠️ Could not gather system information: {e}")
    
    # Display whitelist status
    print(f"🔐 {user_whitelist.get_whitelist_info()}")
    print("🔄 Multi-step planning feature: ENABLED")
    
    try:
        await bot.polling(none_stop=True)
    except Exception as e:
        logger.error(f"Bot polling failed: {e}")
        print("❌ Bot stopped due to an error.")

if __name__ == '__main__':
    asyncio.run(main())