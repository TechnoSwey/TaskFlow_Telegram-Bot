from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict

# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

def get_priority_emoji(priority: int) -> str:
    emojis = {3: "🔴", 2: "🟡", 1: "🟢", 0: "⚪"}
    return emojis.get(priority, "⚪")

def get_priority_name(priority: int) -> str:
    names = {3: "Высокий", 2: "Средний", 1: "Низкий", 0: "Не указан"}
    return names.get(priority, "Не указан")

# ============ ГЛАВНОЕ МЕНЮ ============

def main_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Создать задачу", callback_data="create_task", style="primary")],
        [InlineKeyboardButton("📋 Мои задачи", callback_data="my_tasks", style="success")],
        [InlineKeyboardButton("📂 Шаблоны", callback_data="templates")],
        [InlineKeyboardButton("⏱️ Таймер", callback_data="timer_menu", style="primary")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats_menu", style="success")],
        [InlineKeyboardButton("🏷️ Категории", callback_data="categories_menu")],
        [InlineKeyboardButton("📦 Проекты", callback_data="projects_menu", style="primary")],
        [InlineKeyboardButton("🔔 Уведомления", callback_data="notifications", style="danger")],
        [InlineKeyboardButton("🏆 Достижения", callback_data="achievements")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ ЗАДАЧИ ============

def tasks_keyboard(tasks: List[Dict], page: int = 0, status: str = 'active'):
    keyboard = []
    start_idx = page * 5
    end_idx = min(start_idx + 5, len(tasks))
    
    for task in tasks[start_idx:end_idx]:
        priority_icon = get_priority_emoji(task.get('priority', 2))
        status_icon = "✅" if task.get('status') == 'completed' else "🔄"
        text = f"{priority_icon} {task['title'][:25]}"
        
        subtasks_total = task.get('subtasks_total', 0)
        subtasks_completed = task.get('subtasks_completed', 0)
        if subtasks_total > 0:
            text += f" [{subtasks_completed}/{subtasks_total}]"
        
        btn_style = "success" if task.get('status') == 'completed' else "primary"
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"task_{task['id']}", style=btn_style)
        ])
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"tasks_page_{page-1}_{status}", style="primary"))
    if end_idx < len(tasks):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"tasks_page_{page+1}_{status}", style="primary"))
    if nav:
        keyboard.append(nav)
    
    keyboard.append([
        InlineKeyboardButton("📌 Активные", callback_data="tasks_filter_active", style="primary"),
        InlineKeyboardButton("✅ Выполненные", callback_data="tasks_filter_completed", style="success"),
        InlineKeyboardButton("📦 Архив", callback_data="tasks_filter_archived")
    ])
    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
    ])
    return InlineKeyboardMarkup(keyboard)

def task_detail_keyboard(task_id: int, status: str, is_admin: bool = False):
    keyboard = []
    
    if status == 'active':
        keyboard.append([
            InlineKeyboardButton("⏱️ Начать таймер", callback_data=f"start_timer_{task_id}", style="success"),
            InlineKeyboardButton("✅ Выполнить", callback_data=f"complete_{task_id}", style="primary")
        ])
        keyboard.append([
            InlineKeyboardButton("📈 Прогресс", callback_data=f"progress_{task_id}", style="primary"),
            InlineKeyboardButton("💬 Комментарии", callback_data=f"comments_{task_id}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("🔄 Вернуть в работу", callback_data=f"reactivate_{task_id}", style="primary")
        ])
    
    keyboard.append([
        InlineKeyboardButton("📝 Редактировать", callback_data=f"edit_{task_id}", style="primary"),
        InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_{task_id}", style="danger")
    ])
    
    if is_admin:
        keyboard.append([
            InlineKeyboardButton("👥 Поделиться", callback_data=f"share_{task_id}", style="success")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data="my_tasks")
    ])
    return InlineKeyboardMarkup(keyboard)

