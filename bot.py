import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from config import BOT_TOKEN
from handlers import *
from keyboards import main_menu
from database import db
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import asyncio

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ============ ПЛАНИРОВЩИК УВЕДОМЛЕНИЙ ============

async def check_deadlines(context: ContextTypes.DEFAULT_TYPE):
    """Проверка дедлайнов и отправка уведомлений"""
    try:
        db.cursor.execute("""
            SELECT t.id, t.title, t.user_id, t.deadline, t.priority
            FROM tasks t
            WHERE t.status = 'active' 
              AND t.deadline IS NOT NULL
              AND datetime(t.deadline) BETWEEN datetime('now') AND datetime('now', '+1 hour')
        """)
        tasks = db.cursor.fetchall()
        
        for task in tasks:
            task_id, title, user_id, deadline, priority = task
            try:
                priority_icon = get_priority_emoji(priority or 2)
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⏰ НАПОМИНАНИЕ О ДЕДЛАЙНЕ!\n\n"
                         f"{priority_icon} Задача: {title}\n"
                         f"📅 Дедлайн: {deadline}\n\n"
                         f"Остался 1 час! Срочно завершите задачу!",
                    reply_markup=main_menu()
                )
                logging.info(f"Уведомление о дедлайне отправлено пользователю {user_id}")
            except Exception as e:
                logging.error(f"Ошибка отправки уведомления {user_id}: {e}")
    except Exception as e:
        logging.error(f"Ошибка в check_deadlines: {e}")

async def check_overdue_tasks(context: ContextTypes.DEFAULT_TYPE):
    """Проверка просроченных задач"""
    try:
        db.cursor.execute("""
            SELECT t.id, t.title, t.user_id, t.deadline
            FROM tasks t
            WHERE t.status = 'active' 
              AND t.deadline IS NOT NULL
              AND datetime(t.deadline) < datetime('now')
              AND datetime(t.deadline) > datetime('now', '-1 day')
        """)
        tasks = db.cursor.fetchall()
        
        for task in tasks:
            task_id, title, user_id, deadline = task
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⚠️ ЗАДАЧА ПРОСРОЧЕНА!\n\n"
                         f"📌 Задача: {title}\n"
                         f"📅 Дедлайн был: {deadline}\n\n"
                         f"Срочно примите меры!",
                    reply_markup=main_menu()
                )
                logging.info(f"Уведомление о просрочке отправлено пользователю {user_id}")
            except Exception as e:
                logging.error(f"Ошибка отправки уведомления о просрочке {user_id}: {e}")
    except Exception as e:
        logging.error(f"Ошибка в check_overdue_tasks: {e}")

async def check_long_running_tasks(context: ContextTypes.DEFAULT_TYPE):
    """Проверка задач, которые выполняются слишком долго"""
    try:
        db.cursor.execute("""
            SELECT ts.id, ts.task_id, t.title, t.user_id, ts.start_time,
                   (JULIANDAY('now') - JULIANDAY(ts.start_time)) * 24 as hours
            FROM time_sessions ts
            JOIN tasks t ON ts.task_id = t.id
            WHERE ts.end_time IS NULL
              AND (JULIANDAY('now') - JULIANDAY(ts.start_time)) * 24 > 2
        """)
        sessions = db.cursor.fetchall()
        
        for session in sessions:
            session_id, task_id, title, user_id, start_time, hours = session
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⚠️ ВНИМАНИЕ!\n\n"
                         f"Задача: {title}\n"
                         f"Выполняется уже {hours:.1f} часов\n"
                         f"Начало: {start_time}\n\n"
                         f"Не забыли остановить таймер?",
                    reply_markup=main_menu()
                )
                logging.info(f"Уведомление о долгой задаче отправлено пользователю {user_id}")
            except Exception as e:
                logging.error(f"Ошибка отправки уведомления о долгой задаче: {e}")
    except Exception as e:
        logging.error(f"Ошибка в check_long_running_tasks: {e}")

