import aiosqlite
import json
import datetime
from typing import Union, Optional, Dict, List
from .prompt import SYSTEM_PROMPT
from zoneinfo import ZoneInfo


DB_FILE = "context.db"
CONTEXT_EXPIRATION = datetime.timedelta(hours=12)

def get_current_date_str() -> str:
    jakarta_tz = ZoneInfo("Asia/Jakarta")
    current_datetime = datetime.datetime.now(jakarta_tz)
    return current_datetime.strftime("%A, %d %B %Y, %H:%M:%S WIB")

class ContextManager:
    def __init__(self, db_file: str):
        self.db_file = db_file
        
    async def _init_db(self):
        async with aiosqlite.connect(self.db_file) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_contexts (
                    user_id INTEGER PRIMARY KEY,
                    history_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    active_session_name TEXT,
                    session_files_json TEXT
                )
            """)
            await conn.commit()
        print("Pemeriksaan dan inisialisasi database selesai.")

    def _get_formatted_system_prompt_part(self) -> Dict:
        formatted_system_prompt = SYSTEM_PROMPT.format(current_date_str=get_current_date_str())
        return {'role': 'user', 'parts': [formatted_system_prompt]}
    
    async def _create_new_context(self, user_id: int) -> Dict:
        history = [
            self._get_formatted_system_prompt_part(),
            {'role': 'model', 'parts': ["Saya siap membantu. Apa yang ingin Anda tanyakan?"]}
        ]
        await self.save_context(user_id, history, None, {})
        return {
            'history': history,
            'active_session_name': None,
            'session_files': {}
        }
    
    async def get_context(self, user_id: int) -> Dict:
        async with aiosqlite.connect(self.db_file) as conn:
            cursor = await conn.execute(
                "SELECT history_json, timestamp, active_session_name, session_files_json FROM user_contexts WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()

        current_time = datetime.datetime.now()

        if row:
            last_timestamp = datetime.datetime.fromisoformat(row[1])
            if current_time - last_timestamp > CONTEXT_EXPIRATION:
                session_name_to_keep = row[2] or None
                session_files_to_keep = json.loads(row[3] or '{}')
                history = [
                    self._get_formatted_system_prompt_part(),
                    {'role': 'model', 'parts': ["Saya siap membantu. Apa yang ingin Anda tanyakan?"]}
                ]
                await self.save_context(user_id, history, session_name_to_keep, session_files_to_keep)
                return {
                    'history': history,
                    'active_session_name': session_name_to_keep,
                    'session_files': session_files_to_keep
                }
            
            history = json.loads(row[0])
            history[0] = self._get_formatted_system_prompt_part()
            session_name = row[2]
            session_files = json.loads(row[3] or '{}')
            return {
                'history': history,
                'active_session_name': session_name,
                'session_files': session_files
            }
        else:
            return await self._create_new_context(user_id)
        
    async def save_context(self, user_id: int, history: List, session_name: Optional[str], session_files: Dict):
        async with aiosqlite.connect(self.db_file) as conn:
            history_json = json.dumps(history)
            session_files_json = json.dumps(session_files)
            timestamp_iso = datetime.datetime.now().isoformat()
            await conn.execute("""
                INSERT INTO user_contexts (user_id, history_json, timestamp, active_session_name, session_files_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                history_json = excluded.history_json,
                timestamp = excluded.timestamp,
                active_session_name = excluded.active_session_name,
                session_files_json = excluded.session_files_json
            """, (user_id, history_json, timestamp_iso, session_name, session_files_json))
            await conn.commit()

    async def reset_context(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_file) as conn:
            cursor = await conn.execute("DELETE FROM user_contexts WHERE user_id = ?", (user_id,))
            deleted_rows = cursor.rowcount
            await conn.commit()
        return deleted_rows > 0
    
    async def end_session(self, user_id: int) -> Optional[str]:
        context = await self.get_context(user_id)
        session_name = context.get('active_session_name')
        if session_name:
            context['active_session_name'] = None
            context['session_files'] = {}
            await self.save_context(user_id, context['history'], None, {})
        return session_name
    
    async def add_file_to_session(self, user_id: int, file_name: str, file_content: str):
        context = await self.get_context(user_id)
        session_files = context.get('session_files', {})
        session_files[file_name] = file_content
        session_name = context.get('active_session_name') or f"Sesi Otomatis"
        await self.save_context(user_id, context['history'], session_name, session_files)

    async def add_web_search_to_session(self, user_id: int, query: str, search_results: List[Dict]):
        context = await self.get_context(user_id)
        session_files = context.get('session_files', {})
        formatted_results = f"Hasil pencarian untuk kueri '{query}':\n\n"
        
        for i, result in enumerate(search_results):
            formatted_results += (
                f"Sumber {i+1}: {result['title']} ({result['url']})\n"
                f"Ringkasan: {result['body']}\n---\n"
            )
        
        file_name = f"Konteks Web: '{query[:50]}...'"
        session_files[file_name] = formatted_results
        session_name = context.get('active_session_name') or "Sesi Otomatis"
        await self.save_context(user_id, context['history'], session_name, session_files)

    async def get_session_files_context(self, user_id: int) -> Optional[str]:
        context = await self.get_context(user_id)
        session_files = context.get('session_files', {})
        
        if not session_files:
            return None
        
        full_context = (
            "KONTEKS TAMBAHAN: Selain pengetahuan umum Anda, gunakan informasi dari "
            "sumber-sumber berikut (file, tautan, atau hasil pencarian web) untuk "
            "memperkaya jawaban Anda jika relevan dengan pertanyaan pengguna.\n\n"
        )
        
        for i, (name, content) in enumerate(session_files.items()):
            full_context += f"--- KONTEN SUMBER {i+1}: `{name}` ---\n"
            full_context += f"{content[:4000]}...\n"
            full_context += f"--- AKHIR KONTEN: `{name}` ---\n\n"
        return full_context
