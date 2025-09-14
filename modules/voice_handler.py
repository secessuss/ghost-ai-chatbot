import os
import asyncio
import aiofiles
import logging
from .bot_setup import bot, whisper_model


async def process_voice_message(message):
    if whisper_model is None:
        logging.error("Model Whisper tidak tersedia, transkripsi dibatalkan.")
        return "Maaf, fitur pesan suara sedang tidak dapat digunakan saat ini."
    voice_ogg_path = f"voice_{message.from_user.id}_{message.message_id}.ogg"
    
    try:
        file_info = await bot.get_file(message.voice.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        async with aiofiles.open(voice_ogg_path, 'wb') as new_file:
            await new_file.write(downloaded_file)
        
        def transcribe_sync():
            return whisper_model.transcribe(voice_ogg_path, language='id', fp16=False)
        
        result = await asyncio.to_thread(transcribe_sync)
        transcribed_text = result['text']
        return transcribed_text
    
    except Exception as e:
        logging.error(f"Error saat memproses pesan suara: {e}", exc_info=True)
        return None
    
    finally:
        if os.path.exists(voice_ogg_path):
            os.remove(voice_ogg_path)
