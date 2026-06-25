from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from keyboards import *
from utils import format_time, format_duration, get_years_list
from datetime import datetime
import re

# === ОСНОВНЫЕ ОБРАБОТЧИКИ ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.username)
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я помогу тебе управлять задачами и временем.\n"
        "Используй меню для навигации.",
        reply_markup=main_menu()
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data
    
    # Главное меню
    if data == "back_to_main":
        await query.edit_message_text(
            "🏠 Главное меню",
            reply_markup=main_menu()
        )
        return
    
    # Задачи
    elif data == "my_tasks":
        await show_tasks(update, context, user_id)
    
    elif data.startswith("tasks_page_"):
        parts = data.split("_")
        page = int(parts[2])
        status = parts[3] if len(parts) > 3 else 'active'
        await show_tasks(update, context, user_id, page, status)
    
    elif data.startswith("tasks_filter_"):
        status = data.split("_")[2]
        await show_tasks(update, context, user_id, 0, status)
    
    elif data.startswith("task_"):
        task_id = int(data.split("_")[1])
        await show_task_detail(update, context, task_id)
    
    elif data.startswith("complete_"):
        task_id = int(data.split("_")[1])
        db.update_task_status(task_id, 'completed')
        await query.edit_message_text("✅ Задача выполнена!")
        await show_tasks(update, context, user_id)
    
    elif data.startswith("reactivate_"):
        task_id = int(data.split("_")[1])
        db.update_task_status(task_id, 'active')
        await query.edit_message_text("🔄 Задача возвращена в работу!")
        await show_tasks(update, context, user_id)
    
    elif data.startswith("delete_"):
        task_id = int(data.split("_")[1])
        task = db.get_task(task_id)
        if task and task['user_id'] == user_id:
            db.delete_task(task_id)
            await query.edit_message_text("🗑️ Задача удалена!")
            await show_tasks(update, context, user_id)
        else:
            await query.edit_message_text("❌ Ошибка: задача не найдена")
    
    # Таймер
    elif data == "timer_menu":
        await show_timer_menu(update, context)
    
    elif data == "timer_start":
        await start_timer(update, context)
    
    elif data == "timer_stop":
        await stop_timer(update, context)
    
    elif data == "timer_status":
        await show_timer_status(update, context)
    
    elif data.startswith("start_timer_"):
        task_id = int(data.split("_")[2])
        await start_timer_for_task(update, context, task_id)
    
    # Категории
    elif data == "categories_menu":
        await show_categories(update, context)
    
    elif data == "add_category":
        context.user_data['awaiting_category'] = True
        await query.edit_message_text(
            "✏️ Введите название новой категории:"
        )
    
    # Статистика
    elif data == "stats_menu":
        await query.edit_message_text(
            "📊 Выберите тип статистики:",
            reply_markup=stats_keyboard()
        )
    
    elif data == "stats_overall":
        await show_overall_stats(update, context, user_id)
    
    elif data == "stats_by_category":
        await show_category_stats(update, context, user_id)
    
    elif data == "stats_today":
        await show_period_stats(update, context, user_id, 'today')
    
    elif data == "stats_week":
        await show_period_stats(update, context, user_id, 'week')
    
    elif data == "stats_month":
        await show_period_stats(update, context, user_id, 'month')
    
    elif data == "stats_category_choice":
        await show_category_choice(update, context, user_id)
    
    elif data.startswith("stats_category_"):
        category_name = data.split("_")[2]
        await show_stats_by_category_detail(update, context, user_id, category_name)
    
    # Шаблоны
    elif data == "templates":
        await show_templates(update, context, user_id)
    
    elif data.startswith("use_template_"):
        template_id = int(data.split("_")[2])
        await use_template(update, context, user_id, template_id)
    
    elif data == "create_template":
        context.user_data['creating_template'] = True
        await query.edit_message_text(
            "✏️ Введите название шаблона:"
        )
    
    # Создание задачи
    elif data == "create_task":
        context.user_data['creating_task'] = True
        await query.edit_message_text(
            "✏️ Введите название задачи (можно указать дедлайн в формате ГГГГ-ММ-ДД ЧЧ:ММ):"
        )
    
    # === НОВЫЙ РАЗДЕЛ: УВЕДОМЛЕНИЯ ===
    elif data == "notifications":
        await show_notifications_menu(update, context)
    
    elif data == "notif_deadlines":
        await show_deadlines(update, context, user_id)
    
    elif data == "notif_overdue":
        await show_overdue(update, context, user_id)
    
    elif data == "notif_stats":
        await show_task_stats(update, context, user_id)

