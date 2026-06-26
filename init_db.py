from database import db

def init_database():
    print("📦 Создание структуры базы данных...")
    
    try:
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = db.cursor.fetchall()
        print(f"✅ Создано таблиц: {len(tables)}")
        
        for table in tables:
            print(f"   - {table[0]}")
        
        # Проверяем достижения
        achievements = db.get_all_achievements()
        print(f"✅ Загружено достижений: {len(achievements)}")
        
        print("✅ База данных инициализирована успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при инициализации БД: {e}")

if __name__ == "__main__":
    init_database()
