from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from keyboards import *
from utils import *
from datetime import datetime, timedelta
import re
import json

# Состояния для ConversationHandler
(
    CREATE_TASK, CREATE_TASK_CATEGORY, CREATE_TASK_PRIORITY, CREATE_TASK_DEADLINE,
    CREATE_TEMPLATE, TEMPLATE_CATEGORY,
    ADD_COMMENT,
    CREATE_PROJECT, CREATE_PROJECT_DESCRIPTION,
    ADD_PROJECT_MEMBER,
    SET_NOTIFICATION_TIME,
    TUTORIAL_STEP
) = range(12)

# ============ ОСНОВНЫЕ ОБРАБОТЧИКИ ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.username)
    
    if not db.get_tutorial_completed(user.id, 'main'):
        await show_tutorial(update, context)
        return
    
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
    
    if data == "back_to_main":
        await query.edit_message_text("🏠 Главное меню", reply_markup=main_menu())
        return
    
    # === ЗАДАЧИ ===
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
        await query.edit_message_text("✅ Задача выполнена! 🎉")
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
    
    elif data.startswith("priority_"):
        parts = data.split("_")
        task_id = int(parts[1])
        priority = int(parts[2])
        db.cursor.execute("UPDATE tasks SET priority = ? WHERE id = ?", (priority, task_id))
        db.connection.commit()
        await query.edit_message_text(f"✅ Приоритет обновлён: {get_priority_name(priority)}")
        await show_task_detail(update, context, task_id)
    
    elif data.startswith("progress_"):
        task_id = int(data.split("_")[1])
        task = db.get_task(task_id)
        if task and task['user_id'] == user_id:
            await query.edit_message_text(
                f"📈 Прогресс задачи: {task['progress']}%\n\nВыберите новый прогресс:",
                reply_markup=progress_keyboard(task_id, task['progress'])
            )
    
    elif data.startswith("set_progress_"):
        parts = data.split("_")
        task_id = int(parts[2])
        progress = int(parts[3])
        db.update_task_progress(task_id, progress)
        await query.edit_message_text(f"✅ Прогресс обновлён: {progress}%")
        await show_task_detail(update, context, task_id)
    
    elif data.startswith("react_"):
        parts = data.split("_")
        task_id = int(parts[1])
        emoji = parts[2]
        db.update_task_emoji(task_id, emoji)
        await query.edit_message_text(f"✅ Реакция обновлена: {emoji}")
        await show_task_detail(update, context, task_id)
    
    elif data.startswith("edit_"):
        task_id = int(data.split("_")[1])
        context.user_data['editing_task'] = task_id
        await query.edit_message_text("✏️ Введите новое название задачи:")
    
    elif data.startswith("share_"):
        task_id = int(data.split("_")[1])
        projects = db.get_user_projects(user_id)
        if not projects:
            await query.edit_message_text("❌ У вас нет проектов. Создайте проект сначала.", reply_markup=main_menu())
            return
        await query.edit_message_text(
            f"📦 Выберите проект для задачи:",
            reply_markup=share_task_keyboard(task_id, projects)
        )
    
    elif data.startswith("share_task_"):
        parts = data.split("_")
        task_id = int(parts[2])
        project_id = int(parts[3])
        db.cursor.execute("UPDATE tasks SET project_id = ? WHERE id = ?", (project_id, task_id))
        db.connection.commit()
        await query.edit_message_text("✅ Задача добавлена в проект!")
        await show_task_detail(update, context, task_id)
    
    elif data == "create_task":
        context.user_data['creating_task'] = True
        await query.edit_message_text(
            "✏️ Введите название задачи (можно указать дедлайн в формате ГГГГ-ММ-ДД ЧЧ:ММ):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]
            ])
        )
    
    elif data.startswith("task_cat_"):
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
        priority = context.user_data.get('task_priority', 2)
        
        task_id = db.create_task(
            user_id=user_id,
            title=title,
            category_id=category_id,
            deadline=deadline,
            priority=priority
        )
        
        deadline_text = f"\n⏰ Дедлайн: {deadline}" if deadline else ""
        priority_text = f"\n🔴 Приоритет: {get_priority_name(priority)}"
        
        await query.edit_message_text(
            f"✅ Задача создана!\n\n📌 {title}{deadline_text}{priority_text}",
            reply_markup=main_menu()
        )
        context.user_data.pop('creating_task', None)
        context.user_data.pop('task_title', None)
        context.user_data.pop('task_deadline', None)
        context.user_data.pop('task_priority', None)
    
    elif data.startswith("template_cat_"):
        if data == "template_cat_none":
            category_id = None
        else:
            category_id = int(data.split("_")[2])
        
        title = context.user_data.get('template_title', 'Без названия')
        db.create_task(user_id, title, category_id, is_template=True)
        await query.edit_message_text(f"✅ Шаблон '{title}' создан!", reply_markup=main_menu())
        context.user_data.pop('creating_template', None)
        context.user_data.pop('template_title', None)
    
    # === ТАЙМЕР ===
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
    
    # === КАТЕГОРИИ ===
    elif data == "categories_menu":
        await show_categories(update, context)
    
    elif data == "add_category":
        context.user_data['awaiting_category'] = True
        await query.edit_message_text("✏️ Введите название новой категории:")
    
    elif data == "delete_category_choose":
        categories = db.get_categories()
        await query.edit_message_text(
            "🗑️ Выберите категорию для удаления:",
            reply_markup=delete_category_choice_keyboard(categories)
        )
    
    elif data.startswith("delete_category_"):
        category_id = int(data.split("_")[2])
        db.cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        db.connection.commit()
        await query.edit_message_text("✅ Категория удалена!")
        await show_categories(update, context)
    
    elif data.startswith("category_"):
        category_id = int(data.split("_")[1])
        await show_tasks_by_category(update, context, user_id, category_id)
    
    # === СТАТИСТИКА ===
    elif data == "stats_menu":
        await query.edit_message_text("📊 Выберите тип статистики:", reply_markup=stats_keyboard())
    
    elif data == "stats_overall":
        await show_overall_stats(update, context, user_id)
    
    elif data == "stats_by_category":
        years = get_years_list()
        await query.edit_message_text("📈 Выберите год:", reply_markup=year_choice_keyboard(years))
    
    elif data.startswith("stats_year_"):
        year = int(data.split("_")[2])
        await show_category_stats(update, context, user_id, year)
    
    elif data == "stats_today":
        await show_period_stats(update, context, user_id, 'today')
    
    elif data == "stats_week":
        await show_period_stats(update, context, user_id, 'week')
    
    elif data == "stats_month":
        await show_period_stats(update, context, user_id, 'month')
    
    elif data == "stats_category_choice":
        categories = db.get_categories()
        await query.edit_message_text("🏷️ Выберите категорию:", reply_markup=category_choice_keyboard(categories))
    
    elif data.startswith("stats_category_"):
        category_id = int(data.split("_")[2])
        category = db.cursor.execute("SELECT name FROM categories WHERE id = ?", (category_id,)).fetchone()
        if category:
            await show_stats_by_category_detail(update, context, user_id, category[0])
    
    elif data == "stats_compare":
        await query.edit_message_text("📊 Выберите периоды для сравнения:", reply_markup=compare_periods_keyboard())
    
    elif data.startswith("compare_"):
        await show_compare_stats(update, context, user_id, data)
    
    elif data == "stats_top_tasks":
        await show_top_tasks(update, context, user_id)
    
    elif data == "stats_activity":
        await show_daily_activity(update, context, user_id)
    
    elif data == "stats_predictions":
        await show_predictions(update, context, user_id)
    
    elif data == "stats_export":
        await export_stats(update, context, user_id)
    
    # === ПРОЕКТЫ ===
    elif data == "projects_menu":
        await show_projects(update, context, user_id)
    
    elif data == "create_project":
        context.user_data['creating_project'] = True
        await query.edit_message_text("✏️ Введите название проекта:")
    
    elif data.startswith("project_"):
        project_id = int(data.split("_")[1])
        await show_project_detail(update, context, project_id, user_id)
    
    elif data.startswith("project_add_member_"):
        project_id = int(data.split("_")[3])
        context.user_data['adding_member_project'] = project_id
        await query.edit_message_text("👤 Введите username пользователя для добавления в проект:")
    
    elif data.startswith("project_members_"):
        project_id = int(data.split("_")[2])
        await show_project_members(update, context, project_id, user_id)
    
    elif data.startswith("project_tasks_"):
        project_id = int(data.split("_")[2])
        await show_tasks(update, context, user_id, 0, 'active', project_id)
    
    elif data.startswith("project_archive_"):
        project_id = int(data.split("_")[2])
        role = db.get_user_role(project_id, user_id)
        if role in ['admin', 'owner']:
            db.archive_project(project_id)
            await query.edit_message_text("✅ Проект заархивирован!")
            await show_projects(update, context, user_id)
        else:
            await query.edit_message_text("❌ У вас нет прав для этого действия")
    
    elif data.startswith("project_leave_"):
        project_id = int(data.split("_")[2])
        db.remove_project_member(project_id, user_id)
        await query.edit_message_text("✅ Вы вышли из проекта!")
        await show_projects(update, context, user_id)
    
    elif data.startswith("member_"):
        parts = data.split("_")
        project_id = int(parts[1])
        member_id = int(parts[2])
        member = db.cursor.execute("SELECT username FROM users WHERE user_id = ?", (member_id,)).fetchone()
        if member:
            await query.edit_message_text(
                f"👤 Пользователь: {member[0] or 'Пользователь'}\n\nДействия:",
                reply_markup=project_member_actions_keyboard(project_id, member_id, 'admin')
            )
    
    elif data.startswith("member_role_"):
        parts = data.split("_")
        project_id = int(parts[2])
        member_id = int(parts[3])
        role = parts[4]
        db.cursor.execute(
            "UPDATE project_members SET role = ? WHERE project_id = ? AND user_id = ?",
            (role, project_id, member_id)
        )
        db.connection.commit()
        await query.edit_message_text(f"✅ Роль обновлена: {role}")
        await show_project_members(update, context, project_id, user_id)
    
    elif data.startswith("member_remove_"):
        parts = data.split("_")
        project_id = int(parts[2])
        member_id = int(parts[3])
        db.remove_project_member(project_id, member_id)
        await query.edit_message_text("✅ Пользователь удалён из проекта!")
        await show_project_members(update, context, project_id, user_id)
    
    # === ШАБЛОНЫ ===
    elif data == "templates":
        await show_templates(update, context, user_id)
    
    elif data.startswith("use_template_"):
        template_id = int(data.split("_")[2])
        await use_template(update, context, user_id, template_id)
    
    elif data == "create_template":
        context.user_data['creating_template'] = True
        await query.edit_message_text("✏️ Введите название шаблона:")
    
    # === УВЕДОМЛЕНИЯ ===
    elif data == "notifications":
        await show_notifications_menu(update, context, user_id)
    
    elif data == "notif_deadlines":
        await show_deadlines(update, context, user_id)
    
    elif data == "notif_overdue":
        await show_overdue(update, context, user_id)
    
    elif data == "notif_stats":
        await show_task_stats(update, context, user_id)
    
    elif data == "notif_progress":
        await show_progress_reminder(update, context, user_id)
    
    elif data == "notif_settings":
        await show_notification_settings(update, context, user_id)
    
    elif data == "settings_daily_summary":
        await query.edit_message_text(
            "⏰ Выберите час для ежедневной сводки:",
            reply_markup=set_time_keyboard("daily")
        )
    
    elif data.startswith("daily_hour_"):
        hour = data.split("_")[2]
        context.user_data['daily_hour'] = int(hour)
        await query.edit_message_text(
            f"⏰ Выберите минуты для ежедневной сводки (час: {hour}):",
            reply_markup=set_time_keyboard("daily_min")
        )
    
    elif data.startswith("daily_min_"):
        await save_notification_settings(update, context, user_id, 'daily')
    
    elif data == "settings_weekly_summary":
        await query.edit_message_text(
            "📅 Выберите день недели для еженедельной сводки:",
            reply_markup=set_day_keyboard("weekly")
        )
    
    elif data.startswith("weekly_day_"):
        day = int(data.split("_")[2])
        context.user_data['weekly_day'] = day
        await query.edit_message_text(
            f"⏰ Выберите час для еженедельной сводки (день: {['Пн','Вт','Ср','Чт','Пт','Сб','Вс'][day]}):",
            reply_markup=set_time_keyboard("weekly_hour")
        )
    
    elif data.startswith("weekly_hour_"):
        hour = data.split("_")[2]
        context.user_data['weekly_hour'] = int(hour)
        await query.edit_message_text(
            f"⏰ Выберите минуты для еженедельной сводки (час: {hour}):",
            reply_markup=set_time_keyboard("weekly_min")
        )
    
    elif data.startswith("weekly_min_"):
        await save_notification_settings(update, context, user_id, 'weekly')
    
    # === ДОСТИЖЕНИЯ ===
    elif data == "achievements":
        await show_achievements(update, context, user_id)
    
    elif data.startswith("achievement_"):
        achievement_id = data.split("_")[1]
        await show_achievement_detail(update, context, achievement_id)
    
    elif data == "all_achievements":
        await show_all_achievements(update, context, user_id)
    
    elif data.startswith("ach_info_"):
        achievement_id = data.split("_")[2]
        await show_achievement_detail(update, context, achievement_id)
    
    # === ПОМОЩЬ ===
    elif data == "help":
        await show_help(update, context)
    
    elif data == "help_commands":
        await show_commands(update, context)
    
    elif data == "tutorial_start":
        await show_tutorial(update, context)
    
    elif data.startswith("tutorial_next_"):
        tutorial_id = data.split("_")[2]
        await tutorial_next(update, context, tutorial_id)
    
    elif data.startswith("tutorial_back_"):
        tutorial_id = data.split("_")[2]
        await tutorial_back(update, context, tutorial_id)
    
    elif data == "tutorial_close":
        await query.edit_message_text("🏠 Главное меню", reply_markup=main_menu())
    
    # === КОММЕНТАРИИ ===
    elif data.startswith("comments_"):
        task_id = int(data.split("_")[1])
        await show_comments(update, context, task_id)
    
    elif data.startswith("add_comment_"):
        task_id = int(data.split("_")[2])
        context.user_data['comment_task'] = task_id
        await query.edit_message_text("💬 Введите ваш комментарий:")
    
    # === ПОВТОРЯЮЩИЕСЯ ЗАДАЧИ ===
    elif data.startswith("recurring_"):
        parts = data.split("_")
        task_id = int(parts[1])
        pattern = parts[2]
        db.cursor.execute(
            "UPDATE tasks SET is_recurring = 1, recurring_pattern = ? WHERE id = ?",
            (pattern, task_id)
        )
        db.connection.commit()
        await query.edit_message_text(f"✅ Задача теперь повторяется: {pattern}")
        await show_task_detail(update, context, task_id)

# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                    user_id: int, page: int = 0, status: str = 'active',
                    project_id: int = None):
    query = update.callback_query
    tasks = db.get_user_tasks(user_id, status, project_id)
    
    if not tasks:
        await query.edit_message_text(f"📋 Нет {status} задач", reply_markup=main_menu())
        return
    
    text = f"📋 Список задач ({status}):\n\n"
    start_idx = page * 5
    end_idx = min(start_idx + 5, len(tasks))
    
    for i, task in enumerate(tasks[start_idx:end_idx], start_idx + 1):
        priority_icon = get_priority_emoji(task.get('priority', 2))
        status_icon = "✅" if task.get('status') == 'completed' else "🔄"
        text += f"{i}. {priority_icon} {task['title']}\n"
        if task.get('category'):
            text += f"   {task.get('category_emoji', '📁')} {task['category']}\n"
        if task.get('deadline'):
            text += f"   ⏰ {task['deadline']}\n"
        subtasks_total = task.get('subtasks_total', 0)
        subtasks_completed = task.get('subtasks_completed', 0)
        if subtasks_total > 0:
            text += f"   📋 Подзадачи: {subtasks_completed}/{subtasks_total}\n"
        if task.get('progress', 0) > 0:
            text += f"   📈 {task['progress']}%\n"
        text += "\n"
    
    text += f"Всего: {len(tasks)} задач"
    await query.edit_message_text(text, reply_markup=tasks_keyboard(tasks, page, status))

