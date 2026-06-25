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

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def check_deadlines(context: ContextTypes.DEFAULT_TYPE):
    """Проверка дедлайнов и отправка уведомлений"""
    try:
        # Получаем все активные задачи с дедлайном в ближайший час
        db.cursor.execute("""
            SELECT t.id, t.title, t.user_id, t.deadline
            FROM tasks t
            WHERE t.status = 'active' 
              AND t.deadline IS NOT NULL
              AND datetime(t.deadline) BETWEEN datetime('now') AND datetime('now', '+1 hour')
        """)
        tasks = db.cursor.fetchall()
        
        for task in tasks:
            task_id, title, user_id, deadline = task
            try:
                # Отправляем уведомление пользователю
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⏰ НАПОМИНАНИЕ!\n\n"
                         f"Задача: {title}\n"
                         f"Дедлайн: {deadline}\n\n"
                         f"Остался 1 час! Срочно завершите задачу!",
                    reply_markup=main_menu()
                )
                logging.info(f"Уведомление отправлено пользователю {user_id} о задаче {task_id}")
            except Exception as e:
                logging.error(f"Ошибка отправки уведомления {user_id}: {e}")
        
    except Exception as e:
        logging.error(f"Ошибка в check_deadlines: {e}")

async def check_long_running_tasks(context: ContextTypes.DEFAULT_TYPE):
    """Проверка задач, которые выполняются слишком долго (более 2 часов)"""
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

async def daily_summary(context: ContextTypes.DEFAULT_TYPE):
    """Ежедневная сводка о задачах"""
    try:
        db.cursor.execute("SELECT user_id FROM users")
        users = db.cursor.fetchall()
        
        for (user_id,) in users:
            try:
                # Считаем задачи за сегодня
                db.cursor.execute("""
                    SELECT COUNT(*), 
                           SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END)
                    FROM tasks
                    WHERE user_id = ? 
                      AND date(created_at) = date('now')
                """, (user_id,))
                total, completed = db.cursor.fetchone()
                
                # Активные задачи с дедлайном на сегодня
                db.cursor.execute("""
                    SELECT COUNT(*)
                    FROM tasks
                    WHERE user_id = ? 
                      AND status = 'active'
                      AND date(deadline) = date('now')
                """, (user_id,))
                due_today = db.cursor.fetchone()[0]
                
                # Просроченные задачи
                db.cursor.execute("""
                    SELECT COUNT(*)
                    FROM tasks
                    WHERE user_id = ? 
                      AND status = 'active'
                      AND deadline IS NOT NULL
                      AND date(deadline) < date('now')
                """, (user_id,))
                overdue = db.cursor.fetchone()[0]
                
                text = f"📊 ЕЖЕДНЕВНАЯ СВОДКА\n\n"
                text += f"📌 За сегодня создано: {total or 0} задач\n"
                text += f"✅ Выполнено: {completed or 0} задач\n"
                
                if due_today > 0:
                    text += f"\n⚠️ Срочных задач на сегодня: {due_today}\n"
                
                if overdue > 0:
                    text += f"🚨 Просроченных задач: {overdue}\n"
                    text += "Срочно проверьте их!\n"
                
                if due_today == 0 and overdue == 0:
                    text += "\n🎉 Отличная работа! Все задачи в порядке."
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=main_menu()
                )
                logging.info(f"Сводка отправлена пользователю {user_id}")
            except Exception as e:
                logging.error(f"Ошибка отправки сводки пользователю {user_id}: {e}")
        
    except Exception as e:
        logging.error(f"Ошибка в daily_summary: {e}")

async def weekly_summary(context: ContextTypes.DEFAULT_TYPE):
    """Еженедельная сводка"""
    try:
        db.cursor.execute("SELECT user_id FROM users")
        users = db.cursor.fetchall()
        
        for (user_id,) in users:
            try:
                # Статистика за неделю
                db.cursor.execute("""
                    SELECT COUNT(*),
                           SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END)
                    FROM tasks
                    WHERE user_id = ? 
                      AND date(created_at) >= date('now', '-7 days')
                """, (user_id,))
                total, completed = db.cursor.fetchone()
                
                # Время за неделю
                db.cursor.execute("""
                    SELECT COALESCE(SUM(duration_minutes), 0)
                    FROM time_sessions ts
                    JOIN tasks t ON ts.task_id = t.id
                    WHERE t.user_id = ? 
                      AND date(ts.end_time) >= date('now', '-7 days')
                """, (user_id,))
                time_spent = db.cursor.fetchone()[0]
                
                text = f"📊 ЕЖЕНЕДЕЛЬНАЯ СВОДКА\n\n"
                text += f"📌 Создано задач за неделю: {total or 0}\n"
                text += f"✅ Выполнено: {completed or 0}\n"
                text += f"⏱️ Времени затрачено: {format_duration(time_spent)}\n"
                
                if total and total > 0:
                    percent = (completed / total * 100)
                    text += f"\n📈 Продуктивность: {percent:.1f}%"
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=main_menu()
                )
            except Exception as e:
                logging.error(f"Ошибка отправки недельной сводки {user_id}: {e}")
    except Exception as e:
        logging.error(f"Ошибка в weekly_summary: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logging.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=main_menu()
        )

def main():
    """Главная функция запуска бота"""
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Регистрация команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    
    # Регистрация callback обработчиков
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(CallbackQueryHandler(handle_task_category, pattern="^task_cat_"))
    application.add_handler(CallbackQueryHandler(handle_template_category, pattern="^template_cat_"))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # === НАСТРОЙКА УВЕДОМЛЕНИЙ ===
    scheduler = AsyncIOScheduler()
    
    # 1. Проверка дедлайнов каждые 5 минут
    scheduler.add_job(
        check_deadlines, 
        'interval', 
        minutes=5,
        args=[application]
    )
    
    # 2. Проверка долгих задач каждые 15 минут
    scheduler.add_job(
        check_long_running_tasks,
        'interval',
        minutes=15,
        args=[application]
    )
    
    # 3. Ежедневная сводка в 21:00
    scheduler.add_job(
        daily_summary,
        CronTrigger(hour=21, minute=0),
        args=[application]
    )
    
    # 4. Еженедельная сводка в воскресенье в 20:00
    scheduler.add_job(
        weekly_summary,
        CronTrigger(day_of_week='sun', hour=20, minute=0),
        args=[application]
    )
    
    scheduler.start()
    logging.info("✅ Планировщик уведомлений запущен")
    logging.info("📅 Ежедневная сводка: 21:00")
    logging.info("📅 Еженедельная сводка: Воскресенье 20:00")
    logging.info("⏰ Проверка дедлайнов: каждые 5 минут")
    
    # Запуск бота
    print("🤖 Бот запущен!")
    print("📅 Ежедневная сводка: 21:00")
    print("📅 Еженедельная сводка: Воскресенье 20:00")
    print("⏰ Проверка дедлайнов: каждые 5 минут")
    application.run_polling()

if __name__ == "__main__":
    main()
