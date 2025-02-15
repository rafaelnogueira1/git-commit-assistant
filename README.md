# Git Commit Assistant

AI-powered Git commit assistant that helps you write better commit messages using Google's Gemini AI.

## Features

- 🤖 AI-powered commit message suggestions
- 📝 Conventional commits format with emojis
- 🔍 Smart analysis of your changes
- 🎨 Beautiful CLI interface
- 🔒 Protected branch validation
- 🚀 Optional automatic push

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

1. Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Set your API key:

```bash
export GEMINI_API_KEY='your-api-key'
```

## Usage

Instead of `git commit`, you can use either:

```bash
ga                  # Short command (recommended)
git-commit-assistant  # Full command
```

Available options:

```bash
ga -a               # Stage all changes
ga -p               # Push after commit
ga -f               # Skip confirmations

# Combine options
ga -a -p            # Stage all changes and push
ga -a -p -f         # Stage all, push, and skip confirmations
```

The assistant will:

1. Show your staged/unstaged changes
2. Analyze the changes using AI
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
