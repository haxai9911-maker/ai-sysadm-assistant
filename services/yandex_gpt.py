import aiohttp
import logging
from typing import Dict, Optional, List
import platform

from services.system_info import SystemInfo

logger = logging.getLogger(__name__)

class YandexGPTClient:
    def __init__(self, api_key: str, folder_id: str):
        self.api_key = api_key
        self.folder_id = folder_id
        self.api_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        self.system_info = None
        
    async def initialize_system_info(self):
        """Initialize system information once"""
        if self.system_info is None:
            self.system_info = await SystemInfo.get_system_info()
    
    async def analyze_task_complexity(self, user_request: str) -> Dict:
        """
        Analyze if a task requires a multi-step plan or can be done with a single command
        
        Returns:
            Dict with 'requires_plan' (bool) and 'reason' (str)
        """
        # Ensure system info is initialized
        await self.initialize_system_info()
        
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }
        
        complexity_prompt = {
            "role": "system",
            "text": f"""You are an expert system administrator. Analyze if the user's request requires a multi-step execution plan or can be completed with a single CLI command.

SYSTEM INFORMATION:
{self.system_info}

TASK ANALYSIS GUIDELINES:
- A task requires a plan if it involves multiple distinct operations
- A task requires a plan if it has dependencies between steps
- A task requires a plan if it involves configuration changes
- A task requires a plan if it involves multiple system components
- A task does NOT require a plan if it can be done with one command
- A task does NOT require a plan if it's a simple query or status check

EXAMPLES OF SIMPLE TASKS (no plan needed):
- "list files in current directory" -> single `ls` command
- "check disk space" -> single `df -h` command  
- "show running processes" -> single `ps aux` command
- "display memory usage" -> single `free -h` command

EXAMPLES OF COMPLEX TASKS (plan needed):
- "set up disk monitoring with alerts" -> multiple steps
- "backup website and database" -> multiple steps
- "analyze system performance and generate report" -> multiple steps
- "clean up temporary files and optimize storage" -> multiple steps

RESPONSE FORMAT:
Respond with PURE JSON (without any markdown formatting) containing:
{{
    "requires_plan": true/false,
    "reason": "Brief explanation of why the task does/doesn't require a plan",
    "estimated_commands": 1  // Estimated number of commands needed
}}

IMPORTANT:
- Be conservative - only recommend plans for truly complex tasks
- Consider the current system environment
- NEVER use markdown code blocks (```) in your responses
- ALWAYS respond with pure JSON"""
        }
        
        messages = [complexity_prompt, {"role": "user", "text": f"Analyze this task: {user_request}"}]
        
        data = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.1,  # Low temperature for consistent analysis
                "maxTokens": 500
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
        
    async def send_prompt(self, prompt: str, conversation_history: List[Dict] = None, plan_mode: bool = False) -> Dict:
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
- Create practical, safe steps appropriate for the current system
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
