import logging
import asyncio
from typing import Dict, Optional
import telebot
from telebot import types
from telebot.async_telebot import AsyncTeleBot

from config import Config
from models.user_session import UserSession, SessionManager, NORMAL_STATE, PLANNING_STATE, EXECUTING_STATE
from models.whitelist import UserWhitelist
from services.yandex_gpt import YandexGPTClient
from services.command_executor import CommandExecutor
from services.message_sender import MessageSender
from services.system_info import SystemInfo
from utils.helpers import extract_json_from_response, format_plan_message

logger = logging.getLogger(__name__)

class BotHandlers:
    """Class to handle all bot message handlers"""
    
    def __init__(self, bot: AsyncTeleBot, session_manager: SessionManager, whitelist: UserWhitelist,
                 yandex_gpt: YandexGPTClient, command_executor: CommandExecutor, message_sender: MessageSender):
        self.bot = bot
        self.session_manager = session_manager
        self.whitelist = whitelist
        self.yandex_gpt = yandex_gpt
        self.command_executor = command_executor
        self.message_sender = message_sender
        
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all message handlers"""
        self.bot.message_handler(commands=['start'])(self.start_command)
        self.bot.message_handler(commands=['help'])(self.help_command)
        self.bot.message_handler(commands=['cancel'])(self.cancel_command)
        self.bot.message_handler(commands=['system'])(self.system_command)
        self.bot.message_handler(commands=['clear'])(self.clear_history)
        self.bot.message_handler(commands=['status'])(self.status_command)
        self.bot.message_handler(func=lambda message: True)(self.handle_message)
    
    async def check_user_access(self, message) -> bool:
        """
        Check if user is allowed to use the bot
        Returns True if allowed, False otherwise
        """
        user_id = message.from_user.id
        username = message.from_user.username
        
        if not self.whitelist.is_user_allowed(username, user_id):
            access_denied_msg = (
                "🚫 *Access Denied*\n\n"
                "You are not authorized to use this bot.\n\n"
                "If you believe this is an error, please contact the administrator."
            )
            await self.message_sender.reply_safe(message, access_denied_msg)
            return False
        return True

    async def start_command(self, message):
        """Send a message when the command /start is issued."""
        try:
            # Check user access
            if not await self.check_user_access(message):
                return
                
            user_id = message.from_user.id
            session = self.session_manager.get_session(user_id)
            
            # Reset any existing state
            session.reset_all()
            
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
            await self.message_sender.reply_safe(message, welcome_text)
            
        except Exception as e:
            logger.error(f"Error in start_command: {str(e)}")

    async def help_command(self, message):
        """Send a message when the command /help is issued."""
        try:
            # Check user access
            if not await self.check_user_access(message):
                return
                
            help_text = """
🎯 **Available Commands** (also available in menu):

/start - Start the bot and show welcome message
/help - Show this help information and usage guide
/status - Show bot status and active sessions
/system - Display detailed system information
/clear - Clear conversation history and reset state
/cancel - Cancel current operation or plan execution

🔧 **How to Use:**

**Simple Tasks:**
Just send your request in natural language!
- "List files in current directory"
- "Check disk space" 
- "Show running processes"
- "Display memory usage"

**Complex Tasks:**
The bot automatically detects complex tasks and creates execution plans!
- "Set up disk monitoring with alerts"
- "Backup website files and database"
- "Analyze system performance"

⚡ **Smart Features:**
- **Auto-complexity detection**: Bot analyzes if your task needs a multi-step plan
- **Safe execution**: Dangerous commands are automatically blocked
- **Conversation memory**: Remembers context across messages
- **Multi-user support**: Handles multiple users simultaneously

⚠️ **Safety Features:**
- Command validation and timeout protection
- User whitelist support
- Comprehensive logging and audit trails

💡 **Pro Tips:**
- Be specific: "Check disk usage on /home partition"
- Use natural language: "Show me what's running on port 80"
- Cancel anytime with /cancel
- Check system info with /system

