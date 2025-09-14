import google.generativeai as genai
import logging
import asyncio
import json
import re
from typing import List, Dict
from . import config
from .bot_setup import context_manager
from .context_manager import get_current_date_str
from .search_handler import search_web
from .llm_specialized import generate_image_prompt_with_gemini
from .image_handler import generate_image_from_hf
from .utils import safe_get_response_text, get_gemini_model


logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s'
)

async def _summarize_text_async(text_to_summarize: str) -> str:
    model = await get_gemini_model()
    if not model:
        return text_to_summarize
    
    try:
        logging.info(f"Meringkas teks dengan panjang {len(text_to_summarize)} karakter.")
        summarization_prompt = (
            f"Ringkas teks berikut menjadi jawaban yang padat dan naratif, "
            f"pertahankan semua poin kunci:\n\n---\n{text_to_summarize}\n---"
        )
        response = await model.generate_content_async(
            summarization_prompt, 
            safety_settings=config.SAFETY_SETTINGS
        )
        summarized_text = await safe_get_response_text(response)
        
        if "ERROR_" not in summarized_text and summarized_text.strip():
            logging.info(f"Peringkasan berhasil. Panjang baru: {len(summarized_text)}")
            return summarized_text
        else:
            logging.warning("Peringkasan gagal, kembali ke teks asli.")
            return text_to_summarize
        
    except Exception as e:
        logging.error(f"Error saat peringkasan: {e}")
        return text_to_summarize
    
async def _run_image_generation_task(user_prompt: str):
    yield {'event': 'EXTRACTING_DESCRIPTION'}
    model = await get_gemini_model()
    if not model:
        yield {'type': 'text', 'data': "🕒 Sistem sedang sibuk. Coba lagi nanti."}
        return
    
    try:
        description_prompt = (
            f"Ekstrak deskripsi gambar dari permintaan ini: \"{user_prompt}\". "
            f"Jawab HANYA dengan deskripsi gambarnya."
        )
        response = await model.generate_content_async(description_prompt)
        description = (await safe_get_response_text(response)).strip()
        
        if not description or "ERROR" in description:
            yield {'type': 'text', 'data': "Saya tidak mengerti gambar apa yang Anda ingin saya buat."}
            return
        
        yield {'event': 'GENERATING_PROMPT', 'data': description}
        enhanced_prompt = await generate_image_prompt_with_gemini(description)
        
        if "Error" in enhanced_prompt or "sibuk" in enhanced_prompt or "teknis" in enhanced_prompt:
             yield {'type': 'text', 'data': f"Gagal untuk: {enhanced_prompt}"}
             return
        yield {'event': 'GENERATING_IMAGE'}

        image_data = await generate_image_from_hf(enhanced_prompt)
        
        if isinstance(image_data, bytes):
            yield {'type': 'image', 'data': image_data, 'caption': description}
        else:
            yield {'type': 'text', 'data': f"Gagal membuat gambar: {image_data}"}

    except Exception as e:
        logging.error(f"Error tak terduga di _run_image_generation_task: {e}", exc_info=True)
        yield {'type': 'text', 'data': "⚠️ Terjadi gangguan teknis."}

