from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict

def main_menu():
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("➕ Создать задачу", callback_data="create_task")],
        [InlineKeyboardButton("📋 Мои задачи", callback_data="my_tasks")],
        [InlineKeyboardButton("📂 Шаблоны", callback_data="templates")],
        [InlineKeyboardButton("⏱️ Таймер", callback_data="timer_menu")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats_menu")],
        [InlineKeyboardButton("🏷️ Категории", callback_data="categories_menu")],
        [InlineKeyboardButton("🔔 Уведомления", callback_data="notifications")],  # НОВАЯ КНОПКА
    ]
    return InlineKeyboardMarkup(keyboard)

def tasks_keyboard(tasks: List[Dict], page: int = 0, status: str = 'active'):
    """Клавиатура для списка задач"""
    keyboard = []
    
    # Показываем по 5 задач на странице
    start_idx = page * 5
    end_idx = min(start_idx + 5, len(tasks))
    
    for task in tasks[start_idx:end_idx]:
        status_icon = "✅" if task['status'] == 'completed' else "🔄"
        keyboard.append([
            InlineKeyboardButton(
                f"{status_icon} {task['title'][:30]}",
                callback_data=f"task_{task['id']}"
            )
        ])
    
    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"tasks_page_{page-1}_{status}"))
    if end_idx < len(tasks):
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"tasks_page_{page+1}_{status}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Фильтры
    keyboard.append([
        InlineKeyboardButton("📌 Активные", callback_data="tasks_filter_active"),
        InlineKeyboardButton("✅ Выполненные", callback_data="tasks_filter_completed"),
    ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def task_detail_keyboard(task_id: int, status: str):
    """Клавиатура для деталей задачи"""
    keyboard = []
    
    if status == 'active':
        keyboard.append([
            InlineKeyboardButton("⏱️ Начать", callback_data=f"start_timer_{task_id}"),
            InlineKeyboardButton("✅ Выполнена", callback_data=f"complete_{task_id}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("🔄 В работу", callback_data=f"reactivate_{task_id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_{task_id}")
    ])
    keyboard.append([
        InlineKeyboardButton("🔙 Назад к задачам", callback_data="my_tasks")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def templates_keyboard(templates: List[Dict]):
    """Клавиатура для шаблонов"""
    keyboard = []
    for template in templates:
        keyboard.append([
            InlineKeyboardButton(
                f"📄 {template['title']} ({template['category'] or 'Без категории'})",
                callback_data=f"use_template_{template['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("➕ Создать шаблон", callback_data="create_template")
    ])
    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def categories_keyboard(categories: List[Dict]):
    """Клавиатура для категорий"""
    keyboard = []
    for cat in categories:
        keyboard.append([
            InlineKeyboardButton(f"🏷️ {cat['name']}", callback_data=f"category_{cat['id']}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("➕ Добавить категорию", callback_data="add_category")
    ])
    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def stats_keyboard():
    """Клавиатура для статистики"""
    keyboard = [
        [InlineKeyboardButton("📊 Общая статистика", callback_data="stats_overall")],
        [InlineKeyboardButton("📈 По категориям", callback_data="stats_by_category")],
        [InlineKeyboardButton("📅 За сегодня", callback_data="stats_today")],
        [InlineKeyboardButton("📆 За неделю", callback_data="stats_week")],
        [InlineKeyboardButton("📅 За месяц", callback_data="stats_month")],
        [InlineKeyboardButton("🏷️ По категории", callback_data="stats_category_choice")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def timer_keyboard():
    """Клавиатура для таймера"""
    keyboard = [
        [InlineKeyboardButton("⏱️ Начать таймер", callback_data="timer_start")],
        [InlineKeyboardButton("⏹️ Остановить таймер", callback_data="timer_stop")],
        [InlineKeyboardButton("⏳ Активная сессия", callback_data="timer_status")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def notifications_keyboard():
    """Клавиатура для уведомлений"""
    keyboard = [
        [InlineKeyboardButton("📋 Задачи с дедлайном", callback_data="notif_deadlines")],
        [InlineKeyboardButton("⚠️ Просроченные задачи", callback_data="notif_overdue")],
        [InlineKeyboardButton("📊 Статистика задач", callback_data="notif_stats")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)
