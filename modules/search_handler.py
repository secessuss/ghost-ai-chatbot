import logging
import asyncio
from ddgs import DDGS
from typing import List, Dict, Any


logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s'
)

def _perform_search_sync(query: str, max_results: int) -> list:
    with DDGS() as ddgs:
        return list(ddgs.text(query, region='id-id', max_results=max_results))
    
async def search_web(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    search_results: List[Dict[str, Any]] = []
    processed_urls = set()
    
    try:
        logging.info(f"Melakukan pencarian web untuk: '{query}'")
        results_list = await asyncio.to_thread(_perform_search_sync, query, max_results)

        for res in results_list:
            url = res.get('href')
            if url and url not in processed_urls:
                search_results.append({
                    'title': res.get('title', 'Tanpa Judul'),
                    'body': res.get('body', 'Tidak ada ringkasan.'),
                    'url': url
                })
                processed_urls.add(url)

        if not search_results:
            logging.warning(f"Tidak ada hasil pencarian yang ditemukan untuk kueri: '{query}'")
        return search_results
    
    except Exception as e:
        logging.error(f"Error saat melakukan pencarian web dengan DDGS: {e}", exc_info=True)
        return []