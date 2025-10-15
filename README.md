# 🤖 Yandex GPT CLI Telegram Bot

A powerful Telegram bot that integrates with Yandex GPT to execute CLI commands on your server.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue)
![Yandex GPT](https://img.shields.io/badge/Yandex-GPT-orange)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

### 🤖 AI-Powered Command Generation
- **Natural Language Processing**: Convert natural language requests into CLI commands
- **Yandex GPT Integration**: Leverages Yandex's powerful language model
- **OS-Aware Commands**: Automatically generates commands appropriate for your operating system
- **Smart Explanations**: Provides clear explanations for each command

### 🔧 Advanced Execution
- **Multi-Step Planning**: Handles complex tasks with automated step-by-step execution plans
- **Real-time Execution**: Runs commands directly on your server
- **Progress Tracking**: Monitors execution with detailed progress reports
- **Automatic Step Progression**: Seamlessly moves between plan steps

### 🔒 Security & Safety
- **User Whitelist**: Restrict access to specific Telegram usernames
- **Command Validation**: Blocks dangerous and harmful commands
- **Execution Timeouts**: Prevents hanging processes
- **Comprehensive Logging**: Detailed audit trails for all operations

### 💬 Smart Interaction
- **Conversation Memory**: Maintains context across multiple messages
- **Follow-up Questions**: Asks for additional information when needed
- **Markdown Support**: Beautifully formatted responses with code blocks
- **Multi-User Support**: Handles multiple users simultaneously

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- Yandex Cloud account with GPT API access
- Server with CLI access

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd sysadm-bot
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

```bash
cp .env.example .env
# Edit .env with your credentials
```

# Configuration

Create `.env` file with your credentials:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Yandex GPT Configuration
YANDEX_API_KEY=your_yandex_gpt_api_key_here
YANDEX_FOLDER_ID=your_yandex_folder_id_here

# Security Configuration (Optional)
ALLOWED_USERS=username1,username2,username3
```

## Getting credentials

### Telegram Bot Token:

1. Message @BotFather on Telegram
2. Use `/newbot` command
3. Follow the instructions to create your bot
4. Copy the provided token

### Yandex GPT Credentials:

1. Go to Yandex Cloud Console
2. Create a new cloud or select existing one
3. Enable the "Yandex GPT" service
4. Create an API key in "Service accounts" section
5. Copy the Folder ID from your cloud overview

## Running the Bot

```bash
python bot.py
```

The bot will start and display system information. You should see:

```text
🤖 Bot is starting...
🖥️ System Information:
[Your system details]
🔐 Whitelist: [Status]
🔄 Multi-step planning feature: ENABLED
```

## 📖 Usage

### Basic Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize the bot and show welcome message |
| `/help` | Display help information and usage guide |
| `/status` | Show bot status and active sessions |
| `/system` | Display detailed system information |
| `/clear` | Clear conversation history |
| `/cancel` | Cancel current operation |

### Simple Task Examples

**File Operations:**

```
"List all files in current directory"
"Find large files in /var/log"
"Show disk usage by folder"
```

**System Monitoring:**

```
"Check disk space"
"Show running processes"
"Display memory usage"
"Check network connections"
```

**User Management:**

```
"List logged in users"
"Show system uptime"
"Check service status"
```


### Complex Task Examples

The bot automatically detects complex requests and creates execution plans:

**Multi-step Operations:**

```
"Set up disk monitoring with alerts"
"Backup website files and database"
"Analyze system performance and generate report"
"Clean up temporary files and optimize storage"
```

**Example Plan Execution:**

```
User: "Set up monitoring for disk space and alert when it's low"

Bot: 🔍 This looks like a complex task. Generating an execution plan...

📋 Execution Plan

Overview: Set up disk space monitoring with alert system
Estimated Time: 5-10 minutes
Risks: Requires cron access, may need mail system setup

Steps (4 total):

Step 1: Check current disk usage and identify partitions
Expected: List of partitions with usage percentages

Step 2: Create disk monitoring script
Expected: Bash script that checks disk usage

Step 3: Set up cron job for regular monitoring
Expected: Automated monitoring every hour

Step 4: Configure alert mechanism
Expected: Email or notification when threshold exceeded

Do you want to execute this plan?
Reply with yes to proceed or no to cancel.
```


### Plan Confirmation Commands

**To approve a plan:**
- `yes`
- `y` 
- `confirm`
- `ok`
- `proceed`

**To reject a plan:**
- `no`
- `n`
- `cancel`
- `stop`