async def check_progress_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Напоминание о задачах с низким прогрессом"""
    try:
        db.cursor.execute("""
            SELECT t.id, t.title, t.user_id, t.progress, t.created_at
            FROM tasks t
            WHERE t.status = 'active'
              AND t.progress < 50
              AND t.created_at IS NOT NULL
              AND date(t.created_at) < date('now', '-2 days')
        """)
        tasks = db.cursor.fetchall()
        
        for task in tasks:
            task_id, title, user_id, progress, created_at = task
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📈 НАПОМИНАНИЕ О ПРОГРЕССЕ\n\n"
                         f"Задача: {title}\n"
                         f"Текущий прогресс: {progress}%\n"
                         f"Создана: {created_at}\n\n"
                         f"Попробуйте продвинуться в выполнении!",
                    reply_markup=main_menu()
                )
                logging.info(f"Напоминание о прогрессе отправлено пользователю {user_id}")
            except Exception as e:
                logging.error(f"Ошибка отправки напоминания о прогрессе {user_id}: {e}")
    except Exception as e:
        logging.error(f"Ошибка в check_progress_reminder: {e}")

async def daily_summary(context: ContextTypes.DEFAULT_TYPE):
    """Ежедневная сводка о задачах"""
    try:
        users = db.get_all_users()
        
        for user_id in users:
            try:
                settings = db.get_user_settings(user_id)
                hour = settings.get('daily_hour', 21)
                minute = settings.get('daily_min', 0)
                
                now = datetime.now()
                if now.hour != hour or now.minute != minute:
                    continue
                
                tasks = db.get_user_tasks(user_id, 'active')
                completed_today = db.cursor.execute("""
                    SELECT COUNT(*) FROM tasks 
                    WHERE user_id = ? 
                      AND status = 'completed'
                      AND date(created_at) = date('now')
                """, (user_id,)).fetchone()[0]
                
                overdue = db.get_overdue_tasks(user_id)
                deadlines = db.get_tasks_with_deadline(user_id, 24)
                
                text = f"📊 ЕЖЕДНЕВНАЯ СВОДКА\n\n"
                text += f"📌 Активных задач: {len(tasks)}\n"
                text += f"✅ Выполнено сегодня: {completed_today}\n"
                text += f"⚠️ Просроченных: {len(overdue)}\n"
                text += f"⏰ Дедлайнов (24ч): {len(deadlines)}\n"
                
                if len(deadlines) > 0:
                    text += "\nБлижайшие дедлайны:\n"
                    for t in deadlines[:3]:
                        text += f"• {t['title']} - {t['deadline']}\n"
                
                if len(tasks) == 0 and len(overdue) == 0:
                    text += "\n🎉 Отличная работа! Все задачи выполнены."
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=main_menu()
                )
                logging.info(f"Ежедневная сводка отправлена пользователю {user_id}")
            except Exception as e:
                logging.error(f"Ошибка отправки сводки пользователю {user_id}: {e}")
    except Exception as e:
        logging.error(f"Ошибка в daily_summary: {e}")

async def weekly_summary(context: ContextTypes.DEFAULT_TYPE):
    """Еженедельная сводка"""
    try:
        users = db.get_all_users()
        
        for user_id in users:
            try:
                settings = db.get_user_settings(user_id)
                day = settings.get('weekly_day', 6)
                hour = settings.get('weekly_hour', 20)
                minute = settings.get('weekly_min', 0)
                
                now = datetime.now()
                if now.weekday() != day or now.hour != hour or now.minute != minute:
                    continue
                
                weekly = db.get_weekly_summary(user_id)
                monthly = db.get_monthly_summary(user_id)
                top_tasks = db.get_top_tasks(user_id, 3)
                
                text = f"📊 ЕЖЕНЕДЕЛЬНАЯ СВОДКА\n\n"
                text += f"📅 Активных дней: {weekly['active_days']}/7\n"
                text += f"✅ Выполнено задач: {weekly['completed']}\n"
                text += f"⏱️ Времени затрачено: {format_duration(weekly['total_time'])}\n"
                text += f"\n📊 За месяц: {format_duration(monthly['total_time'])}\n"
                
                if top_tasks:
                    text += "\n🏆 Топ задач:\n"
                    for t in top_tasks[:3]:
                        text += f"• {t['title']} - {format_duration(t['time'])}\n"
                
                if weekly['completed'] > 0:
                    productivity = weekly['completed'] / 7 * 100
                    text += f"\n📈 Продуктивность: {productivity:.1f}%"
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=main_menu()
                )
                logging.info(f"Еженедельная сводка отправлена пользователю {user_id}")
            except Exception as e:
                logging.error(f"Ошибка отправки недельной сводки пользователю {user_id}: {e}")
    except Exception as e:
        logging.error(f"Ошибка в weekly_summary: {e}")

async def create_recurring_tasks(context: ContextTypes.DEFAULT_TYPE):
    """Создание повторяющихся задач"""
    try:
        db.create_recurring_instances()
        logging.info("Повторяющиеся задачи созданы")
    except Exception as e:
        logging.error(f"Ошибка в create_recurring_tasks: {e}")

# ============ ОБРАБОТЧИК ОШИБОК ============

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=main_menu()
        )

# ============ ГЛАВНАЯ ФУНКЦИЯ ============

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Регистрация команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    
    # Регистрация callback обработчиков
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Регистрация обработчиков текста
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # ============ НАСТРОЙКА ПЛАНИРОВЩИКА ============
    scheduler = AsyncIOScheduler()
    
    # Проверка дедлайнов каждые 5 минут
    scheduler.add_job(
        check_deadlines,
        'interval',
        minutes=5,
        args=[application]
    )
    
    # Проверка просроченных задач каждый час
    scheduler.add_job(
        check_overdue_tasks,
        'interval',
        hours=1,
        args=[application]
    )
    
    # Проверка долгих задач каждые 15 минут
    scheduler.add_job(
        check_long_running_tasks,
        'interval',
        minutes=15,
        args=[application]
    )
    
    # Напоминание о прогрессе каждые 6 часов
    scheduler.add_job(
        check_progress_reminder,
        'interval',
        hours=6,
        args=[application]
    )
    
    # Создание повторяющихся задач каждый день в 00:00
    scheduler.add_job(
        create_recurring_tasks,
        CronTrigger(hour=0, minute=0),
        args=[application]
    )
    
    # Ежедневная сводка (проверка каждый час)
    scheduler.add_job(
        daily_summary,
        'interval',
        hours=1,
        args=[application]
    )
    
    # Еженедельная сводка (проверка каждый час)
    scheduler.add_job(
        weekly_summary,
        'interval',
        hours=1,
        args=[application]
    )
    
    scheduler.start()
    
    logging.info("✅ Планировщик уведомлений запущен")
    logging.info("📅 Проверка дедлайнов: каждые 5 минут")
    logging.info("📅 Проверка просрочек: каждый час")
    logging.info("📅 Проверка долгих задач: каждые 15 минут")
    logging.info("📅 Напоминания о прогрессе: каждые 6 часов")
    logging.info("📅 Повторяющиеся задачи: каждый день в 00:00")
    logging.info("📅 Ежедневная сводка: по настройкам пользователя")
    logging.info("📅 Еженедельная сводка: по настройкам пользователя")
    
    print("🤖 Бот запущен!")
    print("📅 Проверка дедлайнов: каждые 5 минут")
    print("📅 Повторяющиеся задачи: каждый день в 00:00")
    
    application.run_polling()

if __name__ == "__main__":
    main()
