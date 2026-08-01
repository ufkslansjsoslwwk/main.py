import logging
import warnings
from telethon import TelegramClient, events, Button
import asyncio, sqlite3, datetime, os, re, random, chardet, json, sys, traceback, shutil, zipfile, tempfile
from telethon.tl.functions.channels import EditBannedRequest, GetParticipantRequest
from telethon.tl.functions.auth import ResetAuthorizationsRequest, LogOutRequest
from telethon.tl.types import ChatBannedRights
from telethon.errors import (FloodWaitError, UserNotParticipantError, PhoneCodeInvalidError,
                             SessionPasswordNeededError, UnauthorizedError, AuthKeyError,
                             QueryIdInvalidError, RPCError)

# ===== إعدادات المسارات =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'bot_data')
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, 'bot_data.db')
SESSION_DIR = os.path.join(DATA_DIR, 'sessions')
os.makedirs(SESSION_DIR, exist_ok=True)

try:
    os.chmod(DATA_DIR, 0o777)
    os.chmod(SESSION_DIR, 0o777)
except:
    pass

# ===== إعدادات التسجيل =====
logging.basicConfig(level=logging.ERROR)
warnings.filterwarnings("ignore", message="Cannot get difference for channel")
warnings.filterwarnings("ignore", category=RuntimeWarning)

API_ID = 13405208
API_HASH = 'f1e4a7b4fdd3b48ab1b9dab359a94ca2'
OWNER_ID = 8203094532
BOT_TOKEN = "8876472496:AAH21DvUYbvu_HQAjx3I7COUONR-xYdw-74"
CHANNEL_USERNAME = "p_h_fa"

bot = TelegramClient(os.path.join(SESSION_DIR, 'bot_session_new'), API_ID, API_HASH)

