import os
import sys
import signal
import asyncio
import logging
import subprocess
import whisper
from dotenv import load_dotenv
from telebot.types import BotCommand
from telebot.asyncio_helper import ApiTelegramException


async def set_bot_commands(bot):
    commands = [
        BotCommand("menu", "⚙️ Buka Menu Fitur"),
    ]
    await bot.set_my_commands(commands)
    logging.info("Menu perintah bot telah diatur.")
    
async def main():
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    load_dotenv()

    import modules.bot_setup
    logging.info("Memuat model Whisper...")

    try:
        model_instance = whisper.load_model("tiny")
        modules.bot_setup.whisper_model = model_instance
        logging.info("Model Whisper berhasil dimuat dan siap digunakan.")
    except Exception as e:
        logging.error(f"Gagal memuat model Whisper. Fitur pesan suara tidak akan berfungsi. Error: {e}")
        modules.bot_setup.whisper_model = None

    from modules.context_manager import ContextManager, DB_FILE
    context_manager_instance = ContextManager(DB_FILE)
    modules.bot_setup.context_manager = context_manager_instance
    logging.info("Menginisialisasi database...")
    await context_manager_instance._init_db()
    logging.info("Database siap.")
    
    import modules.handlers 
    from modules.bot_setup import bot
    await set_bot_commands(bot)
    required_vars = ["TELEGRAM_BOT_TOKEN", "GEMINI_API_KEYS"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logging.critical(f"Error: Variabel environment berikut tidak ditemukan: {', '.join(missing_vars)}.")
        return
    
    if not os.getenv("HUGGINGFACE_API_TOKEN"):
        logging.warning("Warning: HUGGINGFACE_API_TOKEN tidak ditemukan. Fitur pembuatan gambar tidak akan berfungsi.")

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def signal_handler(sig, frame):
        print('\nBot sedang berhenti... (Ctrl+C ditekan)')
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    logging.info("Bot sedang berjalan...")
    task = loop.create_task(bot.infinity_polling(timeout=60))
    await stop_event.wait()
    logging.info("Menghentikan polling bot...")
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        logging.info("Task polling berhasil dibatalkan.")
    logging.info("Bot telah berhenti.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nBot dihentikan oleh pengguna.")
    except Exception as e:
        logging.critical(f"CRITICAL ERROR: Terjadi kesalahan tak terduga di level atas: {e}", exc_info=True)