async def show_task_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
    query = update.callback_query
    task = db.get_task(task_id)
    
    if not task:
        await query.edit_message_text("❌ Задача не найдена")
        return
    
    status_icon = "✅" if task['status'] == 'completed' else "🔄"
    priority_icon = get_priority_emoji(task.get('priority', 2))
    priority_name = get_priority_name(task.get('priority', 2))
    
    text = f"📌 Задача\n\n"
    text += f"Название: {task['title']}\n"
    if task.get('description'):
        text += f"📝 {task['description']}\n"
    text += f"Статус: {status_icon} {task['status']}\n"
    text += f"Приоритет: {priority_icon} {priority_name}\n"
    if task.get('deadline'):
        text += f"⏰ Дедлайн: {task['deadline']}\n"
    if task.get('progress', 0) > 0:
        text += f"📈 Прогресс: {task['progress']}%\n"
    if task.get('emoji_reaction'):
        text += f"Реакция: {task['emoji_reaction']}\n"
    
    # Подзадачи
    subtasks = db.get_subtasks(task_id)
    if subtasks:
        text += f"\n📋 Подзадачи ({len(subtasks)}):\n"
        for s in subtasks:
            icon = "✅" if s['status'] == 'completed' else "🔄"
            text += f"   {icon} {s['title']} ({s['progress']}%)\n"
    
    # Комментарии
    comments = db.get_task_comments(task_id)
    if comments:
        text += f"\n💬 Комментарии ({len(comments)}):\n"
        for c in comments[:3]:
            text += f"   {c['username']}: {c['comment'][:30]}...\n"
    
    is_admin = False
    if task.get('project_id'):
        role = db.get_user_role(task['project_id'], task['user_id'])
        is_admin = role in ['admin', 'owner']
    
    await query.edit_message_text(text, reply_markup=task_detail_keyboard(task_id, task['status'], is_admin))

