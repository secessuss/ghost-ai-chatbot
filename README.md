# GHOST - AI Telegram Bot

GHOST is an AI chatbot for Telegram designed to be an analytical and insightful discussion partner. The bot can understand conversational context, process various types of media, and connect to the internet to provide relevant and up-to-date information.

## Key Features

- **Contextual Conversation**: Manages conversation history to provide relevant and continuous responses.
- **Multimedia Analysis**: Can analyze and explain images sent by users.
- **Document Processing**: Reads and extracts text from various file formats, including PDF, DOCX, PPTX, and spreadsheets (CSV, XLSX).
- **Web Integration**: Can access content from URLs and perform web searches using DuckDuckGo to answer questions about current events.
- **Voice Message Transcription**: Converts voice messages into text using OpenAI's Whisper model for further processing.
- **Image Generation**: Generates images based on text descriptions using models from Hugging Face.
- **Session Management**: Manages context from files and web searches in separate sessions that can be activated or ended by users.

## Technologies Used

- **Language**: Python 3
- **Main Libraries**:
  - `pyTelegramBotAPI` for interaction with the Telegram API.
  - `google-generativeai` as the main language model (LLM).
  - `openai-whisper` for audio transcription.
  - `duckduckgo-search` for web search.
  - `Pillow`, `PyMuPDF`, `python-docx`, `python-pptx`, `pandas` for file processing.
  - `aiosqlite` for local database (context storage).
  - `aiohttp` for asynchronous HTTP requests.

## Installation and Setup

Follow these steps to run the bot in your local environment.

### 1. Prerequisites

- Python 3.10 or newer.
- A Telegram account and bot token.
- API keys from Google AI (Gemini) and Hugging Face.

### 2. Clone the Repository

```bash
git clone https://github.com/secessuss/ghost-ai-chatbot.git
cd ghost-ai-chatbot
```

### 3. Set Up Virtual Environment

It is highly recommended to use a virtual environment.

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
.\venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

### 4. Install Dependencies

Install all required libraries using `requirements.txt`.

```bash
pip install -r requirements.txt
```

### 5. Configure Environment

Create a new file named `.env` in the project root directory. Fill it with your API keys.

```env
# Replace with your Telegram bot token
TELEGRAM_BOT_TOKEN="7323298469:AAHGYR..."

# Enter one or more Gemini API keys, separated by commas
GEMINI_API_KEYS="AIzaSy...ZuY,AIzaSy...v-U"

# Enter your Hugging Face API token for image generation
HUGGINGFACE_API_TOKEN="hf_XWGUQXFsJkrt..."
```

**Important**: Never share your `.env` file or upload it to a public repository. This file is already included in `.gitignore` to prevent data leaks.

## Running the Bot

Once everything is configured, run the bot with the following command:

```bash
python main.py
```

The bot will start and be ready to receive messages on Telegram. You can stop it by pressing `Ctrl+C` in the terminal.

## License

This project is licensed under the **MIT License**. See the [LICENSE](./LICENSE) file for more details.
