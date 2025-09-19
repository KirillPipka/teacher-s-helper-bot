'''
import sqlite3, json
sqlite3.register_adapter(dict, lambda x:json.dumps(x).encode('utf8'));sqlite3.register_adapter(list, lambda x:json.dumps(x).encode('utf8'));sqlite3.register_converter("JSON", lambda x:json.loads(x.decode('utf8')));db = sqlite3.connect(r"D:\\Уроки\\Python\\Чат-бот(Проба 1)\\internet\\project-for-telegram\\user_data.db", detect_types=sqlite3.PARSE_DECLTYPES);cur = db.cursor()
cur.execute("INSERT INTO classes_table VALUES (5748567108, ?, 1, '8A')", [[5748567108, 1, 2]])
'''

from aiogram import Bot, types
from datetime import datetime
from types import NoneType
import sqlite3
import logging
import json

logger = logging.getLogger(__name__)

def adapt_obj_to_JSON(obj):
    return json.dumps(obj).encode("utf8")
def convert_JSON_to_list(data):
    return json.loads(data.decode("utf8"))
def adapt_datetime_to_DATE(dat):
    return dat.strftime("%Y-%m-%d").encode("utf8")
def convert_DATE_to_str(data):
    return data.decode("utf8")
sqlite3.register_adapter(list, adapt_obj_to_JSON)
sqlite3.register_adapter(dict, adapt_obj_to_JSON)
sqlite3.register_converter("JSON", convert_JSON_to_list)
sqlite3.register_adapter(datetime, adapt_datetime_to_DATE)
sqlite3.register_converter("DATE", convert_DATE_to_str)

API_TOKEN = "7125996413:AAF68-QqouSzBH8pCLamukjVgLgmh14UtIM"

bot = Bot(token=API_TOKEN)

db = sqlite3.connect("user_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
cur = db.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS authorized (
        userID INTEGER,
        authorizedAs INTEGER
)""")
# Authorized as 0 - student, 1 - teacher

cur.execute("""CREATE TABLE IF NOT EXISTS tests_table (
        userID       INTEGER,
        testID       INTEGER,
        path         JSON,
        modif        JSON,
        creationDate DATE,
        classID      INTEGER,
        parallel     STRING,
        doneBy       JSON
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS classes_table (
        teacherID  INTEGER,
        studentsID JSON,
        classID    INTEGER,
        name       STRING
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS collections_table (
        classID      INTEGER,
        testsID      JSON,
        timeCompl    INTEGER,
        studCompl    JSON,
        creationDate DATE,
        name         STRING
)""")

async def error_occured(data, reason, where = "unstated"):
    if type(data) == types.Message:
        message: types.Message = data
        user_id: int = data.from_user.id
    elif type(data) == types.CallbackQuery:
        message: types.Message = data.message
        user_id: int = data.from_user.id
    elif type(data) == types.Update:
        if type(data.message) != NoneType:
            message: types.Message = data.message
            user_id: int = data.message.from_user.id
        elif type(data.callback_query) != NoneType:
            message: types.Message = data.callback_query.message
            user_id: int = data.callback_query.from_user.id

    fetch = cur.execute("SELECT authorizedAs FROM authorized WHERE userID == ?",
                        [user_id]).fetchall()
    if (0,) in fetch and (1,) in fetch:
        is_both = True
    else:
        is_both = False

    if reason[0] == "l": # Login ...
        if reason[1] == "t": # Teacher only access
            if not is_both:
                logger.warning(f"User {user_id} gained access for"+
                               f" entering function {where} for teacher.")
            await message.reply("К сожалению, чтобы зайти в этот раздел Вам"+
                             " нужен аккаут учителя.")
        elif reason[1] == "s": # Student only access
            if not is_both:
                logger.warning(f"User {user_id} gained access for"+
                               f" entering function {where} for student.")
            await message.reply("К сожалению, чтобы зайти в этот раздел Вам"+
                             " нужен аккаут ученика.")
        elif reason[1] == "n": # Not registered
            await message.reply("Вы ещё не зарегестрированы в системе.\n"+
                             "Обратитесь к администратору.")
    if reason[0] == "w": # Warn user ...
        if reason[1] == "u": # Data unavaliable
            kb = [[types.InlineKeyboardButton(text = "Вернуться",
                                     callback_data = "menu_callback_redirect")]]
            keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
            await message.reply("Не удалось загрузить данные.",
                             reply_markup = keyboard)
        if reason[1] == "i": # Wrong user input
            await message.reply("Неверный формат сообщения.")

    if reason[0] == "e": # Error
        logger.warning(f"User {user_id} invoked error in {where}.")
        await data.reply("Неожиданная ошибка. Администраторы уведомлены об"+
                         " ошибке и скоро её исправят.")