async def _run_research(model: genai.GenerativeModel, user_prompt: str, history: List[dict]):
    history_text = "\n".join([
        f"{item['role']}: {item['parts'][0]}" 
        for item in history 
        if 'parts' in item and item['parts']
    ])
    
    multi_query_prompt = (
        f'Anda adalah ahli strategi riset. Berdasarkan percakapan ini:\n---\n{history_text}\n---\n'
        f'Dan permintaan terakhir: "{user_prompt}", buatlah daftar JSON berisi 5-6 kueri pencarian '
        f'Google yang beragam dan spesifik untuk mendapatkan jawaban komprehensif. '
        f'Contoh: ["kueri 1", "kueri 2"]'
    )
    
    search_queries = []
    try:
        response = await model.generate_content_async(multi_query_prompt)
        response_text = await safe_get_response_text(response)
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        
        if json_match:
            search_queries = json.loads(json_match.group(0))

        if not isinstance(search_queries, list) or not all(isinstance(q, str) for q in search_queries):
            raise ValueError("Format JSON tidak valid")
        
        logging.info(f"Kueri riset awal yang dibuat: {search_queries}")

    except (json.JSONDecodeError, ValueError, AttributeError) as e:
        logging.warning(f"Gagal membuat multi-kueri, kembali ke kueri tunggal. Error: {e}")
        search_queries = [user_prompt]

    if len(search_queries) > 1:
        deduplication_prompt = (
            f'Dari daftar kueri pencarian JSON berikut, hapus atau gabungkan item yang sangat mirip '
            f'dan kemungkinan akan menghasilkan hasil yang sama. Jaga agar tetap 5-6 kueri terbaik. '
            f'Kembalikan HANYA daftar JSON yang telah disempurnakan.\n\n'
            f'Daftar Awal: {json.dumps(search_queries)}'
        )
        
        try:
            response = await model.generate_content_async(deduplication_prompt)
            response_text = await safe_get_response_text(response)
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            
            if json_match:
                refined_queries = json.loads(json_match.group(0))
                if isinstance(refined_queries, list) and refined_queries:
                    search_queries = refined_queries
                    logging.info(f"Kueri yang disempurnakan: {search_queries}")

        except (json.JSONDecodeError, ValueError, AttributeError) as e:
            logging.warning(f"Gagal menyempurnakan kueri, menggunakan daftar awal. Error: {e}")

    combined_results = []
    processed_urls = set()
    queries_str = ", ".join(search_queries)
    
    for query in search_queries:
        yield {'event': 'RESEARCH_QUERY', 'data': query}
        results_list = await search_web(query)
        
        for result in results_list:
            url = result.get('url')
            if url and url not in processed_urls:
                combined_results.append(result)
                processed_urls.add(url)

    if not combined_results:
        yield {'type': 'text', 'data': "Tidak ditemukan hasil pencarian yang relevan di web."}
        return
    yield {'type': 'add_to_context', 'query': queries_str, 'results': combined_results}