async def show_tasks_by_category(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, category_id: int):
    query = update.callback_query
    category = db.cursor.execute("SELECT name FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not category:
        await query.edit_message_text("❌ Категория не найдена")
        return
    
    tasks = db.get_user_tasks(user_id, 'active')
    tasks = [t for t in tasks if t.get('category_id') == category_id]
    
    if not tasks:
        await query.edit_message_text(f"📋 Нет задач в категории '{category[0]}'", reply_markup=categories_keyboard(db.get_categories()))
        return
    
    text = f"📋 Задачи в категории '{category[0]}':\n\n"
    for i, task in enumerate(tasks, 1):
        priority_icon = get_priority_emoji(task.get('priority', 2))
        text += f"{i}. {priority_icon} {task['title']}\n"
        if task.get('deadline'):
            text += f"   ⏰ {task['deadline']}\n"
        text += "\n"
    
    await query.edit_message_text(text, reply_markup=categories_keyboard(db.get_categories()))

# ============ ТАЙМЕР ============

async def show_timer_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    active = db.get_active_session(query.from_user.id)
    status_text = ""
    if active:
        start_time = datetime.fromisoformat(active['start_time'])
        elapsed = (datetime.now() - start_time).total_seconds() // 60
        status_text = f"\n\n⏳ Активная задача: {active['task_title']}\nПрошло: {format_duration(elapsed)}"
    
    await query.edit_message_text(f"⏱️ Управление таймером{status_text}", reply_markup=timer_keyboard())

async def start_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    active = db.get_active_session(user_id)
    if active:
        await query.edit_message_text(
            f"⚠️ У вас уже запущен таймер!\nЗадача: {active['task_title']}",
            reply_markup=main_menu()
        )
        return
    
    tasks = db.get_user_tasks(user_id, 'active')
    if not tasks:
        await query.edit_message_text("❌ У вас нет активных задач.", reply_markup=main_menu())
        return
    
    await query.edit_message_text(
        "⏱️ Выберите задачу для таймера:",
        reply_markup=timer_task_selection_keyboard(tasks)
    )

async def start_timer_for_task(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
    query = update.callback_query
    user_id = query.from_user.id
    
    task = db.get_task(task_id)
    if not task or task['user_id'] != user_id:
        await query.edit_message_text("❌ Задача не найдена")
        return
    
    db.start_session(task_id)
    await query.edit_message_text(
        f"⏱️ Таймер запущен!\nЗадача: {task['title']}\nВремя: {datetime.now().strftime('%H:%M:%S')}",
        reply_markup=main_menu()
    )

async def stop_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    active = db.get_active_session(user_id)
    if not active:
        await query.edit_message_text("❌ Нет активного таймера.", reply_markup=main_menu())
        return
    
    db.stop_session(active['session_id'])
    # Получаем длительность
    session = db.cursor.execute(
        "SELECT duration_minutes FROM time_sessions WHERE id = ?",
        (active['session_id'],)
    ).fetchone()
    
    duration = session[0] if session else 0
    await query.edit_message_text(
        f"⏹️ Таймер остановлен!\nЗадача: {active['task_title']}\n⏱️ Итого: {format_duration(duration)}",
        reply_markup=main_menu()
    )

async def show_timer_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    active = db.get_active_session(user_id)
    if not active:
        await query.edit_message_text("❌ Нет активного таймера.", reply_markup=timer_keyboard())
        return
    
    start_time = datetime.fromisoformat(active['start_time'])
    elapsed = (datetime.now() - start_time).total_seconds() // 60
    
    await query.edit_message_text(
        f"⏳ Активный таймер\n\nЗадача: {active['task_title']}\nНачало: {start_time.strftime('%H:%M:%S')}\nПрошло: {format_duration(elapsed)}",
        reply_markup=timer_keyboard()
    )

# ============ КАТЕГОРИИ ============

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    categories = db.get_categories()
    
    if not categories:
        text = "🏷️ Нет категорий"
    else:
        text = "🏷️ Список категорий:\n\n"
        for cat in categories:
            text += f"• {cat['emoji']} {cat['name']}\n"
    
    await query.edit_message_text(text, reply_markup=categories_keyboard(categories))

# ============ СТАТИСТИКА ============

async def show_overall_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    
    total = db.get_total_time_spent(user_id)
    stats = db.get_stats_by_category(user_id)
    weekly = db.get_weekly_summary(user_id)
    monthly = db.get_monthly_summary(user_id)
    
    text = "📊 Общая статистика\n\n"
    text += f"⏱️ Всего времени: {format_duration(total)}\n"
    text += f"📅 За неделю: {format_duration(weekly['total_time'])}\n"
    text += f"📅 За месяц: {format_duration(monthly['total_time'])}\n"
    text += f"✅ Задач за неделю: {weekly['completed']}\n"
    text += f"✅ Задач за месяц: {monthly['completed']}\n\n"
    text += "📈 По категориям:\n"
    
    for stat in stats[:10]:
        if stat['minutes'] > 0:
            percent = (stat['minutes'] / total * 100) if total > 0 else 0
            text += f"• {stat['emoji']} {stat['category']}: {format_duration(stat['minutes'])} ({percent:.1f}%)\n"
    
    await query.edit_message_text(text, reply_markup=stats_keyboard())

async def show_category_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, year: int):
    query = update.callback_query
    stats = db.get_stats_by_category(user_id, year)
    
    if not stats or all(s['minutes'] == 0 for s in stats):
        await query.edit_message_text(f"📊 Нет данных за {year} год", reply_markup=stats_keyboard())
        return
    
    total = sum(s['minutes'] for s in stats)
    text = f"📊 Статистика за {year} год\n\n"
    text += f"⏱️ Всего: {format_duration(total)}\n\n"
    
    for stat in stats:
        if stat['minutes'] > 0:
            percent = (stat['minutes'] / total * 100) if total > 0 else 0
            text += f"• {stat['emoji']} {stat['category']}: {format_duration(stat['minutes'])} ({percent:.1f}%)\n"
    
    await query.edit_message_text(text, reply_markup=stats_keyboard())

async def show_period_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, period: str):
    query = update.callback_query
    stats = db.get_detailed_stats(user_id, period=period)
    
    if not stats:
        await query.edit_message_text(f"📊 Нет данных за {period}", reply_markup=stats_keyboard())
        return
    
    text = f"📊 Статистика за {period}\n\n"
    total = sum(s['minutes'] for s in stats)
    text += f"⏱️ Всего: {format_duration(total)}\n\n"
    
    by_category = {}
    for stat in stats:
        cat = stat['category'] or 'Без категории'
        by_category[cat] = by_category.get(cat, 0) + stat['minutes']
    
    for cat, minutes in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
        text += f"• {cat}: {format_duration(minutes)}\n"
    
    await query.edit_message_text(text, reply_markup=stats_keyboard())

