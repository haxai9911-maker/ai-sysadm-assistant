import json
import re
from typing import Optional, Dict

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

def get_complexity_examples() -> str:
    """Get examples of complex vs simple tasks for the AI"""
    return """
SIMPLE TASKS (single command, no plan needed):
- "list files in current directory" -> ls -la
- "check disk space" -> df -h
- "show running processes" -> ps aux
- "display memory usage" -> free -h
- "check network connections" -> netstat -tuln
- "show system uptime" -> uptime
- "list logged in users" -> who
- "check current directory" -> pwd

COMPLEX TASKS (multiple steps, plan needed):
- "set up disk monitoring with alerts"
- "backup website files and database"
- "analyze system performance and generate report"
- "clean up temporary files and optimize storage"
- "set up automated backups"
- "monitor and alert on high CPU usage"
- "configure firewall rules for web server"
- "migrate database to new server"
"""