def create_task_keyboard():
    keyboard = [
        [InlineKeyboardButton("Без категории", callback_data="task_cat_none")],
        [InlineKeyboardButton("➕ Новая категория", callback_data="task_cat_new", style="success")],
        [InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main", style="danger")]
    ]
    return InlineKeyboardMarkup(keyboard)

def task_priority_keyboard(task_id: int):
    keyboard = [
        [
            InlineKeyboardButton("🔴 Высокий", callback_data=f"priority_{task_id}_3", style="danger"),
            InlineKeyboardButton("🟡 Средний", callback_data=f"priority_{task_id}_2", style="primary")
        ],
        [
            InlineKeyboardButton("🟢 Низкий", callback_data=f"priority_{task_id}_1", style="success"),
            InlineKeyboardButton("⚪ Не указан", callback_data=f"priority_{task_id}_0")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"task_{task_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def progress_keyboard(task_id: int, current_progress: int):
    keyboard = []
    row = []
    for i in range(0, 101, 10):
        label = f"{i}%"
        if i == current_progress:
            label = f"✅ {i}%"
        row.append(InlineKeyboardButton(label, callback_data=f"set_progress_{task_id}_{i}"))
        if len(row) == 5:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"task_{task_id}")])
    return InlineKeyboardMarkup(keyboard)

def emoji_reaction_keyboard(task_id: int):
    keyboard = [
        [
            InlineKeyboardButton("😊", callback_data=f"react_{task_id}_😊"),
            InlineKeyboardButton("😍", callback_data=f"react_{task_id}_😍"),
            InlineKeyboardButton("🤔", callback_data=f"react_{task_id}_🤔"),
            InlineKeyboardButton("😰", callback_data=f"react_{task_id}_😰"),
            InlineKeyboardButton("🔥", callback_data=f"react_{task_id}_🔥")
        ],
        [
            InlineKeyboardButton("💪", callback_data=f"react_{task_id}_💪"),
            InlineKeyboardButton("🎯", callback_data=f"react_{task_id}_🎯"),
            InlineKeyboardButton("⭐", callback_data=f"react_{task_id}_⭐"),
            InlineKeyboardButton("💡", callback_data=f"react_{task_id}_💡"),
            InlineKeyboardButton("🚀", callback_data=f"react_{task_id}_🚀")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"task_{task_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ ТАЙМЕР ============

def timer_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("⏱️ Начать", callback_data="timer_start", style="success"),
            InlineKeyboardButton("⏹️ Остановить", callback_data="timer_stop", style="danger")
        ],
        [InlineKeyboardButton("⏳ Активная сессия", callback_data="timer_status", style="primary")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def timer_task_selection_keyboard(tasks: List[Dict]):
    keyboard = []
    for task in tasks:
        keyboard.append([
            InlineKeyboardButton(task['title'][:25], callback_data=f"start_timer_{task['id']}", style="primary")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="timer_menu")])
    return InlineKeyboardMarkup(keyboard)

# ============ СТАТИСТИКА ============

def stats_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 Общая", callback_data="stats_overall", style="primary"),
            InlineKeyboardButton("📈 По категориям", callback_data="stats_by_category", style="success")
        ],
        [
            InlineKeyboardButton("📅 За сегодня", callback_data="stats_today"),
            InlineKeyboardButton("📆 За неделю", callback_data="stats_week"),
            InlineKeyboardButton("📅 За месяц", callback_data="stats_month")
        ],
        [
            InlineKeyboardButton("🏷️ По категории", callback_data="stats_category_choice", style="primary"),
            InlineKeyboardButton("📊 Сравнение", callback_data="stats_compare", style="success")
        ],
        [
            InlineKeyboardButton("🏆 Топ задач", callback_data="stats_top_tasks"),
            InlineKeyboardButton("📈 Дневная активность", callback_data="stats_activity")
        ],
        [
            InlineKeyboardButton("🔮 Прогнозы", callback_data="stats_predictions", style="primary"),
            InlineKeyboardButton("📤 Экспорт CSV", callback_data="stats_export", style="success")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def category_choice_keyboard(categories: List[Dict]):
    keyboard = []
    for cat in categories:
        keyboard.append([
            InlineKeyboardButton(f"{cat['emoji']} {cat['name']}", callback_data=f"stats_category_{cat['id']}", style="primary")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="stats_menu")])
    return InlineKeyboardMarkup(keyboard)

def year_choice_keyboard(years: List[int]):
    keyboard = []
    for year in years:
        keyboard.append([
            InlineKeyboardButton(str(year), callback_data=f"stats_year_{year}", style="primary")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="stats_menu")])
    return InlineKeyboardMarkup(keyboard)