# === ФУНКЦИИ ДЛЯ ЗАДАЧ ===

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                    user_id: int, page: int = 0, status: str = 'active'):
    query = update.callback_query
    tasks = db.get_user_tasks(user_id, status)
    
    if not tasks:
        await query.edit_message_text(
            f"📋 Нет {status} задач",
            reply_markup=main_menu()
        )
        return
    
    text = f"📋 Список задач ({status}):\n\n"
    start_idx = page * 5
    end_idx = min(start_idx + 5, len(tasks))
    
    for i, task in enumerate(tasks[start_idx:end_idx], start_idx + 1):
        status_icon = "✅" if task['status'] == 'completed' else "🔄"
        text += f"{i}. {status_icon} {task['title']}\n"
        if task['category']:
            text += f"   🏷️ {task['category']}\n"
        if task['deadline']:
            text += f"   ⏰ Дедлайн: {task['deadline']}\n"
        text += "\n"
    
    text += f"Всего: {len(tasks)} задач"
    
    await query.edit_message_text(
        text,
        reply_markup=tasks_keyboard(tasks, page, status)
    )

async def show_task_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
    query = update.callback_query
    task = db.get_task(task_id)
    
    if not task:
        await query.edit_message_text("❌ Задача не найдена")
        return
    
    status_icon = "✅" if task['status'] == 'completed' else "🔄"
    text = f"📌 Задача\n\n"
    text += f"Название: {task['title']}\n"
    text += f"Статус: {status_icon} {task['status']}\n"
    if task['deadline']:
        text += f"⏰ Дедлайн: {task['deadline']}\n"
    
    # Получаем время по задаче
    sessions = db.get_detailed_stats(task['user_id'])
    total_time = sum(s['minutes'] for s in sessions if s['task'] == task['title'])
    if total_time:
        text += f"⏱️ Затрачено: {format_duration(total_time)}\n"
    
    await query.edit_message_text(
        text,
        reply_markup=task_detail_keyboard(task_id, task['status'])
    )

# === ФУНКЦИИ ДЛЯ ТАЙМЕРА ===

async def show_timer_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Проверяем активную сессию
    active = db.get_active_session(query.from_user.id)
    status_text = ""
    if active:
        start_time = datetime.fromisoformat(active['start_time'])
        elapsed = (datetime.now() - start_time).total_seconds() // 60
        status_text = f"\n\n⏳ Активная задача: {active['task_title']}\nПрошло: {format_duration(elapsed)}"
    
    await query.edit_message_text(
        f"⏱️ Управление таймером{status_text}",
        reply_markup=timer_keyboard()
    )

