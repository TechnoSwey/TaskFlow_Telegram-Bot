from datetime import datetime, timedelta

def format_duration(minutes: int) -> str:
    """Форматирует минуты в удобочитаемый вид"""
    if minutes < 60:
        return f"{int(minutes)} мин"
    
    hours = minutes // 60
    mins = minutes % 60
    
    if hours < 24:
        return f"{int(hours)} ч {int(mins)} мин"
    
    days = hours // 24
    hours = hours % 24
    return f"{int(days)} д {int(hours)} ч {int(mins)} мин"

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
