# Short name of `collection of problems` is `colProb`

from utils import cur, db, bot, error_occured
from aiogram.fsm.context import FSMContext
from aiogram import types, F, Router
from datetime import datetime
from aiogram import flags
import numpy as np
import logging

router = Router()

# Teacher functions to make collections of problems


@router.callback_query(F.data[:22] == "teacher_colprob_create")
@flags.permission("teacher")
async def teacher_colprob_create_1(callback: types.CallbackQuery,
                                   state: FSMContext) -> None | int:  # Добавить меню, как из teacher_tests_control
    fetch = np.array(cur.execute("""SELECT classID, name FROM classes_table WHERE
                teacherID == ?""", [callback.from_user.id]).fetchall(), dtype="<U21")
    additional_info = (await state.get_data())["additional_info"]
    # Checks
    if additional_info["dataFor"] != 6:
        selected = np.array([callback.data[22:]], dtype="<U21")
    else:
        selected = np.array([*additional_info["selected"]+callback.data[22:]],
                            dtype="<U21")
    if int(callback.data[22:]) != 0 and int(callback.data[22:]) not in fetch[:, 0]:
        await error_occured("e")
        callback.data = "teacher_colprob_create0"
        await teacher_colprob_class(callback, state)
        return -1
    
    # Mark selected
    select_map = np.isin(fetch[:, 0], selected)
    fetch[select_map, 1] = [i.upper()+" (ВЫБРАН)" for i in fetch[select_map, 1]]
    # Buttons
    for i in range(len(fetch)):
        kb.append([types.InlineKeyboardButton(text = fetch[i, 1],
                    callback_data = f"teacher_colprob_create{fetch[i, 0]}")])
    kb += [[types.InlineKeyboardButton(text = "Отмена",
                                       callback_data = "menu_callback_redirect")]]
    kb += [[types.InlineKeyboardButton(text = "Дальше",
                                       callback_data = "teacher_colprob_create_1")]]# Добавить клавиатуру и изменить оптимизацию
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)

    await state.update_data(additional_info = {"dataFor": 6,
                                               "selected": selected.tolist()})
    await callback.message.edit_text("Создание сборника задач.\nВыберите классы,"\
                                      " к которым будет добален сборник:",
                                     reply_markup = keyboard)

@router.callback_query(F.data == "teacher_colprob_create_1")
@flags.permission("teacher")
async def teacher_colprob_create_1_comfirm(callback: types.CallbackQuery,
                                           state: FSMContext) -> None | int:
    kb = [[types.InlineKeyboardButton(text = "Отмена",
                                      callback_data = "menu_callback_redirect")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
    msg = """Создание сборника задач.
Введите название(по умолчанию берётся дата создания):
Чтобы взять значение по умолчанию, отправьте любой символ."""
    await bot.send_message(text = msg,
                           chat_id = message.chat.id,
                           reply_markup = keyboard)


"""==============================================================================="""
async def _old_teacher_colprob_create_1(message: types.Message,
                                        state: FSMContext) -> None | int:
    additional_info = (await state.get_data())["additional_info"]
    if additional_info["dataFor"] != 5:
        return -2

    kb = [[types.InlineKeyboardButton(text = "Вернуться",
                                      callback_data = "menu_callback_redirect")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
    name = additional_info["name"]

    avalliable_class = cur.execute("""SELECT classID FROM classes_table
                                    WHERE name == ? LIMIT 1""", [name]).fetchall()
    if avalliable_class == ():
        await callback.message.edit_text("Класс с таким названием недоступен или"\
                                          " не существует\nПопробуйте другое",
                                         chat_id = message.chat.id,
                                         reply_markup = keyboard)
        return
    await state.update_data(additional_info={"dataFor": 6,
                                             "selected":additional_info["selected"],
                                             "classID": int(avalliable_class[0][0])})

    msg = """Создание сборника задач.
Введите название(по умолчанию берётся дата создания):
Чтобы взять значение по умолчанию, отправьте любой символ."""
    await bot.send_message(text = msg,
                           reply_markup = keyboard)
"""==============================================================================="""


@router.callback_query(F.data == "teacher_colprob_create_2")
@flags.permission("teacher")
async def teacher_colprob_create_2(message: types.Message,
                                   state: FSMContext) -> None | int:
    additional_info = (await state.get_data())["additional_info"]
    if additional_info["dataFor"] != 6:
        return -2

    kb = [[types.InlineKeyboardButton(text = "Отмена",
                                      callback_data = "menu_callback_redirect")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)

    # Required data
    name = additional_info["text"]
    class_id = additional_info["classID"]
    class_name = cur.execute("SELECT name FROM collections_table WHERE classID == ?",
                             [class_id]).fetchall()
    class_name = [i[0][0] for i in class_name]

    if len(name) == 1:
        name = datetime.today()
    elif len(name) > 20:
        await bot.send_message(text = "Имя слишком длинное(максимум 20 символов)\n"\
                                "Попробуйте другое",
                               chat_id = message.chat.id,
                               reply_markup = keyboard)
        return
    elif name < 5:
        await bot.send_message(text = "Имя слишком короткое(минимум 5 символов)\n"\
                                "Попробуйте другое",
                               chat_id = message.chat.id,
                               reply_markup = keyboard)
        return
    elif name in class_name:
        await bot.send_message(text = "Это имя уже используется в этом классе\n"\
                                "Попробуйте другое",
                               chat_id = message.chat.id,
                               reply_markup = keyboard)
        return
    await state.update_data(additional_info={"dataFor":  7,
                                             "selected": additional_info["selected"],
                                             "classID":  additional_info["classID"],
                                             "name":     name})
    msg = """Создание сборника задач.
Введите время выполнения(по умолчанию одна неделя), время можно указать \
в днях(Д) и неделях(Н):
Принимается формат [число]Д или [число]Н"""
    await bot.send_message(text = msg,
                           chat_id = message.chat.id,
                           reply_markup = keyboard)


async def teacher_colprob_create_3(message: types.Message,
                                   state: FSMContext) -> None | int:
    additional_info = (await state.get_data())["additional_info"]
    if additional_info["dataFor"] != 7:
        return -1

    kb = [[types.InlineKeyboardButton(text = "Отмена",###########################################
                                      callback_data = "menu_callback_redirect")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)

    # Required data
    msg = "Выберите задачи, которые необходимо добавить в сборник."
    text = additional_info["text"]

    if text[-1] == "Н":
        days = 7
    elif text[-1] == "Д":
        days = 1
    else:
        msg = """\nВы не указали измерение времени - в днях(Д) или неделях(Н).
Автоматически выбирается измерение в днях.""" + msg
    if text[:-1].isdigit():
        days *= int(text[:-1])
    elif len(text) != 1:
        await error_occured(callback.message, "wi")
        return

    await bot.send_message(text = msg,
                           chat_id = message.chat.id,
                           reply_markup = keyboard)