**Example Workflow:**
1. Send: "Set up monitoring for disk space"
2. Bot analyzes complexity and creates a plan
3. Review and approve the plan
4. Bot executes step by step automatically
5. Get detailed progress reports
            """
            await self.message_sender.reply_safe(message, help_text)
            
        except Exception as e:
            logger.error(f"Error in help_command: {str(e)}")

    async def cancel_command(self, message):
        """Cancel current operation."""
        try:
            # Check user access
            if not await self.check_user_access(message):
                return
                
            user_id = message.from_user.id
            session = self.session_manager.get_session(user_id)
            
            if session.state in [PLANNING_STATE, EXECUTING_STATE]:
                session.reset_plan()
                await self.message_sender.reply_safe(message, "🛑 Operation cancelled. Back to normal mode.")
            else:
                await self.message_sender.reply_safe(message, "ℹ️ No active operation to cancel.")
                
        except Exception as e:
            logger.error(f"Error in cancel_command: {str(e)}")

    async def system_command(self, message):
        """Show detailed system information."""
        try:
            # Check user access
            if not await self.check_user_access(message):
                return
                
            system_info = await SystemInfo.get_system_info()
            await self.message_sender.reply_safe(message, f"🖥️ **System Information:**\n\n{system_info}")
        except Exception as e:
            logger.error(f"Error in system_command: {str(e)}")
            await self.message_sender.reply_safe(message, "❌ Failed to gather system information")

    async def clear_history(self, message):
        """Clear conversation history."""
        try:
            # Check user access
            if not await self.check_user_access(message):
                return
                
            user_id = message.from_user.id
            session = self.session_manager.get_session(user_id)
            session.reset_all()
            await self.message_sender.reply_safe(message, "✅ Conversation history and state cleared!")
            
        except Exception as e:
            logger.error(f"Error in clear_history: {str(e)}")

    async def status_command(self, message):
        """Show bot status."""
        try:
            # Check user access
            if not await self.check_user_access(message):
                return
                
            user_id = message.from_user.id
            session = self.session_manager.get_session(user_id)
            history_length = len(session.conversation_history)
            
            state_display = {
                NORMAL_STATE: "Normal",
                PLANNING_STATE: "Planning",
                EXECUTING_STATE: "Executing Plan"
            }.get(session.state, "Unknown")
            
            status_text = f"""
🤖 **Bot Status**