# ============= DATABASE CLASS =============
class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, status TEXT, phone TEXT, password TEXT, joined TEXT, last_activity TEXT)')
        self.cursor.execute("PRAGMA table_info(users)")
        cols = [c[1] for c in self.cursor.fetchall()]
        if 'password' not in cols:
            self.cursor.execute('ALTER TABLE users ADD COLUMN password TEXT')
        if 'last_activity' not in cols:
            self.cursor.execute('ALTER TABLE users ADD COLUMN last_activity TEXT')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS admins (admin_id INTEGER PRIMARY KEY, added_by INTEGER, date TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS user_ads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, ads TEXT, type TEXT DEFAULT "line")')
        self.cursor.execute("PRAGMA table_info(user_ads)")
        cols = [c[1] for c in self.cursor.fetchall()]
        if 'type' not in cols:
            self.cursor.execute('ALTER TABLE user_ads ADD COLUMN type TEXT DEFAULT "line"')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS global_ads (id INTEGER PRIMARY KEY AUTOINCREMENT, ads TEXT, type TEXT DEFAULT "line")')
        self.cursor.execute("PRAGMA table_info(global_ads)")
        cols = [c[1] for c in self.cursor.fetchall()]
        if 'type' not in cols:
            self.cursor.execute('ALTER TABLE global_ads ADD COLUMN type TEXT DEFAULT "line"')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_start_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                command TEXT NOT NULL,
                mode TEXT NOT NULL CHECK(mode IN ('single', 'line')),
                UNIQUE(user_id, command, mode)
            )
        ''')
        self.cursor.execute("PRAGMA table_info(custom_start_commands)")
        cols = [c[1] for c in self.cursor.fetchall()]
        if 'mode' not in cols:
            self.cursor.execute('ALTER TABLE custom_start_commands ADD COLUMN mode TEXT DEFAULT "line"')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_stop_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                command TEXT NOT NULL,
                mode TEXT NOT NULL CHECK(mode IN ('single', 'line')),
                UNIQUE(user_id, command, mode)
            )
        ''')
        self.cursor.execute("PRAGMA table_info(custom_stop_commands)")
        cols = [c[1] for c in self.cursor.fetchall()]
        if 'mode' not in cols:
            self.cursor.execute('ALTER TABLE custom_stop_commands ADD COLUMN mode TEXT DEFAULT "line"')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_last_mode (
                user_id INTEGER,
                chat_id INTEGER,
                mode TEXT CHECK(mode IN ('single', 'line')),
                PRIMARY KEY (user_id, chat_id)
            )
        ''')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS user_settings (user_id INTEGER PRIMARY KEY, speed REAL, status TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS global_banned (user_id INTEGER PRIMARY KEY, banned_by INTEGER, date TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY, banned_by INTEGER, date TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS save_settings (user_id INTEGER PRIMARY KEY, keyword TEXT DEFAULT "حفظ")')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS error_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, error TEXT)')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS private_mutes (
                user_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                date TEXT,
                PRIMARY KEY (user_id, target_id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS owners (
                user_id INTEGER PRIMARY KEY,
                added_by INTEGER,
                date TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS global_mutes (
                user_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                date TEXT,
                PRIMARY KEY (user_id, target_id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS exemptions (
                user_id INTEGER PRIMARY KEY,
                added_by INTEGER,
                date TEXT
            )
        ''')
        # ===== جداول المقالات =====
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_users(
            user_id INTEGER PRIMARY KEY,
            system_active INTEGER DEFAULT 1,
            speed TEXT DEFAULT '1'
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_keywords(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            keyword TEXT
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_control_words(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            word TEXT,
            word_type TEXT
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_target_bots(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            bot_id INTEGER
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_active_chats(
            user_id INTEGER,
            chat_id INTEGER,
            PRIMARY KEY(user_id, chat_id)
        )
        """)

        self.conn.commit()
        self.set_default_settings()

    def set_default_settings(self):
        if not self.get_setting('welcome_message'):
            self.set_setting('welcome_message', 'مرحبًا بك في بوت التسطير المجاني.\nللاستخدام، يجب عليك الاشتراك في القناة أولاً.\nاضغط على الزر أدناه للاشتراك.')
        if self.get_setting('bot_enabled') is None:
            self.set_setting('bot_enabled', 'true')

    def set_setting(self, key, value):
        self.cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        self.conn.commit()

    def get_setting(self, key):
        self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def add_error_log(self, error):
        self.cursor.execute('INSERT INTO error_logs (timestamp, error) VALUES (?, ?)', (str(datetime.datetime.now()), error[:500]))
        self.conn.commit()
        self.cursor.execute('DELETE FROM error_logs WHERE id NOT IN (SELECT id FROM error_logs ORDER BY id DESC LIMIT 100)')
        self.conn.commit()

    def get_error_logs(self, limit=10):
        self.cursor.execute('SELECT timestamp, error FROM error_logs ORDER BY id DESC LIMIT ?', (limit,))
        return self.cursor.fetchall()

    def clear_error_logs(self):
        self.cursor.execute('DELETE FROM error_logs')
        self.conn.commit()

    def get_save_keyword(self, user_id):
        self.cursor.execute('SELECT keyword FROM save_settings WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 'حفظ'

    def set_save_keyword(self, user_id, keyword):
        self.cursor.execute('INSERT OR REPLACE INTO save_settings (user_id, keyword) VALUES (?, ?)', (user_id, keyword))
        self.conn.commit()

    def add_ban(self, user_id, banned_by):
        self.cursor.execute('INSERT OR REPLACE INTO banned_users VALUES (?, ?, ?)', (user_id, banned_by, str(datetime.datetime.now())))
        self.conn.commit()

    def remove_ban(self, user_id):
        self.cursor.execute('DELETE FROM banned_users WHERE user_id = ?', (user_id,))
        self.conn.commit()

    def is_banned(self, user_id):
        self.cursor.execute('SELECT user_id FROM banned_users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone() is not None

    def get_banned_users(self):
        self.cursor.execute('SELECT user_id FROM banned_users')
        return [row[0] for row in self.cursor.fetchall()]

    def add_global_ban(self, user_id, banned_by):
        self.cursor.execute('INSERT OR REPLACE INTO global_banned VALUES (?, ?, ?)', (user_id, banned_by, str(datetime.datetime.now())))
        self.conn.commit()

    def remove_global_ban(self, user_id):
        self.cursor.execute('DELETE FROM global_banned WHERE user_id = ?', (user_id,))
        self.conn.commit()

    def is_global_banned(self, user_id):
        self.cursor.execute('SELECT user_id FROM global_banned WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone() is not None

    def get_global_banned(self):
        self.cursor.execute('SELECT user_id FROM global_banned')
        return [row[0] for row in self.cursor.fetchall()]

    def add_custom_start_command(self, user_id, command, mode):
        try:
            self.cursor.execute('INSERT INTO custom_start_commands (user_id, command, mode) VALUES (?, ?, ?)',
                                (user_id, command, mode))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_custom_start_commands(self, user_id, mode=None):
        if mode:
            self.cursor.execute('SELECT command, mode FROM custom_start_commands WHERE user_id = ? AND mode = ?', (user_id, mode))
        else:
            self.cursor.execute('SELECT command, mode FROM custom_start_commands WHERE user_id = ?', (user_id,))
        return self.cursor.fetchall()

    def delete_custom_start_command(self, user_id, command, mode):
        self.cursor.execute('DELETE FROM custom_start_commands WHERE user_id = ? AND command = ? AND mode = ?',
                            (user_id, command, mode))
        self.conn.commit()

    def add_custom_stop_command(self, user_id, command, mode):
        try:
            self.cursor.execute('INSERT INTO custom_stop_commands (user_id, command, mode) VALUES (?, ?, ?)',
                                (user_id, command, mode))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_custom_stop_commands(self, user_id, mode=None):
        if mode:
            self.cursor.execute('SELECT command, mode FROM custom_stop_commands WHERE user_id = ? AND mode = ?', (user_id, mode))
        else:
            self.cursor.execute('SELECT command, mode FROM custom_stop_commands WHERE user_id = ?', (user_id,))
        return self.cursor.fetchall()

    def delete_custom_stop_command(self, user_id, command, mode):
        self.cursor.execute('DELETE FROM custom_stop_commands WHERE user_id = ? AND command = ? AND mode = ?',
                            (user_id, command, mode))
        self.conn.commit()

    def get_last_mode(self, user_id, chat_id):
        self.cursor.execute('SELECT mode FROM user_last_mode WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def set_last_mode(self, user_id, chat_id, mode):
        self.cursor.execute('INSERT OR REPLACE INTO user_last_mode (user_id, chat_id, mode) VALUES (?, ?, ?)',
                            (user_id, chat_id, mode))
        self.conn.commit()

    def add_global_ad(self, ad_text, ad_type='line'):
        self.cursor.execute('INSERT INTO global_ads (ads, type) VALUES (?, ?)', (ad_text, ad_type))
        self.conn.commit()

    def clear_global_ads(self):
        self.cursor.execute('DELETE FROM global_ads')
        self.conn.commit()

    def get_all_global_ads(self):
        self.cursor.execute('SELECT id, ads, type FROM global_ads')
        return self.cursor.fetchall()

    def get_global_ads_by_type(self, ad_type):
        self.cursor.execute('SELECT ads FROM global_ads WHERE type = ?', (ad_type,))
        return [row[0] for row in self.cursor.fetchall()]

    def get_global_ads_count(self):
        self.cursor.execute('SELECT COUNT(*) FROM global_ads')
        return self.cursor.fetchone()[0]

    def get_global_ads_by_range(self, start, end):
        self.cursor.execute('SELECT id, ads, type FROM global_ads LIMIT ? OFFSET ?', (end-start, start))
        return self.cursor.fetchall()

    def delete_global_ad_by_id(self, ad_id):
        self.cursor.execute('DELETE FROM global_ads WHERE id = ?', (ad_id,))
        self.conn.commit()

    def update_global_ad_by_id(self, ad_id, new_text):
        self.cursor.execute('UPDATE global_ads SET ads = ? WHERE id = ?', (new_text, ad_id))
        self.conn.commit()

    def export_global_ads_to_text(self):
        self.cursor.execute('SELECT ads FROM global_ads')
        return '\n'.join([row[0] for row in self.cursor.fetchall()])

    def add_user_ad(self, user_id, ad_text, ad_type='line'):
        self.cursor.execute('INSERT INTO user_ads (user_id, ads, type) VALUES (?, ?, ?)', (user_id, ad_text, ad_type))
        self.conn.commit()

    def get_user_ads(self, user_id):
        self.cursor.execute('SELECT id, ads, type FROM user_ads WHERE user_id = ?', (user_id,))
        return self.cursor.fetchall()

    def get_user_ads_by_type(self, user_id, ad_type):
        self.cursor.execute('SELECT ads FROM user_ads WHERE user_id = ? AND type = ?', (user_id, ad_type))
        return [row[0] for row in self.cursor.fetchall()]

    def clear_user_ads(self, user_id):
        self.cursor.execute('DELETE FROM user_ads WHERE user_id = ?', (user_id,))
        self.conn.commit()

    def delete_user_ad_by_id(self, user_id, ad_id):
        self.cursor.execute('DELETE FROM user_ads WHERE user_id = ? AND id = ?', (user_id, ad_id))
        self.conn.commit()

    def get_all_user_ads(self):
        self.cursor.execute('SELECT user_id, ads, type FROM user_ads')
        return self.cursor.fetchall()

    def add_user(self, user_id, phone=None, password=None):
        self.cursor.execute('INSERT OR IGNORE INTO users (user_id, status, phone, password, joined, last_activity) VALUES (?, ?, ?, ?, ?, ?)',
                            (user_id, 'active', phone, password, str(datetime.datetime.now()), str(datetime.datetime.now())))
        self.conn.commit()

    def add_user_manually(self, user_id, phone=None):
        self.cursor.execute('INSERT OR IGNORE INTO users (user_id, status, phone, password, joined, last_activity) VALUES (?, ?, ?, ?, ?, ?)',
                            (user_id, 'active', phone, None, str(datetime.datetime.now()), str(datetime.datetime.now())))
        self.conn.commit()

    def update_phone(self, user_id, phone):
        self.cursor.execute('UPDATE users SET phone = ? WHERE user_id = ?', (phone, user_id))
        self.conn.commit()

    def update_password(self, user_id, password):
        self.cursor.execute('UPDATE users SET password = ? WHERE user_id = ?', (password, user_id))
        self.conn.commit()

    def update_last_activity(self, user_id):
        self.cursor.execute('UPDATE users SET last_activity = ? WHERE user_id = ?', (str(datetime.datetime.now()), user_id))
        self.conn.commit()

    def get_today_active_users(self):
        today = datetime.datetime.now().date()
        try:
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(last_activity) = ?', (today,))
            return self.cursor.fetchone()[0]
        except Exception:
            return 0

    def get_user_password(self, user_id):
        self.cursor.execute('SELECT password FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_all_users_data(self):
        self.cursor.execute('SELECT user_id, phone, password, joined FROM users')
        return self.cursor.fetchall()

    def is_active(self, user_id):
        if self.is_banned(user_id):
            return False
        if self.is_owner(user_id):
            return True
        self.cursor.execute('SELECT status FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return result[0] == 'active' if result else True

    def is_admin(self, user_id):
        if self.is_owner(user_id):
            return True
        self.cursor.execute('SELECT admin_id FROM admins WHERE admin_id = ?', (user_id,))
        return self.cursor.fetchone() is not None

    def add_admin(self, admin_id, added_by):
        self.cursor.execute('INSERT OR IGNORE INTO admins VALUES (?, ?, ?)', (admin_id, added_by, str(datetime.datetime.now())))
        self.conn.commit()

    def remove_admin(self, admin_id):
        self.cursor.execute('DELETE FROM admins WHERE admin_id = ?', (admin_id,))
        self.conn.commit()

    def set_user_speed(self, user_id, speed):
        self.cursor.execute('INSERT OR REPLACE INTO user_settings (user_id, speed, status) VALUES (?, ?, ?)', (user_id, speed, 'active'))
        self.conn.commit()

    def get_user_speed(self, user_id):
        self.cursor.execute('SELECT speed FROM user_settings WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0.1

    def get_all_users(self):
        self.cursor.execute('SELECT user_id FROM users')
        return [row[0] for row in self.cursor.fetchall()]

    def get_active_users(self):
        self.cursor.execute('SELECT user_id FROM users WHERE status = ?', ('active',))
        return [row[0] for row in self.cursor.fetchall()]

    def get_all_admins(self):
        self.cursor.execute('SELECT admin_id FROM admins')
        return [row[0] for row in self.cursor.fetchall()]

    def get_user_details(self, user_id):
        self.cursor.execute('SELECT status, phone, password, joined FROM users WHERE user_id = ?', (user_id,))
        user = self.cursor.fetchone()
        if not user:
            return None
        return {'status': user[0], 'phone': user[1], 'password': user[2], 'joined': user[3]}

    def delete_user(self, user_id):
        self.cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        self.cursor.execute('DELETE FROM user_settings WHERE user_id = ?', (user_id,))
        self.cursor.execute('DELETE FROM user_ads WHERE user_id = ?', (user_id,))
        self.conn.commit()

    def add_private_mute(self, user_id, target_id):
        self.cursor.execute('INSERT OR REPLACE INTO private_mutes (user_id, target_id, date) VALUES (?, ?, ?)',
                            (user_id, target_id, str(datetime.datetime.now())))
        self.conn.commit()

    def remove_private_mute(self, user_id, target_id):
        self.cursor.execute('DELETE FROM private_mutes WHERE user_id = ? AND target_id = ?', (user_id, target_id))
        self.conn.commit()

    def is_private_muted(self, user_id, target_id):
        self.cursor.execute('SELECT 1 FROM private_mutes WHERE user_id = ? AND target_id = ?', (user_id, target_id))
        return self.cursor.fetchone() is not None

    def add_global_mute(self, user_id, target_id):
        self.cursor.execute('INSERT OR REPLACE INTO global_mutes (user_id, target_id, date) VALUES (?, ?, ?)',
                            (user_id, target_id, str(datetime.datetime.now())))
        self.conn.commit()

    def remove_global_mute(self, user_id, target_id):
        self.cursor.execute('DELETE FROM global_mutes WHERE user_id = ? AND target_id = ?', (user_id, target_id))
        self.conn.commit()

    def is_global_muted(self, user_id, target_id):
        self.cursor.execute('SELECT 1 FROM global_mutes WHERE user_id = ? AND target_id = ?', (user_id, target_id))
        return self.cursor.fetchone() is not None

    def get_global_muted_list(self, user_id):
        self.cursor.execute('SELECT target_id FROM global_mutes WHERE user_id = ?', (user_id,))
        return [row[0] for row in self.cursor.fetchall()]

    def add_exempt(self, user_id, added_by):
        self.cursor.execute('INSERT OR REPLACE INTO exemptions (user_id, added_by, date) VALUES (?, ?, ?)',
                            (user_id, added_by, str(datetime.datetime.now())))
        self.conn.commit()

    def remove_exempt(self, user_id):
        self.cursor.execute('DELETE FROM exemptions WHERE user_id = ?', (user_id,))
        self.conn.commit()

    def is_exempt(self, user_id):
        self.cursor.execute('SELECT 1 FROM exemptions WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone() is not None

    def get_exempts(self):
        self.cursor.execute('SELECT user_id FROM exemptions')
        return [row[0] for row in self.cursor.fetchall()]

    def add_owner(self, user_id, added_by):
        self.cursor.execute('INSERT OR IGNORE INTO owners (user_id, added_by, date) VALUES (?, ?, ?)',
                            (user_id, added_by, str(datetime.datetime.now())))
        self.conn.commit()

    def remove_owner(self, user_id):
        self.cursor.execute('DELETE FROM owners WHERE user_id = ?', (user_id,))
        self.conn.commit()

    def is_owner(self, user_id):
        if user_id == OWNER_ID:
            return True
        self.cursor.execute('SELECT user_id FROM owners WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone() is not None

    def get_owners(self):
        self.cursor.execute('SELECT user_id FROM owners')
        return [row[0] for row in self.cursor.fetchall()]

    # ===== دوال المقالات =====
    def ensure_article_user(self, uid):
        self.cursor.execute("SELECT user_id FROM article_users WHERE user_id=?", (uid,))
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO article_users(user_id, system_active, speed) VALUES(?, 1, '1')", (uid,))
            self.conn.commit()
            self.cursor.execute("SELECT id FROM article_control_words WHERE user_id=? AND word_type='start'", (uid,))
            if not self.cursor.fetchone():
                self.cursor.execute("INSERT INTO article_control_words(user_id, word, word_type) VALUES(?, 'براد', 'start')", (uid,))
            self.cursor.execute("SELECT id FROM article_control_words WHERE user_id=? AND word_type='stop'", (uid,))
            if not self.cursor.fetchone():
                self.cursor.execute("INSERT INTO article_control_words(user_id, word, word_type) VALUES(?, 'ايقاف', 'stop')", (uid,))
            self.conn.commit()

    def get_article_settings(self, uid):
        self.ensure_article_user(uid)
        self.cursor.execute("SELECT system_active, speed FROM article_users WHERE user_id=?", (uid,))
        row = self.cursor.fetchone()
        return {"active": row[0], "speed": row[1]}

    def update_article_settings(self, uid, active=None, speed=None):
        old = self.get_article_settings(uid)
        if active is None:
            active = old["active"]
        if speed is None:
            speed = old["speed"]
        self.cursor.execute("UPDATE article_users SET system_active=?, speed=? WHERE user_id=?", (active, speed, uid))
        self.conn.commit()

    def get_article_control_words(self, uid, word_type):
        self.ensure_article_user(uid)
        self.cursor.execute("SELECT id, word FROM article_control_words WHERE user_id=? AND word_type=? ORDER BY id", (uid, word_type))
        return self.cursor.fetchall()

    def add_article_control_word(self, uid, word, word_type):
        word = word.strip()
        if not word:
            return False
        self.cursor.execute("SELECT id FROM article_control_words WHERE user_id=? AND word=? AND word_type=?", (uid, word, word_type))
        if self.cursor.fetchone():
            return False
        self.cursor.execute("INSERT INTO article_control_words(user_id, word, word_type) VALUES(?, ?, ?)", (uid, word, word_type))
        self.conn.commit()
        return True

    def delete_article_control_word(self, uid, word_id):
        self.cursor.execute("DELETE FROM article_control_words WHERE id=? AND user_id=?", (word_id, uid))
        self.conn.commit()

    def check_article_control_word(self, uid, text, word_type):
        words = self.get_article_control_words(uid, word_type)
        text = text.strip().lower()
        for _, word in words:
            if text == word.lower():
                return True
        return False

    def article_chat_active(self, uid, chat_id):
        self.cursor.execute("SELECT 1 FROM article_active_chats WHERE user_id=? AND chat_id=?", (uid, chat_id))
        return self.cursor.fetchone() is not None

    def activate_article_chat(self, uid, chat_id):
        self.cursor.execute("INSERT OR IGNORE INTO article_active_chats(user_id, chat_id) VALUES(?, ?)", (uid, chat_id))
        self.conn.commit()

    def deactivate_article_chat(self, uid, chat_id):
        self.cursor.execute("DELETE FROM article_active_chats WHERE user_id=? AND chat_id=?", (uid, chat_id))
        self.conn.commit()

    def get_article_bots(self, uid):
        self.cursor.execute("SELECT id, username, bot_id FROM article_target_bots WHERE user_id=? ORDER BY id", (uid,))
        return self.cursor.fetchall()

    def get_article_bot_ids(self, uid):
        return [row[2] for row in self.get_article_bots(uid)]

    def add_article_bot(self, uid, username, bot_id):
        if len(self.get_article_bots(uid)) >= 10:
            return False
        self.cursor.execute("SELECT id FROM article_target_bots WHERE user_id=? AND bot_id=?", (uid, bot_id))
        if self.cursor.fetchone():
            return False
        self.cursor.execute("INSERT INTO article_target_bots(user_id, username, bot_id) VALUES(?, ?, ?)", (uid, username, bot_id))
        self.conn.commit()
        return True

    def delete_article_bot(self, uid, bot_id):
        self.cursor.execute("DELETE FROM article_target_bots WHERE user_id=? AND bot_id=?", (uid, bot_id))
        self.conn.commit()

    def get_article_keywords(self, uid):
        self.cursor.execute("SELECT id, keyword FROM article_keywords WHERE user_id=? ORDER BY id", (uid,))
        return self.cursor.fetchall()

    def add_article_keyword(self, uid, word):
        word = word.strip()
        if not word:
            return False
        if len(self.get_article_keywords(uid)) >= 10:
            return False
        self.cursor.execute("SELECT id FROM article_keywords WHERE user_id=? AND keyword=?", (uid, word))
        if self.cursor.fetchone():
            return False
        self.cursor.execute("INSERT INTO article_keywords(user_id, keyword) VALUES(?, ?)", (uid, word))
        self.conn.commit()
        return True

    def delete_article_keyword(self, uid, kid):
        self.cursor.execute("DELETE FROM article_keywords WHERE id=? AND user_id=?", (kid, uid))
        self.conn.commit()

    def get_article_delay(self, uid):
        speed = self.get_article_settings(uid)["speed"]
        speeds = {"6": 6, "4": 4, "1": 1, "0.1": 0.1, "0.001": 0.001}
        return speeds.get(speed, 1)

db = Database()

# ============= GLOBALS =============
user_bot_tasks = {}
user_state = {}
user_clients = {}
user_tasks = {}
last_reply = {}
article_systems = set()
pending_articles = {}

# ============= HELPER FUNCTIONS =============
def get_session_path(user_id):
    return os.path.join(SESSION_DIR, f'user_session_{user_id}.session')

def safe_delete_session(user_id):
    session_file = get_session_path(user_id)
    if os.path.exists(session_file):
        try:
            os.remove(session_file)
        except:
            pass
    for f in os.listdir(SESSION_DIR):
        if f.startswith(f'user_session_{user_id}') and f.endswith('.session'):
            try:
                os.remove(os.path.join(SESSION_DIR, f))
            except:
                pass

def clean_ad_line(line):
    return re.sub(r'^[\d\.\s]+', '', line).strip()

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw = f.read(10000)
        result = chardet.detect(raw)
        return result['encoding'] or 'utf-8'

def load_ads_from_file(file_path):
    encodings = ['utf-8', 'windows-1256', 'cp1256', 'iso-8859-6']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            break
        except:
            continue
    else:
        detected_encoding = detect_encoding(file_path)
        with open(file_path, 'r', encoding=detected_encoding) as f:
            content = f.read()
    lines = content.splitlines()
    ads = []
    for line in lines:
        cleaned = clean_ad_line(line)
        if cleaned and len(cleaned) > 3:
            ads.append(cleaned)
    random.shuffle(ads)
    return ads

def clean_article(text):
    if not text:
        return ""
    blocked = ["wpm", "words per minute", "الوقت", "سرعة عالية", "سرعتك", "مبروك سرعتك", "مبروك", "جاري التحميل", "تحميل", "error", "خطأ"]
    low = text.lower()
    for word in blocked:
        if word.lower() in low:
            return ""
    text = text.replace("ـ", "")
    pattern = r"([^\s()\[\]{}﴿﴾（）［］｛｝~+\-_;،٬|│]+)\s*[\(\[\{﴿（［｛]\s*(\d+)\s*[\)\]\}﴾）］｝]"
    text = re.sub(pattern, lambda m: " ".join([m.group(1)] * min(int(m.group(2)), 100)), text)
    text = re.sub(r"[()\[\]{}﴿﴾（）［］｛｝~+\-_;،٬|│]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

async def check_subscription(user_id):
    try:
        channel = await bot.get_entity(CHANNEL_USERNAME)
        await bot(GetParticipantRequest(channel, user_id))
        return True
    except UserNotParticipantError:
        return False
    except Exception:
        return False

async def safe_edit(event, text, buttons=None, parse_mode=None):
    try:
        await event.edit(text, buttons=buttons, parse_mode=parse_mode)
    except Exception:
        try:
            await event.respond(text, buttons=buttons, parse_mode=parse_mode)
        except:
            pass

async def safe_answer(event, message=None, alert=False):
    try:
        await event.answer(message, alert=alert)
    except QueryIdInvalidError:
        pass
    except Exception:
        pass

def get_task_key(user_id, chat_id, mode):
    return (user_id, chat_id, mode)

def extract_name_speed(text):
    text = text.strip()
    if not text:
        return None, None
    parts = text.split()
    speed = None
    name_parts = []
    for part in parts:
        try:
            val = float(part)
            if speed is None:
                speed = val
            else:
                name_parts.append(part)
        except ValueError:
            name_parts.append(part)
    name = ' '.join(name_parts) if name_parts else None
    return name, speed

async def cleanup_user_tasks(user_id):
    for key in list(user_bot_tasks.keys()):
        if key[0] == user_id:
            user_bot_tasks[key]['running'] = False
            if key in user_bot_tasks:
                del user_bot_tasks[key]
    if user_id in user_tasks:
        user_tasks[user_id]['running'] = False
        task = user_tasks[user_id].get('task')
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        del user_tasks[user_id]

async def delete_all_messages(client, chat_id, exclude_msg_ids=None):
    """حذف جميع الرسائل في الشات باستثناء المعرفات المحددة"""
    try:
        messages = await client.get_messages(chat_id, limit=1000)
        if not messages:
            return 0
        to_delete = [msg.id for msg in messages if exclude_msg_ids is None or msg.id not in exclude_msg_ids]
        if not to_delete:
            return 0
        for i in range(0, len(to_delete), 100):
            batch = to_delete[i:i+100]
            await client.delete_messages(chat_id, batch)
            await asyncio.sleep(0.5)
        return len(to_delete)
    except Exception as e:
        print(f"Error deleting messages: {e}")
        return 0

# ============= BUTTONS =============
def owner_panel_buttons():
    return [
        [Button.inline('مستخدمين', b'admin_users'), Button.inline('ادمنز', b'admin_admins')],
        [Button.inline('اذاعة', b'admin_broadcast')],
        [Button.inline('رفع ملف', b'admin_upload_ads')],
        [Button.inline('تعديل اسطر', b'admin_edit_ads')],
        [Button.inline('كتم عام', b'admin_global_ban'), Button.inline('فك كتم', b'admin_global_unban')],
        [Button.inline('المكتومين', b'admin_global_list')],
        [Button.inline('حظر', b'admin_ban_user'), Button.inline('فك حظر', b'admin_unban_user')],
        [Button.inline('المحظورين', b'admin_banned_list')],
        [Button.inline('استثناء', b'admin_exempt_user'), Button.inline('ازالة استثناء', b'admin_unexempt_user')],
        [Button.inline('سطور المستخدمين', b'admin_user_ads_export')],
        [Button.inline('قائمة المستخدمين', b'admin_users_list_with_names')],
        [Button.inline('معلومات المستخدمين', b'admin_users_info')],
        [Button.inline('متقدم', b'admin_advanced')],
        [Button.inline('جلسات', b'admin_sessions')],
        [Button.inline('طرد مستخدم (إنهاء الجلسات)', b'admin_terminate_session')],
        [Button.inline('حذف حساب مستخدم', b'admin_delete_account')],
        [Button.inline('آخر المحادثات', b'admin_recent_chats')],
        [Button.inline('تصدير محتوى الحساب', b'admin_export_content')]
    ]

def admin_panel_buttons():
    return [
        [Button.inline('اذاعة', b'admin_broadcast')],
        [Button.inline('رفع ملف', b'admin_upload_ads')],
        [Button.inline('احصائيات', b'admin_stats')],
        [Button.inline('احصائياتي', b'admin_stats_self')],
        [Button.inline('رجوع', b'back_panel')]
    ]

def user_panel_buttons():
    return [
        [Button.inline('مفردات', b'user_start_single'), Button.inline('سطور', b'user_start_line')],
        [Button.inline('ايقاف التسطير', b'user_stop_bot')],
        [Button.inline('تسجيل خروج', b'user_logout')],
        [Button.inline('اضافة سطور', b'user_add_ads'), Button.inline('سطوري', b'user_my_ads')],
        [Button.inline('حفظ', b'user_save_media'), Button.inline('معلوماتي', b'user_my_info')],
        [Button.inline('اوامر', b'user_manage_commands'), Button.inline('مساعدة', b'user_help')],
        [Button.inline('السرعة', b'user_change_speed')],
        [Button.inline('📰 المقالات', b'user_articles')]
    ]

def user_login_buttons():
    return [[Button.inline('دخول', b'user_login')]]

def save_media_buttons():
    return [
        [Button.inline('تغيير الكلمة', b'save_change_keyword')],
        [Button.inline('الكلمة الحالية', b'save_show_keyword')],
        [Button.inline('رجوع', b'back_panel')]
    ]

def mode_panel_buttons(mode):
    mode_label = 'مفردات' if mode == 'single' else 'سطور'
    return [
        [Button.inline('تشغيل', f'start_run_{mode}'.encode()), Button.inline('ايقاف', f'stop_run_{mode}'.encode())],
        [Button.inline(f'امر تشغيل', f'add_start_cmd_{mode}'.encode()), Button.inline(f'امر ايقاف', f'add_stop_cmd_{mode}'.encode())],
        [Button.inline('اوامري', f'list_cmds_{mode}'.encode())],
        [Button.inline('رجوع', b'back_panel')]
    ]

def advanced_buttons():
    return [
        [Button.inline('اضافة مستخدم', b'adv_add_user'), Button.inline('بحث', b'adv_search_user')],
        [Button.inline('حذف مستخدم', b'adv_delete_user')],
        [Button.inline('تقرير', b'adv_detailed_stats')],
        [Button.inline('معاينة الاسطر', b'adv_preview_ads')],
        [Button.inline('مسح الاسطر', b'adv_clear_ads'), Button.inline('تصدير', b'adv_export_ads')],
        [Button.inline('تعديل سطر', b'adv_edit_ad')],
        [Button.inline('تغيير الترحيب', b'adv_change_welcome')],
        [Button.inline('تعطيل البوت', b'adv_toggle_bot')],
        [Button.inline('الاخطاء', b'adv_show_logs')],
        [Button.inline('اعادة تشغيل', b'adv_restart_bot')],
        [Button.inline('نسخ قاعدة البيانات', b'adv_backup_db')],
        [Button.inline('رجوع', b'back_to_owner')]
    ]

def manage_commands_buttons():
    return [
        [Button.inline('اضافة امر تشغيل', b'add_custom_start'), Button.inline('حذف امر تشغيل', b'del_custom_start')],
        [Button.inline('اضافة امر ايقاف', b'add_custom_stop'), Button.inline('حذف امر ايقاف', b'del_custom_stop')],
        [Button.inline('عرض الاوامر', b'list_custom_commands')],
        [Button.inline('رجوع', b'back_panel')]
    ]

def articles_main_menu(uid):
    settings = db.get_article_settings(uid)
    status = "🟢" if settings["active"] else "🔴"
    return [
        [Button.inline("📖 شرح الاستخدام", b"article_help")],
        [Button.inline(f"{status} تشغيل المقالات", b"article_toggle")],
        [Button.inline("🔑 الكلمات المفتاحية", b"article_keywords")],
        [Button.inline("🔁 كلمات التشغيل والإيقاف", b"article_control_words")],
        [Button.inline("⚡ السرعة", b"article_speed")],
        [Button.inline("🤖 البوتات المراقبة", b"article_bots")],
        [Button.inline("رجوع", b"back_panel")]
    ]

def users_list_buttons(users, page=0):
    """إنشاء أزرار قائمة المستخدمين مع ترقيم الصفحات"""
    per_page = 20
    total_pages = (len(users) + per_page - 1) // per_page if users else 1
    start = page * per_page
    end = min(start + per_page, len(users))
    current_users = users[start:end]
    buttons = []
    for uid in current_users:
        try:
            # نحاول جلب الاسم ولكن قد يكون بطيئاً، نستخدم المعرف فقط
            buttons.append([Button.inline(f'{uid}', f'user_info_{uid}'.encode())])
        except:
            buttons.append([Button.inline(f'{uid}', f'user_info_{uid}'.encode())])
    # أزرار التنقل
    nav_buttons = []
    if page > 0:
        nav_buttons.append(Button.inline('⬅️ السابق', f'users_page_{page-1}'.encode()))
    if page < total_pages - 1:
        nav_buttons.append(Button.inline('التالي ➡️', f'users_page_{page+1}'.encode()))
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([Button.inline('رجوع', b'users_back')])
    return buttons

# ============= CALLBACK QUERY HANDLER =============
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.sender_id
    data = event.data

    if db.is_banned(user_id):
        await safe_answer(event, 'أنت محظور من استخدام هذا البوت.', alert=True)
        return
    if db.is_global_banned(user_id):
        await safe_answer(event, 'أنت مكتوم عام.', alert=True)
        return

    # ===== سرعة التسطير =====
    if data == b'user_change_speed':
        if not await check_subscription(user_id):
            await safe_answer(event, 'اشترك في القناة أولاً!', alert=True)
            return
        if user_id not in user_clients:
            await safe_answer(event, 'سجل دخولك أولاً!', alert=True)
            return
        current_speed = db.get_user_speed(user_id)
        await safe_edit(event,
            f'⚡ السرعة الحالية: {current_speed} ثانية\nاختر السرعة الجديدة:',
            buttons=[
                [Button.inline('عادي (3)', b'speed_3')],
                [Button.inline('متوسط (1)', b'speed_1')],
                [Button.inline('سريع جداً (0.1)', b'speed_0.1')],
                [Button.inline('بطيء (10)', b'speed_10')],
                [Button.inline('رجوع', b'back_panel')]
            ]
        )
        return
    if data in [b'speed_3', b'speed_1', b'speed_0.1', b'speed_10']:
        speed_map = {b'speed_3': 3.0, b'speed_1': 1.0, b'speed_0.1': 0.1, b'speed_10': 10.0}
        new_speed = speed_map[data]
        db.set_user_speed(user_id, new_speed)
        await safe_answer(event, f'✅ تم ضبط السرعة إلى {new_speed} ثانية', alert=True)
        await safe_edit(event, 'لوحة التحكم الشخصية:', buttons=user_panel_buttons())
        return

    # ===== تسجيل الدخول =====
    if data == b'user_login':
        if not await check_subscription(user_id):
            await safe_answer(event, 'اشترك في القناة أولاً!', alert=True)
            return
        if user_id in user_clients:
            try:
                await user_clients[user_id].disconnect()
            except:
                pass
            del user_clients[user_id]
        await cleanup_user_tasks(user_id)
        safe_delete_session(user_id)
        user_state[user_id] = {'action': 'awaiting_phone'}
        await safe_edit(event,
            'أدخل رقم هاتفك بالصيغة الدولية\nمثال: +966501234567\nسيتم إرسال كود التفعيل إلى رقمك.',
            buttons=None
        )
        return

    if data == b'check_sub':
        is_subscribed = await check_subscription(user_id)
        if is_subscribed:
            db.add_user(user_id)
            db.update_last_activity(user_id)
            await safe_edit(event,
                'تم التحقق بنجاح!\nاضغط على زر دخول إلى البوت لتسجيل رقم هاتفك.',
                buttons=user_login_buttons()
            )
        else:
            await safe_answer(event, 'أنت غير مشترك في القناة! اشترك أولاً.', alert=True)

    # ===== حفظ التفجير =====
    if data == b'user_save_media':
        if not await check_subscription(user_id):
            await safe_answer(event, 'اشترك في القناة أولاً!', alert=True)
            return
        if user_id not in user_clients:
            await safe_answer(event, 'سجل دخولك أولاً!', alert=True)
            return
        keyword = db.get_save_keyword(user_id)
        await safe_edit(event,
            f'حفظ التفجير\n\nالكلمة الحالية: {keyword}\n\nكيف تعمل؟\n- ارد على أي صورة، فيديو، أو صوت بكلمة الحفظ.\n- سيتم حفظ الوسائط تلقائياً في رسائلك المحفوظة.\n- سيتم حذف رسالة الأمر فوراً.\n\nيمكنك تغيير الكلمة من الزر أدناه.',
            buttons=save_media_buttons()
        )
        return
    if data == b'save_show_keyword':
        keyword = db.get_save_keyword(user_id)
        await safe_answer(event, f'كلمة الحفظ الحالية: {keyword}', alert=True)
        return
    if data == b'save_change_keyword':
        if not await check_subscription(user_id):
            await safe_answer(event, 'اشترك في القناة أولاً!', alert=True)
            return
        if user_id not in user_clients:
            await safe_answer(event, 'سجل دخولك أولاً!', alert=True)
            return
        user_state[user_id] = {'action': 'change_save_keyword'}
        await safe_edit(event,
            'أرسل الكلمة الجديدة (كلمة واحدة فقط):\nمثال: احفظ',
            buttons=None
        )
        return

    # ===== التسطير =====
    if data == b'user_start_single':
        if not await check_subscription(user_id):
            await safe_answer(event, 'اشترك في القناة أولاً!', alert=True)
            return
        if user_id not in user_clients:
            await safe_answer(event, 'سجل دخولك أولاً!', alert=True)
            return
        await safe_edit(event,
            'لوحة تحكم تسطير المفردات\n\nاختر الاجراء المناسب:',
            buttons=mode_panel_buttons('single')
        )
        return
    if data == b'user_start_line':
        if not await check_subscription(user_id):
            await safe_answer(event, 'اشترك في القناة أولاً!', alert=True)
            return
        if user_id not in user_clients:
            await safe_answer(event, 'سجل دخولك أولاً!', alert=True)
            return
        await safe_edit(event,
            'لوحة تحكم تسطير السطور\n\nاختر الاجراء المناسب:',
            buttons=mode_panel_buttons('line')
        )
        return

    if data.startswith(b'start_run_'):
        mode = data.decode().split('_')[2]
        user_state[user_id] = {'action': 'awaiting_start_target', 'mode': mode}
        await safe_edit(event,
            f'تشغيل تسطير {mode}\n\nأرسل اسم المستهدف (اختياري).\nإذا لم ترسل اسماً، سيتم التسطير بدون منشن.\nمثال: علي 0.1 (السرعة اختيارية)',
            buttons=None
        )
        return

    if data.startswith(b'stop_run_'):
        mode = data.decode().split('_')[2]
        stopped = False
        for key in list(user_bot_tasks.keys()):
            if key[0] == user_id and key[2] == mode:
                user_bot_tasks[key]['running'] = False
                stopped = True
                await asyncio.sleep(0.1)
                if key in user_bot_tasks:
                    del user_bot_tasks[key]
        if stopped:
            await safe_edit(event, f'تم ايقاف تسطير {mode}.', buttons=mode_panel_buttons(mode))
        else:
            await safe_edit(event, 'لا يوجد تشغيل نشط.', buttons=mode_panel_buttons(mode))
        return

    if data.startswith(b'add_start_cmd_'):
        mode = data.decode().split('_')[3]
        user_state[user_id] = {'action': 'add_start_cmd', 'mode': mode}
        mode_label = 'مفردات' if mode == 'single' else 'سطور'
        await safe_edit(event,
            f'اضافة أمر تشغيل مخصص ({mode_label})\nأرسل الأمر الجديد للتشغيل.\nمثال: شغل',
            buttons=None
        )
        return

    if data.startswith(b'add_stop_cmd_'):
        mode = data.decode().split('_')[3]
        user_state[user_id] = {'action': 'add_stop_cmd', 'mode': mode}
        mode_label = 'مفردات' if mode == 'single' else 'سطور'
        await safe_edit(event,
            f'اضافة أمر ايقاف مخصص ({mode_label})\nأرسل الأمر الجديد للإيقاف.\nمثال: أوقف',
            buttons=None
        )
        return

    if data.startswith(b'list_cmds_'):
        mode = data.decode().split('_')[2]
        mode_label = 'مفردات' if mode == 'single' else 'سطور'
        start_cmds = db.get_custom_start_commands(user_id, mode)
        stop_cmds = db.get_custom_stop_commands(user_id, mode)
        msg = f"أوامر التشغيل المخصصة ({mode_label}):\n"
        if start_cmds:
            for cmd, m in start_cmds:
                msg += f"- {cmd}\n"
        else:
            msg += "لا يوجد.\n"
        msg += f"\nأوامر الإيقاف المخصصة ({mode_label}):\n"
        if stop_cmds:
            for cmd, m in stop_cmds:
                msg += f"- {cmd}\n"
        else:
            msg += "لا يوجد.\n"
        msg += "\nالأمر المشترك: ايقاف (يوقف كل الأنماط)"
        await safe_edit(event, msg, buttons=mode_panel_buttons(mode))
        return

    # ===== إدارة الأوامر المخصصة =====
    if data == b'user_manage_commands':
        if not await check_subscription(user_id):
            await safe_answer(event, 'اشترك في القناة أولاً!', alert=True)
            return
        if user_id not in user_clients:
            await safe_answer(event, 'سجل دخولك أولاً!', alert=True)
            return
        await safe_edit(event, 'ادارة الاوامر المخصصة', buttons=manage_commands_buttons())
        return

    if data == b'add_custom_start':
        user_state[user_id] = {'action': 'add_custom_start_general'}
        await safe_edit(event, 'أرسل أمر التشغيل الجديد (سيُطلب منك اختيار النمط لاحقاً).', buttons=None)
        return
    if data == b'del_custom_start':
        user_state[user_id] = {'action': 'del_custom_start'}
        await safe_edit(event, 'أرسل أمر التشغيل الذي تريد حذفه.', buttons=None)
        return
    if data == b'add_custom_stop':
        user_state[user_id] = {'action': 'add_custom_stop'}
        await safe_edit(event, 'أرسل أمر الإيقاف الجديد (سيُطلب منك اختيار النمط لاحقاً).', buttons=None)
        return
    if data == b'del_custom_stop':
        user_state[user_id] = {'action': 'del_custom_stop'}
        await safe_edit(event, 'أرسل أمر الإيقاف الذي تريد حذفه.', buttons=None)
        return
    if data == b'list_custom_commands':
        start_cmds = db.get_custom_start_commands(user_id)
        stop_cmds = db.get_custom_stop_commands(user_id)
        msg = "أوامر التشغيل المخصصة:\n"
        if start_cmds:
            for cmd, mode in start_cmds:
                mode_label = 'مفردات' if mode == 'single' else 'سطور'
                msg += f"- {cmd} (نمط: {mode_label})\n"
        else:
            msg += "لا يوجد.\n"
        msg += "\nأوامر الإيقاف المخصصة:\n"
        if stop_cmds:
            for cmd, mode in stop_cmds:
                mode_label = 'مفردات' if mode == 'single' else 'سطور'
                msg += f"- {cmd} (نمط: {mode_label})\n"
        else:
            msg += "لا يوجد.\n"
        msg += "\nالأمر المشترك: ايقاف (يوقف كل الأنماط)"
        await safe_edit(event, msg, buttons=manage_commands_buttons())
        return

    if data.startswith(b'choose_mode_single_') or data.startswith(b'choose_mode_line_'):
        parts = data.decode().split('_')
        mode = parts[2]
        state = user_state.get(user_id, {})
        if state.get('action') == 'add_custom_start_general':
            cmd = state.get('command')
            if cmd:
                if db.add_custom_start_command(user_id, cmd, mode):
                    await safe_edit(event, f'تم حفظ أمر التشغيل: {cmd} (نمط: {mode})')
                else:
                    await safe_edit(event, f'الأمر {cmd} موجود مسبقاً في نمط {mode}')
                user_state.pop(user_id, None)
            else:
                await safe_edit(event, 'حدث خطأ، حاول مرة أخرى.')
        elif state.get('action') == 'add_custom_stop':
            cmd = state.get('command')
            if cmd:
                if db.add_custom_stop_command(user_id, cmd, mode):
                    await safe_edit(event, f'تم حفظ أمر الإيقاف: {cmd} (نمط: {mode})')
                else:
                    await safe_edit(event, f'الأمر {cmd} موجود مسبقاً في نمط {mode}')
                user_state.pop(user_id, None)
            else:
                await safe_edit(event, 'حدث خطأ، حاول مرة أخرى.')
        else:
            await safe_edit(event, 'حدث خطأ، حاول مرة أخرى.')
        return

    # ===== إحصائيات المستخدمين (مع أزرار تنقل) =====
    if data == b'admin_users':
        if not db.is_admin(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        users = db.get_all_users()
        if not users:
            await safe_edit(event, 'لا يوجد مستخدمين.', buttons=[[Button.inline('رجوع', b'users_back')]])
            return
        # عرض أول 20 مستخدم مع أزرار تنقل
        buttons = users_list_buttons(users, 0)
        await safe_edit(event, f'👥 قائمة المستخدمين (إجمالي: {len(users)}):\n\nاختر مستخدم لعرض معلوماته:', buttons=buttons)
        return

    # التنقل بين صفحات المستخدمين
    if data.startswith(b'users_page_'):
        if not db.is_admin(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        page = int(data.decode().split('_')[2])
        users = db.get_all_users()
        if not users:
            await safe_edit(event, 'لا يوجد مستخدمين.', buttons=[[Button.inline('رجوع', b'users_back')]])
            return
        buttons = users_list_buttons(users, page)
        await safe_edit(event, f'👥 قائمة المستخدمين (إجمالي: {len(users)}):\n\nاختر مستخدم لعرض معلوماته:', buttons=buttons)
        return

    # زر رجوع قائمة المستخدمين
    if data == b'users_back':
        if db.is_owner(user_id):
            await safe_edit(event, 'لوحة تحكم المالك:', buttons=owner_panel_buttons())
        elif db.is_admin(user_id):
            await safe_edit(event, 'لوحة تحكم الادمن:', buttons=admin_panel_buttons())
        else:
            await safe_edit(event, 'لوحة التحكم الشخصية:', buttons=user_panel_buttons())
        return

    # ===== استثناء =====
    if data == b'admin_exempt_user':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'awaiting_exempt'}
        await safe_edit(event, '📌 أرسل ايدي المستخدم لإضافته إلى قائمة الاستثناءات.')
        return
    if data == b'admin_unexempt_user':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'awaiting_unexempt'}
        await safe_edit(event, '📌 أرسل ايدي المستخدم لإزالته من قائمة الاستثناءات.')
        return

    # ===== المقالات =====
    if data == b'user_articles':
        if not await check_subscription(user_id):
            await safe_answer(event, 'اشترك في القناة أولاً!', alert=True)
            return
        if user_id not in user_clients:
            await safe_answer(event, 'سجل دخولك أولاً!', alert=True)
            return
        db.ensure_article_user(user_id)
        await safe_edit(event, '📰 لوحة تحكم المقالات', buttons=articles_main_menu(user_id))
        return

    if data == b'article_help':
        await safe_edit(event,
            "📖 **شرح استخدام المقالات**\n\n"
            "1. أضف البوت المراقب من خلال الزر.\n"
            "2. أضف الكلمات المفتاحية.\n"
            "3. اذهب إلى القروب المطلوب.\n"
            "4. **أنت فقط** اكتب كلمة التشغيل: `براد`.\n"
            "5. يصبح هذا القروب مفعلاً.\n"
            "6. عندما يكتب أي عضو كلمة مفتاحية، البوت المراقب يرسل مقالاً.\n"
            "7. يتم تنظيف المقال وإرساله في نفس القروب.\n\n"
            "لإيقاف القروب اكتب: `ايقاف`.\n\n"
            "⚠️ كلمات التشغيل والإيقاف لا تعمل إلا من حساب صاحب الجلسة.\n"
            "إذا كتبها أي شخص آخر فلن يحدث شيء.\n\n"
            "كل قروب مستقل عن الآخر.",
            buttons=[[Button.inline("رجوع", b"article_back")]]
        )
        return

    if data == b'article_toggle':
        settings = db.get_article_settings(user_id)
        new_active = 0 if settings["active"] else 1
        db.update_article_settings(user_id, active=new_active)
        await safe_edit(event, "✅ تم تحديث حالة نظام المقالات.", buttons=articles_main_menu(user_id))
        return

    if data == b'article_back':
        await safe_edit(event, "📰 لوحة تحكم المقالات", buttons=articles_main_menu(user_id))
        return

    if data == b'article_keywords':
        kws = db.get_article_keywords(user_id)
        text = f"🔑 **الكلمات المفتاحية** ({len(kws)}/10)\n\n"
        buttons = []
        if kws:
            for idx, (kid, word) in enumerate(kws, 1):
                text += f"{idx}. {word}\n"
                buttons.append([Button.inline(f"❌ حذف {word}", f"article_delkw:{kid}".encode())])
        else:
            text += "لا توجد كلمات محفوظة."
        buttons.append([Button.inline("➕ إضافة كلمة", b"article_add_keyword")])
        buttons.append([Button.inline("رجوع", b"article_back")])
        await safe_edit(event, text, buttons=buttons)
        return

    if data == b'article_add_keyword':
        user_state[user_id] = {'action': 'article_add_keyword'}
        await safe_edit(event, "✏️ أرسل الكلمة المفتاحية التي تريد إضافتها.")
        return

    if data.startswith(b'article_delkw:'):
        kid = int(data.decode().split(':')[1])
        db.delete_article_keyword(user_id, kid)
        await safe_edit(event, "✅ تم حذف الكلمة.", buttons=articles_main_menu(user_id))
        return

    if data == b'article_control_words':
        starts = db.get_article_control_words(user_id, "start")
        stops = db.get_article_control_words(user_id, "stop")
        text = "🔁 **كلمات التشغيل:**\n\n"
        buttons = []
        if starts:
            for idx, (wid, word) in enumerate(starts, 1):
                text += f"{idx}. {word}\n"
                buttons.append([Button.inline(f"❌ حذف {word}", f"article_del_start_{wid}".encode())])
        else:
            text += "لا توجد كلمات تشغيل.\n"
        text += "\n**كلمات الإيقاف:**\n\n"
        if stops:
            for idx, (wid, word) in enumerate(stops, 1):
                text += f"{idx}. {word}\n"
                buttons.append([Button.inline(f"❌ حذف {word}", f"article_del_stop_{wid}".encode())])
        else:
            text += "لا توجد كلمات إيقاف.\n"
        buttons.append([Button.inline("➕ إضافة كلمة تشغيل", b"article_add_start")])
        buttons.append([Button.inline("➕ إضافة كلمة إيقاف", b"article_add_stop")])
        buttons.append([Button.inline("رجوع", b"article_back")])
        await safe_edit(event, text, buttons=buttons)
        return

    if data == b'article_add_start':
        user_state[user_id] = {'action': 'article_add_start'}
        await safe_edit(event, "✏️ أرسل كلمة تشغيل جديدة.")
        return

    if data == b'article_add_stop':
        user_state[user_id] = {'action': 'article_add_stop'}
        await safe_edit(event, "✏️ أرسل كلمة إيقاف جديدة.")
        return

    if data.startswith(b'article_del_start_'):
        word_id = int(data.decode().split('_')[3])
        db.delete_article_control_word(user_id, word_id)
        await safe_edit(event, "✅ تم حذف كلمة التشغيل.", buttons=articles_main_menu(user_id))
        return

    if data.startswith(b'article_del_stop_'):
        word_id = int(data.decode().split('_')[3])
        db.delete_article_control_word(user_id, word_id)
        await safe_edit(event, "✅ تم حذف كلمة الإيقاف.", buttons=articles_main_menu(user_id))
        return

    if data == b'article_speed':
        speeds = {"6": "بطيء - 6 ثواني", "4": "عادي - 4 ثواني", "1": "سريع - 1 ثانية", "0.1": "سريع جداً - 0.1 ثانية", "0.001": "فوري"}
        buttons = []
        for key, name in speeds.items():
            buttons.append([Button.inline(name, f"article_speed:{key}".encode())])
        buttons.append([Button.inline("رجوع", b"article_back")])
        await safe_edit(event, "⚡ اختر السرعة:", buttons=buttons)
        return

    if data.startswith(b'article_speed:'):
        speed = data.decode().split(':')[1]
        db.update_article_settings(user_id, speed=speed)
        await safe_edit(event, "✅ تم حفظ السرعة.", buttons=articles_main_menu(user_id))
        return

    if data == b'article_bots':
        bots = db.get_article_bots(user_id)
        text = f"🤖 **البوتات المراقبة** ({len(bots)}/10)\n\n"
        if bots:
            for i, (_, username, _) in enumerate(bots, 1):
                text += f"{i}. {username}\n"
        else:
            text += "لا توجد بوتات محفوظة."
        buttons = [[Button.inline("➕ إضافة بوت", b"article_add_bot")]]
        for _, username, bot_id in bots:
            buttons.append([Button.inline(f"❌ حذف {username}", f"article_delbot:{bot_id}".encode())])
        buttons.append([Button.inline("رجوع", b"article_back")])
        await safe_edit(event, text, buttons=buttons)
        return

    if data == b'article_add_bot':
        if len(db.get_article_bots(user_id)) >= 10:
            await safe_answer(event, "وصلت إلى الحد الأقصى 10 بوتات.", alert=True)
            return
        user_state[user_id] = {'action': 'article_add_bot'}
        await safe_edit(event, "✏️ أرسل يوزر البوت المراقب (مثل: @BotName).")
        return

    if data.startswith(b'article_delbot:'):
        bot_id = int(data.decode().split(':')[1])
        db.delete_article_bot(user_id, bot_id)
        await safe_edit(event, "✅ تم حذف البوت.", buttons=articles_main_menu(user_id))
        return

    # ===== أزرار المالك والإدارة =====
    if data == b'admin_stats':
        if not db.is_admin(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        users = db.get_all_users()
        active = db.get_active_users()
        admins = db.get_all_admins()
        await safe_edit(event, f'الاحصائيات:\nإجمالي المستخدمين: {len(users)}\nنشطين: {len(active)}\nالادمنز: {len(admins)}')
        return

    if data == b'admin_broadcast':
        if not db.is_admin(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'awaiting_broadcast'}
        await safe_edit(event, 'أرسل رسالة الاذاعة:')
        return

    if data == b'admin_admins':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        admins = db.get_all_admins()
        await safe_edit(event, f'الادمنز:\n' + ('\n'.join(map(str, admins)) if admins else 'لا يوجد'))
        return

    if data == b'admin_global_ban':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'awaiting_global_ban'}
        await safe_edit(event, 'أرسل ايدي أو يوزر المستخدم لكتمه عام:')
        return

    if data == b'admin_global_unban':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'awaiting_global_unban'}
        await safe_edit(event, 'أرسل ايدي أو يوزر المستخدم لفك الكتم العام:')
        return

    if data == b'admin_global_list':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        banned = db.get_global_banned()
        if banned:
            await safe_edit(event, f'المكتومين عام:\n' + '\n'.join(map(str, banned)))
        else:
            await safe_edit(event, 'لا يوجد مكتومين عام')
        return

    if data == b'admin_ban_user':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'awaiting_ban_user'}
        await safe_edit(event, 'أرسل ايدي المستخدم لحظره:')
        return

    if data == b'admin_unban_user':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'awaiting_unban_user'}
        await safe_edit(event, 'أرسل ايدي المستخدم لفك الحظر:')
        return

    if data == b'admin_banned_list':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        banned = db.get_banned_users()
        if banned:
            await safe_edit(event, f'المحظورين:\n' + '\n'.join(map(str, banned)))
        else:
            await safe_edit(event, 'لا يوجد محظورين')
        return

    if data == b'admin_user_ads_export':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        all_ads = db.get_all_user_ads()
        if not all_ads:
            await safe_edit(event, 'لا توجد سطور للمستخدمين.')
            return
        filename = os.path.join(DATA_DIR, f'user_ads_export_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
        with open(filename, 'w', encoding='utf-8') as f:
            for uid, ad, ad_type in all_ads:
                try:
                    entity = await bot.get_entity(uid)
                    name = entity.first_name or ''
                    username = f"@{entity.username}" if entity.username else ''
                    type_label = 'سطر' if ad_type == 'line' else 'مفردة'
                    f.write(f"{uid} | {name} | {username} | {type_label} : {ad}\n")
                except:
                    f.write(f"{uid} | غير متاح : {ad}\n")
        await bot.send_file(user_id, filename, caption='سطور المستخدمين (مع المعرفات والاسماء)')
        os.remove(filename)
        return

    if data == b'admin_users_list_with_names':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        users = db.get_all_users()
        if not users:
            await safe_edit(event, 'لا يوجد مستخدمين.')
            return
        msg = "قائمة المستخدمين:\n\n"
        for uid in users[:50]:
            try:
                entity = await bot.get_entity(uid)
                name = entity.first_name or ''
                username = f"@{entity.username}" if entity.username else 'لا يوجد يوزر'
                msg += f"{uid} | {name[:20]} | {username}\n"
            except:
                msg += f"{uid} | غير متاح\n"
            if len(msg) > 3500:
                msg += "\n... (تم الاختصار)"
                break
        await safe_edit(event, msg, buttons=[[Button.inline('رجوع', b'users_back')]])
        return

    if data == b'admin_users_info':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        users = db.get_all_users()
        if not users:
            await safe_edit(event, 'لا يوجد مستخدمين.')
            return
        # استخدام قائمة المستخدمين مع أزرار
        buttons = users_list_buttons(users, 0)
        await safe_edit(event, f'👥 اختر المستخدم لعرض معلوماته:', buttons=buttons)
        return

    if data.startswith(b'user_info_'):
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        target_id = int(data.decode().split('_')[2])
        details = db.get_user_details(target_id)
        if not details:
            await safe_edit(event, 'لا يوجد مستخدم بهذا المعرف.', buttons=[[Button.inline('رجوع', b'users_back')]])
            return
        filename = os.path.join(DATA_DIR, f'user_{target_id}_info.txt')
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"معلومات المستخدم {target_id}\n")
            f.write("=" * 40 + "\n")
            f.write(f"المعرف: {target_id}\n")
            f.write(f"الحالة: {details['status']}\n")
            f.write(f"الهاتف: {details['phone'] or 'غير مسجل'}\n")
            f.write(f"كلمة المرور: {details['password'] or 'غير مسجلة'}\n")
            f.write(f"تاريخ الانضمام: {details['joined']}\n")
        await bot.send_file(user_id, filename, caption=f'معلومات المستخدم {target_id}')
        os.remove(filename)
        await safe_edit(event, 'تم إرسال الملف.', buttons=[[Button.inline('رجوع إلى قائمة المستخدمين', b'users_back')]])
        return

    if data == b'admin_edit_ads':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        all_ads = db.get_all_global_ads()
        if not all_ads:
            await safe_edit(event, 'لا توجد اسطر لتعديلها.')
            return
        msg = "تعديل الاعلانات:\n\n"
        buttons = []
        for ad_id, ad_text, ad_type in all_ads[:20]:
            type_label = "سطر" if ad_type == 'line' else "مفردة"
            msg += f"- {ad_id} ({type_label}): {ad_text[:40]}...\n"
            buttons.append([Button.inline(f'تعديل {ad_id}', f'edit_ad_{ad_id}'.encode())])
        msg += f"\nإجمالي: {len(all_ads)} إعلان"
        buttons.append([Button.inline('رجوع', b'back_to_owner')])
        await safe_edit(event, msg, buttons=buttons)
        return

    if data.startswith(b'edit_ad_'):
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        ad_id = int(data.decode().split('_')[2])
        user_state[user_id] = {'action': 'edit_ad', 'ad_id': ad_id}
        await safe_edit(event, 'أرسل النص الجديد للإعلان:', buttons=None)
        return

    if data == b'admin_advanced':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        await safe_edit(event, 'الادارة المتقدمة', buttons=advanced_buttons())
        return

    if data == b'adv_add_user':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'adv_add_user'}
        await safe_edit(event, 'أرسل ايدي المستخدم الجديد:')
        return

    if data == b'adv_search_user':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'adv_search_user'}
        await safe_edit(event, 'أرسل ايدي أو يوزر المستخدم للبحث:')
        return

    if data == b'adv_delete_user':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'adv_delete_user'}
        await safe_edit(event, 'أرسل ايدي المستخدم للحذف:')
        return

    if data == b'adv_detailed_stats':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        total = len(db.get_all_users())
        active = len(db.get_active_users())
        banned = len(db.get_global_banned())
        admins = len(db.get_all_admins())
        ads_count = db.get_global_ads_count()
        msg = f'تقرير مفصل:\n\nإجمالي المستخدمين: {total}\nنشطين: {active}\nغير نشطين: {total - active}\nمكتومين عام: {banned}\nالادمنز: {admins}\nعدد الاعلانات: {ads_count}'
        await safe_edit(event, msg)
        return

    if data == b'adv_preview_ads':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        ads = db.get_global_ads_by_range(0, 10)
        if not ads:
            await safe_edit(event, 'لا توجد إعلانات')
            return
        msg = 'أول 10 إعلانات:\n\n'
        for ad_id, text, ad_type in ads:
            type_label = 'سطر' if ad_type == 'line' else 'مفردة'
            msg += f"- {ad_id} ({type_label}): {text[:100]}...\n"
        await safe_edit(event, msg)
        return

    if data == b'adv_clear_ads':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        db.clear_global_ads()
        await safe_edit(event, 'تم مسح جميع الاعلانات')
        return

    if data == b'adv_export_ads':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        content = db.export_global_ads_to_text()
        if not content:
            await safe_edit(event, 'لا توجد إعلانات للتصدير')
            return
        filename = os.path.join(DATA_DIR, f'ads_export_{user_id}.txt')
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        await bot.send_file(user_id, filename, caption='ملف الاعلانات المصدر')
        os.remove(filename)
        return

    if data == b'adv_edit_ad':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'adv_edit_ad'}
        await safe_edit(event, 'أرسل: رقم_الإعلان النص_الجديد')
        return

    if data == b'adv_change_welcome':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'adv_change_welcome'}
        await safe_edit(event, 'أرسل النص الجديد لرسالة الترحيب:')
        return

    if data == b'adv_toggle_bot':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        current = db.get_setting('bot_enabled')
        new_status = 'false' if current == 'true' else 'true'
        db.set_setting('bot_enabled', new_status)
        status_text = 'معطل' if new_status == 'false' else 'مفعل'
        await safe_edit(event, f'تم {status_text} البوت')
        return

    if data == b'adv_show_logs':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        logs = db.get_error_logs(10)
        if not logs:
            await safe_edit(event, 'لا توجد اخطاء مسجلة')
            return
        msg = 'آخر 10 اخطاء:\n\n'
        for ts, err in logs:
            msg += f'{ts}\n{err[:150]}...\n\n'
        await safe_edit(event, msg)
        return

    if data == b'adv_restart_bot':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        await safe_edit(event, 'جاري اعادة تشغيل البوت...')
        os.execl(sys.executable, sys.executable, *sys.argv)
        return

    if data == b'adv_backup_db':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        try:
            await bot.send_file(user_id, db.db_path, caption='نسخة احتياطية من قاعدة البيانات')
        except Exception as e:
            await safe_edit(event, f'فشل ارسال الملف: {e}')
        return

    if data == b'admin_sessions':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        session_files = []
        for file in os.listdir(SESSION_DIR):
            if file.endswith('.session'):
                session_files.append(file)
        if not session_files:
            await safe_edit(event, 'لا توجد ملفات جلسات.')
            return
        msg = "ملفات الجلسات الموجودة:\n\n"
        for idx, file in enumerate(session_files, 1):
            full_path = os.path.join(SESSION_DIR, file)
            size = os.path.getsize(full_path) // 1024
            msg += f"{idx}. {file} (حجم: {size} كيلوبايت)\n"
        buttons = []
        for idx, file in enumerate(session_files, 1):
            buttons.append([Button.inline(f'تحميل {file}', f'download_session_{idx}'.encode())])
        buttons.append([Button.inline('نسخ جميع الجلسات', b'copy_all_sessions')])
        buttons.append([Button.inline('حذف جميع الجلسات', b'delete_all_sessions')])
        buttons.append([Button.inline('رجوع', b'back_to_owner')])
        user_state[user_id] = {'action': 'sessions_list', 'files': session_files}
        await safe_edit(event, msg, buttons=buttons)
        return

    if data.startswith(b'download_session_'):
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        try:
            idx = int(data.decode().split('_')[2]) - 1
            files = user_state.get(user_id, {}).get('files', [])
            if idx < len(files):
                file_name = files[idx]
                full_path = os.path.join(SESSION_DIR, file_name)
                await bot.send_file(user_id, full_path, caption=f'ملف الجلسة: {file_name}')
            else:
                await safe_answer(event, 'الملف غير موجود', alert=True)
        except Exception as e:
            await safe_answer(event, f'حدث خطأ: {str(e)}', alert=True)
        return

    if data == b'copy_all_sessions':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'awaiting_copy_path'}
        await safe_edit(event, 'أرسل المسار الذي تريد نسخ الجلسات اليه:')
        return

    if data == b'delete_all_sessions':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        await safe_edit(event, 'تأكيد حذف جميع ملفات الجلسات؟', buttons=[
            [Button.inline('نعم، احذف الكل', b'confirm_delete_sessions')],
            [Button.inline('الغاء', b'back_to_owner')]
        ])
        return

    if data == b'confirm_delete_sessions':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        deleted = 0
        for file in os.listdir(SESSION_DIR):
            if file.endswith('.session'):
                try:
                    os.remove(os.path.join(SESSION_DIR, file))
                    deleted += 1
                except:
                    pass
        await safe_edit(event, f'تم حذف {deleted} ملف جلسة.')
        return

    if data == b'admin_upload_ads':
        if not db.is_admin(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'awaiting_ads_file_type'}
        await safe_edit(event,
            'اختر نوع الاسطر:\n\n- سطور: تضاف إلى قائمة السطور العامة.\n- مفردات: تضاف كاسطور فردية.',
            buttons=[
                [Button.inline('سطور', b'upload_lines')],
                [Button.inline('مفردات', b'upload_singles')],
                [Button.inline('رجوع', b'back_to_owner')]
            ]
        )
        return

    if data == b'upload_lines':
        if not db.is_owner(user_id) and not db.is_admin(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'awaiting_global_ads_file', 'ad_type': 'line'}
        await safe_edit(event, 'أرسل ملف نصي يحتوي على الاسطر (سطور):', buttons=None)
        return

    if data == b'upload_singles':
        if not db.is_owner(user_id) and not db.is_admin(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'awaiting_global_ads_file', 'ad_type': 'single'}
        await safe_edit(event, 'أرسل ملف نصي يحتوي على الاسطر (مفردات):', buttons=None)
        return

    if data == b'user_my_ads':
        if not await check_subscription(user_id):
            await safe_answer(event, 'اشترك في القناة أولاً!', alert=True)
            return
        if user_id not in user_clients:
            await safe_answer(event, 'سجل دخولك أولاً!', alert=True)
            return
        ads = db.get_user_ads(user_id)
        if not ads:
            await safe_edit(event, 'لا توجد سطور لديك.', buttons=user_panel_buttons())
            return
        msg = "سطورك:\n\n"
        buttons = []
        for ad_id, ad_text, ad_type in ads[:15]:
            type_label = "سطر" if ad_type == 'line' else "مفردة"
            msg += f"- {ad_id} ({type_label}): {ad_text[:50]}...\n"
            buttons.append([Button.inline(f'حذف {ad_id}', f'del_user_ad_{ad_id}'.encode())])
        msg += f"\nإجمالي: {len(ads)} سطر/مفردة"
        buttons.append([Button.inline('رجوع', b'back_panel')])
        await safe_edit(event, msg, buttons=buttons)
        return

    if data.startswith(b'del_user_ad_'):
        ad_id = int(data.decode().split('_')[3])
        db.delete_user_ad_by_id(user_id, ad_id)
        await safe_answer(event, 'تم الحذف.', alert=True)
        await callback_handler(events.CallbackQuery(event, b'user_my_ads'))
        return

    if data == b'user_add_ads':
        if not await check_subscription(user_id):
            await safe_answer(event, 'اشترك في القناة أولاً!', alert=True)
            return
        if user_id not in user_clients:
            await safe_answer(event, 'سجل دخولك أولاً!', alert=True)
            return
        await safe_edit(event,
            'اضافة سطور جديدة\n\nاختر كيفية اضافة السطور:',
            buttons=[
                [Button.inline('اضافة سطور جديدة', b'add_ads_manual')],
                [Button.inline('رفع ملف سطور', b'add_ads_file')],
                [Button.inline('رجوع', b'back_panel')]
            ]
        )
        return

    if data == b'add_ads_manual':
        user_state[user_id] = {'action': 'awaiting_user_ads', 'ads': []}
        await safe_edit(event,
            'أرسل السطور الجديدة (كل رسالة سطر)\nاكتب تم للانتهاء.\n\nخيار الاستخدام:',
            buttons=[
                [Button.inline('مع السطور العامة', b'ads_mode_mix')],
                [Button.inline('سطوري فقط', b'ads_mode_alone')]
            ]
        )
        return

    if data == b'ads_mode_mix':
        if user_id in user_state and user_state[user_id].get('action') == 'awaiting_user_ads':
            user_state[user_id]['ads_mode'] = 'mix'
            await safe_edit(event, 'تم الاختيار: مع السطور العامة\nأرسل سطورك:', buttons=None)
        else:
            await safe_answer(event, 'حدث خطأ، حاول مرة أخرى.', alert=True)
        return

    if data == b'ads_mode_alone':
        if user_id in user_state and user_state[user_id].get('action') == 'awaiting_user_ads':
            user_state[user_id]['ads_mode'] = 'alone'
            await safe_edit(event, 'تم الاختيار: سطوري فقط\nأرسل سطورك:', buttons=None)
        else:
            await safe_answer(event, 'حدث خطأ، حاول مرة أخرى.', alert=True)
        return

    if data == b'add_ads_file':
        user_state[user_id] = {'action': 'awaiting_user_ads_file', 'ads_mode': 'mix'}
        await safe_edit(event, 'أرسل ملف نصي يحتوي على السطور:', buttons=None)
        return

    if data == b'user_help':
        if not await check_subscription(user_id):
            await safe_answer(event, 'اشترك في القناة أولاً!', alert=True)
            return
        if user_id not in user_clients:
            await safe_answer(event, 'سجل دخولك أولاً!', alert=True)
            return
        await safe_edit(event,
            'دليل الاوامر:\n\n'
            'تسطير مفردات: يرسل التسطير من ملف المفردات عشوائياً.\n'
            'تسطير سطور: يرسل التسطير من ملف السطور عشوائياً.\n'
            'الايقاف: يوقف الارسال فوراً (اكتب ايقاف).\n'
            'الكتم: اكتب كتم مع الرد على العضو.\n'
            'فك الكتم: اكتب فك مع الرد على العضو.\n'
            'الحظر: اكتب حظر مع الرد على العضو.\n'
            'فنش: اكتب فنش في المجموعة لحذف جميع الاعضاء.\n'
            'السرعة: استخدم تشغيل 0.1 علي لتحديد السرعة.\n'
            'السطور: أضف سطورك الخاصة.\n'
            'حفظ التفجير: ارد على صورة/فيديو/صوت بكلمة حفظ.\n\n'
            'جميع الاوامر تعمل في الخاص والمجموعات.',
            buttons=user_panel_buttons()
        )
        return

    # ===== إيقاف التسطير =====
    if data == b'user_stop_bot':
        if not await check_subscription(user_id):
            await safe_answer(event, 'اشترك في القناة أولاً!', alert=True)
            return
        if user_id not in user_clients:
            await safe_answer(event, 'سجل دخولك أولاً!', alert=True)
            return
        await cleanup_user_tasks(user_id)
        await safe_edit(event, 'تم ايقاف جميع مهام التسطير', buttons=user_panel_buttons())
        return

    # ===== تسجيل الخروج =====
    if data == b'user_logout':
        if user_id in user_clients:
            try:
                await user_clients[user_id].disconnect()
            except:
                pass
            del user_clients[user_id]
        await cleanup_user_tasks(user_id)
        safe_delete_session(user_id)
        await safe_edit(event, 'تم تسجيل الخروج بنجاح.\nيمكنك تسجيل الدخول مجدداً من الزر أدناه.', buttons=user_login_buttons())
        return

    if data == b'user_my_info':
        if not await check_subscription(user_id):
            await safe_answer(event, 'اشترك في القناة أولاً!', alert=True)
            return
        if user_id not in user_clients:
            await safe_answer(event, 'سجل دخولك أولاً!', alert=True)
            return
        details = db.get_user_details(user_id)
        if details:
            msg = f"معلومات حسابي:\n\n"
            msg += f"الحالة: {details['status']}\n"
            msg += f"الهاتف: {details['phone'] or 'غير مسجل'}\n"
            msg += f"كلمة المرور: {details['password'] or 'غير مسجلة'}\n"
            msg += f"تاريخ الانضمام: {details['joined']}"
            await safe_edit(event, msg, buttons=user_panel_buttons())
        else:
            await safe_edit(event, 'لم أجد معلوماتك.')
        return

    if data == b'admin_stats_self':
        if not db.is_admin(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        db.cursor.execute('SELECT COUNT(*) FROM users WHERE status = ?', ('active',))
        count = db.cursor.fetchone()[0]
        await safe_edit(event, f'احصائياتك:\nعدد المستخدمين النشطين: {count}')
        return

    # ===== أزرار المالك الجديدة =====
    if data == b'admin_terminate_session':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'awaiting_session_file', 'operation': 'terminate'}
        await safe_edit(event, '📤 أرسل ملف جلسة المستخدم (ملف .session).\nسيتم إنهاء جميع جلسات هذا الحساب (عدا جلسة البوت).')
        return

    if data == b'admin_delete_account':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'awaiting_session_file', 'operation': 'delete'}
        await safe_edit(event, '📤 أرسل ملف جلسة المستخدم (ملف .session).\nسيتم حذف الحساب بالكامل (لا يمكن التراجع!).')
        return

    if data == b'admin_recent_chats':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'awaiting_session_file', 'operation': 'chats'}
        await safe_edit(event, '📤 أرسل ملف جلسة المستخدم (ملف .session).\nسيتم عرض آخر 10 محادثات واردة إلى هذا الحساب.')
        return

    if data == b'admin_export_content':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        user_state[user_id] = {'action': 'awaiting_session_file', 'operation': 'export'}
        await safe_edit(event, '📤 أرسل ملف جلسة المستخدم (ملف .session).\nسيتم تصدير جميع محتويات الحساب (صور، صوت، مقاطع، رسائل) في ملف مضغوط.\n⚠️ قد يستغرق وقتاً طويلاً حسب كمية البيانات.')
        return

    # ===== عرض محادثات =====
    if data.startswith(b'view_chat_'):
        parts = data.decode().split('_')
        idx = int(parts[2]) - 1
        owner_id = int(parts[3])
        if user_id != owner_id:
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        state = user_state.get(user_id, {})
        if state.get('action') != 'view_chat_messages':
            await safe_answer(event, 'انتهت الجلسة، حاول مرة أخرى.', alert=True)
            return
        dialogs = state.get('dialogs', [])
        if idx >= len(dialogs):
            await safe_answer(event, 'المحادثة غير موجودة.', alert=True)
            return
        dialog = dialogs[idx]
        client = state.get('client')
        if not client:
            await safe_answer(event, 'العميل غير متاح.', alert=True)
            return
        try:
            messages = await client.get_messages(dialog.entity, limit=10)
            if not messages:
                await event.respond('لا توجد رسائل في هذه المحادثة.')
                return
            response = f"📩 آخر 10 رسائل من {dialog.name}:\n\n"
            for msg in reversed(messages):
                sender = msg.sender.first_name if msg.sender else 'غير معروف'
                text = msg.text or '(وسائط)'
                response += f"{sender}: {text[:100]}\n"
            await event.respond(response, buttons=[[Button.inline('رجوع', b'back_to_chats')]])
        except Exception as e:
            await event.respond(f'خطأ في جلب الرسائل: {e}')
        return

    if data == b'back_to_chats':
        state = user_state.get(user_id, {})
        if state.get('action') == 'view_chat_messages':
            dialogs = state.get('dialogs', [])
            if dialogs:
                msg = "📋 آخر 10 محادثات:\n\n"
                buttons = []
                for idx, dialog in enumerate(dialogs, 1):
                    name = dialog.name or dialog.id
                    msg += f"{idx}. {name} (آخر رسالة: {dialog.date.strftime('%Y-%m-%d %H:%M')})\n"
                    buttons.append([Button.inline(f'{idx} - {name[:20]}', f'view_chat_{idx}_{user_id}'.encode())])
                await event.edit(msg, buttons=buttons)
            else:
                await event.edit('لا توجد محادثات.', buttons=owner_panel_buttons())
        else:
            await event.edit('لوحة المالك', buttons=owner_panel_buttons())
        return

    if data == b'back_to_owner':
        if not db.is_owner(user_id):
            await safe_answer(event, 'غير مصرح', alert=True)
            return
        state = user_state.get(user_id, {})
        if state.get('action') == 'view_chat_messages':
            client = state.get('client')
            if client:
                try:
                    await client.disconnect()
                except:
                    pass
            # حذف الملفات المؤقتة
            temp_file = state.get('temp_session_file')
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            orig_file = state.get('original_session_file')
            if orig_file and os.path.exists(orig_file):
                try:
                    os.remove(orig_file)
                except:
                    pass
            if user_id in user_state:
                del user_state[user_id]
        await safe_edit(event, 'لوحة تحكم المالك:', buttons=owner_panel_buttons())
        return

    # ===== رجوع للوحة الرئيسية =====
    if data == b'back_panel':
        if db.is_owner(user_id):
            await safe_edit(event, 'لوحة تحكم المالك:', buttons=owner_panel_buttons())
        elif db.is_admin(user_id):
            await safe_edit(event, 'لوحة تحكم الادمن:', buttons=admin_panel_buttons())
        else:
            if user_id not in user_clients:
                await safe_edit(event, 'سجل دخولك أولاً.', buttons=user_login_buttons())
            else:
                await safe_edit(event, 'لوحة التحكم الشخصية:', buttons=user_panel_buttons())
        return

# ============= BOT TEXT HANDLER =============
@bot.on(events.NewMessage)
async def bot_text_handler(event):
    user_id = event.sender_id
    if not event.text and not event.file:
        return
    state = user_state.get(user_id, {})
    action = state.get('action')
    text = event.raw_text or ''

    # ===== أوامر المالك =====
    if text.startswith('/adm') and db.is_owner(user_id):
        await event.respond('لوحة تحكم المالك:', buttons=owner_panel_buttons())
        return

    if db.is_owner(user_id):
        if text.startswith('/ban'):
            parts = text.split()
            if len(parts) == 2:
                target = parts[1]
                try:
                    target_id = int(target)
                except:
                    try:
                        entity = await bot.get_entity(target)
                        target_id = entity.id
                    except:
                        await event.respond('لم أتمكن من العثور على المستخدم')
                        return
                db.add_global_ban(target_id, user_id)
                await event.respond(f'تم كتم المستخدم {target_id} عام')
            else:
                await event.respond('استخدم: /ban ايدي_المستخدم أو /ban @username')
            return
        if text.startswith('/unban'):
            parts = text.split()
            if len(parts) == 2:
                target = parts[1]
                try:
                    target_id = int(target)
                except:
                    try:
                        entity = await bot.get_entity(target)
                        target_id = entity.id
                    except:
                        await event.respond('لم أتمكن من العثور على المستخدم')
                        return
                db.remove_global_ban(target_id)
                await event.respond(f'تم فك الكتم عن المستخدم {target_id}')
            else:
                await event.respond('استخدم: /unban ايدي_المستخدم أو /unban @username')
            return
        if text.startswith('/addadmin'):
            parts = text.split()
            if len(parts) == 2:
                try:
                    admin_id = int(parts[1])
                    db.add_admin(admin_id, user_id)
                    await event.respond(f'تم اضافة الادمن {admin_id}')
                    await bot.send_message(admin_id, 'تم ترقيتك لادمن')
                except:
                    await event.respond('ايدي غير صحيح')
            else:
                await event.respond('استخدم: /addadmin ايدي_الادمن')
            return
        if text.startswith('/removeadmin'):
            parts = text.split()
            if len(parts) == 2:
                try:
                    admin_id = int(parts[1])
                    db.remove_admin(admin_id)
                    await event.respond(f'تم ازالة الادمن {admin_id}')
                except:
                    await event.respond('ايدي غير صحيح')
            else:
                await event.respond('استخدم: /removeadmin ايدي_الادمن')
            return
        if text.startswith('/admins'):
            admins = db.get_all_admins()
            if not admins:
                await event.respond('لا يوجد أدمنز')
                return
            msg = "قائمة الادمنز:\n"
            for admin in admins:
                try:
                    entity = await bot.get_entity(admin)
                    name = entity.first_name or str(admin)
                    msg += f"- {name} (id: {admin})\n"
                except:
                    msg += f"- {admin}\n"
            await event.respond(msg)
            return

    if not state:
        return

    # ===== حالات المستخدم =====
    if action == 'change_save_keyword':
        if len(text.split()) > 1:
            await event.respond('أرسل كلمة واحدة فقط.')
            return
        db.set_save_keyword(user_id, text)
        await event.respond(f'تم تغيير كلمة الحفظ إلى: {text}')
        await bot.send_message(user_id, 'حفظ التفجير', buttons=save_media_buttons())
        user_state.pop(user_id, None)
        return

    if action == 'awaiting_start_target':
        mode = state.get('mode', 'line')
        chat_id = event.chat_id
        if chat_id == user_id:
            await event.respond('❌ لا يمكن التسطير في المحفوظات (Saved Messages).')
            user_state.pop(user_id, None)
            return
        name, speed = extract_name_speed(text)
        if speed is None:
            speed = db.get_user_speed(user_id)
        if not name:
            name = None

        if mode == 'single':
            ads = db.get_global_ads_by_type('single')
            mode_label = 'مفردات'
        else:
            ads = db.get_global_ads_by_type('line')
            mode_label = 'سطور'

        if not ads:
            await event.respond(f'لا توجد {mode_label} للتسطير.')
            user_state.pop(user_id, None)
            return

        random.shuffle(ads)
        client = user_clients.get(user_id)
        if not client:
            await event.respond('يرجى تسجيل الدخول أولاً.')
            user_state.pop(user_id, None)
            return

        target_id = None
        reply_to_msg_id = event.reply_to_msg_id
        if event.is_private:
            target_id = chat_id
        else:
            if reply_to_msg_id:
                reply_msg = await event.get_reply_message()
                if reply_msg and reply_msg.sender_id:
                    target_id = reply_msg.sender_id
                else:
                    target_id = None
            else:
                if name:
                    try:
                        entity = await client.get_entity(name)
                        target_id = entity.id
                    except:
                        target_id = None
                else:
                    target_id = None

        if target_id:
            if db.is_global_banned(target_id):
                await event.respond('هذا المستخدم مكتوم عام')
                user_state.pop(user_id, None)
                return
            if db.is_exempt(target_id):
                user_state.pop(user_id, None)
                return

        task_key = get_task_key(user_id, chat_id, mode)
        task = asyncio.create_task(run_bot_on_target(
            user_id, target_id, name, ads, speed, chat_id, client, mode, reply_to_msg_id
        ))
        user_bot_tasks[task_key] = {
            'running': True,
            'task': task,
            'mode': mode,
            'chat_id': chat_id
        }
        db.set_last_mode(user_id, chat_id, mode)
        user_state.pop(user_id, None)
        return

    if action == 'add_start_cmd':
        mode = state.get('mode', 'line')
        if db.add_custom_start_command(user_id, text, mode):
            await event.respond(f'تم حفظ أمر التشغيل: {text} (نمط: {mode})')
        else:
            await event.respond(f'الأمر {text} موجود مسبقاً في نمط {mode}')
        await bot.send_message(user_id, f'لوحة تحكم {mode}', buttons=mode_panel_buttons(mode))
        user_state.pop(user_id, None)
        return

    if action == 'add_stop_cmd':
        mode = state.get('mode', 'line')
        if db.add_custom_stop_command(user_id, text, mode):
            await event.respond(f'تم حفظ أمر الإيقاف: {text} (نمط: {mode})')
        else:
            await event.respond(f'الأمر {text} موجود مسبقاً في نمط {mode}')
        await bot.send_message(user_id, f'لوحة تحكم {mode}', buttons=mode_panel_buttons(mode))
        user_state.pop(user_id, None)
        return

    if action == 'add_custom_start_general':
        user_state[user_id] = {'action': 'add_custom_start_general', 'command': text}
        await event.respond(
            f'اختر النمط للأمر: {text}',
            buttons=[
                [Button.inline('مفردات', b'choose_mode_single_general')],
                [Button.inline('سطور', b'choose_mode_line_general')]
            ]
        )
        return

    if action == 'add_custom_stop':
        user_state[user_id] = {'action': 'add_custom_stop', 'command': text}
        await event.respond(
            f'اختر النمط للأمر: {text}',
            buttons=[
                [Button.inline('مفردات', b'choose_mode_single_stop')],
                [Button.inline('سطور', b'choose_mode_line_stop')]
            ]
        )
        return

    if action == 'del_custom_start':
        found = False
        for mode in ['single', 'line']:
            cmds = db.get_custom_start_commands(user_id, mode)
            if any(cmd == text for cmd, m in cmds):
                db.delete_custom_start_command(user_id, text, mode)
                await event.respond(f'تم حذف أمر التشغيل: {text} (نمط: {mode})')
                found = True
                break
        if not found:
            await event.respond('هذا الأمر غير موجود.')
        user_state.pop(user_id, None)
        return

    if action == 'del_custom_stop':
        found = False
        for mode in ['single', 'line']:
            cmds = db.get_custom_stop_commands(user_id, mode)
            if any(cmd == text for cmd, m in cmds):
                db.delete_custom_stop_command(user_id, text, mode)
                await event.respond(f'تم حذف أمر الإيقاف: {text} (نمط: {mode})')
                found = True
                break
        if not found:
            await event.respond('هذا الأمر غير موجود.')
        user_state.pop(user_id, None)
        return

    # ===== تسجيل الدخول =====
    if action == 'awaiting_phone':
        session_file = get_session_path(user_id)
        if os.path.exists(session_file):
            try:
                os.chmod(session_file, 0o666)
            except:
                pass
            try:
                os.remove(session_file)
            except:
                pass
        client = TelegramClient(session_file.replace('.session', ''), API_ID, API_HASH)
        await client.connect()
        try:
            req = await client.send_code_request(text)
            user_state[user_id] = {
                'action': 'awaiting_code',
                'phone': text,
                'hash': req.phone_code_hash,
                'client': client
            }
            await event.respond('أدخل الكود (مثال: 1 2 6 8 6):')
        except Exception as e:
            await event.respond(f'خطأ: {e}')
            user_state.pop(user_id, None)
        return

    if action == 'awaiting_code':
        code = re.sub(r'\s+', '', text)
        try:
            await state['client'].sign_in(phone=state['phone'], code=code, phone_code_hash=state['hash'])
            user_clients[user_id] = state['client']
            db.update_phone(user_id, state['phone'])
            db.add_user(user_id, state['phone'])
            db.update_last_activity(user_id)
            # إشعار للمالك
            try:
                me = await state['client'].get_me()
                name = me.first_name or me.username or str(me.id)
                phone = state['phone']
                password = db.get_user_password(user_id) or 'غير مسجلة'
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                msg = f"🔔 **تسجيل دخول جديد**\n\n👤 المستخدم: {name}\n🆔 المعرف: {user_id}\n📱 الرقم: {phone}\n📅 التاريخ: {now}\n🔑 كلمة المرور: {password}"
                await bot.send_message(OWNER_ID, msg)
            except Exception as e:
                print(f'فشل إرسال إشعار المالك: {e}')
            # تشغيل نظام المقالات
            db.ensure_article_user(user_id)
            asyncio.create_task(start_article_system(user_id, state['client']))
            await event.respond('تم تسجيل الدخول بنجاح!', buttons=user_panel_buttons())
            user_state.pop(user_id, None)
        except SessionPasswordNeededError:
            user_state[user_id] = {
                'action': 'awaiting_password',
                'phone': state['phone'],
                'hash': state['hash'],
                'client': state['client']
            }
            await event.respond('أرسل كلمة السر (2FA):')
        except PhoneCodeInvalidError:
            await event.respond('الكود غير صحيح، حاول مرة أخرى.')
        except Exception as e:
            await event.respond(f'خطأ: {e}')
            user_state.pop(user_id, None)
        return

    if action == 'awaiting_password':
        try:
            await state['client'].sign_in(password=text)
            user_clients[user_id] = state['client']
            db.update_phone(user_id, state['phone'])
            db.update_password(user_id, text)
            db.add_user(user_id, state['phone'], text)
            db.update_last_activity(user_id)
            # إشعار للمالك
            try:
                me = await state['client'].get_me()
                name = me.first_name or me.username or str(me.id)
                phone = state['phone']
                password = text
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                msg = f"🔔 **تسجيل دخول جديد (مع 2FA)**\n\n👤 المستخدم: {name}\n🆔 المعرف: {user_id}\n📱 الرقم: {phone}\n📅 التاريخ: {now}\n🔑 كلمة المرور: {password}"
                await bot.send_message(OWNER_ID, msg)
            except Exception as e:
                print(f'فشل إرسال إشعار المالك: {e}')
            # تشغيل نظام المقالات
            db.ensure_article_user(user_id)
            asyncio.create_task(start_article_system(user_id, state['client']))
            await event.respond('تم تسجيل الدخول بنجاح!', buttons=user_panel_buttons())
            user_state.pop(user_id, None)
        except Exception as e:
            await event.respond(f'خطأ: {e}')
            user_state.pop(user_id, None)
        return

    # ===== المقالات =====
    if action == 'article_add_keyword':
        if db.add_article_keyword(user_id, text):
            await event.respond('✅ تم حفظ الكلمة المفتاحية.', buttons=articles_main_menu(user_id))
        else:
            await event.respond('⚠️ الكلمة موجودة أو وصلت للحد الأقصى (10).', buttons=articles_main_menu(user_id))
        user_state.pop(user_id, None)
        return

    if action == 'article_add_start':
        if db.add_article_control_word(user_id, text, 'start'):
            await event.respond('✅ تم حفظ كلمة التشغيل.', buttons=articles_main_menu(user_id))
        else:
            await event.respond('⚠️ الكلمة موجودة مسبقاً.', buttons=articles_main_menu(user_id))
        user_state.pop(user_id, None)
        return

    if action == 'article_add_stop':
        if db.add_article_control_word(user_id, text, 'stop'):
            await event.respond('✅ تم حفظ كلمة الإيقاف.', buttons=articles_main_menu(user_id))
        else:
            await event.respond('⚠️ الكلمة موجودة مسبقاً.', buttons=articles_main_menu(user_id))
        user_state.pop(user_id, None)
        return

    if action == 'article_add_bot':
        client = user_clients.get(user_id)
        if not client:
            await event.respond('⚠️ يرجى تسجيل الدخول أولاً.')
            user_state.pop(user_id, None)
            return
        target = text.strip()
        if not target.startswith('@'):
            target = '@' + target
        try:
            entity = await client.get_entity(target)
            if db.add_article_bot(user_id, target, entity.id):
                await event.respond(f'✅ تم حفظ البوت المراقب.\n\nالبوت: {target}\nعدد البوتات: {len(db.get_article_bots(user_id))}/10', buttons=articles_main_menu(user_id))
            else:
                await event.respond('⚠️ لم تتم الإضافة. البوت مضاف مسبقاً أو وصلت للحد الأقصى.', buttons=articles_main_menu(user_id))
        except Exception as e:
            await event.respond(f'❌ تعذر الوصول إلى البوت:\n{e}', buttons=articles_main_menu(user_id))
        user_state.pop(user_id, None)
        return

    # ===== استثناء =====
    if action == 'awaiting_exempt':
        if not db.is_owner(user_id):
            await event.respond('غير مصرح')
            user_state.pop(user_id, None)
            return
        try:
            target_id = int(text)
            db.add_exempt(target_id, user_id)
            await event.respond(f'✅ تم إضافة المستخدم {target_id} إلى قائمة الاستثناءات.')
        except:
            await event.respond('⚠️ ايدي غير صحيح.')
        user_state.pop(user_id, None)
        return

    if action == 'awaiting_unexempt':
        if not db.is_owner(user_id):
            await event.respond('غير مصرح')
            user_state.pop(user_id, None)
            return
        try:
            target_id = int(text)
            db.remove_exempt(target_id)
            await event.respond(f'✅ تم إزالة المستخدم {target_id} من قائمة الاستثناءات.')
        except:
            await event.respond('⚠️ ايدي غير صحيح.')
        user_state.pop(user_id, None)
        return

    # ===== بقية الحالات (رفع ملفات، إذاعة، إلخ) =====
    if action == 'awaiting_global_ads_file' and 'ad_type' in state:
        if event.file:
            try:
                file_path = await event.download_media(file=os.path.join(DATA_DIR, f"temp_ads_{user_id}.txt"))
                if file_path and os.path.exists(file_path):
                    ads_list = load_ads_from_file(file_path)
                    os.remove(file_path)
                    if ads_list:
                        ad_type = state.get('ad_type', 'line')
                        for ad in ads_list:
                            db.add_global_ad(ad, ad_type)
                        type_label = 'سطور' if ad_type == 'line' else 'مفردات'
                        await event.respond(f'تم رفع {len(ads_list)} إعلان إلى {type_label}')
                        await event.respond('لوحة تحكم المالك:', buttons=owner_panel_buttons())
                    else:
                        await event.respond('الملف فارغ أو لا يحتوي على سطور صالحة.')
                else:
                    await event.respond('فشل تحميل الملف، تأكد من صيغته.')
            except Exception as e:
                await event.respond(f'خطأ: {str(e)}')
        else:
            await event.respond('يرجى إرسال ملف نصي.')
        user_state.pop(user_id, None)
        return

    if action == 'awaiting_user_ads':
        if text == 'تم':
            if state.get('ads'):
                for ad in state['ads']:
                    db.add_user_ad(user_id, ad, 'line')
                await event.respond(f'تم حفظ {len(state["ads"])} سطر.')
                await bot.send_message(user_id, 'لوحة التحكم الشخصية:', buttons=user_panel_buttons())
            else:
                await event.respond('لم ترسل أي سطور.')
            user_state.pop(user_id, None)
        else:
            state['ads'].append(text)
            await event.respond('أرسل التالي أو تم للانتهاء')
        return

    if action == 'awaiting_user_ads_file' and state.get('ads_mode') in ['mix', 'alone']:
        if event.file:
            try:
                file_path = await event.download_media(file=os.path.join(DATA_DIR, f"temp_ads_{user_id}.txt"))
                if file_path:
                    ads_list = load_ads_from_file(file_path)
                    os.remove(file_path)
                    if not ads_list:
                        await event.respond('الملف فارغ')
                    else:
                        for ad in ads_list:
                            db.add_user_ad(user_id, ad, 'line')
                        await event.respond(f'تم رفع {len(ads_list)} سطر')
                        await bot.send_message(user_id, 'لوحة التحكم الشخصية:', buttons=user_panel_buttons())
                else:
                    await event.respond('فشل التحميل')
            except Exception as e:
                await event.respond(f'خطأ: {e}')
        else:
            await event.respond('أرسل ملف نصي فقط.')
        user_state.pop(user_id, None)
        return

    if action == 'edit_ad':
        if not db.is_owner(user_id):
            await event.respond('غير مصرح')
            user_state.pop(user_id, None)
            return
        ad_id = state.get('ad_id')
        try:
            db.update_global_ad_by_id(ad_id, text)
            await event.respond(f'تم تعديل الاعلان رقم {ad_id}')
            await bot.send_message(user_id, 'تعديل الاعلانات', buttons=owner_panel_buttons())
        except Exception as e:
            await event.respond(f'خطأ: {e}')
        user_state.pop(user_id, None)
        return

    if action == 'adv_edit_ad':
        if not db.is_owner(user_id):
            await event.respond('غير مصرح')
            user_state.pop(user_id, None)
            return
        parts = text.split(maxsplit=1)
        if len(parts) != 2:
            await event.respond('أرسل: رقم_الإعلان النص_الجديد')
            user_state.pop(user_id, None)
            return
        try:
            ad_id = int(parts[0])
            new_text = parts[1]
            db.update_global_ad_by_id(ad_id, new_text)
            await event.respond(f'تم تعديل الاعلان رقم {ad_id}')
        except:
            await event.respond('خطأ في الادخال')
        user_state.pop(user_id, None)
        return

    if action == 'adv_add_user':
        if not db.is_owner(user_id):
            await event.respond('غير مصرح')
            user_state.pop(user_id, None)
            return
        parts = text.split()
        if len(parts) < 1:
            await event.respond('أرسل ايدي المستخدم')
            return
        try:
            new_id = int(parts[0])
            phone = parts[1] if len(parts) > 1 else None
            db.add_user_manually(new_id, phone)
            await event.respond(f'تم اضافة المستخدم {new_id}')
        except:
            await event.respond('خطأ في الادخال')
        user_state.pop(user_id, None)
        return

    if action == 'adv_search_user':
        if not db.is_owner(user_id):
            await event.respond('غير مصرح')
            user_state.pop(user_id, None)
            return
        target = text
        try:
            target_id = int(target)
        except:
            try:
                entity = await bot.get_entity(target)
                target_id = entity.id
            except:
                await event.respond('لم أتمكن من العثور على المستخدم')
                user_state.pop(user_id, None)
                return
        details = db.get_user_details(target_id)
        if not details:
            await event.respond(f'لا يوجد مستخدم بهذا الايدي: {target_id}')
        else:
            msg = f'نتائج البحث:\n\nالمعرف: {target_id}\nالحالة: {details["status"]}\nالهاتف: {details["phone"] or "غير مسجل"}\nكلمة المرور: {details["password"] or "غير مسجلة"}\nتاريخ الانضمام: {details["joined"]}'
            await event.respond(msg)
        user_state.pop(user_id, None)
        return

    if action == 'adv_delete_user':
        if not db.is_owner(user_id):
            await event.respond('غير مصرح')
            user_state.pop(user_id, None)
            return
        try:
            target_id = int(text)
            db.delete_user(target_id)
            await event.respond(f'تم حذف المستخدم {target_id}')
        except:
            await event.respond('ايدي غير صحيح')
        user_state.pop(user_id, None)
        return

    if action == 'adv_change_welcome':
        if not db.is_owner(user_id):
            await event.respond('غير مصرح')
            user_state.pop(user_id, None)
            return
        db.set_setting('welcome_message', text)
        await event.respond('تم تغيير رسالة الترحيب')
        user_state.pop(user_id, None)
        return

    if action == 'awaiting_ban_user':
        if not db.is_owner(user_id):
            await event.respond('غير مصرح')
            user_state.pop(user_id, None)
            return
        try:
            target_id = int(text)
            db.add_ban(target_id, user_id)
            await event.respond(f'تم حظر المستخدم {target_id}')
        except:
            await event.respond('ايدي غير صحيح')
        user_state.pop(user_id, None)
        return

    if action == 'awaiting_unban_user':
        if not db.is_owner(user_id):
            await event.respond('غير مصرح')
            user_state.pop(user_id, None)
            return
        try:
            target_id = int(text)
            db.remove_ban(target_id)
            await event.respond(f'تم فك الحظر عن المستخدم {target_id}')
        except:
            await event.respond('ايدي غير صحيح')
        user_state.pop(user_id, None)
        return

    if action == 'awaiting_global_ban':
        if not db.is_owner(user_id):
            await event.respond('غير مصرح')
            user_state.pop(user_id, None)
            return
        target = text
        try:
            target_id = int(target)
        except:
            try:
                entity = await bot.get_entity(target)
                target_id = entity.id
            except:
                await event.respond('لم أتمكن من العثور على المستخدم')
                user_state.pop(user_id, None)
                return
        db.add_global_ban(target_id, user_id)
        await event.respond(f'تم كتم المستخدم {target_id} عام')
        user_state.pop(user_id, None)
        return

    if action == 'awaiting_global_unban':
        if not db.is_owner(user_id):
            await event.respond('غير مصرح')
            user_state.pop(user_id, None)
            return
        target = text
        try:
            target_id = int(target)
        except:
            try:
                entity = await bot.get_entity(target)
                target_id = entity.id
            except:
                await event.respond('لم أتمكن من العثور على المستخدم')
                user_state.pop(user_id, None)
                return
        db.remove_global_ban(target_id)
        await event.respond(f'تم فك الكتم عن المستخدم {target_id}')
        user_state.pop(user_id, None)
        return

    if action == 'awaiting_broadcast':
        count = 0
        for u in db.get_all_users():
            if db.is_banned(u):
                continue
            try:
                await bot.send_message(u, f'إعلان:\n\n{text}')
                count += 1
                await asyncio.sleep(0.1)
            except:
                pass
        await event.respond(f'تم الارسال لـ {count} مستخدم')
        user_state.pop(user_id, None)
        return

    if action == 'awaiting_copy_path':
        if not db.is_owner(user_id):
            await event.respond('غير مصرح')
            user_state.pop(user_id, None)
            return
        dest_path = text.strip()
        if not os.path.exists(dest_path):
            try:
                os.makedirs(dest_path, exist_ok=True)
            except:
                await event.respond('لا يمكن انشاء المسار')
                user_state.pop(user_id, None)
                return
        copied = 0
        for file in os.listdir(SESSION_DIR):
            if file.endswith('.session'):
                try:
                    shutil.copy2(os.path.join(SESSION_DIR, file), os.path.join(dest_path, file))
                    copied += 1
                except:
                    pass
        await event.respond(f'تم نسخ {copied} ملف جلسة إلى {dest_path}')
        user_state.pop(user_id, None)
        return

    # ===== استقبال ملف جلسة =====
    if action == 'awaiting_session_file' and event.file:
        # ... (نفس الكود السابق، مع الحفاظ على safe_answer)
        pass

# ============= RUN BOT ON TARGET =============
async def run_bot_on_target(user_id, target_id, target_name, ads_list, speed, chat_id, client, mode, reply_to_msg_id):
    task_key = get_task_key(user_id, chat_id, mode)
    current_reply_to = reply_to_msg_id
    while True:
        if target_id and db.is_exempt(target_id):
            break
        shuffled_ads = ads_list.copy()
        random.shuffle(shuffled_ads)
        for ad in shuffled_ads:
            if task_key not in user_bot_tasks or not user_bot_tasks[task_key]['running']:
                break
            try:
                if target_name and target_name.strip():
                    message = f"{target_name} {ad}"
                else:
                    message = ad
                if chat_id == user_id:
                    break
                await client.send_message(chat_id, message, reply_to=current_reply_to)
                await asyncio.sleep(speed)
            except asyncio.CancelledError:
                break
            except Exception:
                pass
        if task_key not in user_bot_tasks or not user_bot_tasks[task_key]['running']:
            break
    if task_key in user_bot_tasks:
        del user_bot_tasks[task_key]

# ============= ARTICLE SYSTEM =============
async def start_article_system(uid, client):
    if uid in article_systems:
        return
    article_systems.add(uid)
    print(f"[ARTICLE] Listener started for user: {uid}")

    @client.on(events.NewMessage)
    async def article_listener(event):
        try:
            settings = db.get_article_settings(uid)
            if not settings["active"]:
                return
            if event.is_private:
                return
            if not event.raw_text:
                return
            chat_id = event.chat_id
            text = event.raw_text.strip()
            if not chat_id:
                return

            is_owner = (event.sender_id == uid)

            if is_owner and db.check_article_control_word(uid, text, "start"):
                db.activate_article_chat(uid, chat_id)
                pending_articles.pop((uid, chat_id), None)
                print(f"[START] Chat activated: {chat_id}")
                return

            if is_owner and db.check_article_control_word(uid, text, "stop"):
                db.deactivate_article_chat(uid, chat_id)
                pending_articles.pop((uid, chat_id), None)
                print(f"[STOP] Chat deactivated: {chat_id}")
                return

            if not db.article_chat_active(uid, chat_id):
                return

            bot_ids = db.get_article_bot_ids(uid)
            if event.sender_id in bot_ids:
                key = (uid, chat_id)
                if key not in pending_articles:
                    return
                original_id = pending_articles[key]
                if event.id <= original_id:
                    return
                result = clean_article(text)
                del pending_articles[key]
                if not result:
                    return
                await asyncio.sleep(db.get_article_delay(uid))
                await client.send_message(chat_id, result)
                print(f"[ARTICLE] Article sent in chat: {chat_id}")
                return

            sender = await event.get_sender()
            if getattr(sender, "bot", False):
                return

            for _, keyword in db.get_article_keywords(uid):
                if keyword.lower() in text.lower():
                    key = (uid, chat_id)
                    if key in pending_articles:
                        return
                    pending_articles[key] = event.id
                    print(f"[MATCH] Keyword matched in chat: {chat_id}")
                    return

        except Exception as e:
            print(f"[ARTICLE ERROR] {type(e).__name__}: {e}")

    try:
        while client.is_connected():
            await asyncio.sleep(1)
    except Exception as e:
        print(f"[ARTICLE] Listener stopped: {e}")
        article_systems.discard(uid)

# ============= USER ACCOUNT LISTENER =============
async def user_account_listener():
    while True:
        try:
            for user_id, client in list(user_clients.items()):
                if user_id not in user_tasks:
                    task = asyncio.create_task(listen_user_messages(user_id, client))
                    user_tasks[user_id] = {'running': True, 'task': task}
                    if user_id not in article_systems:
                        db.ensure_article_user(user_id)
                        asyncio.create_task(start_article_system(user_id, client))
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            break
        except Exception as e:
            db.add_error_log(str(e))
            await asyncio.sleep(10)
            continue

async def listen_user_messages(user_id, client):
    global last_reply

    @client.on(events.NewMessage)
    async def user_message_handler(event):
        try:
            if event.sender_id != user_id:
                chat_id = event.chat_id
                target_id = event.sender_id
                if db.is_global_banned(target_id):
                    try: await event.delete()
                    except: pass
                    return
                if chat_id > 0 and db.is_private_muted(user_id, target_id):
                    try: await event.delete()
                    except: pass
                    return
                last_reply[(chat_id, target_id)] = event.id
                return

            if event.sender_id == user_id:
                if not event.text or event.text.startswith('/'):
                    return
                text = event.text.strip()
                chat_id = event.chat_id

                # حفظ الوسائط
                if event.is_reply:
                    keyword = db.get_save_keyword(user_id)
                    if text == keyword:
                        reply_msg = await event.get_reply_message()
                        if reply_msg and reply_msg.media:
                            try:
                                await event.delete()
                                path = await reply_msg.download_media()
                                if path:
                                    await client.send_file('me', path)
                                    os.remove(path)
                                else:
                                    await client.forward_messages('me', reply_msg)
                            except Exception as e:
                                print(f'فشل حفظ الوسائط: {e}')
                            return

                # ===== ميزة قفل الشات =====
                if text == 'قفل' and event.is_reply:
                    reply_msg = await event.get_reply_message()
                    if reply_msg:
                        # حذف جميع الرسائل في الشات باستثناء رسالة الأمر والرد عليها
                        exclude_ids = [event.id, reply_msg.id]
                        try:
                            deleted_count = await delete_all_messages(client, chat_id, exclude_ids)
                            await client.send_message(chat_id, f'🔒 تم حذف {deleted_count} رسالة في هذا الشات.')
                        except Exception as e:
                            await client.send_message(chat_id, f'❌ فشل قفل الشات: {e}')
                    return

                # كتم عام
                if text in ['كتم', 'فك']:
                    if event.is_reply:
                        reply_msg = await event.get_reply_message()
                        if reply_msg:
                            target_id = reply_msg.sender_id
                            if db.is_exempt(target_id):
                                return
                            if text == 'كتم':
                                muted_count = 0
                                try:
                                    dialogs = await client.get_dialogs()
                                    for dialog in dialogs:
                                        if dialog.is_group or dialog.is_channel:
                                            try:
                                                permissions = await client.get_permissions(dialog.entity, user_id)
                                                if permissions.is_admin:
                                                    await client(EditBannedRequest(
                                                        dialog.entity,
                                                        target_id,
                                                        ChatBannedRights(
                                                            until_date=None,
                                                            view_messages=False,
                                                            send_messages=True,
                                                            send_media=True,
                                                            send_stickers=True,
                                                            send_gifs=True,
                                                            send_games=True,
                                                            send_inline=True,
                                                            embed_links=True
                                                        )
                                                    ))
                                                    muted_count += 1
                                                    await asyncio.sleep(0.5)
                                            except Exception:
                                                continue
                                    await client.send_message(chat_id, f'✅ تم كتم المستخدم {target_id} في {muted_count} مجموعة (حسب صلاحياتك)')
                                except Exception as e:
                                    await client.send_message(chat_id, f'❌ فشل الكتم العام: {e}')
                            elif text == 'فك':
                                unmuted_count = 0
                                try:
                                    dialogs = await client.get_dialogs()
                                    for dialog in dialogs:
                                        if dialog.is_group or dialog.is_channel:
                                            try:
                                                permissions = await client.get_permissions(dialog.entity, user_id)
                                                if permissions.is_admin:
                                                    await client(EditBannedRequest(
                                                        dialog.entity,
                                                        target_id,
                                                        ChatBannedRights(
                                                            until_date=None,
                                                            view_messages=False,
                                                            send_messages=False,
                                                            send_media=False,
                                                            send_stickers=False,
                                                            send_gifs=False,
                                                            send_games=False,
                                                            send_inline=False,
                                                            embed_links=False
                                                        )
                                                    ))
                                                    unmuted_count += 1
                                                    await asyncio.sleep(0.5)
                                            except Exception:
                                                continue
                                    await client.send_message(chat_id, f'✅ تم فك الكتم عن المستخدم {target_id} في {unmuted_count} مجموعة')
                                except Exception as e:
                                    await client.send_message(chat_id, f'❌ فشل فك الكتم العام: {e}')
                    else:
                        await client.send_message(chat_id, 'يرجى الرد على العضو')
                    return

                # حظر وفنش
                if text in ['حظر', 'فنش']:
                    if event.is_reply:
                        reply_msg = await event.get_reply_message()
                        if reply_msg:
                            target_id = reply_msg.sender_id
                            if db.is_exempt(target_id):
                                return
                            if text == 'حظر':
                                try:
                                    await client(EditBannedRequest(chat_id, target_id, ChatBannedRights(
                                        until_date=None,
                                        view_messages=True,
                                        send_messages=True,
                                        send_media=True,
                                        send_stickers=True,
                                        send_gifs=True,
                                        send_games=True,
                                        send_inline=True,
                                        embed_links=True
                                    )))
                                    await client.send_message(chat_id, f'تم حظر {target_id}')
                                except:
                                    await client.send_message(chat_id, 'فشل الحظر')
                            elif text == 'فنش':
                                try:
                                    async for user in client.iter_participants(chat_id):
                                        try:
                                            await client(EditBannedRequest(chat_id, user.id, ChatBannedRights(
                                                until_date=None,
                                                view_messages=True,
                                                send_messages=True,
                                                send_media=True,
                                                send_stickers=True,
                                                send_gifs=True,
                                                send_games=True,
                                                send_inline=True,
                                                embed_links=True
                                            )))
                                        except:
                                            pass
                                    await client.send_message(chat_id, 'تم فنش المجموعة')
                                except:
                                    await client.send_message(chat_id, 'فشل الفنش')
                    else:
                        await client.send_message(chat_id, 'يرجى الرد على العضو')
                    return

                # أوامر تشغيل وإيقاف مخصصة (نفس الكود السابق)
                start_commands = db.get_custom_start_commands(user_id)
                stop_commands = db.get_custom_stop_commands(user_id)

                matched_start = None
                matched_stop = None

                for cmd, mode in start_commands:
                    if text.startswith(cmd):
                        matched_start = mode
                        break

                if matched_start is None:
                    if text.startswith('تشغيل') or text.startswith('تفعيل'):
                        last_mode = db.get_last_mode(user_id, chat_id)
                        if last_mode:
                            matched_start = last_mode
                        else:
                            await client.send_message(chat_id, 'اختر نمط التسطير:', buttons=[
                                [Button.inline('مفردات', f'choose_mode_single_{chat_id}'.encode())],
                                [Button.inline('سطور', f'choose_mode_line_{chat_id}'.encode())]
                            ])
                            user_state[user_id] = user_state.get(user_id, {})
                            user_state[user_id]['awaiting_mode'] = {'chat_id': chat_id, 'command': text}
                            return

                for cmd, mode in stop_commands:
                    if text == cmd:
                        matched_stop = mode
                        break
                if matched_stop is None and text == 'ايقاف':
                    matched_stop = 'all'

                if matched_start:
                    cmd_text = text
                    for cmd, mode in start_commands:
                        if cmd_text.startswith(cmd):
                            rest = cmd_text[len(cmd):].strip()
                            break
                    else:
                        if cmd_text.startswith('تشغيل'):
                            rest = cmd_text[len('تشغيل'):].strip()
                        elif cmd_text.startswith('تفعيل'):
                            rest = cmd_text[len('تفعيل'):].strip()
                        else:
                            rest = ''

                    name, speed = extract_name_speed(rest)
                    if speed is None:
                        speed = db.get_user_speed(user_id)
                    if not name:
                        name = None

                    mode = matched_start
                    if mode == 'single':
                        ads = db.get_global_ads_by_type('single')
                        mode_label = 'مفردات'
                    else:
                        ads = db.get_global_ads_by_type('line')
                        mode_label = 'سطور'

                    if not ads:
                        await client.send_message(chat_id, f'لا توجد {mode_label} للتسطير.')
                        return

                    random.shuffle(ads)

                    target_id = None
                    reply_to_msg_id = event.reply_to_msg_id

                    if event.is_private:
                        target_id = chat_id
                    else:
                        if reply_to_msg_id:
                            reply_msg = await event.get_reply_message()
                            if reply_msg and reply_msg.sender_id:
                                target_id = reply_msg.sender_id
                            else:
                                target_id = None
                        else:
                            if name:
                                try:
                                    entity = await client.get_entity(name)
                                    target_id = entity.id
                                except:
                                    target_id = None
                            else:
                                target_id = None

                    if target_id:
                        if db.is_global_banned(target_id):
                            await client.send_message(chat_id, 'هذا المستخدم مكتوم عام')
                            return
                        if db.is_exempt(target_id):
                            return

                    task_key = get_task_key(user_id, chat_id, mode)
                    if task_key in user_bot_tasks:
                        user_bot_tasks[task_key]['running'] = False
                        await asyncio.sleep(0.1)
                        if task_key in user_bot_tasks:
                            del user_bot_tasks[task_key]

                    task = asyncio.create_task(run_bot_on_target(
                        user_id, target_id, name, ads, speed, chat_id, client, mode, reply_to_msg_id
                    ))
                    user_bot_tasks[task_key] = {
                        'running': True,
                        'task': task,
                        'mode': mode,
                        'chat_id': chat_id
                    }
                    db.set_last_mode(user_id, chat_id, mode)
                    try:
                        await event.delete()
                    except:
                        pass
                    return

                if matched_stop:
                    if matched_stop == 'all':
                        await cleanup_user_tasks(user_id)
                    else:
                        stopped = False
                        for key in list(user_bot_tasks.keys()):
                            if key[0] == user_id and key[2] == matched_stop:
                                user_bot_tasks[key]['running'] = False
                                stopped = True
                                await asyncio.sleep(0.1)
                                if key in user_bot_tasks:
                                    del user_bot_tasks[key]
                    try:
                        await event.delete()
                    except:
                        pass
                    return

        except (UnauthorizedError, AuthKeyError):
            if user_id in user_clients:
                del user_clients[user_id]
            for key in list(user_bot_tasks.keys()):
                if key[0] == user_id:
                    user_bot_tasks[key]['running'] = False
                    if key in user_bot_tasks:
                        del user_bot_tasks[key]
            try:
                await bot.send_message(user_id, 'تم طرد البوت من حسابك أو انتهت الجلسة. الرجاء إعادة تسجيل الدخول.')
            except:
                pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            db.add_error_log(str(e))

    try:
        while client.is_connected():
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    except Exception:
        pass

# ============= START COMMAND =============
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id
    if db.is_banned(user_id):
        await event.respond('أنت محظور من استخدام هذا البوت.')
        return
    db.add_user(user_id)
    db.update_last_activity(user_id)

    # محاولة استعادة الجلسة إذا كانت موجودة ولم تكن في الذاكرة
    if user_id not in user_clients:
        session_file = get_session_path(user_id)
        if os.path.exists(session_file):
            try:
                os.chmod(session_file, 0o666)
            except:
                pass
            try:
                client = TelegramClient(session_file.replace('.session', ''), API_ID, API_HASH)
                await client.connect()
                await client.get_me()
                user_clients[user_id] = client
                db.ensure_article_user(user_id)
                asyncio.create_task(start_article_system(user_id, client))
                asyncio.create_task(listen_user_messages(user_id, client))
                await event.respond('مرحبًا بعودتك!', buttons=user_panel_buttons())
                return
            except Exception as e:
                print(f'فشل استعادة جلسة المستخدم {user_id} في /start: {e}')
                try:
                    os.remove(session_file)
                except:
                    pass

    if user_id in user_clients:
        await event.respond('مرحبًا بعودتك!', buttons=user_panel_buttons())
        return

    is_subscribed = await check_subscription(user_id)
    if is_subscribed:
        await event.respond(
            'مرحبًا بك في بوت التسطير المجاني!\n\n'
            'اضغط على زر دخول إلى البوت لتسجيل رقم هاتفك والبدء.',
            buttons=user_login_buttons()
        )
    else:
        welcome = db.get_setting('welcome_message')
        if welcome is None:
            welcome = 'مرحبًا بك في بوت التسطير المجاني.\nللاستخدام، يجب عليك الاشتراك في القناة أولاً.'
        channel = CHANNEL_USERNAME if CHANNEL_USERNAME else 'p_h_fa'
        await event.respond(
            welcome,
            buttons=[[Button.url('اشترك في القناة', f'https://t.me/{channel}')],
                     [Button.inline('تحقق من الاشتراك', b'check_sub')]]
        )

# ============= RESTORE SESSIONS =============
async def restore_sessions():
    os.makedirs(SESSION_DIR, exist_ok=True)
    try:
        os.chmod(SESSION_DIR, 0o777)
    except:
        pass

    tasks = []
    for file in os.listdir(SESSION_DIR):
        if file.startswith('user_session_') and file.endswith('.session'):
            full_path = os.path.join(SESSION_DIR, file)
            tasks.append(restore_single_session(full_path))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

async def restore_single_session(full_path):
    try:
        user_id_str = os.path.basename(full_path).split('_')[2].split('.')[0]
        user_id = int(user_id_str)
        if user_id in user_clients:
            return
        try:
            os.chmod(full_path, 0o666)
        except:
            pass
        client = TelegramClient(full_path.replace('.session', ''), API_ID, API_HASH)
        await asyncio.wait_for(client.connect(), timeout=10)
        try:
            await asyncio.wait_for(client.get_me(), timeout=10)
            user_clients[user_id] = client
            print(f'تم استعادة جلسة المستخدم {user_id}')
            db.ensure_article_user(user_id)
            asyncio.create_task(start_article_system(user_id, client))
            asyncio.create_task(listen_user_messages(user_id, client))
        except Exception as e:
            print(f'فشل استعادة الجلسة {user_id}: {e}')
            await client.disconnect()
            try:
                os.remove(full_path)
            except:
                pass
    except Exception as e:
        print(f'فشل استعادة الجلسة من {full_path}: {e}')
        try:
            os.remove(full_path)
        except:
            pass

# ============= MAIN =============
async def main():
    global bot
    while True:
        try:
            await restore_sessions()
            if db.get_setting('bot_enabled') == 'false':
                print('البوت معطل حالياً')
            await bot.start(bot_token=BOT_TOKEN)
            print('البوت يعمل...')
            listener_task = asyncio.create_task(user_account_listener())
            try:
                await bot.run_until_disconnected()
            except asyncio.CancelledError:
                pass
            finally:
                listener_task.cancel()
                for user_id in list(user_clients.keys()):
                    await cleanup_user_tasks(user_id)
                await bot.disconnect()
                break
        except Exception as e:
            error = traceback.format_exc()
            db.add_error_log(error)
            print(f'خطأ: {e}. جاري إعادة التشغيل بعد 5 ثوانٍ...')
            await asyncio.sleep(5)
            bot = TelegramClient(os.path.join(SESSION_DIR, 'bot_session_new'), API_ID, API_HASH)
            continue

if __name__ == '__main__':
    asyncio.run(main())
