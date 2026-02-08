from aiogram import Bot, types
from datetime import datetime
from dotenv import load_dotenv
from types import NoneType
import sqlite3
import logging
import json
import os

logger = logging.getLogger(__name__)
load_dotenv()

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

bot = Bot(token = os.environ.get("API_TOKEN"))

db = sqlite3.connect("user_data.db", detect_types = sqlite3.PARSE_DECLTYPES)
cur = db.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS authorized (
        userID       INTEGER,
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
        classIDs     JSON,
        testsIDs     JSON,
        timeCompl    INTEGER,
        creationDate DATE,
        name         STRING,
        teacherID    INTEGER
)""")

db.commit()

async def error_occured(data, reason, where = "unstated", *args):
    message: types.Message
    user_id: int
    if type(data) == types.Message:
        message = data
        user_id = data.from_user.id

    elif type(data) == types.CallbackQuery:
        message = data.message
        user_id = data.from_user.id

    elif type(data) == types.Update:
        if type(data.message) != NoneType:
            message = data.message
            user_id = data.message.from_user.id
        elif type(data.callback_query) != NoneType:
            message = data.callback_query.message
            user_id = data.callback_query.from_user.id

    if reason[0] == "l": # Login ...
        fetch = cur.execute(
            "SELECT authorizedAs FROM authorized WHERE userID == ?",
            [user_id]
        ).fetchall()
        if (0,) in fetch and (1,) in fetch:
            is_both = True
        else:
            is_both = False

        if reason[1] == "t": # Teacher only access
            if not is_both:
                logger.warning(f"User {user_id} gained access for"+
                    f" entering function {where} for teacher.")
            await message.reply("К сожалению, чтобы зайти в этот раздел Вам"+
                " нужен аккаунт учителя.")
        elif reason[1] == "s": # Student only access
            if not is_both:
                logger.warning(f"User {user_id} gained access for"+
                    f" entering function {where} for student.")
            await message.reply("К сожалению, чтобы зайти в этот раздел Вам"+
                " нужен аккаунт ученика.")
        elif reason[1] == "n": # Not registered
            await message.reply("Вы ещё не зарегистрированы в системе.\n"+
                "Обратитесь к администратору.")
    if reason[0] == "w": # Warn user ...
        if reason[1] == "u": # Data unavaliable
            kb = [[types.InlineKeyboardButton(text = "Вернуться",
                callback_data = "menu_callback_redirect")]]
            keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
            await message.reply("Не удалось загрузить данные.",
                reply_markup = keyboard)
        elif reason[1] == "i": # Wrong user input
            await message.reply("Неверный формат сообщения.")

    if reason[0] == "e": # Error
        logger.warning(f"User {user_id} invoked error in {where}.")
        await data.reply("Неожиданная ошибка. Администраторы уведомлены об"+
            " ошибке и скоро её исправят.")
        raise "Error occured in "+where+" with data "+str(args)
