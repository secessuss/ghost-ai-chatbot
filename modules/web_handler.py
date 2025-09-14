import logging
import asyncio
from newspaper import Article, Config
import aiohttp
from bs4 import BeautifulSoup
from typing import Tuple, Optional


logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s'
)

def _extract_with_newspaper_sync(url: str) -> Tuple[Optional[str], Optional[str]]:

    try:
        config = Config()
        config.browser_user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        )
        config.request_timeout = 20
        article = Article(url, config=config)
        article.download()
        article.parse()
        title = article.title if article.title else "Tanpa Judul"
        content = article.text
        return content, title
    
    except Exception as e:
        logging.error(f"[Newspaper3k] Gagal memproses URL {url}: {e}")
        return None, None
    
async def _extract_with_bs_async(url: str) -> Tuple[Optional[str], Optional[str]]:
    logging.info(f"[BeautifulSoup] Mencoba mengambil konten dari URL: {url}")
    
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        ),
    }
    
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=20) as response:
                response.raise_for_status()
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                for script_or_style in soup(['script', 'style', 'nav', 'footer', 'header']):
                    script_or_style.decompose()
                
                title = soup.title.string if soup.title else "Tanpa Judul"
                text = soup.body.get_text(separator=' ', strip=True)
                return text, title
            
    except Exception as e:
        logging.error(f"[BeautifulSoup] Gagal mem-parsing konten dari {url}: {e}")
        return None, None
    
async def extract_content_from_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    logging.info(f"Memulai proses ekstraksi kombinasi untuk URL: {url}")
    
    try:
        content_np, title_np = await asyncio.to_thread(_extract_with_newspaper_sync, url)
        if content_np and len(content_np) > 150:
            logging.info(f"Ekstraksi dengan Newspaper3k berhasil untuk {url}")
            return content_np, title_np
        logging.warning(f"Newspaper3k tidak mendapatkan konten yang cukup dari {url}. Menjalankan fallback.")
    
    except Exception as e:
        logging.error(f"Error saat menjalankan thread Newspaper3k: {e}. Menjalankan fallback.")
    
    content_bs, title_bs = await _extract_with_bs_async(url)

    if content_bs:
        logging.info(f"Ekstraksi dengan BeautifulSoup (fallback) berhasil untuk {url}")
    else:
        logging.warning(f"Semua metode ekstraksi gagal untuk {url}")
    return content_bs, title_bs