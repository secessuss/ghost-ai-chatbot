import asyncio
import logging
import google.generativeai as genai
from . import config
from .bot_setup import bot
from telebot.asyncio_helper import ApiTelegramException
from telebot.types import Message


async def send_or_edit_message(
    chat_id: int, 
    text: str, 
    placeholder_message: Message = None, 
    **kwargs
) -> Message:
    
    try:
        if placeholder_message:
            return await bot.edit_message_text(
                text, 
                chat_id, 
                placeholder_message.message_id, 
                **kwargs
            )
        else:
            return await bot.send_message(chat_id, text, **kwargs)
        
    except ApiTelegramException as e:
        if "message is not modified" not in str(e):
            logging.warning(f"Gagal mengirim/mengedit pesan: {e}")
        return placeholder_message
    
async def get_gemini_model():
    initial_key_index = config.current_api_key_index
    
    while True:
        try:
            api_key = config.get_gemini_api_key()
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(config.GEMINI_MODEL)
            return model
        
        except Exception as e:
            if "API key" in str(e) or "Resource has been exhausted" in str(e) or "quota" in str(e).lower():
                logging.warning(f"API Key error: {e}")
                if config.rotate_gemini_api_key() == initial_key_index:
                    logging.error("Semua kunci API Gemini telah gagal.")
                    return None
            else:
                logging.error(f"Error tak terduga saat inisialisasi model Gemini: {e}", exc_info=True)
                return None
            
async def safe_get_response_text(response):

    try:
        if hasattr(response, 'candidates'):
            all_parts = []
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                         if hasattr(part, 'text'):
                            all_parts.append(part.text)

            if all_parts:
                return "".join(all_parts)
            
        if hasattr(response, '_result') and hasattr(response._result, 'candidates'):
             return await safe_get_response_text(response._result)
        
    except (ValueError, AttributeError, IndexError):
        pass

    try:
        finish_reason = response.candidates[0].finish_reason
        if str(finish_reason) == "FinishReason.SAFETY":
            return "ERROR_SAFETY"
        if str(finish_reason) == "FinishReason.RECITATION":
            return "ERROR_RECITATION"
        
    except (AttributeError, IndexError):
        pass    
    return "ERROR_EMPTY"