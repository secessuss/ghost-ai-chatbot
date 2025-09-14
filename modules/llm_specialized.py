import google.generativeai as genai
import logging
from . import config
from .prompt import IMAGE_GENERATION_PROMPT
from .utils import safe_get_response_text, get_gemini_model


async def _run_specialized_task(prompt: str) -> str:
    model = await get_gemini_model()
    if not model:
        return "🤖 Sistem sedang sibuk. Coba beberapa saat lagi."
    
    try:
        response = await model.generate_content_async(
            prompt, 
            safety_settings=config.SAFETY_SETTINGS
        )
        result = await safe_get_response_text(response)
        
        if "ERROR_SAFETY" in result:
            return "🔒 Respons diblokir karena kebijakan sistem."
        elif "ERROR_" in result:
            return "⚠️ Terjadi kesalahan pada sistem."
        return result
    
    except Exception as e:
        logging.error(f"Unexpected error on specialized task: {e}")
        return "⚠️ Terjadi kesalahan teknis."

async def generate_image_prompt_with_gemini(user_description: str) -> str:
    logging.info(f"Generating image prompt for: '{user_description}'")
    final_prompt = f"{IMAGE_GENERATION_PROMPT}\n\nDeskripsi Pengguna: \"{user_description}\""
    return await _run_specialized_task(final_prompt)