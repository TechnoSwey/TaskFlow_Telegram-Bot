from database import db

def init_database():
    """Инициализация базы данных"""
    print("📦 Создание структуры базы данных...")
    
    # База данных создаётся автоматически при инициализации Database
    # Но мы можем проверить, что все таблицы созданы
    try:
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = db.cursor.fetchall()
        print(f"✅ Создано таблиц: {len(tables)}")
        
        for table in tables:
            print(f"   - {table[0]}")
        
        print("✅ База данных инициализирована успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при инициализации БД: {e}")

if __name__ == "__main__":
    init_database()