async def show_stats_by_category_detail(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                       user_id: int, category_name: str):
    query = update.callback_query
    years = get_years_list()
    keyboard = []
    
    for year in years:
        stats = db.get_stats_by_category(user_id, year)
        for s in stats:
            if s['category'] == category_name and s['minutes'] > 0:
                keyboard.append([
                    InlineKeyboardButton(
                        f"📅 {year}: {format_duration(s['minutes'])}",
                        callback_data=f"stats_year_category_{year}_{category_name}"
                    )
                ])
    
    if not keyboard:
        await query.edit_message_text(f"📊 Нет данных по категории '{category_name}'", reply_markup=stats_keyboard())
        return
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="stats_category_choice")])
    await query.edit_message_text(
        f"📊 Статистика по категории '{category_name}':",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_compare_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, compare_type: str):
    query = update.callback_query
    # Упрощённая версия сравнения
    current = db.get_weekly_summary(user_id)
    previous = db.get_weekly_summary_previous(user_id)
    
    text = "📊 Сравнение периодов\n\n"
    text += f"Текущая неделя: {format_duration(current['total_time'])} ({current['completed']} задач)\n"
    text += f"Прошлая неделя: {format_duration(previous['total_time'])} ({previous['completed']} задач)\n"
    
    if previous['total_time'] > 0:
        change = ((current['total_time'] - previous['total_time']) / previous['total_time'] * 100)
        icon = "📈" if change > 0 else "📉"
        text += f"\n{icon} Изменение: {change:+.1f}%"
    
    await query.edit_message_text(text, reply_markup=stats_keyboard())

async def show_top_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    tasks = db.get_top_tasks(user_id, 10)
    
    if not tasks:
        await query.edit_message_text("🏆 Нет данных для топа задач", reply_markup=stats_keyboard())
        return
    
    text = "🏆 Топ задач по времени:\n\n"
    for i, task in enumerate(tasks, 1):
        text += f"{i}. {task['title']}\n"
        text += f"   {task['category']}: {format_duration(task['time'])}\n\n"
    
    await query.edit_message_text(text, reply_markup=stats_keyboard())

