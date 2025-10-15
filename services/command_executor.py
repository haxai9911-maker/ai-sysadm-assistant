import asyncio
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class CommandExecutor:
    """Class to safely execute CLI commands"""
    
    DANGEROUS_PATTERNS = [
        'rm -rf', 'format', 'dd', 'mkfs', '> /dev/sd', ':(){:|:&};:', 
        'chmod 777', 'passwd', 'adduser', 'useradd', 'deluser', 
        'chown root', 'chgrp root', 'visudo', 'crontab -r'
    ]
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    async def execute_command(self, command: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Execute CLI command and return output
        
        Args:
            command: The command to execute
            
        Returns:
            tuple: (output, error) - if successful, output contains result, otherwise error contains error message
        """
        try:
            # Security check - prevent dangerous commands
            if self._is_dangerous_command(command):
                return None, "Error: Command contains potentially dangerous operations"
            
            # Execute command with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout)
            
            output = stdout.decode('utf-8', errors='ignore') if stdout else ""
            error = stderr.decode('utf-8', errors='ignore') if stderr else ""
            
            if process.returncode != 0:
                return None, f"Command failed with return code {process.returncode}: {error}"
                
            return output, None
            
        except asyncio.TimeoutError:
            return None, f"Command timed out after {self.timeout} seconds"
        except Exception as e:
            return None, f"Error executing command: {str(e)}"
    
    def _is_dangerous_command(self, command: str) -> bool:
        """Check if command contains dangerous patterns"""
        return any(pattern in command for pattern in self.DANGEROUS_PATTERNS)