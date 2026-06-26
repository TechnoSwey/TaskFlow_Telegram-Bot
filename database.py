import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from config import DATABASE_NAME, DEFAULT_CATEGORIES
import json

class Database:
    def __init__(self):
        self.connection = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self._init_tables()
        self._init_categories()
        self._init_default_achievements()

    def _init_tables(self):
        """Создание всех таблиц"""
        
        # Пользователи
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settings TEXT DEFAULT '{}',
                current_project_id INTEGER
            )
        ''')

        # Категории
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                emoji TEXT DEFAULT '📁'
            )
        ''')

        # Проекты (для общей работы)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                owner_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_archived BOOLEAN DEFAULT 0,
                FOREIGN KEY(owner_id) REFERENCES users(user_id)
            )
        ''')

        # Участники проектов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_members (
                project_id INTEGER,
                user_id INTEGER,
                role TEXT DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(project_id, user_id),
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')

        # Задачи (расширенная версия)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                project_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                category_id INTEGER,
                priority INTEGER DEFAULT 2,
                is_template BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deadline TIMESTAMP,
                status TEXT DEFAULT 'active',
                parent_task_id INTEGER,
                is_recurring BOOLEAN DEFAULT 0,
                recurring_pattern TEXT,
                estimated_time INTEGER,
                progress INTEGER DEFAULT 0,
                emoji_reaction TEXT,
                order_index INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(category_id) REFERENCES categories(id),
                FOREIGN KEY(parent_task_id) REFERENCES tasks(id)
            )
        ''')

        # Комментарии к задачам
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                user_id INTEGER,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(task_id) REFERENCES tasks(id),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
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

        # Достижения пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_achievements (
                user_id INTEGER,
                achievement_id TEXT,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                progress INTEGER DEFAULT 0,
                PRIMARY KEY(user_id, achievement_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')

        # Доступные достижения
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT,
                requirement_type TEXT,
                requirement_value INTEGER,
                reward TEXT
            )
        ''')

        # Ежедневная активность
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_activity (
                user_id INTEGER,
                date DATE,
                tasks_completed INTEGER DEFAULT 0,
                time_spent INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                PRIMARY KEY(user_id, date)
            )
        ''')

        # Прогнозы (сохраняем историю прогнозов)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_id INTEGER,
                predicted_duration INTEGER,
                actual_duration INTEGER,
                accuracy REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(task_id) REFERENCES tasks(id)
            )
        ''')

        # Интерактивные туторы (состояние прохождения)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tutorial_progress (
                user_id INTEGER,
                tutorial_id TEXT,
                step INTEGER DEFAULT 0,
                completed BOOLEAN DEFAULT 0,
                PRIMARY KEY(user_id, tutorial_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')

        self.connection.commit()

    def _init_categories(self):
        """Добавление категорий по умолчанию с эмодзи"""
        for name, emoji in DEFAULT_CATEGORIES:
            self.cursor.execute(
                "INSERT OR IGNORE INTO categories (name, emoji) VALUES (?, ?)",
                (name, emoji)
            )
        self.connection.commit()

    def _init_default_achievements(self):
        """Добавление достижений по умолчанию"""
        achievements = [
            ("first_task", "Первый шаг", "Создай первую задачу", "🌟", "tasks_created", 1, "Опыт +10"),
            ("task_master", "Мастер задач", "Создай 100 задач", "👑", "tasks_created", 100, "Опыт +100"),
            ("time_keeper", "Хранитель времени", "Потрать 100 часов на задачи", "⏰", "time_spent", 6000, "Опыт +50"),
            ("early_bird", "Ранняя пташка", "Выполни задачу до 8:00", "🌅", "early_task", 1, "Опыт +20"),
            ("night_owl", "Ночная сова", "Выполни задачу после 23:00", "🦉", "night_task", 1, "Опыт +20"),
            ("perfect_week", "Идеальная неделя", "Выполни все задачи за неделю", "🏆", "perfect_week", 1, "Опыт +200"),
            ("project_lead", "Лидер проекта", "Создай проект с 5 участниками", "🚀", "project_members", 5, "Опыт +150"),
            ("commentator", "Комментатор", "Оставь 50 комментариев", "💬", "comments", 50, "Опыт +30"),
            ("streak_7", "7 дней подряд", "Выполняй задачи 7 дней подряд", "🔥", "streak_days", 7, "Опыт +70"),
            ("streak_30", "30 дней подряд", "Выполняй задачи 30 дней подряд", "💎", "streak_days", 30, "Опыт +300"),
        ]
        for ach_id, name, desc, icon, req_type, req_value, reward in achievements:
            self.cursor.execute('''
                INSERT OR IGNORE INTO achievements (id, name, description, icon, requirement_type, requirement_value, reward)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (ach_id, name, desc, icon, req_type, req_value, reward))
        self.connection.commit()

    # ========== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ==========
    
    def register_user(self, user_id: int, username: str = None):
        self.cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        self.connection.commit()

    def get_user_settings(self, user_id: int) -> dict:
        self.cursor.execute("SELECT settings FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row:
            return json.loads(row[0])
        return {}

    def update_user_settings(self, user_id: int, settings: dict):
        self.cursor.execute(
            "UPDATE users SET settings = ? WHERE user_id = ?",
            (json.dumps(settings), user_id)
        )
        self.connection.commit()

    def get_all_users(self) -> List[int]:
        self.cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in self.cursor.fetchall()]

    # ========== РАБОТА С ПРОЕКТАМИ ==========
    
    def create_project(self, name: str, description: str, owner_id: int) -> int:
        self.cursor.execute(
            "INSERT INTO projects (name, description, owner_id) VALUES (?, ?, ?)",
            (name, description, owner_id)
        )
        self.connection.commit()
        project_id = self.cursor.lastrowid
        self.cursor.execute(
            "INSERT INTO project_members (project_id, user_id, role) VALUES (?, ?, 'admin')",
            (project_id, owner_id)
        )
        self.connection.commit()
        return project_id

    def get_user_projects(self, user_id: int) -> List[Dict]:
        query = """
            SELECT p.id, p.name, p.description, p.owner_id, p.created_at, pm.role
            FROM projects p
            JOIN project_members pm ON p.id = pm.project_id
            WHERE pm.user_id = ? AND p.is_archived = 0
            ORDER BY p.created_at DESC
        """
        self.cursor.execute(query, (user_id,))
        rows = self.cursor.fetchall()
        return [
            {"id": r[0], "name": r[1], "description": r[2], "owner_id": r[3], 
             "created_at": r[4], "role": r[5]} for r in rows
        ]

    def add_project_member(self, project_id: int, user_id: int, role: str = 'member'):
        self.cursor.execute(
            "INSERT OR IGNORE INTO project_members (project_id, user_id, role) VALUES (?, ?, ?)",
            (project_id, user_id, role)
        )
        self.connection.commit()
        self._check_achievements(user_id)

    def get_project_members(self, project_id: int) -> List[Dict]:
        query = """
            SELECT u.user_id, u.username, pm.role, pm.joined_at
            FROM project_members pm
            JOIN users u ON pm.user_id = u.user_id
            WHERE pm.project_id = ?
        """
        self.cursor.execute(query, (project_id,))
        rows = self.cursor.fetchall()
        return [
            {"user_id": r[0], "username": r[1], "role": r[2], "joined_at": r[3]}
            for r in rows
        ]

    def get_user_role(self, project_id: int, user_id: int) -> Optional[str]:
        self.cursor.execute(
            "SELECT role FROM project_members WHERE project_id = ? AND user_id = ?",
            (project_id, user_id)
        )
        row = self.cursor.fetchone()
        return row[0] if row else None

    def remove_project_member(self, project_id: int, user_id: int):
        self.cursor.execute(
            "DELETE FROM project_members WHERE project_id = ? AND user_id = ?",
            (project_id, user_id)
        )
        self.connection.commit()

    def archive_project(self, project_id: int):
        self.cursor.execute(
            "UPDATE projects SET is_archived = 1 WHERE id = ?",
            (project_id,)
        )
        self.connection.commit()

    # ========== РАБОТА С ЗАДАЧАМИ (РАСШИРЕННАЯ) ==========
    
    def create_task(self, user_id: int, title: str, category_id: int = None,
                   project_id: int = None, parent_task_id: int = None,
                   priority: int = 2, deadline: str = None, 
                   estimated_time: int = None, description: str = None,
                   is_recurring: bool = False, recurring_pattern: str = None,
                   emoji_reaction: str = None) -> int:
        self.cursor.execute('''
            INSERT INTO tasks (user_id, project_id, title, description, category_id, 
                              priority, deadline, parent_task_id, estimated_time,
                              is_recurring, recurring_pattern, emoji_reaction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, project_id, title, description, category_id,
              priority, deadline, parent_task_id, estimated_time,
              is_recurring, recurring_pattern, emoji_reaction))
        self.connection.commit()
        task_id = self.cursor.lastrowid
        
        # Обновляем статистику пользователя
        self._update_user_stats(user_id)
        
        # Проверяем достижения
        self._check_achievements(user_id)
        
        return task_id

    def get_user_tasks(self, user_id: int, status: str = 'active', 
                       project_id: int = None, priority: int = None) -> List[Dict]:
        query = """
            SELECT t.id, t.title, t.description, t.status, t.created_at, t.deadline,
                   t.priority, t.progress, t.parent_task_id, t.estimated_time,
                   t.is_recurring, t.recurring_pattern, t.emoji_reaction,
                   c.name as category_name, c.emoji as category_emoji,
                   p.name as project_name
            FROM tasks t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.user_id = ? AND t.status = ? AND t.is_template = 0
        """
        params = [user_id, status]
        
        if project_id is not None:
            query += " AND t.project_id = ?"
            params.append(project_id)
        
        if priority is not None:
            query += " AND t.priority = ?"
            params.append(priority)
        
        query += " ORDER BY t.priority DESC, t.deadline ASC, t.created_at DESC"
        
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        
        tasks = []
        for r in rows:
            task = {
                "id": r[0], "title": r[1], "description": r[2], "status": r[3],
                "created_at": r[4], "deadline": r[5], "priority": r[6],
                "progress": r[7], "parent_task_id": r[8], "estimated_time": r[9],
                "is_recurring": r[10], "recurring_pattern": r[11],
                "emoji_reaction": r[12], "category": r[13] or "Без категории",
                "category_emoji": r[14] or "📁", "project_name": r[15]
            }
            subtasks = self.get_subtasks(r[0])
            task["subtasks"] = subtasks
            task["subtasks_completed"] = sum(1 for s in subtasks if s['status'] == 'completed')
            task["total_subtasks"] = len(subtasks)
            tasks.append(task)
        
        return tasks

    def get_task(self, task_id: int) -> Optional[Dict]:
        query = """
            SELECT t.id, t.title, t.description, t.status, t.created_at, t.deadline,
                   t.priority, t.progress, t.parent_task_id, t.estimated_time,
                   t.is_recurring, t.recurring_pattern, t.emoji_reaction,
                   t.user_id, t.project_id, t.category_id
            FROM tasks t
            WHERE t.id = ?
        """
        self.cursor.execute(query, (task_id,))
        row = self.cursor.fetchone()
        if row:
            return {
                "id": row[0], "title": row[1], "description": row[2], "status": row[3],
                "created_at": row[4], "deadline": row[5], "priority": row[6],
                "progress": row[7], "parent_task_id": row[8], "estimated_time": row[9],
                "is_recurring": row[10], "recurring_pattern": row[11],
                "emoji_reaction": row[12], "user_id": row[13], "project_id": row[14],
                "category_id": row[15]
            }
        return None

    def get_subtasks(self, task_id: int) -> List[Dict]:
        query = """
            SELECT id, title, status, priority, progress, deadline
            FROM tasks
            WHERE parent_task_id = ? AND is_template = 0
            ORDER BY priority DESC, created_at ASC
        """
        self.cursor.execute(query, (task_id,))
        rows = self.cursor.fetchall()
        return [
            {"id": r[0], "title": r[1], "status": r[2], "priority": r[3], 
             "progress": r[4], "deadline": r[5]}
            for r in rows
        ]

    def update_task_status(self, task_id: int, status: str):
        self.cursor.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (status, task_id)
        )
        self.connection.commit()
        
        # Если задача выполнена, обновляем активность
        if status == 'completed':
            task = self.get_task(task_id)
            if task:
                self._update_daily_activity(task['user_id'], task_id)
                self._update_user_stats(task['user_id'])
                self._check_achievements(task['user_id'])
                self._check_subtasks_completion(task_id)

    def update_task_progress(self, task_id: int, progress: int):
        self.cursor.execute(
            "UPDATE tasks SET progress = ? WHERE id = ?",
            (min(100, max(0, progress)), task_id)
        )
        self.connection.commit()
        self._check_subtasks_completion(task_id)

    def update_task_emoji(self, task_id: int, emoji: str):
        self.cursor.execute(
            "UPDATE tasks SET emoji_reaction = ? WHERE id = ?",
            (emoji, task_id)
        )
        self.connection.commit()

    def _check_subtasks_completion(self, task_id: int):
        self.cursor.execute(
            "SELECT parent_task_id FROM tasks WHERE id = ?", (task_id,)
        )
        row = self.cursor.fetchone()
        if row and row[0]:
            parent_id = row[0]
            subtasks = self.get_subtasks(parent_id)
            completed = sum(1 for s in subtasks if s['status'] == 'completed')
            total = len(subtasks)
            if total > 0:
                progress = int((completed / total) * 100)
                if progress == 100:
                    self.update_task_status(parent_id, 'completed')
                self.cursor.execute(
                    "UPDATE tasks SET progress = ? WHERE id = ?",
                    (progress, parent_id)
                )
                self.connection.commit()

    def delete_task(self, task_id: int):
        self.cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.connection.commit()

    def get_tasks_with_deadline(self, user_id: int, hours: int = 24) -> List[Dict]:
        query = """
            SELECT id, title, deadline, priority
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
            {"id": r[0], "title": r[1], "deadline": r[2], "priority": r[3]}
            for r in rows
        ]

    def get_overdue_tasks(self, user_id: int) -> List[Dict]:
        query = """
            SELECT id, title, deadline, priority
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
            {"id": r[0], "title": r[1], "deadline": r[2], "priority": r[3]}
            for r in rows
        ]

    def get_tasks_by_priority(self, user_id: int) -> Dict[int, int]:
        self.cursor.execute("""
            SELECT priority, COUNT(*) 
            FROM tasks 
            WHERE user_id = ? AND status = 'active'
            GROUP BY priority
        """, (user_id,))
        rows = self.cursor.fetchall()
        return {r[0]: r[1] for r in rows}

    # ========== ПОВТОРЯЮЩИЕСЯ ЗАДАЧИ ==========
    
    def create_recurring_instances(self):
        """Создаёт новые экземпляры повторяющихся задач"""
        now = datetime.now()
        self.cursor.execute("""
            SELECT id, user_id, title, category_id, priority, recurring_pattern,
                   estimated_time, project_id, description
            FROM tasks
            WHERE is_recurring = 1 AND status != 'archived'
        """)
        tasks = self.cursor.fetchall()
        
        for task in tasks:
            task_id, user_id, title, category_id, priority, pattern, estimated, project_id, desc = task
            
            # Проверяем, нужно ли создать новую задачу
            if pattern == 'daily':
                self._create_recurring_instance(task_id, user_id, title, category_id, 
                                               priority, estimated, project_id, desc, 1)
            elif pattern == 'weekly':
                self._create_recurring_instance(task_id, user_id, title, category_id,
                                               priority, estimated, project_id, desc, 7)
            elif pattern == 'monthly':
                self._create_recurring_instance(task_id, user_id, title, category_id,
                                               priority, estimated, project_id, desc, 30)

    def _create_recurring_instance(self, original_id, user_id, title, category_id,
                                   priority, estimated, project_id, desc, days_offset):
        deadline = (datetime.now() + timedelta(days=days_offset)).strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('''
            INSERT INTO tasks (user_id, title, category_id, priority, 
                              deadline, estimated_time, project_id, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, title, category_id, priority, deadline, estimated, project_id, desc))
        self.connection.commit()

    # ========== КОММЕНТАРИИ ==========
    
    def add_comment(self, task_id: int, user_id: int, comment: str):
        self.cursor.execute(
            "INSERT INTO task_comments (task_id, user_id, comment) VALUES (?, ?, ?)",
            (task_id, user_id, comment)
        )
        self.connection.commit()
        self._check_achievements(user_id)

    def get_task_comments(self, task_id: int) -> List[Dict]:
        query = """
            SELECT tc.id, tc.comment, tc.created_at, u.username
            FROM task_comments tc
            JOIN users u ON tc.user_id = u.user_id
            WHERE tc.task_id = ?
            ORDER BY tc.created_at DESC
        """
        self.cursor.execute(query, (task_id,))
        rows = self.cursor.fetchall()
        return [
            {"id": r[0], "comment": r[1], "created_at": r[2], "username": r[3] or "Пользователь"}
            for r in rows
        ]

    def get_comment_count(self, user_id: int) -> int:
        self.cursor.execute(
            "SELECT COUNT(*) FROM task_comments WHERE user_id = ?",
            (user_id,)
        )
        return self.cursor.fetchone()[0]

    # ========== ВРЕМЕННЫЕ СЕССИИ ==========
    
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

    def get_total_time_spent(self, user_id: int) -> int:
        self.cursor.execute("""
            SELECT COALESCE(SUM(duration_minutes), 0)
            FROM time_sessions ts
            JOIN tasks t ON ts.task_id = t.id
            WHERE t.user_id = ?
        """, (user_id,))
        return self.cursor.fetchone()[0] or 0

    def get_tasks_by_completion_time(self, user_id: int) -> List[Dict]:
        """Получить задачи с их временем выполнения для прогнозов"""
        self.cursor.execute("""
            SELECT t.id, t.title, t.estimated_time, 
                   COALESCE(AVG(ts.duration_minutes), t.estimated_time) as avg_time,
                   COUNT(ts.id) as session_count
            FROM tasks t
            LEFT JOIN time_sessions ts ON t.id = ts.task_id
            WHERE t.user_id = ? AND t.status = 'completed'
            GROUP BY t.id
            HAVING session_count > 0
        """, (user_id,))
        rows = self.cursor.fetchall()
        return [
            {"id": r[0], "title": r[1], "estimated": r[2], "avg_time": r[3], "count": r[4]}
            for r in rows
        ]

    # ========== СТАТИСТИКА И АНАЛИТИКА ==========
    
    def get_stats_by_category(self, user_id: int, year: int = None) -> List[Dict]:
        query = """
            SELECT c.name, c.emoji, COALESCE(SUM(ts.duration_minutes), 0) as total_minutes
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
            {"category": r[0] or "Без категории", "emoji": r[1] or "📁", "minutes": r[2]}
            for r in rows
        ]

    def get_detailed_stats(self, user_id: int, category: str = None, 
                          period: str = 'year') -> List[Dict]:
        query = """
            SELECT 
                strftime('%Y-%m', ts.end_time) as period,
                c.name as category,
                t.title as task,
                ts.duration_minutes,
                t.priority
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
        elif period == 'week':
            query += " AND strftime('%W', ts.end_time) = strftime('%W', CURRENT_TIMESTAMP)"
        elif period == 'month':
            query += " AND strftime('%Y-%m', ts.end_time) = strftime('%Y-%m', CURRENT_TIMESTAMP)"
        
        query += " ORDER BY ts.end_time DESC LIMIT 100"
        
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        return [
            {
                "period": r[0],
                "category": r[1] or "Без категории",
                "task": r[2],
                "minutes": r[3],
                "priority": r[4]
            }
            for r in rows
        ]

    def get_daily_activity(self, user_id: int, days: int = 30) -> List[Dict]:
        query = """
            SELECT date, tasks_completed, time_spent
            FROM daily_activity
            WHERE user_id = ? 
              AND date >= date('now', ?)
            ORDER BY date DESC
        """
        self.cursor.execute(query, (user_id, f'-{days} days'))
        rows = self.cursor.fetchall()
        return [
            {"date": r[0], "tasks": r[1], "time": r[2]}
            for r in rows
        ]

    def get_top_tasks(self, user_id: int, limit: int = 10) -> List[Dict]:
        query = """
            SELECT t.title, c.name as category, 
                   COALESCE(SUM(ts.duration_minutes), 0) as total_time
            FROM tasks t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN time_sessions ts ON t.id = ts.task_id
            WHERE t.user_id = ? AND ts.duration_minutes IS NOT NULL
            GROUP BY t.id
            ORDER BY total_time DESC
            LIMIT ?
        """
        self.cursor.execute(query, (user_id, limit))
        rows = self.cursor.fetchall()
        return [
            {"title": r[0], "category": r[1] or "Без категории", "time": r[2]}
            for r in rows
        ]

    def get_weekly_summary(self, user_id: int) -> Dict:
        query = """
            SELECT 
                COUNT(DISTINCT date) as active_days,
                SUM(tasks_completed) as completed,
                SUM(time_spent) as total_time
            FROM daily_activity
            WHERE user_id = ? 
              AND date >= date('now', '-7 days')
        """
        self.cursor.execute(query, (user_id,))
        row = self.cursor.fetchone()
        return {
            "active_days": row[0] or 0,
            "completed": row[1] or 0,
            "total_time": row[2] or 0
        }

    def get_monthly_summary(self, user_id: int) -> Dict:
        query = """
            SELECT 
                COUNT(DISTINCT date) as active_days,
                SUM(tasks_completed) as completed,
                SUM(time_spent) as total_time
            FROM daily_activity
            WHERE user_id = ? 
              AND strftime('%Y-%m', date) = strftime('%Y-%m', CURRENT_TIMESTAMP)
        """
        self.cursor.execute(query, (user_id,))
        row = self.cursor.fetchone()
        return {
            "active_days": row[0] or 0,
            "completed": row[1] or 0,
            "total_time": row[2] or 0
        }

    def get_productivity_trend(self, user_id: int, days: int = 30) -> List[Dict]:
        query = """
            SELECT date, tasks_completed
            FROM daily_activity
            WHERE user_id = ? 
              AND date >= date('now', ?)
            ORDER BY date ASC
        """
        self.cursor.execute(query, (user_id, f'-{days} days'))
        rows = self.cursor.fetchall()
        return [
            {"date": r[0], "completed": r[1]}
            for r in rows
        ]

    # ========== ПРОГНОЗЫ ==========
    
    def predict_task_duration(self, user_id: int, task_title: str) -> Optional[int]:
        """Предсказывает время выполнения задачи на основе истории"""
        self.cursor.execute("""
            SELECT AVG(ts.duration_minutes) as avg_time
            FROM tasks t
            JOIN time_sessions ts ON t.id = ts.task_id
            WHERE t.user_id = ? 
              AND t.title LIKE ?
              AND ts.duration_minutes IS NOT NULL
            GROUP BY t.id
            ORDER BY COUNT(ts.id) DESC
            LIMIT 1
        """, (user_id, f'%{task_title}%'))
        row = self.cursor.fetchone()
        return int(row[0]) if row and row[0] else None

    def save_prediction(self, user_id: int, task_id: int, predicted: int, actual: int):
        accuracy = 1 - abs(predicted - actual) / predicted if predicted > 0 else 0
        self.cursor.execute("""
            INSERT INTO predictions (user_id, task_id, predicted_duration, actual_duration, accuracy)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, task_id, predicted, actual, accuracy))
        self.connection.commit()

    # ========== ДОСТИЖЕНИЯ ==========
    
    def _check_achievements(self, user_id: int):
        """Проверяет и разблокирует достижения пользователя"""
        stats = self._get_user_stats(user_id)
        
        self.cursor.execute(
            "SELECT id, requirement_type, requirement_value FROM achievements"
        )
        achievements = self.cursor.fetchall()
        
        for ach_id, req_type, req_value in achievements:
            # Проверяем, не разблокировано ли уже
            self.cursor.execute(
                "SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_id = ?",
                (user_id, ach_id)
            )
            if self.cursor.fetchone():
                continue
            
            # Проверяем условие
            unlocked = False
            if req_type == 'tasks_created':
                unlocked = stats.get('tasks_created', 0) >= req_value
            elif req_type == 'time_spent':
                unlocked = stats.get('time_spent', 0) >= req_value
            elif req_type == 'early_task':
                unlocked = stats.get('early_tasks', 0) >= req_value
            elif req_type == 'night_task':
                unlocked = stats.get('night_tasks', 0) >= req_value
            elif req_type == 'perfect_week':
                unlocked = stats.get('perfect_weeks', 0) >= req_value
            elif req_type == 'project_members':
                unlocked = stats.get('project_members', 0) >= req_value
            elif req_type == 'comments':
                unlocked = self.get_comment_count(user_id) >= req_value
            elif req_type == 'streak_days':
                unlocked = stats.get('streak_days', 0) >= req_value
            
            if unlocked:
                self.cursor.execute(
                    "INSERT INTO user_achievements (user_id, achievement_id) VALUES (?, ?)",
                    (user_id, ach_id)
                )
                self.connection.commit()

    def _get_user_stats(self, user_id: int) -> Dict:
        """Получает статистику пользователя для проверки достижений"""
        stats = {}
        
        # Количество созданных задач
        self.cursor.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ?",
            (user_id,)
        )
        stats['tasks_created'] = self.cursor.fetchone()[0]
        
        # Общее время
        stats['time_spent'] = self.get_total_time_spent(user_id)
        
        # Ранние задачи (до 8:00)
        self.cursor.execute("""
            SELECT COUNT(*) FROM time_sessions ts
            JOIN tasks t ON ts.task_id = t.id
            WHERE t.user_id = ? AND strftime('%H', ts.start_time) < '08'
        """, (user_id,))
        stats['early_tasks'] = self.cursor.fetchone()[0]
        
        # Ночные задачи (после 23:00)
        self.cursor.execute("""
            SELECT COUNT(*) FROM time_sessions ts
            JOIN tasks t ON ts.task_id = t.id
            WHERE t.user_id = ? AND strftime('%H', ts.start_time) > '23'
        """, (user_id,))
        stats['night_tasks'] = self.cursor.fetchone()[0]
        
        # Идеальные недели
        self.cursor.execute("""
            SELECT COUNT(DISTINCT strftime('%W', date)) 
            FROM daily_activity
            WHERE user_id = ? AND tasks_completed > 0
        """, (user_id,))
        stats['perfect_weeks'] = self.cursor.fetchone()[0]
        
        # Участники проектов
        self.cursor.execute("""
            SELECT COUNT(DISTINCT user_id) FROM project_members
            WHERE project_id IN (
                SELECT project_id FROM project_members WHERE user_id = ?
            )
        """, (user_id,))
        stats['project_members'] = self.cursor.fetchone()[0]
        
        # Streak
        self.cursor.execute("""
            SELECT date FROM daily_activity
            WHERE user_id = ? AND tasks_completed > 0
            ORDER BY date DESC
        """, (user_id,))
        dates = [r[0] for r in self.cursor.fetchall()]
        from utils import calculate_streak
        stats['streak_days'] = calculate_streak(dates)
        
        return stats

    def get_user_achievements(self, user_id: int) -> List[Dict]:
        query = """
            SELECT a.id, a.name, a.description, a.icon, a.reward, ua.unlocked_at
            FROM user_achievements ua
            JOIN achievements a ON ua.achievement_id = a.id
            WHERE ua.user_id = ?
            ORDER BY ua.unlocked_at DESC
        """
        self.cursor.execute(query, (user_id,))
        rows = self.cursor.fetchall()
        return [
            {"id": r[0], "name": r[1], "description": r[2], "icon": r[3], 
             "reward": r[4], "unlocked_at": r[5]}
            for r in rows
        ]

    def get_all_achievements(self) -> List[Dict]:
        self.cursor.execute("""
            SELECT id, name, description, icon, requirement_type, requirement_value, reward
            FROM achievements
            ORDER BY id
        """)
        rows = self.cursor.fetchall()
        return [
            {"id": r[0], "name": r[1], "description": r[2], "icon": r[3],
             "requirement": f"{r[4]} > {r[5]}", "reward": r[6]}
            for r in rows
        ]

    # ========== ЕЖЕДНЕВНАЯ АКТИВНОСТЬ ==========
    
    def _update_daily_activity(self, user_id: int, task_id: int):
        today = datetime.now().date().isoformat()
        self.cursor.execute("""
            INSERT INTO daily_activity (user_id, date, tasks_completed, time_spent)
            VALUES (?, ?, 1, 
                COALESCE((SELECT duration_minutes FROM time_sessions 
                         WHERE task_id = ? ORDER BY end_time DESC LIMIT 1), 0)
            )
            ON CONFLICT(user_id, date) DO UPDATE SET
                tasks_completed = tasks_completed + 1,
                time_spent = time_spent + 
                    COALESCE((SELECT duration_minutes FROM time_sessions 
                             WHERE task_id = ? ORDER BY end_time DESC LIMIT 1), 0)
        """, (user_id, today, task_id, task_id))
        self.connection.commit()

    def _update_user_stats(self, user_id: int):
        """Обновляет статистику пользователя"""
        # Обновляем daily_activity для сегодняшнего дня
        today = datetime.now().date().isoformat()
        
        # Получаем сегодняшние завершённые задачи
        self.cursor.execute("""
            SELECT COUNT(*), COALESCE(SUM(ts.duration_minutes), 0)
            FROM tasks t
            JOIN time_sessions ts ON t.id = ts.task_id
            WHERE t.user_id = ? 
              AND date(t.created_at) = date('now')
              AND t.status = 'completed'
        """, (user_id,))
        completed, time_spent = self.cursor.fetchone()
        
        # Обновляем или вставляем запись
        self.cursor.execute("""
            INSERT INTO daily_activity (user_id, date, tasks_completed, time_spent)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET
                tasks_completed = ?,
                time_spent = ?
        """, (user_id, today, completed or 0, time_spent or 0, completed or 0, time_spent or 0))
        self.connection.commit()

    # ========== ИНТЕРАКТИВНЫЕ ТУТОРЫ ==========
    
    def get_tutorial_progress(self, user_id: int, tutorial_id: str) -> Dict:
        self.cursor.execute(
            "SELECT step, completed FROM tutorial_progress WHERE user_id = ? AND tutorial_id = ?",
            (user_id, tutorial_id)
        )
        row = self.cursor.fetchone()
        if row:
            return {"step": row[0], "completed": bool(row[1])}
        return {"step": 0, "completed": False}

    def update_tutorial_progress(self, user_id: int, tutorial_id: str, step: int = None, completed: bool = False):
        if step is not None:
            self.cursor.execute("""
                INSERT INTO tutorial_progress (user_id, tutorial_id, step, completed)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, tutorial_id) DO UPDATE SET
                    step = ?,
                    completed = ?
            """, (user_id, tutorial_id, step, completed, step, completed))
        else:
            self.cursor.execute("""
                INSERT INTO tutorial_progress (user_id, tutorial_id, completed)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, tutorial_id) DO UPDATE SET
                    completed = ?
            """, (user_id, tutorial_id, completed, completed))
        self.connection.commit()

    def get_tutorial_completed(self, user_id: int, tutorial_id: str) -> bool:
        self.cursor.execute(
            "SELECT completed FROM tutorial_progress WHERE user_id = ? AND tutorial_id = ?",
            (user_id, tutorial_id)
        )
        row = self.cursor.fetchone()
        return bool(row[0]) if row else False

    # ========== ЭКСПОРТ СТАТИСТИКИ ==========
    
    def export_stats_csv(self, user_id: int) -> str:
        """Экспортирует статистику в CSV формат"""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow(["Категория", "Время (мин)", "Задач выполнено"])
        
        # Данные по категориям
        stats = self.get_stats_by_category(user_id)
        for stat in stats:
            if stat['minutes'] > 0:
                writer.writerow([stat['category'], stat['minutes'], 0])
        
        # Дневная активность
        writer.writerow([])
        writer.writerow(["Дата", "Задач выполнено", "Время (мин)"])
        activity = self.get_daily_activity(user_id, 30)
        for day in activity:
            writer.writerow([day['date'], day['tasks'], day['time']])
        
        return output.getvalue()

    def close(self):
        self.connection.close()

# Singleton для использования во всём приложении
db = Database()
