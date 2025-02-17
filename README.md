# Git Commit Assistant

AI-powered Git commit assistant that helps you write better commit messages using multiple AI services.

## Features

- 🤖 Multiple AI services support (Gemini, GPT-4, Claude, Deepseek)
- 📝 Conventional commits format with emojis
- 🔍 Smart analysis of your changes
- 🎨 Beautiful CLI interface
- 🔒 Protected branch validation
- 🚀 Optional automatic push
- 🔐 Secure API key storage using system keyring

## Installation

### Via NPM (Recommended)

```bash
npm install -g git-commit-assistant
```

The installation will automatically create a Python virtual environment and install all dependencies.

### Updating

To update to the latest version:

```bash
npm install -g git-commit-assistant@latest
```

### Via Python (Alternative)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Unix/macOS:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate

# Install package
pip3 install git-commit-assistant
```

## Setup

1. Choose your preferred AI service and get the API key:

   - [Google AI Studio](https://makersuite.google.com/app/apikey) for Gemini (default)
   - [OpenAI](https://platform.openai.com/api-keys) for GPT-4
   - [Anthropic](https://console.anthropic.com/account/keys) for Claude
   - [Deepseek](https://platform.deepseek.com/) for Deepseek

2. Configure your API key:

```bash
# Interactive configuration (recommended)
gcommit --configure

# Or set environment variables
export GEMINI_API_KEY='your-api-key'      # For Gemini
export OPENAI_API_KEY='your-api-key'      # For OpenAI
export ANTHROPIC_API_KEY='your-api-key'   # For Claude
export DEEPSEEK_API_KEY='your-api-key'    # For Deepseek
```

3. Select your AI service:

```bash
# Check current configuration
gcommit --list

# Use specific service for one commit
gcommit -s openai   # or gemini, claude, deepseek

# Set default service
export AI_SERVICE='openai'  # or gemini, claude, deepseek
```

## Usage

Instead of `git commit`, you can use either:

```bash
gcommit              # Short command (recommended)
git-commit-assistant # Full command
```

Available options:

```bash
gcommit -a          # Stage all changes
gcommit -p          # Push after commit
gcommit -f          # Skip confirmations
gcommit -s openai   # Use OpenAI service
gcommit -c          # Configure AI service and API key
gcommit -l          # Show current AI service configuration

# Combine options
gcommit -a -p       # Stage all changes and push
gcommit -a -p -f    # Stage all, push, and skip confirmations
gcommit -a -s claude # Stage all and use Claude
```

The assistant will:

1. Show your staged/unstaged changes
2. Analyze the changes using the selected AI service
3. Suggest a commit message following conventional commits
4. Let you edit or accept the message
5. Create the commit (and push if requested)

## Requirements

- Python 3.6+
- Node.js 14+ (for NPM installation)
- Git

## License

MIT

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.