async def show_daily_activity(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    activity = db.get_daily_activity(user_id, 30)
    
    if not activity:
        await query.edit_message_text("📈 Нет данных об активности", reply_markup=stats_keyboard())
        return
    
    text = "📈 Дневная активность (последние 30 дней):\n\n"
    for day in activity[:14]:
        text += f"📅 {day['date']}: {day['tasks']} задач, {format_duration(day['time'])}\n"
    
    await query.edit_message_text(text, reply_markup=stats_keyboard())

async def show_predictions(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    tasks = db.get_tasks_by_completion_time(user_id)
    
    if not tasks:
        await query.edit_message_text("🔮 Нет данных для прогнозов", reply_markup=stats_keyboard())
        return
    
    text = "🔮 Прогнозы времени:\n\n"
    for task in tasks[:10]:
        text += f"📌 {task['title']}\n"
        text += f"   Среднее: {format_duration(task['avg_time'])}\n"
        if task['estimated']:
            text += f"   Оценка: {format_duration(task['estimated'])}\n"
        text += f"   Выполнений: {task['count']}\n\n"
    
    await query.edit_message_text(text, reply_markup=stats_keyboard())

async def export_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    csv_data = db.export_stats_csv(user_id)
    
    await query.edit_message_text(
        "📤 Статистика экспортирована в CSV!\n\n"
        "Скопируйте данные ниже:\n\n"
        f"```\n{csv_data[:1000]}\n```",
        reply_markup=stats_keyboard(),
        parse_mode='Markdown'
    )

# ============ ПРОЕКТЫ ============

async def show_projects(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    projects = db.get_user_projects(user_id)
    
    if not projects:
        await query.edit_message_text("📦 У вас нет проектов", reply_markup=projects_keyboard([]))
        return
    
    text = "📦 Ваши проекты:\n\n"
    for p in projects:
        role_icon = "👑" if p['role'] == 'admin' else "👤"
        text += f"{role_icon} {p['name']}\n"
        if p.get('description'):
            text += f"   {p['description']}\n"
        text += f"   Создан: {p['created_at']}\n\n"
    
    await query.edit_message_text(text, reply_markup=projects_keyboard(projects))

async def show_project_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, project_id: int, user_id: int):
    query = update.callback_query
    project = db.cursor.execute(
        "SELECT id, name, description, owner_id, created_at FROM projects WHERE id = ?",
        (project_id,)
    ).fetchone()
    
    if not project:
        await query.edit_message_text("❌ Проект не найден")
        return
    
    role = db.get_user_role(project_id, user_id)
    members = db.get_project_members(project_id)
    
    text = f"📦 {project[1]}\n\n"
    text += f"📝 {project[2] or 'Нет описания'}\n"
    text += f"👑 Владелец: {project[3]}\n"
    text += f"📅 Создан: {project[4]}\n"
    text += f"👥 Участников: {len(members)}\n"
    text += f"🔑 Ваша роль: {role or 'Нет'}\n"
    
    await query.edit_message_text(text, reply_markup=project_detail_keyboard(project_id, role or 'member'))

async def show_project_members(update: Update, context: ContextTypes.DEFAULT_TYPE, project_id: int, user_id: int):
    query = update.callback_query
    members = db.get_project_members(project_id)
    
    if not members:
        await query.edit_message_text("👥 Нет участников", reply_markup=project_detail_keyboard(project_id, 'member'))
        return
    
    text = "👥 Участники проекта:\n\n"
    for m in members:
        role_icon = "👑" if m['role'] == 'admin' else "👤"
        text += f"{role_icon} {m['username'] or 'Пользователь'} ({m['role']})\n"
        text += f"   Присоединился: {m['joined_at']}\n\n"
    
    is_admin = db.get_user_role(project_id, user_id) in ['admin', 'owner']
    await query.edit_message_text(text, reply_markup=project_members_keyboard(members, project_id, is_admin))

# ============ ШАБЛОНЫ ============

async def show_templates(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    templates = db.get_user_templates(user_id)
    
    if not templates:
        await query.edit_message_text("📂 Нет шаблонов", reply_markup=templates_keyboard([]))
        return
    
    text = "📂 Ваши шаблоны:\n\n"
    for t in templates:
        text += f"• {t['title']}"
        if t.get('category'):
            text += f" ({t['category']})"
        text += "\n"
    
    await query.edit_message_text(text, reply_markup=templates_keyboard(templates))

async def use_template(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, template_id: int):
    query = update.callback_query
    template = db.get_task(template_id)
    
    if not template or template['user_id'] != user_id:
        await query.edit_message_text("❌ Шаблон не найден")
        return
    
    task_id = db.create_task(
        user_id=user_id,
        title=f"{template['title']} (из шаблона)",
        category_id=template.get('category_id'),
        priority=template.get('priority', 2),
        description=template.get('description')
    )
    
    await query.edit_message_text(
        f"✅ Задача создана из шаблона!\n📌 {template['title']}",
        reply_markup=main_menu()
    )

# ============ УВЕДОМЛЕНИЯ ============

async def show_notifications_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    tasks = db.get_tasks_with_deadline(user_id, 24)
    overdue = db.get_overdue_tasks(user_id)
    stats = db.get_task_stats_for_user(user_id)
    
    text = "🔔 ЦЕНТР УВЕДОМЛЕНИЙ\n\n"
    text += f"📌 Дедлайны (24ч): {len(tasks)}\n"
    text += f"⚠️ Просроченных: {len(overdue)}\n"
    text += f"📊 Активных задач: {stats.get('active', 0)}\n"
    text += f"✅ Выполнено сегодня: {stats.get('completed_today', 0)}\n"
    
    await query.edit_message_text(text, reply_markup=notifications_keyboard())

async def show_deadlines(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    tasks = db.get_tasks_with_deadline(user_id, 24)
    
    if not tasks:
        await query.edit_message_text("🔔 Нет дедлайнов в ближайшие 24 часа", reply_markup=notifications_keyboard())
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
        else:
            status = f"⏳ {hours:.1f} ч"
        
        priority_icon = get_priority_emoji(task.get('priority', 2))
        text += f"{i}. {priority_icon} {task['title']}\n"
        text += f"   📅 {task['deadline']}\n"
        text += f"   {status}\n\n"
    
    await query.edit_message_text(text, reply_markup=notifications_keyboard())

async def show_overdue(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    tasks = db.get_overdue_tasks(user_id)
    
    if not tasks:
        await query.edit_message_text("✅ Нет просроченных задач!", reply_markup=notifications_keyboard())
        return
    
    text = "⚠️ ПРОСРОЧЕННЫЕ ЗАДАЧИ:\n\n"
    for i, task in enumerate(tasks, 1):
        deadline = datetime.fromisoformat(task['deadline'])
        overdue_days = (datetime.now() - deadline).total_seconds() / 86400
        priority_icon = get_priority_emoji(task.get('priority', 2))
        text += f"{i}. {priority_icon} {task['title']}\n"
        text += f"   📅 Дедлайн: {task['deadline']}\n"
        text += f"   🚨 Просрочено: {overdue_days:.1f} дн\n\n"
    
    await query.edit_message_text(text, reply_markup=notifications_keyboard())

async def show_task_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    stats = db.get_task_stats_for_user(user_id)
    
    text = "📊 СТАТИСТИКА ЗАДАЧ\n\n"
    text += f"📌 Всего: {stats.get('total', 0)}\n"
    text += f"🔄 Активных: {stats.get('active', 0)}\n"
    text += f"✅ Выполнено сегодня: {stats.get('completed_today', 0)}\n"
    
    if stats.get('total', 0) > 0:
        completed = stats['total'] - stats['active']
        percent = (completed / stats['total'] * 100)
        text += f"\n📈 Прогресс: {percent:.1f}% выполнено"
    
    await query.edit_message_text(text, reply_markup=notifications_keyboard())

async def show_progress_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    tasks = db.get_user_tasks(user_id, 'active')
    stagnant_tasks = [t for t in tasks if t.get('progress', 0) < 50 and t.get('created_at')]
    
    if not stagnant_tasks:
        await query.edit_message_text("📈 Все задачи в хорошем прогрессе!", reply_markup=notifications_keyboard())
        return
    
    text = "📈 ЗАДАЧИ С МАЛЫМ ПРОГРЕССОМ:\n\n"
    for task in stagnant_tasks[:5]:
        text += f"• {task['title']} ({task.get('progress', 0)}%)\n"
    
    await query.edit_message_text(text, reply_markup=notifications_keyboard())

async def show_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    settings = db.get_user_settings(user_id)
    
    text = "⚙️ НАСТРОЙКИ УВЕДОМЛЕНИЙ\n\n"
    text += f"📅 Ежедневная сводка: {settings.get('daily_hour', 21)}:00\n"
    text += f"📅 Еженедельная: {['Пн','Вт','Ср','Чт','Пт','Сб','Вс'][settings.get('weekly_day', 6)]} {settings.get('weekly_hour', 20)}:00\n"
    text += f"⏰ Проверка дедлайнов: каждые {settings.get('deadline_check_interval', 5)} мин\n"
    
    await query.edit_message_text(text, reply_markup=notification_settings_keyboard())

async def save_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, setting_type: str):
    query = update.callback_query
    settings = db.get_user_settings(user_id)
    
    if setting_type == 'daily':
        settings['daily_hour'] = context.user_data.get('daily_hour', 21)
        settings['daily_min'] = context.user_data.get('daily_min', 0)
    elif setting_type == 'weekly':
        settings['weekly_day'] = context.user_data.get('weekly_day', 6)
        settings['weekly_hour'] = context.user_data.get('weekly_hour', 20)
        settings['weekly_min'] = context.user_data.get('weekly_min', 0)
    
    db.update_user_settings(user_id, settings)
    await query.edit_message_text("✅ Настройки сохранены!", reply_markup=notifications_keyboard())

# ============ ДОСТИЖЕНИЯ ============

async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    achievements = db.get_user_achievements(user_id)
    
    if not achievements:
        await query.edit_message_text("🏆 У вас пока нет достижений", reply_markup=main_menu())
        return
    
    text = "🏆 ВАШИ ДОСТИЖЕНИЯ:\n\n"
    for ach in achievements:
        text += f"{ach['icon']} {ach['name']}\n"
        text += f"   {ach['description']}\n"
        text += f"   {ach['reward']}\n\n"
    
    await query.edit_message_text(text, reply_markup=achievements_keyboard(achievements))

async def show_all_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    all_ach = db.get_all_achievements()
    user_ach = db.get_user_achievements(user_id)
    unlocked_ids = [a['id'] for a in user_ach]
    
    text = "📋 ВСЕ ДОСТИЖЕНИЯ:\n\n"
    for ach in all_ach:
        icon = "✅" if ach['id'] in unlocked_ids else "🔒"
        text += f"{icon} {ach['icon']} {ach['name']}\n"
        text += f"   {ach['description']}\n"
        text += f"   {ach['reward']}\n\n"
    
    await query.edit_message_text(text, reply_markup=all_achievements_keyboard(all_ach, unlocked_ids))

async def show_achievement_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, achievement_id: str):
    query = update.callback_query
    ach = db.cursor.execute(
        "SELECT id, name, description, icon, requirement_type, requirement_value, reward FROM achievements WHERE id = ?",
        (achievement_id,)
    ).fetchone()
    
    if not ach:
        await query.edit_message_text("❌ Достижение не найдено")
        return
    
    text = f"{ach[3]} {ach[1]}\n\n"
    text += f"{ach[2]}\n"
    text += f"Требование: {ach[4]} > {ach[5]}\n"
    text += f"Награда: {ach[6]}"
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="achievements")]
    ]))