async def generate_response_stream(user_id: int, user_prompt: str):
    model = await get_gemini_model()
    if not model:
        yield {'type': 'text', 'data': "🕒 Sistem sedang sibuk karena semua kunci API gagal. Coba lagi beberapa saat lagi."}
        return
    
    try:
        context_data = await context_manager.get_context(user_id)
        history = context_data['history']
        
        session_files = context_data.get('session_files', {})
        file_context_summary = ""
        if session_files:
            file_names = ", ".join([f"`{name}`" for name in session_files.keys()])
            file_context_summary = f"\nKonteks Sesi Saat Ini: Pengguna telah menambahkan file berikut: {file_names}."

        history_text = "\n".join([
            f"{item['role']}: {item['parts'][0]}" 
            for item in history 
            if 'parts' in item and item['parts']
        ])
        history_text += file_context_summary

        strategy_prompt = f"""
        Analisis permintaan terakhir pengguna berdasarkan riwayat percakapan dan konteks sesi untuk menentukan tindakan terbaik.

        Permintaan Terakhir Pengguna: "{user_prompt}"

        Riwayat & Konteks Sesi:
        ---
        {history_text}
        ---

        Berdasarkan ini, pilih HANYA SATU dari label berikut:
        - "CONTEXT_SPECIFIC_QUESTION": Jika pengguna mengajukan pertanyaan yang secara langsung merujuk pada konten file atau tautan yang ada dalam sesi.
        - "CODE_GENERATION": Jika pengguna secara eksplisit meminta untuk menulis, membuat, atau memberikan kode.
        - "NEEDS_RESEARCH": Jika pengguna meminta informasi baru yang jelas tidak ada dalam riwayat atau konteks file.
        - "IMAGE_GENERATION": Jika pengguna secara eksplisit meminta untuk membuat atau menghasilkan gambar.
        - "ANSWER_IN_HISTORY": Jika riwayat percakapan kemungkinan besar sudah berisi jawaban.
        - "CASUAL_CONVERSATION": Untuk sapaan atau pertanyaan yang tidak memerlukan memori atau konteks.
        """
        
        strategy_response = await model.generate_content_async(strategy_prompt)
        strategy = (await safe_get_response_text(strategy_response)).strip().upper()
        logging.info(f"Strategi yang dipilih: {strategy}")
        
        if "NEEDS_RESEARCH" in strategy or ("CODE_GENERATION" in strategy and not session_files):
            yield {'event': 'RESEARCH_START'}
            research_generator = _run_research(model, user_prompt, history)

            async for research_event in research_generator:
                if research_event.get('type') == 'add_to_context':
                    await context_manager.add_web_search_to_session(
                        user_id, 
                        research_event['query'], 
                        research_event['results']
                    )
                elif research_event.get('type') == 'text':
                    yield research_event
                    return
                else:
                    yield research_event

        elif "IMAGE_GENERATION" in strategy:
            async for result in _run_image_generation_task(user_prompt):
                yield result
            return
        yield {'event': 'GENERATION_START'}
        
        final_context = await context_manager.get_session_files_context(user_id)
        final_prompt_text = ""

        if final_context:
            final_prompt_text = (
                f"Gunakan informasi dari konteks tambahan berikut untuk membantu menjawab pertanyaan pengguna secara lebih mendalam dan akurat. "
                f"Tetaplah berperan sebagai GHOST, partner diskusi yang analitis.\n\n"
                f"--- KONTEKS TAMBAHAN (Dari File, Tautan, atau Pencarian Web) ---\n{final_context}\n--- AKHIR KONTEKS ---\n\n"
                f"Pertanyaan Pengguna: {user_prompt}"
            )
            logging.info("Menambahkan konteks (file/web) ke dalam prompt.")
        else:
            final_prompt_text = user_prompt
            logging.info("Tidak ada konteks tambahan, menggunakan prompt pengguna secara langsung.")

        if "ANSWER_IN_HISTORY" in strategy or "CASUAL_CONVERSATION" in strategy:
             final_prompt_text = (
                f"Anda sedang dalam percakapan. Permintaan terakhir pengguna adalah: \"{user_prompt}\"\n\n"
                f"TUGAS PENTING: Jawab permintaan pengguna. Namun, JANGAN HANYA MENGULANG jawaban Anda sebelumnya jika pengguna menanyakan pertanyaan yang sama atau serupa lagi. "
                f"Asumsikan mereka tidak puas dan menginginkan jawaban yang lebih baik atau lebih detail. "
                f"Jika Anda benar-benar tidak bisa memberikan detail lebih lanjut, nyatakan hal itu dengan jelas menggunakan kalimat yang baru."
            )
             logging.info("Menggunakan instruksi anti-pengulangan untuk percakapan.")

        history_for_api = history + [{'role': 'user', 'parts': [final_prompt_text]}]

        response_stream = await model.generate_content_async(
            history_for_api, 
            stream=True, 
            safety_settings=config.SAFETY_SETTINGS
        )

        full_response_text = ""
        async for chunk in response_stream:
            text = await safe_get_response_text(chunk)
            if "ERROR_" not in text:
                full_response_text += text
                yield {'type': 'text', 'data': text}
            else:
                logging.warning(f"Potongan stream diblokir: {text}")

        if not full_response_text:
             yield {'type': 'text', 'data': "Saya tidak dapat memberikan respons karena pembatasan sistem."}
             return
        
        history.append({'role': 'user', 'parts': [user_prompt]})
        history.append({'role': 'model', 'parts': [full_response_text]})
        await context_manager.save_context(
            user_id, 
            history, 
            context_data.get('active_session_name'), 
            context_data.get('session_files', {})
        )
        yield {'type': 'stream_end', 'full_text': full_response_text}

    except Exception as e:
        logging.error(f"Error tak terduga di generate_response_stream: {e}", exc_info=True)
        yield {'type': 'text', 'data': "⚠️ Terjadi gangguan teknis. Coba lagi nanti."}
