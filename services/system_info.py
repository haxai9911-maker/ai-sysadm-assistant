import os
import platform
import socket
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

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
            distro_info = SystemInfo._get_distro_info(system)
            
            # Get current working directory
            cwd = os.getcwd()
            
            # Get user info
            import getpass
            current_user = getpass.getuser()
            
            # Get memory information
            memory_info = await SystemInfo._get_memory_info(system)
            
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
    
    @staticmethod
    def _get_distro_info(system: str) -> str:
        """Get distribution information for Linux systems"""
        if system != "Linux":
            return f"{system} {platform.release()}"
        
        try:
            with open('/etc/os-release', 'r') as f:
                os_release = f.read()
            for line in os_release.split('\n'):
                if line.startswith('PRETTY_NAME='):
                    return line.split('=', 1)[1].strip('"')
            return "Linux (unknown distribution)"
        except:
            return "Linux"
    
    @staticmethod
    async def _get_memory_info(system: str) -> str:
        """Get memory information"""
        memory_info = ""
        if system in ["Linux", "Darwin"]:
            try:
                if system == "Linux":
                    with open('/proc/meminfo', 'r') as f:
                        mem_lines = f.readlines()
                    for line in mem_lines:
                        if line.startswith('MemTotal:'):
                            total_mem_kb = int(line.split()[1])
                            total_mem_gb = round(total_mem_kb / (1024 * 1024), 1)
                            memory_info = f", {total_mem_gb}GB RAM"
                            break
                else:  # Darwin (macOS)
                    result = await asyncio.create_subprocess_shell(
                        'sysctl hw.memsize',
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        shell=True
                    )
                    stdout, stderr = await result.communicate()
                    if stdout:
                        mem_bytes = int(stdout.decode().split(':')[1].strip())
                        total_mem_gb = round(mem_bytes / (1024**3), 1)
                        memory_info = f", {total_mem_gb}GB RAM"
            except:
                pass
        return memory_info