👤 Active sessions: {self.session_manager.get_session_count()}
💬 Your message history: {history_length} messages
🔄 Current state: {state_display}
{self.whitelist.get_whitelist_info()}
            """
            await self.message_sender.reply_safe(message, status_text)
            
        except Exception as e:
            logger.error(f"Error in status_command: {str(e)}")

    async def generate_plan(self, message, user_request: str) -> bool:
        """Generate a plan for complex tasks"""
        session = self.session_manager.get_session(message.from_user.id)
        
        # Show typing action
        await self.bot.send_chat_action(message.chat.id, 'typing')
        
        try:
            # Send to Yandex GPT in plan mode
            response = await self.yandex_gpt.send_prompt(
                f"Create a detailed step-by-step plan for: {user_request}",
                plan_mode=True
            )
            
            if "error" in response:
                await self.message_sender.reply_safe(message, f"❌ Error generating plan: {response['error']}")
                return False
            
            # Extract response text
            result = response.get('result', {})
            alternatives = result.get('alternatives', [])
            
            if not alternatives:
                await self.message_sender.reply_safe(message, "❌ No response from AI for plan generation")
                return False
                
            ai_response = alternatives[0].get('message', {}).get('text', '')
            
            # Try to parse as JSON
            plan_data = extract_json_from_response(ai_response)
            
            if plan_data and 'plan' in plan_data:
                session.current_plan = plan_data
                session.state = PLANNING_STATE
                session.current_step = 0
                session.plan_results = []
                
                # Format and send the plan to user
                plan_message = format_plan_message(plan_data)
                plan_message += "\n\n**Do you want to execute this plan?**\nReply with `yes` to proceed or `no` to cancel."
                
                await self.message_sender.reply_safe(message, plan_message)
                return True
            else:
                await self.message_sender.reply_safe(message, "❌ Could not generate a valid plan. Please try a different request.")
                return False
                
        except Exception as e:
            logger.error(f"Error in generate_plan: {str(e)}")
            await self.message_sender.reply_safe(message, "❌ An error occurred while generating the plan.")
            return False

    async def execute_next_step(self, message) -> bool:
        """Execute the next step in the plan"""
        session = self.session_manager.get_session(message.from_user.id)
        plan = session.current_plan or {}
        steps = plan.get('plan', [])
        current_step = session.current_step
        
        if current_step >= len(steps):
            # Plan completed
            await self.finish_plan_execution(message)
            return True
        
        step = steps[current_step]
        step_description = step.get('description', 'Unknown step')
        
        # Show typing action
        await self.bot.send_chat_action(message.chat.id, 'typing')
        
        try:
            # Ask Yandex GPT for command to execute this step
            prompt = f"""
            We are executing step {current_step + 1} of the plan: "{step_description}"
            
            Please provide the CLI command to execute this step.
            Consider the system context and ensure the command is safe and appropriate.
            """
            
            response = await self.yandex_gpt.send_prompt(prompt)
            
            if "error" in response:
                await self.message_sender.reply_safe(message, f"❌ Error getting command for step {current_step + 1}: {response['error']}")
                session.current_step += 1
                session.plan_results.append({
                    'step': current_step + 1,
                    'description': step_description,
                    'status': 'error',
                    'error': response['error']
                })
                return await self.execute_next_step(message)
            
            # Extract response
            result = response.get('result', {})
            alternatives = result.get('alternatives', [])
            
            if not alternatives:
                await self.message_sender.reply_safe(message, f"❌ No response for step {current_step + 1}")
                session.current_step += 1
                session.plan_results.append({
                    'step': current_step + 1,
                    'description': step_description,
                    'status': 'error',
                    'error': 'No AI response'
                })
                return await self.execute_next_step(message)
                
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
                
                await self.message_sender.reply_safe(message, step_message)
                
                output, error = await self.command_executor.execute_command(command)
                
                # Store result
                if error:
                    result_status = 'error'
                    result_message = f"❌ {error}"
                    session.plan_results.append({
                        'step': current_step + 1,
                        'description': step_description,
                        'command': command,
                        'status': 'error',
                        'output': error
                    })
                else:
                    result_status = 'success'
                    # Truncate long output
                    output_display = self.message_sender.safe_truncate(output)
                    result_message = f"✅ **Success!**\n```\n{output_display}\n```"
                    session.plan_results.append({
                        'step': current_step + 1,
                        'description': step_description,
                        'command': command,
                        'status': 'success',
                        'output': output
                    })
                
                await self.message_sender.reply_safe(message, result_message)
                
            else:
                # If no command found, mark as skipped
                await self.message_sender.reply_safe(message, f"⏭️ **Step {current_step + 1}:** {step_description}\n_No command generated - skipping_")
                session.plan_results.append({
                    'step': current_step + 1,
                    'description': step_description,
                    'status': 'skipped',
                    'output': 'No command generated by AI'
                })
            
            # Move to next step
            session.current_step += 1
            
            # If there are more steps, continue automatically
            if session.current_step < len(steps):
                await asyncio.sleep(1)  # Brief pause between steps
                return await self.execute_next_step(message)
            else:
                await self.finish_plan_execution(message)
                return True
                
        except Exception as e:
            logger.error(f"Error in execute_next_step: {str(e)}")
            await self.message_sender.reply_safe(message, f"❌ Error executing step {current_step + 1}")
            session.current_step += 1
            session.plan_results.append({
                'step': current_step + 1,
                'description': step_description,
                'status': 'error',
                'error': str(e)
            })
            return await self.execute_next_step(message)

    async def finish_plan_execution(self, message):
        """Finish plan execution and show summary"""
        session = self.session_manager.get_session(message.from_user.id)
        plan_results = session.plan_results
        
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
        
        await self.message_sender.reply_safe(message, summary_message)
        
        # Reset session state
        session.reset_plan()

    async def handle_structured_response(self, message, session, response_data):
        """Handle structured JSON response from AI."""
        try:
            if 'command' in response_data:
                # Execute command
                command = response_data['command']
                explanation = response_data.get('explanation', 'No explanation provided')
                
                message_text = f"🔧 **Executing:** `{command}`\n📝 **Explanation:** {explanation}"
                await self.message_sender.reply_safe(message, message_text)
                
                output, error = await self.command_executor.execute_command(command)
                
                if error:
                    await self.message_sender.reply_safe(message, f"❌ {error}")
                else:
                    # Truncate long output
                    output = self.message_sender.safe_truncate(output)
                    output_message = f"✅ **Output:**\n```\n{output}\n```"
                    await self.message_sender.reply_safe(message, output_message)
                    
            elif 'question' in response_data:
                # Ask follow-up question
                question = response_data['question']
                needed_for = response_data.get('needed_for', 'further processing')
                
                session.waiting_for_followup = True
                
                question_message = (
                    f"❓ **Question:** {question}\n"
                    f"📋 **Needed for:** {needed_for}\n\n"
                    f"Please reply with the requested information."
                )
                await self.message_sender.reply_safe(message, question_message)
                
            else:
                # If it's JSON but doesn't contain expected fields, show as text
                await self.message_sender.reply_safe(message, str(response_data))
                
        except Exception as e:
            logger.error(f"Error in handle_structured_response: {str(e)}")
            await self.message_sender.reply_safe(
                message, 
                "❌ An error occurred while processing the structured response."
            )

    async def process_ai_response(self, message, session, ai_response):
        """Process AI response and take appropriate action."""
        try:
            # First try to extract JSON from Markdown code blocks
            json_data = extract_json_from_response(ai_response)
            
            if json_data:
                # If we found JSON, use it
                await self.handle_structured_response(message, session, json_data)
            else:
                # If no JSON found, show the response as is
                await self.message_sender.reply_safe(message, ai_response)
                
        except Exception as e:
            logger.error(f"Error in process_ai_response: {str(e)}")
            await self.message_sender.reply_safe(
                message,
                "❌ An error occurred while processing the AI response."
            )

    async def handle_followup(self, message, session, user_response):
        """Handle follow-up responses from user."""
        session.waiting_for_followup = False
        
        # Show typing action
        try:
            await self.bot.send_chat_action(message.chat.id, 'typing')
        except Exception as e:
            logger.warning(f"Failed to send typing action in followup: {e}")
        
        try:
            # Create follow-up prompt
            followup_prompt = f"User provided the following information: {user_response}. Please continue with the original request."
            
            # Send to Yandex GPT with full history
            response = await self.yandex_gpt.send_prompt(followup_prompt, session.conversation_history)
            
            if "error" in response:
                await self.message_sender.reply_safe(message, f"❌ Error: {response['error']}")
                return
            
            # Process response
            result = response.get('result', {})
            alternatives = result.get('alternatives', [])
            
            if not alternatives:
                await self.message_sender.reply_safe(message, "❌ No response from AI")
                return
                
            ai_response = alternatives[0].get('message', {}).get('text', '')
            
            # Update conversation history
            session.add_message_to_history("user", followup_prompt)
            session.add_message_to_history("assistant", ai_response)
            
            # Process the AI response using the new approach
            await self.process_ai_response(message, session, ai_response)
                
        except Exception as e:
            logger.error(f"Error in handle_followup: {str(e)}")
            await self.message_sender.reply_safe(
                message, 
                "❌ An error occurred while processing your response."
            )

    async def handle_message(self, message):
        """Handle all incoming messages."""
        try:
            # Check user access
            if not await self.check_user_access(message):
                return
                
            user_id = message.from_user.id
            user_message = message.text.strip().lower()
            
            session = self.session_manager.get_session(user_id)
            current_state = session.state
            
            # Handle plan confirmation
            if current_state == PLANNING_STATE:
                if user_message in ['yes', 'y', 'confirm', 'ok', 'proceed']:
                    session.state = EXECUTING_STATE
                    await self.message_sender.reply_safe(message, "🚀 Starting plan execution...")
                    await self.execute_next_step(message)
                    return
                elif user_message in ['no', 'n', 'cancel', 'stop']:
                    session.reset_plan()
                    await self.message_sender.reply_safe(message, "❌ Plan execution cancelled.")
                    return
                else:
                    await self.message_sender.reply_safe(
                        message, 
                        "❓ Please confirm the plan: reply with `yes` to proceed or `no` to cancel."
                    )
                    return
            
            # Handle normal message processing
            if session.waiting_for_followup:
                await self.handle_followup(message, session, user_message)
                return
            
            # Show typing action
            try:
                await self.bot.send_chat_action(message.chat.id, 'typing')
            except Exception as e:
                logger.warning(f"Failed to send typing action: {e}")
            
            original_message = message.text  # Keep original case for the request
            
            # For new conversations, analyze task complexity first
            if not session.conversation_history:
                complexity_result = await self.analyze_task_complexity(message, original_message)
                if complexity_result is not None:
                    # If complexity analysis determined we need a plan, generate it
                    if complexity_result:
                        return
                    # If complexity analysis determined we don't need a plan, continue with normal processing
            
            # Normal message processing
            response = await self.yandex_gpt.send_prompt(original_message, session.conversation_history)
            
            if "error" in response:
                await self.message_sender.reply_safe(message, f"❌ Error: {response['error']}")
                return
            
            # Extract response text
            result = response.get('result', {})
            alternatives = result.get('alternatives', [])
            
            if not alternatives:
                await self.message_sender.reply_safe(message, "❌ No response from AI")
                return
                
            ai_response = alternatives[0].get('message', {}).get('text', '')
            
            # Update conversation history
            session.add_message_to_history("user", original_message)
            session.add_message_to_history("assistant", ai_response)
            
            # Process the AI response
            await self.process_ai_response(message, session, ai_response)
                
        except Exception as e:
            logger.error(f"Error in handle_message: {str(e)}")
            await self.message_sender.reply_safe(
                message, 
                "❌ An error occurred while processing your request."
            )

    async def analyze_task_complexity(self, message, user_request: str) -> Optional[bool]:
        """
        Analyze if a task requires a multi-step plan
        
        Returns:
            bool: True if plan was generated, False if no plan needed, None if analysis failed
        """
        try:
            await self.message_sender.reply_safe(
                message, 
                "🤔 Analyzing task complexity..."
            )
            
            # Show typing action
            await self.bot.send_chat_action(message.chat.id, 'typing')
            
            # Analyze task complexity
            response = await self.yandex_gpt.analyze_task_complexity(user_request)
            
            if "error" in response:
                logger.error(f"Error analyzing task complexity: {response['error']}")
                return None
            
            # Extract response
            result = response.get('result', {})
            alternatives = result.get('alternatives', [])
            
            if not alternatives:
                logger.error("No response from AI for complexity analysis")
                return None
                
            ai_response = alternatives[0].get('message', {}).get('text', '')
            
            # Parse complexity analysis result
            from utils.helpers import extract_json_from_response
            complexity_data = extract_json_from_response(ai_response)
            
            if complexity_data and 'requires_plan' in complexity_data:
                requires_plan = complexity_data['requires_plan']
                reason = complexity_data.get('reason', 'No reason provided')
                estimated_commands = complexity_data.get('estimated_commands', 1)
                
                if requires_plan:
                    await self.message_sender.reply_safe(
                        message,
                        f"🔍 **Analysis:** {reason}\n"
                        f"📊 **Complexity:** High (estimated {estimated_commands} commands)\n\n"
                        f"Generating execution plan..."
                    )
                    # Generate the plan
                    return await self.generate_plan(message, user_request)
                else:
                    await self.message_sender.reply_safe(
                        message,
                        f"✅ **Analysis:** {reason}\n"
                        f"📊 **Complexity:** Low (estimated {estimated_commands} commands)\n\n"
                        f"Proceeding with direct execution..."
                    )
                    return False
            else:
                logger.error("Could not parse complexity analysis result")
                return None
                
        except Exception as e:
            logger.error(f"Error in analyze_task_complexity: {str(e)}")
            await self.message_sender.reply_safe(
                message,
                "❌ Failed to analyze task complexity. Proceeding with direct execution."
            )
            return None 
