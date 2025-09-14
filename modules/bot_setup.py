import telebot.async_telebot as telebot
from .config import TELEGRAM_TOKEN


bot = telebot.AsyncTeleBot(TELEGRAM_TOKEN, parse_mode=None)
context_manager = None
whisper_model = None
