import os
from dotenv import load_dotenv


load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_KEYS = [
    key.strip() 
    for key in os.getenv("GEMINI_API_KEYS", "").split(',') 
    if key.strip()
]

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN tidak ditemukan di file .env atau environment variables.")

if not GEMINI_API_KEYS:
    raise ValueError("GEMINI_API_KEYS tidak ditemukan. Pastikan ada setidaknya satu key.")

current_api_key_index = 0

def get_gemini_api_key():
    global current_api_key_index
    return GEMINI_API_KEYS[current_api_key_index]

def rotate_gemini_api_key():
    global current_api_key_index
    current_api_key_index = (current_api_key_index + 1) % len(GEMINI_API_KEYS)
    print(f"API Key diputar. Menggunakan key index: {current_api_key_index}")
    return current_api_key_index

SAFETY_SETTINGS = {
    'HARM_CATEGORY_HARASSMENT': 'block_none',
    'HARM_CATEGORY_HATE_SPEECH': 'block_none',
    'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'block_none',
    'HARM_CATEGORY_DANGEROUS_CONTENT': 'block_none',
}