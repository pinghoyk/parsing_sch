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

def day_commads(message, tomorrow = None):  # команда для получения расписания на указанный день
    bot.delete_message(message.chat.id, message.message_id)
    user_id = message.chat.id

    user = SQL_request("SELECT * FROM users WHERE id = ?", (int(user_id),))

    if user[4] == None: 
        bot.edit_message_text(chat_id=message.chat.id, message_id=user[1], text="Сначала выберите корпус!", reply_markup=keyboard_complex)
    elif user[2] == None:
        courses = parser.table_courses(COMPLEX_LINKS[user[4]])
        keyboard = keyboard_courses(courses)
        bot.edit_message_text(chat_id=message.chat.id, message_id=user[1], text="Сначала выберите группу!", reply_markup=keyboard)
    else: 
        bot.edit_message_text(chat_id=message.chat.id, message_id=user[1], text="Загрузка расписания...")

        complex_choice = user[4]
        group = user[2]
        day = now_day(tomorrow) 
        if group.split(":")[0] == "teacher":
            try:
                text = get_day_teacher(complex_choice, group.split(":")[1], day)
                text = markup_text(text, is_teacher_format=True)
                bot.edit_message_text(chat_id=message.chat.id, message_id=user[1], text=text, reply_markup=keyboard_day_back, parse_mode="MarkdownV2")
            except Exception as e:
                print(f"Ошибка: {e}")
                bot.edit_message_text(chat_id=message.chat.id, message_id=user[1], text="Расписание не найдено", reply_markup=keyboard_day_back)
        else:
            schedule = get_day_schedule(complex_choice, group, day)
        
            if schedule != "Не удалось получить расписание":
                  text = markup_text(schedule)
                  bot.edit_message_text(chat_id=message.chat.id, message_id=user[1], text=text, reply_markup=keyboard_day_back, parse_mode="MarkdownV2")
            else:
                  bot.edit_message_text(chat_id=message.chat.id, message_id=user[1], text=schedule, reply_markup=keyboard_day_back)


def save_teacher_schedule(x):  # сохранение данных для преподавателей
    teacher_schedule = parser.get_teacher_schedule(COMPLEX_LINKS[x])
    
    # Получаем текущее время
    current_time = datetime.now()
    
    # Форматируем данные для записи в файл
    file_content = f"Обновлено: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n{teacher_schedule}"
    
    # Сохраняем данные в файл с именем x.txt
    with open(f"{SCRIPT_DIR}/{x}.txt", "w", encoding="utf-8") as file:
        file.write(file_content)
    
    print(f"Расписание для {x} сохранено.")


def check_and_update_schedule(x):  # проверка, нужно ли обновлять расписание
    file_name = f"{x}.txt"
    
    # Проверяем, существует ли файл
    if os.path.exists(f"{SCRIPT_DIR}/{file_name}"):
        with open(f"{SCRIPT_DIR}/{file_name}", "r", encoding="utf-8") as file:
            first_line = file.readline().strip()
            if first_line.startswith("Обновлено:"):
                last_update_time_str = first_line.split(": ")[1]
                last_update_time = datetime.strptime(last_update_time_str, '%Y-%m-%d %H:%M:%S')
                
                # Проверяем, прошло ли 6 часов с последнего обновления
                if (datetime.now() - last_update_time).total_seconds() < 6 * 3600:
                    print("Данные уже обновлены в течение последних 6 часов.")
                    return  # Обновление не требуется
    
    # Если файл не существует или прошло больше 6 часов, обновляем данные
    save_teacher_schedule(x)


def get_week_teacher(complex_choice, teacher):  # получение расписания, для выбранного преподавателя из большого списка
    with open(f"{SCRIPT_DIR}/{complex_choice}.txt", "r", encoding="utf-8") as file:
        lines = file.readlines()
        data = lines[1:]
    data_text = ''.join(data)
    
    data_dict = json.loads(data_text.replace("'", "\""))
    x = (data_dict[teacher])
    return x


def get_day_teacher(complex_choice, teacher, selected_day):  # получение расписания на день
    schedule_week = get_week_teacher(complex_choice, teacher)

    day_schedule = {}
    for key in schedule_week.keys():
        if selected_day.lower() in key.lower():
            day_schedule[key] = schedule_week[key]

    return day_schedule