# ============ ПОМОЩЬ И ТУТОР ============

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = (
        "❓ ПОМОЩЬ\n\n"
        "Этот бот помогает управлять задачами и временем.\n\n"
        "Основные функции:\n"
        "• Создание задач с приоритетами и дедлайнами\n"
        "• Трекинг времени выполнения\n"
        "• Статистика и аналитика\n"
        "• Совместные проекты\n"
        "• Достижения и прогресс\n\n"
        "Нажмите 'Начать тутор' для пошагового обучения."
    )
    await query.edit_message_text(text, reply_markup=help_keyboard())

async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = (
        "📋 КОМАНДЫ БОТА\n\n"
        "/start — Главное меню\n"
        "/help — Помощь\n\n"
        "Все остальные функции доступны через кнопки меню."
    )
    await query.edit_message_text(text, reply_markup=help_keyboard())

async def show_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id if query else update.effective_user.id
    
    tutorial_steps = [
        "🚀 Шаг 1: Создайте свою первую задачу\n\nНажмите 'Создать задачу' и введите название.",
        "📋 Шаг 2: Управляйте задачами\n\nВы можете изменять статус, приоритет и прогресс.",
        "⏱️ Шаг 3: Трекинг времени\n\nЗасекайте время на выполнение задач через таймер.",
        "📊 Шаг 4: Анализируйте статистику\n\nПросматривайте отчёты по категориям и периодам.",
        "📦 Шаг 5: Работайте в проектах\n\nСоздавайте проекты и добавляйте участников.",
        "🏆 Шаг 6: Получайте достижения\n\nВыполняйте задачи и открывайте новые достижения!"
    ]
    
    context.user_data['tutorial_step'] = 0
    context.user_data['tutorial_id'] = 'main'
    
    text = tutorial_steps[0]
    total_steps = len(tutorial_steps)
    
    if query:
        await query.edit_message_text(
            text,
            reply_markup=tutorial_keyboard(0, total_steps, 'main')
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=tutorial_keyboard(0, total_steps, 'main')
        )

async def tutorial_next(update: Update, context: ContextTypes.DEFAULT_TYPE, tutorial_id: str):
    query = update.callback_query
    step = context.user_data.get('tutorial_step', 0) + 1
    
    tutorial_steps = [
        "🚀 Шаг 1: Создайте свою первую задачу\n\nНажмите 'Создать задачу' и введите название.",
        "📋 Шаг 2: Управляйте задачами\n\nВы можете изменять статус, приоритет и прогресс.",
        "⏱️ Шаг 3: Трекинг времени\n\nЗасекайте время на выполнение задач через таймер.",
        "📊 Шаг 4: Анализируйте статистику\n\nПросматривайте отчёты по категориям и периодам.",
        "📦 Шаг 5: Работайте в проектах\n\nСоздавайте проекты и добавляйте участников.",
        "🏆 Шаг 6: Получайте достижения\n\nВыполняйте задачи и открывайте новые достижения!"
    ]
    
    context.user_data['tutorial_step'] = step
    total_steps = len(tutorial_steps)
    
    if step >= total_steps:
        db.update_tutorial_progress(query.from_user.id, 'main', completed=True)
        await query.edit_message_text(
            "🎉 ТУТОР ЗАВЕРШЁН!\n\nТеперь вы готовы использовать бота. Удачи!",
            reply_markup=main_menu()
        )
        return
    
    await query.edit_message_text(
        tutorial_steps[step],
        reply_markup=tutorial_keyboard(step, total_steps, 'main')
    )

async def tutorial_back(update: Update, context: ContextTypes.DEFAULT_TYPE, tutorial_id: str):
    query = update.callback_query
    step = context.user_data.get('tutorial_step', 0) - 1
    
    tutorial_steps = [
        "🚀 Шаг 1: Создайте свою первую задачу\n\nНажмите 'Создать задачу' и введите название.",
        "📋 Шаг 2: Управляйте задачами\n\nВы можете изменять статус, приоритет и прогресс.",
        "⏱️ Шаг 3: Трекинг времени\n\nЗасекайте время на выполнение задач через таймер.",
        "📊 Шаг 4: Анализируйте статистику\n\nПросматривайте отчёты по категориям и периодам.",
        "📦 Шаг 5: Работайте в проектах\n\nСоздавайте проекты и добавляйте участников.",
        "🏆 Шаг 6: Получайте достижения\n\nВыполняйте задачи и открывайте новые достижения!"
    ]
    
    if step < 0:
        step = 0
    
    context.user_data['tutorial_step'] = step
    total_steps = len(tutorial_steps)
    
    await query.edit_message_text(
        tutorial_steps[step],
        reply_markup=tutorial_keyboard(step, total_steps, 'main')
    )

