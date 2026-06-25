import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from config import DATABASE_NAME, DEFAULT_CATEGORIES

class Database:
    def __init__(self):
        self.connection = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self._init_tables()
        self._init_categories()

    def _init_tables(self):
        """Создание таблиц"""
        # Пользователи
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Категории
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            )
        ''')

        # Задачи
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                category_id INTEGER,
                is_template BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deadline TIMESTAMP,
                status TEXT DEFAULT 'active',
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )
        ''')

        # Временные сессии
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS time_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration_minutes INTEGER,
                FOREIGN KEY(task_id) REFERENCES tasks(id)
            )
        ''')

        self.connection.commit()

    def _init_categories(self):
        """Добавление категорий по умолчанию"""
        for category in DEFAULT_CATEGORIES:
            self.cursor.execute(
                "INSERT OR IGNORE INTO categories (name) VALUES (?)",
                (category,)
            )
        self.connection.commit()

    # === Работа с пользователями ===
    def register_user(self, user_id: int, username: str = None):
        self.cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        self.connection.commit()

    # === Работа с категориями ===
    def get_categories(self) -> List[Dict]:
        self.cursor.execute("SELECT id, name FROM categories ORDER BY name")
        return [{"id": row[0], "name": row[1]} for row in self.cursor.fetchall()]

    def get_category_id(self, name: str) -> Optional[int]:
        self.cursor.execute("SELECT id FROM categories WHERE name = ?", (name,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def add_category(self, name: str) -> bool:
        try:
            self.cursor.execute(
                "INSERT INTO categories (name) VALUES (?)",
                (name,)
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    # === Работа с задачами ===
    def create_task(self, user_id: int, title: str, category_id: int = None, 
                   is_template: bool = False, deadline: str = None) -> int:
        self.cursor.execute(
            """INSERT INTO tasks (user_id, title, category_id, is_template, deadline)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, title, category_id, is_template, deadline)
        )
        self.connection.commit()
        return self.cursor.lastrowid

    def get_user_tasks(self, user_id: int, status: str = 'active') -> List[Dict]:
        query = """
            SELECT t.id, t.title, t.status, t.created_at, t.deadline, 
                   c.name as category_name
            FROM tasks t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = ? AND t.status = ? AND t.is_template = 0
            ORDER BY t.created_at DESC
        """
        self.cursor.execute(query, (user_id, status))
        rows = self.cursor.fetchall()
        return [
            {
                "id": row[0],
                "title": row[1],
                "status": row[2],
                "created_at": row[3],
                "deadline": row[4],
                "category": row[5]
            }
            for row in rows
        ]

    def get_user_templates(self, user_id: int) -> List[Dict]:
        query = """
            SELECT t.id, t.title, c.name as category_name
            FROM tasks t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = ? AND t.is_template = 1
            ORDER BY t.title
        """
        self.cursor.execute(query, (user_id,))
        rows = self.cursor.fetchall()
        return [{"id": row[0], "title": row[1], "category": row[2]} for row in rows]

    def update_task_status(self, task_id: int, status: str):
        self.cursor.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (status, task_id)
        )
        self.connection.commit()

    def delete_task(self, task_id: int):
        self.cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.connection.commit()

    def get_task(self, task_id: int) -> Optional[Dict]:
        query = """
            SELECT t.id, t.title, t.status, t.user_id, t.category_id, t.is_template, t.deadline
            FROM tasks t
            WHERE t.id = ?
        """
        self.cursor.execute(query, (task_id,))
        row = self.cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "title": row[1],
                "status": row[2],
                "user_id": row[3],
                "category_id": row[4],
                "is_template": row[5],
                "deadline": row[6]
            }
        return None

    # === Работа с временными сессиями ===
    def start_session(self, task_id: int) -> int:
        self.cursor.execute(
            "INSERT INTO time_sessions (task_id, start_time) VALUES (?, CURRENT_TIMESTAMP)",
            (task_id,)
        )
        self.connection.commit()
        return self.cursor.lastrowid

    def stop_session(self, session_id: int):
        self.cursor.execute(
            """UPDATE time_sessions 
               SET end_time = CURRENT_TIMESTAMP,
                   duration_minutes = ROUND((JULIANDAY(CURRENT_TIMESTAMP) - JULIANDAY(start_time)) * 1440)
               WHERE id = ?""",
            (session_id,)
        )
        self.connection.commit()

    def get_active_session(self, user_id: int) -> Optional[Dict]:
        query = """
            SELECT ts.id, ts.task_id, t.title, ts.start_time
            FROM time_sessions ts
            JOIN tasks t ON ts.task_id = t.id
            WHERE t.user_id = ? AND ts.end_time IS NULL
            ORDER BY ts.start_time DESC
            LIMIT 1
        """
        self.cursor.execute(query, (user_id,))
        row = self.cursor.fetchone()
        if row:
            return {
                "session_id": row[0],
                "task_id": row[1],
                "task_title": row[2],
                "start_time": row[3]
            }
        return None

    # === Статистика ===
    def get_stats_by_category(self, user_id: int, year: int = None) -> List[Dict]:
        """Статистика по категориям за год"""
        query = """
            SELECT c.name, COALESCE(SUM(ts.duration_minutes), 0) as total_minutes
            FROM categories c
            LEFT JOIN tasks t ON t.category_id = c.id AND t.user_id = ?
            LEFT JOIN time_sessions ts ON ts.task_id = t.id
            WHERE ts.duration_minutes IS NOT NULL
        """
        params = [user_id]
        
        if year:
            query += " AND strftime('%Y', ts.end_time) = ?"
            params.append(str(year))
        
        query += " GROUP BY c.id ORDER BY total_minutes DESC"
        
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        return [
            {"category": row[0], "minutes": row[1]}
            for row in rows
        ]

    def get_detailed_stats(self, user_id: int, category: str = None, 
                          period: str = 'year') -> List[Dict]:
        """Детальная статистика"""
        query = """
            SELECT 
                strftime('%Y-%m', ts.end_time) as period,
                c.name as category,
                t.title as task,
                ts.duration_minutes
            FROM time_sessions ts
            JOIN tasks t ON ts.task_id = t.id
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = ? AND ts.duration_minutes IS NOT NULL
        """
        params = [user_id]
        
        if category:
            query += " AND c.name = ?"
            params.append(category)
        
        if period == 'today':
            query += " AND date(ts.end_time) = date('now')"
        elif period == 'month':
            query += " AND strftime('%Y-%m', ts.end_time) = strftime('%Y-%m', CURRENT_TIMESTAMP)"
        elif period == 'week':
            query += " AND strftime('%W', ts.end_time) = strftime('%W', CURRENT_TIMESTAMP)"
        
        query += " ORDER BY ts.end_time DESC LIMIT 100"
        
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        return [
            {
                "period": row[0],
                "category": row[1],
                "task": row[2],
                "minutes": row[3]
            }
            for row in rows
        ]

    def get_total_time(self, user_id: int, category_name: str = None, 
                      year: int = None) -> int:
        """Получить общее время по категории за год"""
        query = """
            SELECT COALESCE(SUM(ts.duration_minutes), 0)
            FROM time_sessions ts
            JOIN tasks t ON ts.task_id = t.id
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = ? AND ts.duration_minutes IS NOT NULL
        """
        params = [user_id]
        
        if category_name:
            query += " AND c.name = ?"
            params.append(category_name)
        
        if year:
            query += " AND strftime('%Y', ts.end_time) = ?"
            params.append(str(year))
        
        self.cursor.execute(query, params)
        return self.cursor.fetchone()[0] or 0

    # === НОВЫЕ МЕТОДЫ ДЛЯ УВЕДОМЛЕНИЙ ===
    def get_tasks_with_deadline(self, user_id: int, hours: int = 24) -> List[Dict]:
        """Получить задачи с дедлайном в ближайшие N часов"""
        query = """
            SELECT id, title, deadline
            FROM tasks
            WHERE user_id = ? 
              AND status = 'active'
              AND deadline IS NOT NULL
              AND datetime(deadline) BETWEEN datetime('now') 
                  AND datetime('now', ?)
            ORDER BY deadline ASC
        """
        self.cursor.execute(query, (user_id, f'+{hours} hours'))
        rows = self.cursor.fetchall()
        return [
            {"id": row[0], "title": row[1], "deadline": row[2]}
            for row in rows
        ]

    def get_overdue_tasks(self, user_id: int) -> List[Dict]:
        """Получить просроченные задачи"""
        query = """
            SELECT id, title, deadline
            FROM tasks
            WHERE user_id = ? 
              AND status = 'active'
              AND deadline IS NOT NULL
              AND datetime(deadline) < datetime('now')
            ORDER BY deadline ASC
        """
        self.cursor.execute(query, (user_id,))
        rows = self.cursor.fetchall()
        return [
            {"id": row[0], "title": row[1], "deadline": row[2]}
            for row in rows
        ]

    def get_task_stats_for_user(self, user_id: int) -> Dict:
        """Получить статистику задач для пользователя"""
        # Всего задач
        self.cursor.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ?", 
            (user_id,)
        )
        total = self.cursor.fetchone()[0]
        
        # Активных задач
        self.cursor.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'active'",
            (user_id,)
        )
        active = self.cursor.fetchone()[0]
        
        # Выполненных сегодня
        self.cursor.execute("""
            SELECT COUNT(*) FROM tasks 
            WHERE user_id = ? 
              AND status = 'completed'
              AND date(created_at) = date('now')
        """, (user_id,))
        completed_today = self.cursor.fetchone()[0]
        
        return {
            "total": total,
            "active": active,
            "completed_today": completed_today
        }

    def close(self):
        self.connection.close()

# Singleton для использования во всём приложении
db = Database()