def send_week_schedule(chat_id, message_id, user_id, is_button_click=False):    # отправка расписания на неделю
    user_id = chat_id

    user = SQL_request("SELECT * FROM users WHERE id = ?", (int(user_id),))
    bot.edit_message_text(chat_id=chat_id, message_id=user[1], text="Загрузка расписания...")

    if user[4] == None: 
        bot.edit_message_text(chat_id=chat_id, message_id=user[1], text="Сначала выберите корпус!", reply_markup=keyboard_complex)
    if user[4] == None: 
        bot.edit_message_text(chat_id=chat_id, message_id=user[1], text="Сначала выберите корпус!", reply_markup=keyboard_complex)
    elif user[2] == None:
        courses = parser.table_courses(COMPLEX_LINKS[user[4]])
        keyboard = keyboard_courses(courses)
        bot.edit_message_text(chat_id=chat_id, message_id=user[1], text="Сначала выберите группу!", reply_markup=keyboard)
    else: 
        user = SQL_request("SELECT * FROM users WHERE id = ?", (int(user_id),)) 
        complex_choice = user[4]
        group = user[2]
    
        if group.split(":")[0] == "teacher":
            try:
                text = get_week_teacher(complex_choice, group.split(":")[1])
                text = markup_text(text, is_teacher_format=True)
                bot.edit_message_text(chat_id=chat_id, message_id=user[1], text=text, reply_markup=keyboard_week, parse_mode="MarkdownV2")
            except Exception as e:
                print(f"Ошибка: {e}")
                bot.edit_message_text(chat_id=chat_id, message_id=user[1], text="Расписание не найдено", reply_markup=keyboard_week)
        else:
            weekly_schedule = get_week_schedule(complex_choice, group)
            if weekly_schedule:
                text = markup_text(weekly_schedule)
                bot.edit_message_text(chat_id=chat_id, message_id=user[1], text=text, reply_markup=keyboard_week, parse_mode="MarkdownV2")
            else:
                bot.edit_message_text(chat_id=chat_id, message_id=user[1], text="Не удалось получить расписание", reply_markup=keyboard_week)


def get_latest_release_text(repo_url):  # получение описание последнего обновления
    if 'github.com' not in repo_url:
        raise ValueError("Укажите корректный URL репозитория GitHub")

    parts = repo_url.split('/')
    if len(parts) < 5:
        raise ValueError("Укажите полный URL репозитория, например: https://github.com/user/repo")

    repo_name = f"{parts[3]}/{parts[4]}"
    api_url = f"https://api.github.com/repos/{repo_name}/releases/latest"
    response = requests.get(api_url)
    if response.status_code == 200:
        release_data = response.json()
        return release_data.get('body', 'Нет описания для последнего релиза')
    else:
        raise Exception(f"Ошибка при получении данных: {response.status_code} - {response.text}")


def mini_notification(text, all_user=None, show=False):  # отправка мини уведомлений
    if all_user == None:
        conn = sqlite3.connect(f'{SCRIPT_DIR}/{DB_NAME}')
        cursor = conn.cursor()
        cursor.execute("SELECT last_call FROM users")
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        for call_id in users:
            try:
                bot.answer_callback_query(callback_query_id=call_id, show_alert=show, text=text)
            except: pass
    else:
        bot.answer_callback_query(callback_query_id=all_user, show_alert=show, text=text)
    

def format_markdown_for_telegram(text):  # форматирует текст с Markdown-разметкой для корректного отображения в Telegram
    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)\*', r'_\1_', text)  # Форматируем курсив *text* -> _text_
    text = re.sub(r'(?m)^#{1,6}\s*(.+)', r'*\1*', text)  # Преобразуем заголовки (#) в жирный текст
    text = re.sub(r'(?m)^\s*-\s+', '• ', text)  # Преобразуем "-" в "•"
    text = re.sub(r'(?m)^\s*\*\s+', '• ', text)  # Преобразуем "*" в "•"
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)  # Форматируем выделение текста **text** -> *text* (жирный)
    text = re.sub(r'[ \t]+', ' ', text)  # Убираем дублирующиеся пробелы, оставляя один
    return text