def compare_periods_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📅 Неделя vs Неделя", callback_data="compare_week_week", style="primary"),
            InlineKeyboardButton("📅 Месяц vs Месяц", callback_data="compare_month_month", style="success")
        ],
        [
            InlineKeyboardButton("📅 Год vs Год", callback_data="compare_year_year", style="primary"),
            InlineKeyboardButton("📅 Текущий vs Прошлый", callback_data="compare_current_previous", style="success")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="stats_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ ПРОЕКТЫ ============

def projects_keyboard(projects: List[Dict]):
    keyboard = []
    for project in projects:
        role_icon = "👑" if project.get('role') == 'admin' else "👤"
        keyboard.append([
            InlineKeyboardButton(
                f"{role_icon} {project['name'][:20]}",
                callback_data=f"project_{project['id']}",
                style="primary"
            )
        ])
    keyboard.append([
        InlineKeyboardButton("➕ Создать проект", callback_data="create_project", style="success")
    ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

def project_detail_keyboard(project_id: int, user_role: str):
    keyboard = []
    
    if user_role in ['admin', 'owner']:
        keyboard.append([
            InlineKeyboardButton("👥 Добавить участника", callback_data=f"project_add_member_{project_id}", style="success"),
            InlineKeyboardButton("🗑️ Архив", callback_data=f"project_archive_{project_id}", style="danger")
        ])
        keyboard.append([
            InlineKeyboardButton("👥 Участники", callback_data=f"project_members_{project_id}", style="primary")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("👥 Участники", callback_data=f"project_members_{project_id}")
        ])
        keyboard.append([
            InlineKeyboardButton("🚪 Выйти", callback_data=f"project_leave_{project_id}", style="danger")
        ])
    
    keyboard.append([
        InlineKeyboardButton("📋 Задачи проекта", callback_data=f"project_tasks_{project_id}", style="primary")
    ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="projects_menu")])
    return InlineKeyboardMarkup(keyboard)

def project_members_keyboard(members: List[Dict], project_id: int, is_admin: bool):
    keyboard = []
    for member in members:
        role_icon = "👑" if member['role'] == 'admin' else "👤"
        text = f"{role_icon} {member['username'] or 'Пользователь'}"
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"member_{project_id}_{member['user_id']}")
        ])
    if is_admin:
        keyboard.append([
            InlineKeyboardButton("🔙 Назад", callback_data=f"project_{project_id}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("🔙 Назад", callback_data=f"project_{project_id}")
        ])
    return InlineKeyboardMarkup(keyboard)

def project_member_actions_keyboard(project_id: int, user_id: int, current_role: str):
    keyboard = []
    if current_role == 'admin':
        keyboard.append([
            InlineKeyboardButton("⬇️ Сделать участником", callback_data=f"member_role_{project_id}_{user_id}_member", style="primary"),
            InlineKeyboardButton("⬆️ Сделать админом", callback_data=f"member_role_{project_id}_{user_id}_admin", style="success")
        ])
        keyboard.append([
            InlineKeyboardButton("❌ Удалить из проекта", callback_data=f"member_remove_{project_id}_{user_id}", style="danger")
        ])
    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data=f"project_members_{project_id}")
    ])
    return InlineKeyboardMarkup(keyboard)

# ============ КАТЕГОРИИ ============

def categories_keyboard(categories: List[Dict]):
    keyboard = []
    for cat in categories:
        keyboard.append([
            InlineKeyboardButton(f"{cat['emoji']} {cat['name']}", callback_data=f"category_{cat['id']}", style="primary")
        ])
    keyboard.append([
        InlineKeyboardButton("➕ Добавить", callback_data="add_category", style="success"),
        InlineKeyboardButton("🗑️ Удалить", callback_data="delete_category_choose", style="danger")
    ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

def delete_category_choice_keyboard(categories: List[Dict]):
    keyboard = []
    for cat in categories:
        keyboard.append([
            InlineKeyboardButton(f"{cat['emoji']} {cat['name']}", callback_data=f"delete_category_{cat['id']}", style="danger")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="categories_menu")])
    return InlineKeyboardMarkup(keyboard)

# ============ ШАБЛОНЫ ============

def templates_keyboard(templates: List[Dict]):
    keyboard = []
    for template in templates:
        keyboard.append([
            InlineKeyboardButton(
                f"📄 {template['title'][:25]}",
                callback_data=f"use_template_{template['id']}",
                style="primary"
            )
        ])
    keyboard.append([
        InlineKeyboardButton("➕ Создать шаблон", callback_data="create_template", style="success")
    ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

# ============ УВЕДОМЛЕНИЯ ============

def notifications_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("⏰ Дедлайны", callback_data="notif_deadlines", style="danger"),
            InlineKeyboardButton("⚠️ Просроченные", callback_data="notif_overdue", style="danger")
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="notif_stats", style="primary"),
            InlineKeyboardButton("📈 Прогресс", callback_data="notif_progress", style="success")
        ],
        [
            InlineKeyboardButton("⚙️ Настройка уведомлений", callback_data="notif_settings", style="primary")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def notification_settings_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📅 Сводка", callback_data="settings_daily_summary", style="primary"),
            InlineKeyboardButton("📅 Еженедельная", callback_data="settings_weekly_summary")
        ],
        [
            InlineKeyboardButton("⏰ Дедлайны", callback_data="settings_deadlines", style="danger"),
            InlineKeyboardButton("📈 Прогресс", callback_data="settings_progress")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="notifications")]
    ]
    return InlineKeyboardMarkup(keyboard)