# ============ КОММЕНТАРИИ ============

async def show_comments(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
    query = update.callback_query
    comments = db.get_task_comments(task_id)
    
    if not comments:
        await query.edit_message_text(
            "💬 Нет комментариев",
            reply_markup=comments_keyboard(task_id)
        )
        return
    
    text = "💬 КОММЕНТАРИИ:\n\n"
    for c in comments:
        text += f"👤 {c['username']} ({c['created_at']}):\n"
        text += f"   {c['comment']}\n\n"
    
    await query.edit_message_text(text, reply_markup=comments_keyboard(task_id))

# ============ ОБРАБОТЧИКИ ТЕКСТА ============

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Создание задачи
    if context.user_data.get('creating_task'):
        context.user_data['creating_task'] = False
        context.user_data['task_title'] = text
        
        deadline = None
        date_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}'
        match = re.search(date_pattern, text)
        if match:
            deadline = match.group()
            title = text.replace(deadline, '').strip()
            context.user_data['task_title'] = title
            context.user_data['task_deadline'] = deadline
        
        categories = db.get_categories()
        keyboard = []
        for cat in categories:
            keyboard.append([
                InlineKeyboardButton(f"{cat['emoji']} {cat['name']}", callback_data=f"task_cat_{cat['id']}")
            ])
        keyboard.append([
            InlineKeyboardButton("Без категории", callback_data="task_cat_none")
        ])
        keyboard.append([
            InlineKeyboardButton("➕ Новая категория", callback_data="task_cat_new", style="success")
        ])
        keyboard.append([
            InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main", style="danger")
        ])
        keyboard.append([
            InlineKeyboardButton("🔴 Высокий", callback_data="task_priority_3", style="danger"),
            InlineKeyboardButton("🟡 Средний", callback_data="task_priority_2", style="primary"),
            InlineKeyboardButton("🟢 Низкий", callback_data="task_priority_1", style="success")
        ])
        
        context.user_data['awaiting_priority'] = True
        await update.message.reply_text(
            f"📌 Задача: {context.user_data['task_title']}\n\nВыберите категорию и приоритет:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Обработка выбора приоритета
    if context.user_data.get('awaiting_priority'):
        context.user_data['awaiting_priority'] = False
        if text in ['🔴 Высокий', '🟡 Средний', '🟢 Низкий']:
            priority_map = {'🔴 Высокий': 3, '🟡 Средний': 2, '🟢 Низкий': 1}
            context.user_data['task_priority'] = priority_map.get(text, 2)
        await update.message.reply_text("✅ Приоритет сохранён", reply_markup=main_menu())
        return
    
    # Добавление категории
    if context.user_data.get('awaiting_category'):
        context.user_data['awaiting_category'] = False
        if db.add_category(text):
            await update.message.reply_text(f"✅ Категория '{text}' добавлена!", reply_markup=main_menu())
        else:
            await update.message.reply_text(f"❌ Категория '{text}' уже существует!", reply_markup=main_menu())
        return
    
    # Создание шаблона
    if context.user_data.get('creating_template'):
        context.user_data['creating_template'] = False
        categories = db.get_categories()
        keyboard = []
        for cat in categories:
            keyboard.append([
                InlineKeyboardButton(f"{cat['emoji']} {cat['name']}", callback_data=f"template_cat_{cat['id']}")
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
    
    # Редактирование задачи
    if context.user_data.get('editing_task'):
        task_id = context.user_data['editing_task']
        db.cursor.execute(
            "UPDATE tasks SET title = ? WHERE id = ?",
            (text, task_id)
        )
        db.connection.commit()
        context.user_data.pop('editing_task', None)
        await update.message.reply_text("✅ Задача обновлена!", reply_markup=main_menu())
        return
    
    # Комментарий
    if context.user_data.get('comment_task'):
        task_id = context.user_data['comment_task']
        db.add_comment(task_id, user_id, text)
        context.user_data.pop('comment_task', None)
        await update.message.reply_text("✅ Комментарий добавлен!", reply_markup=main_menu())
        return
    
    # Создание проекта
    if context.user_data.get('creating_project'):
        context.user_data['creating_project'] = False
        context.user_data['project_name'] = text
        await update.message.reply_text("✏️ Введите описание проекта (или '-' для пропуска):")
        context.user_data['awaiting_project_desc'] = True
        return
    
    if context.user_data.get('awaiting_project_desc'):
        context.user_data['awaiting_project_desc'] = False
        description = text if text != '-' else ''
        project_id = db.create_project(
            name=context.user_data.get('project_name', 'Без названия'),
            description=description,
            owner_id=user_id
        )
        context.user_data.pop('project_name', None)
        await update.message.reply_text(
            f"✅ Проект создан!\n📦 {text}",
            reply_markup=main_menu()
        )
        return
    
    # Добавление участника в проект
    if context.user_data.get('adding_member_project'):
        project_id = context.user_data['adding_member_project']
        username = text.replace('@', '').strip()
        
        # Ищем пользователя по username
        db.cursor.execute(
            "SELECT user_id FROM users WHERE username = ?",
            (username,)
        )
        result = db.cursor.fetchone()
        
        if result:
            db.add_project_member(project_id, result[0])
            await update.message.reply_text(f"✅ Пользователь @{username} добавлен в проект!", reply_markup=main_menu())
        else:
            await update.message.reply_text(f"❌ Пользователь @{username} не найден. Попробуйте снова.", reply_markup=main_menu())
        
        context.user_data.pop('adding_member_project', None)
        return
    
    # Неизвестная команда
    await update.message.reply_text(
        "❓ Используйте кнопки меню для навигации.",
        reply_markup=main_menu()
        )
