import ast
import json
import requests
import os
import re
from datetime import datetime, timedelta
import sqlite3
import threading
import pytz


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = 'database.db'
DB_PATH = f"{SCRIPT_DIR}/{DB_NAME}"
YEAR = 25

COMPLEX_LINKS = {
"Российская 23": "https://pronew.chenk.ru/blocks/manage_groups/website/list.php?id=3",
"Блюхера 91": "https://pronew.chenk.ru/blocks/manage_groups/website/list.php?id=1"
}

DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
LOG = "Логи: "


# ПРОВЕРКИ
if os.path.exists(DB_PATH):
    print(f'{LOG}бд есть!')
else:
    connect = sqlite3.connect(DB_PATH)
    cursor = connect.cursor()
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER,
            message INTEGER, 
            groups TEXT,
            time_registration TIME,
            complex TEXT,
            username TEXT,
            last_call INTEGER
        )
    """)
    connect.commit()
    connect.close()
    print(f"{LOG}бд создана")


# ФУНКЦИИ
def SQL_request(request, params=()):  # sql запросы
    connect = sqlite3.connect(DB_PATH)
    cursor = connect.cursor()
    if request.strip().lower().startswith('select'):
        cursor.execute(request, params)
        result = cursor.fetchone()
        return result
    else:
        cursor.execute(request, params)
        connect.commit()
    connect.close()


def now_time():  # функция получения текущего времени по мск
    now = datetime.now()
    tz = pytz.timezone('Europe/Moscow')
    now_moscow = now.astimezone(tz)
    current_time = now_moscow.strftime("%H:%M")
    current_date = now_moscow.strftime("%m.%d.%Y")
    date = f"{current_date} {current_time}"
    return date


def now_day(day = None):
    today = datetime.today().weekday()
    if day == "tomorrow": 
        today += 1
    if today >= 6:
        today = 0
    return DAYS[today]


def markup_text(schedule, is_teacher_format=False):  # Добавление markdown символов
    # Сортируем расписание по порядку дней недели
    sorted_schedule = sorted(schedule.items(), key=lambda x: DAYS.index(x[0].split(", ")[-1]))

    result = []
    for key, lessons in sorted_schedule:
        result.append(f"*{key}*\n————————————————")
        
        # Сортируем уроки по времени начала, пропуская невалидные значения
        lessons.sort(key=lambda lesson: (
            int(lesson['time_start'].replace('.', '').replace(':', '')) if lesson['time_start'] != '???' else float('inf')
        ))

        for i, lesson in enumerate(lessons, start=1):
            time_start = lesson['time_start']
            time_finish = lesson['time_finish']
            lesson_info = f"\n{i}.  _{time_start} - {time_finish}_\n"

            if is_teacher_format:
                group = lesson['group']
                lesson_name = lesson['lesson_name']
                classroom = lesson['classroom'] if lesson['classroom'] else ''
                lesson_info += f"*Предмет*: {lesson_name}\n_*Группа:* {group}_  *{classroom}*\n"
            else:
                for l in lesson['lessons']:
                    lesson_info += f"*Предмет: *{l['name']}\n"
                    for data in l["data"]:
                        teacher_name = f"*Преподаватель: * {data['teacher']}".replace("отмена", "").strip()
                        lesson_info += f"_{teacher_name}_  *{data['classroom']}*\n"

            result.append(lesson_info)

        result.append("\n\n")

    result = ''.join(result)  # Объединяем список в строку
    result = tg_markdown(result)  # Применяем функцию для обработки markdown в Telegram
    result = result.replace("???", "**???**")  # Подсвечиваем "???", если время неизвестно
    return result


def tg_markdown(text):  # экранирование только для телеграма
    special_characters = r'[]()>#+-=|{}.!'
    escaped_text = ''
    for char in text:
        if char in special_characters:
            escaped_text += f'\\{char}'
        else:
            escaped_text += char
    return escaped_text

def registration(user_id, message_id):
    times = now_time()
    user = SQL_request("SELECT 0 FROM users WHERE id = ?", (user_id,))
    if user is None:
        SQL_request("""INSERT INTO users (id, message, time_registration)
                          VALUES (?, ?, ?)""", (user_id, message_id+1, times))
        print(f"{LOG}зарегистрирован новый пользователь")
        return False
    else:
        menu_id = SQL_request("SELECT message FROM users WHERE id = ?", (user_id,))  # получение id меню
        SQL_request("""UPDATE users SET message = ? WHERE id = ?""", (message_id+1, user_id))  # добавление id нового меню
        print(f"{LOG}пользователь уже существует")
        return menu_id


def get_week_schedule(complex_choice, user_group):  # получение расписания на неделю
    courses = parser.table_courses(COMPLEX_LINKS[complex_choice])

    year_start = int(user_group.split('-')[2])
    course = YEAR - year_start

    groups = courses.get(f'{course} курс', None)
    if not groups or user_group not in groups:
        return None

    url = groups[user_group]
    schedule_week = parser.schedule(f'https://pronew.chenk.ru/blocks/manage_groups/website/{url}')

    return schedule_week


def get_day_schedule(complex_choice, user_group, selected_day):  # получение расписания на выбранный день
    schedule_week = get_week_schedule(complex_choice, user_group)
    if schedule_week != None:
        day_schedule = {}
        for key in schedule_week.keys():
            if selected_day.lower() in key.lower():
                day_schedule[key] = schedule_week[key]
    else: day_schedule = 'Не удалось получить расписание'
    
    return day_schedule