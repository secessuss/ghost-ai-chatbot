import google.generativeai as genai
import logging
import io
from PIL import Image
from . import config
from .bot_setup import context_manager
from .utils import safe_get_response_text, get_gemini_model


async def generate_response_from_image_stream(user_id: int, user_prompt: str, image_bytes: bytes):
    context_data = await context_manager.get_context(user_id)
    history = context_data['history']
    
    model = await get_gemini_model()
    if not model:
        yield {'type': 'text', 'data': "🕒 Sistem sedang sibuk. Coba lagi beberapa saat lagi."}
        return
    
    try:
        try:
            img = Image.open(io.BytesIO(image_bytes))
        except Exception as img_e:
            logging.error(f"Gagal membuka gambar: {img_e}")
            yield {'type': 'text', 'data': "❌ Gagal memproses gambar."}
            return
        
        prompt_text = user_prompt if user_prompt else "Jelaskan gambar ini."
        history_for_request = history + [{'role': 'user', 'parts': [prompt_text, img]}]
        
        response_stream = await model.generate_content_async(
            history_for_request,
            stream=True,
            safety_settings=config.SAFETY_SETTINGS
        )
        
        full_response_text = ""
        async for chunk in response_stream:
            text = await safe_get_response_text(chunk)
            if "ERROR_" not in text:
                full_response_text += text
                yield {'type': 'text', 'data': text}

        if not full_response_text:
             yield {'type': 'text', 'data': "Saya tidak dapat memberikan respons terkait gambar ini karena pembatasan sistem."}
             return
        
        history.append({'role': 'user', 'parts': [f"(Menganalisis gambar) {prompt_text}"]})
        history.append({'role': 'model', 'parts': [full_response_text]})
        await context_manager.save_context(
            user_id, 
            history, 
            context_data.get('active_session_name'), 
            context_data.get('session_files', {})
        )
        yield {'type': 'stream_end', 'full_text': full_response_text}
        return
    
    except Exception as e:
        logging.error(f"Unexpected error in generate_response_from_image_stream: {e}")
        yield {'type': 'text', 'data': "⚠️ Terjadi gangguan teknis saat menganalisis gambar."}