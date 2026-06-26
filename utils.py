from datetime import datetime, timedelta
import json
import csv
from io import StringIO

def format_duration(minutes: int) -> str:
    """Форматирует минуты в удобочитаемый вид"""
    if minutes < 0:
        return "0 мин"
    if minutes < 60:
        return f"{int(minutes)} мин"
    
    hours = minutes // 60
    mins = minutes % 60
    
    if hours < 24:
        return f"{int(hours)} ч {int(mins)} мин"
    
    days = hours // 24
    hours = hours % 24
    return f"{int(days)} д {int(hours)} ч {int(mins)} мин"

def parse_duration(text: str) -> Optional[int]:
    """Парсит строку времени в минуты"""
    import re
    patterns = [
        (r'(\d+)\s*д', 1440),
        (r'(\d+)\s*ч', 60),
        (r'(\d+)\s*м', 1),
    ]
    total = 0
    for pattern, multiplier in patterns:
        match = re.search(pattern, text.lower())
        if match:
            total += int(match.group(1)) * multiplier
    return total if total > 0 else None

def get_years_list() -> list:
    """Возвращает список годов от 2020 до текущего"""
    current_year = datetime.now().year
    return list(range(current_year, 2019, -1))

def format_time(time_str: str) -> str:
    """Форматирует время из ISO строки"""
    try:
        dt = datetime.fromisoformat(time_str)
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return time_str

def get_week_start() -> str:
    """Возвращает начало недели"""
    now = datetime.now()
    start = now - timedelta(days=now.weekday())
    return start.strftime("%Y-%m-%d")

def get_month_start() -> str:
    """Возвращает начало месяца"""
    now = datetime.now()
    return now.replace(day=1).strftime("%Y-%m-%d")

def get_priority_emoji(priority: int) -> str:
    """Возвращает эмодзи для приоритета"""
    emojis = {
        3: "🔴",  # Высокий
        2: "🟡",  # Средний
        1: "🟢",  # Низкий
        0: "⚪"   # Без приоритета
    }
    return emojis.get(priority, "⚪")

def get_priority_name(priority: int) -> str:
    """Возвращает название приоритета"""
    names = {
        3: "Высокий",
        2: "Средний",
        1: "Низкий",
        0: "Не указан"
    }
    return names.get(priority, "Не указан")

def export_to_csv(data: List[Dict], headers: List[str]) -> str:
    """Экспортирует данные в CSV строку"""
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()

def calculate_streak(dates: List[str]) -> int:
    """Рассчитывает текущую серию дней (streak)"""
    if not dates:
        return 0
    
    sorted_dates = sorted(set(dates), reverse=True)
    today = datetime.now().date()
    streak = 0
    
    for date_str in sorted_dates:
        try:
            date_obj = datetime.fromisoformat(date_str).date()
            if (today - date_obj).days == streak:
                streak += 1
            else:
                break
        except:
            continue
    
    return streak

def get_week_number(date_str: str) -> int:
    """Возвращает номер недели для даты"""
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.isocalendar()[1]
    except:
        return 0