def set_time_keyboard(callback_prefix: str):
    keyboard = []
    hours = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
             "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23"]
    
    for i in range(0, 24, 4):
        row = []
        for h in hours[i:i+4]:
            row.append(InlineKeyboardButton(h, callback_data=f"{callback_prefix}_hour_{h}"))
        keyboard.append(row)
    
    minutes = ["00", "15", "30", "45"]
    row = []
    for m in minutes:
        row.append(InlineKeyboardButton(m, callback_data=f"{callback_prefix}_min_{m}"))
    keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="notif_settings")])
    return InlineKeyboardMarkup(keyboard)

def set_day_keyboard(callback_prefix: str):
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    keyboard = []
    row = []
    for i, day in enumerate(days):
        row.append(InlineKeyboardButton(day, callback_data=f"{callback_prefix}_day_{i}"))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="notif_settings")])
    return InlineKeyboardMarkup(keyboard)

# ============ ДОСТИЖЕНИЯ ============

def achievements_keyboard(achievements: List[Dict]):
    keyboard = []
    for ach in achievements:
        keyboard.append([
            InlineKeyboardButton(
                f"{ach['icon']} {ach['name']}",
                callback_data=f"achievement_{ach['id']}",
                style="success"
            )
        ])
    keyboard.append([
        InlineKeyboardButton("📋 Все достижения", callback_data="all_achievements", style="primary")
    ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

def all_achievements_keyboard(achievements: List[Dict], unlocked_ids: List[str]):
    keyboard = []
    for ach in achievements:
        icon = "✅" if ach['id'] in unlocked_ids else "🔒"
        keyboard.append([
            InlineKeyboardButton(
                f"{icon} {ach['icon']} {ach['name']}",
                callback_data=f"ach_info_{ach['id']}",
                style="success" if ach['id'] in unlocked_ids else None
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="achievements")])
    return InlineKeyboardMarkup(keyboard)

# ============ ПОМОЩЬ / ТУТОР ============

def help_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🚀 Начать тутор", callback_data="tutorial_start", style="success"),
            InlineKeyboardButton("❓ Команды", callback_data="help_commands")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def tutorial_keyboard(current_step: int, total_steps: int, tutorial_id: str):
    keyboard = []
    
    nav = []
    if current_step > 0:
        nav.append(InlineKeyboardButton("◀️ Назад", callback_data=f"tutorial_back_{tutorial_id}"))
    if current_step < total_steps - 1:
        nav.append(InlineKeyboardButton("Далее ▶️", callback_data=f"tutorial_next_{tutorial_id}", style="primary"))
    if nav:
        keyboard.append(nav)
    
    keyboard.append([
        InlineKeyboardButton("❌ Закрыть", callback_data="tutorial_close", style="danger")
    ])
    return InlineKeyboardMarkup(keyboard)

# ============ КОММЕНТАРИИ ============

def comments_keyboard(task_id: int):
    keyboard = [
        [InlineKeyboardButton("💬 Добавить комментарий", callback_data=f"add_comment_{task_id}", style="primary")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"task_{task_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def recurring_task_keyboard(task_id: int):
    keyboard = [
        [
            InlineKeyboardButton("📅 Ежедневно", callback_data=f"recurring_{task_id}_daily", style="primary"),
            InlineKeyboardButton("📅 Еженедельно", callback_data=f"recurring_{task_id}_weekly", style="success")
        ],
        [
            InlineKeyboardButton("📅 Ежемесячно", callback_data=f"recurring_{task_id}_monthly", style="primary")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"task_{task_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def share_task_keyboard(task_id: int, projects: List[Dict]):
    keyboard = []
    for project in projects:
        keyboard.append([
            InlineKeyboardButton(f"📦 {project['name']}", callback_data=f"share_{task_id}_{project['id']}", style="primary")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"task_{task_id}")])
    return InlineKeyboardMarkup(keyboard)
