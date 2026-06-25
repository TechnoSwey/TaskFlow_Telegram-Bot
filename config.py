import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DATABASE_NAME = "tasks.db"

# Категории по умолчанию
DEFAULT_CATEGORIES = [
    "Программирование",
    "Встречи",
    "Обучение",
    "Домашние дела",
    "Спорт",
    "Развлечения",
    "Работа"
]
