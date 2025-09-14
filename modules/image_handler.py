import aiohttp
import os
from dotenv import load_dotenv


load_dotenv()

HF_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

async def generate_image_from_hf(prompt: str):
    if not HF_API_TOKEN:
        print("Error: HUGGINGFACE_API_TOKEN tidak ditemukan.")
        return "⚙️ Fitur pembuatan gambar belum dikonfigurasi oleh pemilik bot."
    
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {"inputs": prompt}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                API_URL, 
                headers=headers, 
                json=payload, 
                timeout=120
            ) as response:
                if response.status == 200 and response.headers.get('content-type') == 'image/jpeg':
                    return await response.read()
                else:
                    error_message = await response.json()
                    print(f"Hugging Face API Error: {error_message}")
                    
                    if 'error' in error_message:
                        if 'is currently loading' in error_message['error']:
                            return "⏳ Model sedang dimuat. Coba lagi."
                        return "🖼️❎ Gagal membuat gambar karena gangguan teknis."
                    
                    return "🖼️❎ Gagal membuat gambar karena respons tidak valid."
                
    except aiohttp.ClientTimeout:
        return "Waktu tunggu habis saat mencoba membuat gambar. Silakan coba lagi."
    except Exception as e:
        print(f"An unexpected error occurred with HF API: {e}")
        return "⚠️ Terjadi kesalahan tak terduga."