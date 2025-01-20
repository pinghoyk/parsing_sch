from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from scripts import *

with open('localization.json', 'r', encoding='utf-8') as file:
    locale = json.load(file)

# КНОПКИ
btn_return_complex = InlineKeyboardButton(text="< Назад", callback_data="back_complex")
btn_select_teachers = InlineKeyboardButton(text="Я преподаватель", callback_data='teachers_select')
btn_day = InlineKeyboardButton(text="День", callback_data="select_day")
btn_week = InlineKeyboardButton(text="Неделя", callback_data="select_week")
btn_change_group = InlineKeyboardButton(text="Изменить группу", callback_data="back_courses")
btn_return_main = InlineKeyboardButton(text="< Назад", callback_data="back_main")
days_buttons = [InlineKeyboardButton(text=day, callback_data=f"day_{day.lower()}") for day in DAYS]
btn_dayback = InlineKeyboardButton(text="< Назад", callback_data="select_day")
back = InlineKeyboardButton(text="< Назад", callback_data="back_courses")
btn_back_info = InlineKeyboardButton(text="Назад", callback_data="back_info")
btn_github = InlineKeyboardButton(text="Репозиторий на Github", url="https://github.com/pinghoyk/schedule")
btn_readme = InlineKeyboardButton(text="Описание", callback_data='readme')
btn_what_new = InlineKeyboardButton(text="Что нового?", callback_data='what_new')
btn_return_in_info = InlineKeyboardButton(text="< Назад", callback_data='back_in_info')
btn_admin = InlineKeyboardButton(text="Администратор", callback_data='admin')
btn_stat = InlineKeyboardButton(text="Статистика", callback_data='stat')
btn_bd_download = InlineKeyboardButton(text="База данных", callback_data='bd_download')
btn_restart = InlineKeyboardButton(text="Перезапустить", callback_data='back_complex')
btn_share_schedule = InlineKeyboardButton("Поделится расписанием", switch_inline_query="")

# КЛАВИАТУРЫ

keyboard_week = InlineKeyboardMarkup(row_width=2)
keyboard_week.add(btn_return_main, btn_share_schedule)

keyboard_days = InlineKeyboardMarkup(row_width=2)
keyboard_days.add(*days_buttons, btn_return_main)

keyboard_day_back = InlineKeyboardMarkup(row_width=2)
keyboard_day_back.add(btn_dayback, btn_share_schedule)

keyboard_error = InlineKeyboardMarkup()
keyboard_error.add(btn_change_group)

keyboard_info = InlineKeyboardMarkup(row_width=2)
keyboard_info.add(btn_github)
keyboard_info.add(btn_readme, btn_what_new)
keyboard_info.add(btn_return_main)

keyboard_btn_info = InlineKeyboardMarkup(row_width=2)
keyboard_btn_info.add(btn_back_info)

keyboard_return_info = InlineKeyboardMarkup()
keyboard_return_info.add(btn_return_in_info)

keyboard_admin = InlineKeyboardMarkup(row_width=2)
keyboard_admin.add(btn_stat, btn_bd_download, btn_return_main)

keyboard_restart = InlineKeyboardMarkup(row_width=2)
keyboard_restart.add(btn_restart)

def complex():
	text = locale["bot"]["complex"]
	btn_ros23 = InlineKeyboardButton(text=locale["buttons"]["ros"], callback_data="complex_Российская 23")
	btn_blux91 = InlineKeyboardButton(text=locale["buttons"]["blux"], callback_data="complex_Блюхера 91")
	keyboard = InlineKeyboardMarkup(row_width=1)
	keyboard.add(btn_ros23, btn_blux91)
	return text, keyboard