from environs import Env

# environs kutubxonasidan foydalanish
env = Env()
env.read_env()

# .env fayl ichidan quyidagilarni o'qiymiz
BOT_TOKEN = env.str("BOT_TOKEN")  # Bot Token
ADMINS = env.list("ADMINS")  # adminlar ro'yxati
API_KEY = env.str("API_KEY")
ASSEMBLYAI_API_KEY = env.str("ASSEMBLYAI_API_KEY")
DEEPGRAM_API_KEY = env.str("DEEPGRAM_API_KEY")

DB_USER = env.str("DB_USER")
DB_PASS = env.str("DB_PASS")
DB_NAME = env.str("DB_NAME")
DB_HOST = env.str("DB_HOST")
DB_PORT = env.str("DB_PORT")

BACKEND_HOST = env.str("BACKEND_HOST", "http://localhost:8000")