async def start_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # Проверяем активную сессию
    active = db.get_active_session(user_id)
    if active:
        await query.edit_message_text(
            "⚠️ У вас уже запущен таймер!\n"
            f"Задача: {active['task_title']}",
            reply_markup=main_menu()
        )
        return
    
    # Получаем активные задачи
    tasks = db.get_user_tasks(user_id, 'active')
    if not tasks:
        await query.edit_message_text(
            "❌ У вас нет активных задач. Создайте задачу сначала.",
            reply_markup=main_menu()
        )
        return
    
    # Создаём клавиатуру для выбора задачи
    keyboard = []
    for task in tasks:
        keyboard.append([
            InlineKeyboardButton(
                task['title'][:30],
                callback_data=f"start_timer_{task['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="timer_menu")])
    
    await query.edit_message_text(
        "⏱️ Выберите задачу для таймера:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_timer_for_task(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
    query = update.callback_query
    user_id = query.from_user.id
    
    task = db.get_task(task_id)
    if not task or task['user_id'] != user_id:
        await query.edit_message_text("❌ Задача не найдена")
        return
    
    session_id = db.start_session(task_id)
    
    await query.edit_message_text(
        f"⏱️ Таймер запущен!\n"
        f"Задача: {task['title']}\n"
        f"Время начала: {datetime.now().strftime('%H:%M:%S')}",
        reply_markup=main_menu()
    )

async def stop_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    active = db.get_active_session(user_id)
    if not active:
        await query.edit_message_text(
            "❌ Нет активного таймера.",
            reply_markup=main_menu()
        )
        return
    
    db.stop_session(active['session_id'])
    
    # Получаем длительность
    session = db.get_active_session(user_id)
    
    await query.edit_message_text(
        f"⏹️ Таймер остановлен!\n"
        f"Задача: {active['task_title']}\n"
        f"⏱️ Итого: {format_duration(active['duration'] or 0)}",
        reply_markup=main_menu()
    )

async def show_timer_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    active = db.get_active_session(user_id)
    if not active:
        await query.edit_message_text(
            "❌ Нет активного таймера.",
            reply_markup=timer_keyboard()
        )
        return
    
    start_time = datetime.fromisoformat(active['start_time'])
    elapsed = (datetime.now() - start_time).total_seconds() // 60
    
    await query.edit_message_text(
        f"⏳ Активный таймер\n\n"
        f"Задача: {active['task_title']}\n"
        f"Начало: {start_time.strftime('%H:%M:%S')}\n"
        f"Прошло: {format_duration(elapsed)}",
        reply_markup=timer_keyboard()
    )

# === ФУНКЦИИ ДЛЯ КАТЕГОРИЙ ===

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    categories = db.get_categories()
    
    text = "🏷️ Список категорий:\n\n"
    for cat in categories:
        text += f"• {cat['name']}\n"
    
    await query.edit_message_text(
        text,
        reply_markup=categories_keyboard(categories)
    )

# === ФУНКЦИИ ДЛЯ СТАТИСТИКИ ===

async def show_overall_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    
    # Общая статистика за всё время
    total = db.get_total_time(user_id)
    stats = db.get_stats_by_category(user_id)
    
    text = "📊 Общая статистика\n\n"
    text += f"⏱️ Всего времени: {format_duration(total)}\n\n"
    text += "📈 По категориям:\n"
    
    for stat in stats[:10]:  # Топ 10
        if stat['minutes'] > 0:
            percent = (stat['minutes'] / total * 100) if total > 0 else 0
            text += f"• {stat['category']}: {format_duration(stat['minutes'])} ({percent:.1f}%)\n"
    
    await query.edit_message_text(text, reply_markup=stats_keyboard())

async def show_category_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    
    # Статистика по категориям с выбором года
    years = get_years_list()
    keyboard = []
    for year in years:
        keyboard.append([
            InlineKeyboardButton(f"📅 {year}", callback_data=f"stats_year_{year}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="stats_menu")])
    
    await query.edit_message_text(
        "📈 Выберите год для статистики:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_period_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           user_id: int, period: str):
    query = update.callback_query
    stats = db.get_detailed_stats(user_id, period=period)
    
    if not stats:
        await query.edit_message_text(
            f"📊 Нет данных за {period}",
            reply_markup=stats_keyboard()
        )
        return
    
    text = f"📊 Статистика за {period}\n\n"
    total = sum(s['minutes'] for s in stats)
    text += f"⏱️ Всего: {format_duration(total)}\n\n"
    
    # Группировка по категориям
    by_category = {}
    for stat in stats:
        cat = stat['category'] or 'Без категории'
        by_category[cat] = by_category.get(cat, 0) + stat['minutes']
    
    for cat, minutes in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
        text += f"• {cat}: {format_duration(minutes)}\n"
    
    await query.edit_message_text(text, reply_markup=stats_keyboard())

async def show_category_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    categories = db.get_categories()
    
    keyboard = []
    for cat in categories:
        keyboard.append([
            InlineKeyboardButton(
                cat['name'],
                callback_data=f"stats_category_{cat['name']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="stats_menu")])
    
    await query.edit_message_text(
        "🏷️ Выберите категорию для детальной статистики:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_stats_by_category_detail(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                       user_id: int, category_name: str):
    query = update.callback_query
    
    # Статистика за разные годы
    years = get_years_list()
    keyboard = []
    for year in years:
        total = db.get_total_time(user_id, category_name, year)
        if total > 0:
            keyboard.append([
                InlineKeyboardButton(
                    f"📅 {year}: {format_duration(total)}",
                    callback_data=f"stats_year_category_{year}_{category_name}"
                )
            ])
    
    if not keyboard:
        await query.edit_message_text(
            f"📊 Нет данных по категории '{category_name}'",
            reply_markup=stats_keyboard()
        )
        return
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="stats_category_choice")])
    
    await query.edit_message_text(
        f"📊 Статистика по категории '{category_name}':",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# === ФУНКЦИИ ДЛЯ ШАБЛОНОВ ===

async def show_templates(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    templates = db.get_user_templates(user_id)
    
    if not templates:
        await query.edit_message_text(
            "📂 Нет сохраненных шаблонов",
            reply_markup=templates_keyboard([])
        )
        return
    
    text = "📂 Ваши шаблоны:\n\n"
    for t in templates:
        text += f"• {t['title']}"
        if t['category']:
            text += f" ({t['category']})"
        text += "\n"
    
    await query.edit_message_text(text, reply_markup=templates_keyboard(templates))

async def use_template(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                       user_id: int, template_id: int):
    query = update.callback_query
    template = db.get_task(template_id)
    
    if not template or template['user_id'] != user_id:
        await query.edit_message_text("❌ Шаблон не найден")
        return
    
    # Создаём задачу из шаблона
    new_task_id = db.create_task(
        user_id=user_id,
        title=f"{template['title']} (из шаблона)",
        category_id=template['category_id']
    )
    
    await query.edit_message_text(
        f"✅ Задача создана из шаблона!\n"
        f"📌 {template['title']}",
        reply_markup=main_menu()
    )

# === НОВЫЕ ФУНКЦИИ ДЛЯ УВЕДОМЛЕНИЙ ===

async def show_notifications_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню уведомлений"""
    query = update.callback_query
    
    # Получаем статистику для отображения
    user_id = query.from_user.id
    tasks = db.get_tasks_with_deadline(user_id, 24)
    overdue = db.get_overdue_tasks(user_id)
    stats = db.get_task_stats_for_user(user_id)
    
    text = "🔔 ЦЕНТР УВЕДОМЛЕНИЙ\n\n"
    text += f"📌 Задачи с дедлайном (24ч): {len(tasks)}\n"
    text += f"⚠️ Просроченных задач: {len(overdue)}\n"
    text += f"📊 Активных задач: {stats['active']}\n"
    text += f"✅ Выполнено сегодня: {stats['completed_today']}\n"
    
    await query.edit_message_text(
        text,
        reply_markup=notifications_keyboard()
    )

async def show_deadlines(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Показать задачи с дедлайном"""
    query = update.callback_query
    tasks = db.get_tasks_with_deadline(user_id, 24)
    
    if not tasks:
        await query.edit_message_text(
            "🔔 У вас нет задач с дедлайном в ближайшие 24 часа.",
            reply_markup=notifications_keyboard()
        )
        return
    
    text = "⏰ БЛИЖАЙШИЕ ДЕДЛАЙНЫ:\n\n"
    for i, task in enumerate(tasks, 1):
        deadline = datetime.fromisoformat(task['deadline'])
        remaining = deadline - datetime.now()
        hours = remaining.total_seconds() / 3600
        
        if hours < 0:
            status = "⚠️ ПРОСРОЧЕН!"
        elif hours < 1:
            status = "🔴 МЕНЕЕ ЧАСА!"
        elif hours < 3:
            status = "🟡 МЕНЕЕ 3 ЧАСОВ"
        elif hours < 12:
            status = f"🟠 {hours:.1f} ч"
        else:
            status = f"⏳ {hours:.1f} ч"
        
        text += f"{i}. {task['title']}\n"
        text += f"   📅 {task['deadline']}\n"
        text += f"   {status}\n\n"
    
    await query.edit_message_text(text, reply_markup=notifications_keyboard())

async def show_overdue(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Показать просроченные задачи"""
    query = update.callback_query
    tasks = db.get_overdue_tasks(user_id)
    
    if not tasks:
        await query.edit_message_text(
            "✅ У вас нет просроченных задач! Отлично!",
            reply_markup=notifications_keyboard()
        )
        return
    
    text = "⚠️ ПРОСРОЧЕННЫЕ ЗАДАЧИ:\n\n"
    for i, task in enumerate(tasks, 1):
        deadline = datetime.fromisoformat(task['deadline'])
        overdue_days = (datetime.now() - deadline).total_seconds() / 86400
        text += f"{i}. {task['title']}\n"
        text += f"   📅 Дедлайн был: {task['deadline']}\n"
        text += f"   🚨 Просрочено на {overdue_days:.1f} дней\n\n"
    
    await query.edit_message_text(text, reply_markup=notifications_keyboard())

async def show_task_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Показать статистику задач"""
    query = update.callback_query
    stats = db.get_task_stats_for_user(user_id)
    
    text = "📊 СТАТИСТИКА ЗАДАЧ\n\n"
    text += f"📌 Всего задач: {stats['total']}\n"
    text += f"🔄 Активных: {stats['active']}\n"
    text += f"✅ Выполнено сегодня: {stats['completed_today']}\n"
    
    # Процент выполнения
    if stats['total'] > 0:
        completed = stats['total'] - stats['active']
        percent = (completed / stats['total'] * 100)
        text += f"\n📈 Прогресс: {percent:.1f}% выполнено"
    
    await query.edit_message_text(text, reply_markup=notifications_keyboard())

# === ОБРАБОТЧИКИ ТЕКСТОВЫХ СООБЩЕНИЙ ===

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Создание задачи
    if context.user_data.get('creating_task'):
        context.user_data['creating_task'] = False
        context.user_data['task_title'] = text
        
        # Проверяем, может быть пользователь ввел дедлайн
        deadline = None
        # Ищем дату в формате ГГГГ-ММ-ДД ЧЧ:ММ
        date_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}'
        match = re.search(date_pattern, text)
        if match:
            deadline = match.group()
            # Убираем дату из названия
            title = text.replace(deadline, '').strip()
            context.user_data['task_title'] = title
            context.user_data['task_deadline'] = deadline
        
        # Показываем категории для выбора
        categories = db.get_categories()
        keyboard = []
        for cat in categories:
            keyboard.append([
                InlineKeyboardButton(cat['name'], callback_data=f"task_cat_{cat['id']}")
            ])
        keyboard.append([
            InlineKeyboardButton("Без категории", callback_data="task_cat_none")
        ])
        keyboard.append([
            InlineKeyboardButton("➕ Новая категория", callback_data="task_cat_new")
        ])
        keyboard.append([
            InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")
        ])
        
        deadline_text = f"\n⏰ Дедлайн: {deadline}" if deadline else ""
        await update.message.reply_text(
            f"📌 Задача: {context.user_data['task_title']}{deadline_text}\n\nВыберите категорию:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Добавление категории
    if context.user_data.get('awaiting_category'):
        context.user_data['awaiting_category'] = False
        if db.add_category(text):
            await update.message.reply_text(
                f"✅ Категория '{text}' добавлена!",
                reply_markup=main_menu()
            )
        else:
            await update.message.reply_text(
                f"❌ Категория '{text}' уже существует!",
                reply_markup=main_menu()
            )
        return
    
    # Создание шаблона
    if context.user_data.get('creating_template'):
        context.user_data['creating_template'] = False
        
        categories = db.get_categories()
        keyboard = []
        for cat in categories:
            keyboard.append([
                InlineKeyboardButton(cat['name'], callback_data=f"template_cat_{cat['id']}")
            ])
        keyboard.append([
            InlineKeyboardButton("Без категории", callback_data="template_cat_none")
        ])
        keyboard.append([
            InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")
        ])
        
        context.user_data['template_title'] = text
        await update.message.reply_text(
            f"📄 Шаблон: {text}\n\nВыберите категорию:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Неизвестная команда
    await update.message.reply_text(
        "❓ Используйте кнопки меню для навигации.",
        reply_markup=main_menu()
    )

# === ОБРАБОТЧИКИ ДЛЯ ВЫБОРА КАТЕГОРИИ ПРИ СОЗДАНИИ ===

async def handle_task_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if data == "task_cat_none":
        category_id = None
    elif data == "task_cat_new":
        context.user_data['awaiting_category'] = True
        await query.edit_message_text("✏️ Введите название новой категории:")
        return
    else:
        category_id = int(data.split("_")[2])
    
    title = context.user_data.get('task_title', 'Без названия')
    deadline = context.user_data.get('task_deadline', None)
    task_id = db.create_task(user_id, title, category_id, deadline=deadline)
    
    deadline_text = f"\n⏰ Дедлайн: {deadline}" if deadline else ""
    await query.edit_message_text(
        f"✅ Задача создана!\n\n"
        f"📌 {title}{deadline_text}",
        reply_markup=main_menu()
    )

async def handle_template_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if data == "template_cat_none":
        category_id = None
    else:
        category_id = int(data.split("_")[2])
    
    title = context.user_data.get('template_title', 'Без названия')
    task_id = db.create_task(user_id, title, category_id, is_template=True)
    
    await query.edit_message_text(
        f"✅ Шаблон создан!\n\n"
        f"📄 {title}",
        reply_markup=main_menu()
    )
