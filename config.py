import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DATABASE_NAME = os.getenv("DATABASE_NAME", "tasks.db")

# Категории по умолчанию
DEFAULT_CATEGORIES = [
    ("Программирование", "💻"),
    ("Встречи", "🤝"),
    ("Обучение", "📚"),
    ("Домашние дела", "🏠"),
    ("Спорт", "🏋️"),
    ("Развлечения", "🎮"),
    ("Работа", "💼"),
    ("Личное", "❤️"),
    ("Проекты", "📦")
]

# Настройки уведомлений по умолчанию
DEFAULT_NOTIFICATION_SETTINGS = {
    "daily_summary_hour": 21,
    "daily_summary_minute": 0,
    "weekly_summary_day": 6,  # 0 - понедельник, 6 - воскресенье
    "weekly_summary_hour": 20,
    "weekly_summary_minute": 0,
    "deadline_check_interval": 5,  # минут
    "long_task_threshold": 120,  # минут
    "reminder_before_deadline": 60,  # минут
    "progress_reminder_interval": 1440,  # минут (24 часа)
}
