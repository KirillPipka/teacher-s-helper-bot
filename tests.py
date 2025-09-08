# == Что ещё можно сделать:
#     > Облегчить интерфейс
# ~~~> Добавить время максимального выполнения задачи~~~
# ~~~> Добавить выполнение нескольких задач подряд ( сборник задач - collection of problems[colProb] )~~~
# > Переделать все последовательные операции в scenes для aiogram
# > Проверять, было ли удалено сообщение в middleware
# > Добавить ученикам и учителям имена
#   +В student_tests_rsolve
# > Добавить клавиатуры в:
#   +student_tests_list
#   +teacher_tests_class
# > Добавить сортировку по цифре и литере класса
# > DATA_TESTS, max_table_id и empty_table_ids переделать в @dataclass
# > Добавить статистику
# > i18n на Fluent
# > Импортировать тест из файла
#> Не показывать ученику задание, что он делает
# == Вопросики к коду:
# > Почему STUDENT_tests_rsolve обращается к TEACHER_tests_solve ?
# > Почему если нажать "Вернуться" к меню учителя, но зайти как ученик, то будет меню ученика?

# == Проверки:
# №1.Точно ли всё будет хорошо работать, если вдруг кто-то случайно запустит 2 /start ?
# №2.Что произойдёт, если пользователь удалит сообщение бота у себя?




from datetime import datetime
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, ScenesManager, on
from aiogram import types, F, Router
from aiogram import flags
import numpy as np
from utils import cur, db, bot, error_occured
from paged_view import PagedView
import logging
import random
import string
import json
import math

router = Router()
logger = logging.getLogger(__name__)

# Read file tests.txt and write it's content into data_tests (dict)
def get_tests_file() -> dict:
    with open(r"tests.json", "r", encoding = "utf-8") as file:
        return json.loads(file.read())

DATA_TESTS = get_tests_file()
if DATA_TESTS == None:
    raise EnvironmentError("DATA_TESTS is empty.")

del (get_tests_file)

# Getting list of empty table IDs
fetch = cur.execute("SELECT testID FROM tests_table ORDER BY testID ASC").fetchall()
if fetch == []:
    max_table_id = 4
    empty_table_ids = [0, 1, 2, 3]
else:
    max_table_id = 2**math.ceil(math.log2(int(fetch[-1][0]+1)))
    empty_table_ids = list(set(range(max_table_id)) - set(i[0] for i in fetch))
del (fetch)

async def get_name_by_id(id0, id1 = None, id2 = None) -> [str,]:
    names = []
    names.append(list( DATA_TESTS.keys() )[int(id0)])
    if id1 != None:
        names.append(list( DATA_TESTS[names[0]] )[int(id1)])
    if id2 != None:
        names.append(list( DATA_TESTS[names[0]] \
                                     [names[1]] )[int(id2)])
    return names

async def get_dict_by_id(id0, id1 = None, id2 = None) -> dict:
    if id1 == None:
        all_names = await get_name_by_id(id0)
    elif id2 == None:
        all_names = await get_name_by_id(id0, id1)
        last_name1 = all_names[1]
    else:
        all_names = await get_name_by_id(id0, id1, id2)
        last_name1 = all_names[1]
        last_name2 = all_names[2]
    last_name0 = all_names[0]

    if id1 == None:
        result_dict = DATA_TESTS[last_name0]
    else:
        result_dict = DATA_TESTS[last_name0][last_name1]
    if id2 != None:
        result_dict = DATA_TESTS[last_name0][last_name1][last_name2]

    return result_dict




# Student functions to manage tests

@router.callback_query(F.data == "student_tests_list")
@flags.permission("student")
async def student_tests_list(callback: types.CallbackQuery,
                             state: FSMContext) -> None | int:      # Добавить меню, как из teacher_tests_control
    fetch = np.array(cur.execute("SELECT studentsID FROM classes_table").fetchall())
    class_id = np.array(cur.execute("SELECT classID FROM classes_table").fetchall())
    # Getting <classID> where user id mathes any id in <studentsID>
    class_id = class_id[np.where(fetch[:, 0] == callback.from_user.id)]

    fetch = cur.execute("""SELECT doneBy, path1, path2, path3, creationDate, testID
                         FROM tests_table WHERE classID == ?""",
                        [int(class_id)]).fetchall()
    # Getting all tests data where user is not in <doneBy> column
    kb = []
    for i in range(len(fetch)):
        if callback.from_user.id not in fetch[i][0]:
            path = ") " + "\\".join(await get_name_by_id(*fetch[i][1:4]))
            kb.append([types.InlineKeyboardButton(text = "("+str(fetch[i][4])+\
                                                   path,
                                                  callback_data = "student_tests_"+\
                                                          f"rsolve_{fetch[i][5]}")])
    if len(kb) == 0:
        await error_occured(callback.message, "wu")
        return
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
    await callback.message.edit_text(text = "Невыполненные задания:",
                                     reply_markup = keyboard)

@router.callback_query(F.data[:20] == "student_tests_rsolve") # rsolve - redirect to solve
@flags.permission("student")
async def student_tests_rsolve(callback: types.CallbackQuery,
                               state: FSMContext) -> None | int:
    test_id = int(callback.data[21:])

    if test_id in empty_table_ids:
        await error_occured(callback.message, "wu")
        return
    if (await state.get_data())["additional_info"]["dataFor"] == 4 and \
            (await state.get_data())["additional_info"]["solvingAs"] == 1 and \
            (await state.get_data())["additional_info"]["testID"] == test_id:

        await callback.message.edit_text("Вы уже решаете этот тест!"+ \
                                         "Если это не так, пропишите /start")

    fetch = cur.execute("""SELECT path1, path2, path3, creationDate FROM tests_table
                         WHERE testID == ?""",
                        [test_id]).fetchall()[0]
    await state.update_data(additional_info = {"dataFor":    4,
                                               "testID":     test_id,
                                               "messageID":  callback.message\
                                                             .message_id,
                                               "solving":    1,
                                               "redirectTo": "student_tests_list",
                                               "solvingAs":  1})
    kb = [[types.InlineKeyboardButton(text = "Решить",
                             callback_data = f"teacher_tests_solve")],
          [types.InlineKeyboardButton(text = "Вернуться",
                             callback_data = f"student_tests_list")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
    await callback.message.edit_text("\\".join(await get_name_by_id(*fetch[:3]))+\
                                     f"\nОт {fetch[3]}", reply_markup = keyboard)


# Teacher functions to create tests
# 0 - ], 1 - >, 2 - :

async def teacher_tests_set_modifies(message: types.Message,
                                    state: FSMContext) -> None | int:
    if (await state.get_data())["logged_as"] != 1:
        await error_occured(message, "lt", "teacher_tests_set_modifies")
        return -1

    # Getting important variables
    additional_info = (await state.get_data())["additional_info"]
    if additional_info["dataFor"] != 1:
        return -2
    test_id = additional_info["testID"]

    if test_id in empty_table_ids:
        await error_occured(message, "wu")
        return

    modify = additional_info["modify"]
    modified = cur.execute("SELECT modif FROM tests_table WHERE testID == ?",
                           [test_id]).fetchall()[0][0]
    tmp_list = additional_info["text"][1:-1].split(", ")
    tmp_list = [min(int(tmp_list[0]), int(tmp_list[1])),
                max(int(tmp_list[0]), int(tmp_list[1]))]
    if len(modified[modify][0]) == 2:
        print([tmp_list[0], tmp_list[1], modified[modify][3]])
        if tmp_list[0] == tmp_list[1] and tmp_list[0] in modified[modify][3]:
            await message.reply("Невозможно в данной задаче использовать значение "+\
                                f"переменной {string.ascii_letters[modify]} равное"+\
                                " "+str(tmp_list[0])+".")
            return
        exclude = " \\ {"+str(modified[modify][3])[1:-1]+"}"
    else:
        exclude = ""
    modified[modify][1:3] = [tmp_list[0], tmp_list[1]]

    cur.execute("UPDATE tests_table SET modif = ? WHERE testID == ?",
                [modified, test_id])
    db.commit()
    kb = [[types.InlineKeyboardButton(text = "Готово",
                             callback_data = f"teacher_tests_values"+\
                                      additional_info['operator']+str(test_id))]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)

    await bot.send_message(text = f"Теперь {string.ascii_letters[modify]} ∈ "+\
                            additional_info["text"]+exclude,
                           chat_id = message.chat.id,
                           reply_markup = keyboard)

@router.callback_query(F.data[:20] == "teacher_tests_modify")
@flags.permission("teacher")
async def teacher_tests_modify(callback: types.CallbackQuery,
                               state: FSMContext) -> None | int:
    test_id = int(callback.data[21:callback.data.find("|")])

    if test_id in empty_table_ids:
        await error_occured(callback.message, "wu")
        return

    path1, path2, path3 = cur.execute("""SELECT path1, path2, path3 FROM
                                         tests_table WHERE testID == ?""",
                                                        [test_id]).fetchall()[0]
    last_name0, last_name1, last_name2 = await get_name_by_id(path1, path2, path3)
    modify = int(callback.data[callback.data.find("|")+1:])
    kb = [[types.InlineKeyboardButton(text = "Вернуться",
                             callback_data = f"teacher_tests_values_{test_id}")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
    await state.update_data(additional_info = {"dataFor":   1,
                                               "testID":    test_id,
                                               "modify":    modify,
                                               "messageID": callback.message.\
                                                            message_id,
                                               "operator":  callback.data[20]})

    await callback.message.edit_text(f"{last_name0}\\{last_name1}\\{last_name2}\\"+\
                                      f"Изменение {string.ascii_letters[modify]}\n"+\
                                      "Вы изменяете переменную "+\
                                      string.ascii_letters[modify]+\
                                      "\nВведите её параметры в виде [x, y]\n"+\
                                      "Где x и y - границы чисел\n"+\
                                      "(х может равняться у)",
                                     reply_markup = keyboard)

@router.message(F.text[0] != "/")
@flags.permission("teacher")
async def teacher_tests_check_solving(message: types.Message,
                                      state: FSMContext) -> None | int:
    additional_info = (await state.get_data())["additional_info"]
    if additional_info["dataFor"] != 3:
        return -2

    # Getting important data
    test_id = additional_info["testID"]

    if test_id in empty_table_ids:
        await error_occured(message, "wu")
        return

    path1, path2, path3, done_by = cur.execute("""SELECT path1, path2, path3, doneBy
                                       FROM tests_table WHERE testID == ?""",
                                      [test_id]).fetchall()[0]
    if additional_info["solvingAs"] == 1 and \
       message.from_user.id in done_by:
        await error_occured(message, "wu")
        return
    
    modif = additional_info["testValues"]
    last_dict = await get_dict_by_id(path1, path2, path3)
    last_dict = list(last_dict.values())[0]
    await state.update_data(additional_info = {"dataFor": 0})

    command = last_dict[last_dict.find(";")+1:]
    for_exec = "di=lambda x: int(x) if str(x)[-2:]=='.0' else round(x, ndigits=2);"
    for i in range(len(modif)):
        for_exec += f"{string.ascii_letters[i]}={modif[i]};"
        command = command.replace("<"+str(i)+">", string.ascii_letters[i])
    for_exec += command
    local_context = {}
    exec(for_exec, locals(), local_context)
    result = local_context["ans"] == additional_info["text"]
    if result:
        result = "верно."
    else:
        result = f"неверно.\nВерным ответом было \"{local_context['ans']}\""

    callback_to = ""
    if additional_info["redirectTo"][:16] == "teacher_precheck":
        cur.execute("DELETE FROM tests_table WHERE testID == ?", [test_id])
        db.commit()
        callback_to = f"teacher_tests_precheck_]{path1}>{path2}:{path3}"
    elif additional_info["redirectTo"][:18] == "teacher_tests_view":
        callback_to = f"teacher_tests_view_{test_id}"
    elif additional_info["redirectTo"][:18] == "student_tests_list":
        cur.execute("UPDATE tests_table SET doneBy = ? WHERE testID == ?",
                    [done_by+[message.from_user.id], test_id])
        db.commit()
        callback_to = "student_tests_list"
    kb = [[types.InlineKeyboardButton(text = "Продолжить",
                             callback_data = callback_to)]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)

    await bot.send_message(text=f"Решение задачи №{additional_info['solving']}:\n"+\
                            "\nРешено - "+result,
                           chat_id = message.chat.id,
                           reply_markup = keyboard)



@router.callback_query(F.data[:24] == "teacher_tests_set_parall")
@flags.permission("teacher")
async def teacher_tests_set_parallel(callback: types.CallbackQuery,
            state: FSMContext, selected: [int,...] = []) -> None | int:
    class_id = int(callback.data[24:callback.data.find("|")])
    test_id = int(callback.data[callback.data.find("|")+1:])
    if test_id in empty_table_ids:
        await error_occured(callback.message, "wu")
        return
    cur.execute("UPDATE tests_table SET classID == ? WHERE testID == ?",
                [class_id, test_id])
    db.commit()
    kb = [[types.InlineKeyboardButton(text = "Вернуться",
                    callback_data = f"teacher_tests_values_{test_id}")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
    await callback.message.edit_text("Готово", reply_markup = keyboard)

"""==============================================================================="""
async def _old_teacher_tests_parallel(callback: types.CallbackQuery,
            state: FSMContext) -> None | int:  # Добавить меню, как из teacher_tests_control
    fetch = cur.execute("""SELECT classID, name FROM classes_table WHERE
            teacherID == ?""", [callback.from_user.id]).fetchall()
    kb = []
    for i in range(len(fetch)):
        kb.append([types.InlineKeyboardButton(text = fetch[i][1],
                    callback_data = f"teacher_tests_set_parall{fetch[i][0]}|"+\
                                    callback.data[20:])])   # Test ID
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)

    await callback.message.edit_text("Доступные Вам классы:",
                                     reply_markup = keyboard)
"""==============================================================================="""

@router.callback_query(F.data[:21] == "teacher_tests_createc") # Check if test is OK
@flags.permission("teacher")
async def teacher_tests_create_check(callback: types.CallbackQuery,
                                     state: FSMContext) -> None | int:
    test_id = int(callback.data[21:])
    if test_id in empty_table_ids:
        await error_occured(callback.message, "wu")
        return
    fetch = cur.execute("SELECT classID, userID FROM tests_table WHERE testID == ?",
                        [test_id]).fetchall()
    if fetch[0][0] == 0:
        print(fetch)
        kb = [[types.InlineKeyboardButton(text = "Вернуться",
                             callback_data = f"teacher_tests_values_{test_id}")]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
        await callback.message.edit_text("Вы не указали класс, что получит задание!",
                                         reply_markup = keyboard)
    else:
        await teacher_tests_create_0(callback, state)


# Teacher functions to control tests

@router.callback_query(F.data[:20] == "teacher_tests_fvdel_") # f - final
@flags.permission("teacher")
async def teacher_tests_view_compl_del(callback: types.CallbackQuery,
                                       state: FSMContext) -> None | int:
    test_id = int(callback.data[20:])
    if test_id in empty_table_ids:
        await error_occured(callback.message, "wu")
        return

    cur.execute("DELETE FROM tests_table WHERE testID == ?", [test_id])
    db.commit()
    empty_table_ids = sorted(empty_table_ids + test_id)
    
    kb = [[types.InlineKeyboardButton(text = "Продолжить",
                             callback_data = f"teacher_tests_control")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)

    await callback.message.edit_text("Готово.", reply_markup = keyboard)

@router.callback_query(F.data[:19] == "teacher_tests_vdel_") # v - view ; del - delete
@flags.permission("teacher")
async def teacher_tests_view_del(callback: types.CallbackQuery,
                                 state: FSMContext) -> None | int:
    # Getting important data
    test_id = int(callback.data[19:])

    if test_id in empty_table_ids:
        await error_occured(callback.message, "wu")
        return

    kb = [[types.InlineKeyboardButton(text = "НЕТ",
                             callback_data = "teacher_tests_control")],
          [types.InlineKeyboardButton(text = "Да",
                             callback_data = f"teacher_tests_fvdel_{test_id}")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)

    await callback.message.edit_text("Вы точно хотите удалить данный тест?\nID: "+\
                                     str(test_id), reply_markup = keyboard)

@router.callback_query(F.data[:19] == "teacher_tests_view_")
@flags.permission("teacher")
async def teacher_tests_view(callback: types.CallbackQuery,
                             state: FSMContext) -> None | int:
    # Getting important data
    test_id = int(callback.data[19:])

    if test_id in empty_table_ids:
        await error_occured(callback.message, "wu")
        return

    fetch = cur.execute("SELECT * FROM tests_table WHERE testID == ?", [test_id])
    fetch = fetch.fetchall()[0]
    path1, path2, path3 = fetch[2:5]
    modified = fetch[5]
    creation_date = fetch[6]
    last_name0, last_name1, last_name2 = await get_name_by_id(path1, path2, path3)
    class_name = cur.execute("SELECT name FROM classes_table WHERE classID == ?",
                             [fetch[7]]).fetchall()[0][0]
    done_by = fetch[8] #############################################################################
    if done_by == [-1]:
        await error_occured(callback.message, "e", teacher_tests_view)
        return

    standart_limits = []
    for i in range(len(modified)):
        if len(modified[i]) == 1:
            standart_limits.append(f"{string.ascii_letters[i]} = {modified[i]}")
        elif len(modified[i]) == 3:
            standart_limits.append(string.ascii_letters[i]+
                                   f" ∈ [{modified[i][1]}, {modified[i][2]}]")
        else:
            standart_limits.append(string.ascii_letters[i]+
                                   f" ∈ [{modified[i][1]}, {modified[i][2]}] \\ "+
                                   "{"+str(modified[i][3])[1:-1]+"}")
    await state.update_data(additional_info = {"dataFor":    4,
                                               "testID":     test_id,
                                               "messageID":  callback.message\
                                                             .message_id,
                                               "solving":    1,
                                               "redirectTo": "teacher_tests_view_"+\
                                                             str(test_id),
                                               "solvingAs":  0})

    kb = [[types.InlineKeyboardButton(text = "Прорешать",
                             callback_data = "teacher_tests_solve")],
          [types.InlineKeyboardButton(text = "Удалить",
                             callback_data = f"teacher_tests_vdel_{test_id}")],
          [types.InlineKeyboardButton(text = "Вернуться",
                                      callback_data = "teacher_tests_control")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)

    await callback.message.edit_text(f"Путь: {last_name0}\\{last_name1}\\" + \
                                     f"{last_name2}\nID теста: {test_id}\n"+ \
                                     f"Выдано классу: {class_name}\n"      + \
                                     f"Выполнено учениками: {done_by}\n"   + \
                                     "Выбранные настройки:\n"              + \
                                     "\n".join(standart_limits)            + \
                                     f"\nВремя создания: {creation_date}",
                                     reply_markup = keyboard)

@router.callback_query(F.data[:20] == "teacher_tests_cmove_")
@flags.permission("teacher")
async def teacher_tests_control_move(callback: types.CallbackQuery,
                                     state: FSMContext) -> None | int:
    additional_info = (await state.get_data())["additional_info"]
    if additional_info["dataFor"] != 2:
        current_page = 0
    else:
        current_page = additional_info["page"]
    pages = (len(cur.execute("SELECT * FROM tests_table WHERE userID == ?",
                             [callback.from_user.id]).fetchall())+4)//5
    if callback.data[20] == "B":
        current_page -= 1
    else:
        current_page += 1

    if current_page < 0 or current_page >= pages:
        await error_occured(callback.message, "wu")
        return

    await state.update_data(additional_info = {"dataFor": 2,
                                               "page":    current_page})
    await teacher_tests_control(callback, state)

@router.callback_query(F.data == "teacher_tests_control")
@flags.permission("teacher")
async def teacher_tests_control(callback: types.CallbackQuery,
                                state: FSMContext) -> None | int:
    cur.execute("DELETE FROM tests_table WHERE doneBy == ? OR classID == 0", [[-1]])
    db.commit()

    additional_info = (await state.get_data())["additional_info"]
    if additional_info["dataFor"] != 2:
        current_page = 0
    else:
        current_page = additional_info["page"]
    pages = (len(cur.execute("SELECT * FROM tests_table WHERE userID == ?",
                             [callback.from_user.id]).fetchall())+4)//5

    if current_page > pages - 1:
        await error_occured(callback.message, "wu")
        return

    fetch = cur.execute("""SELECT path1, path2, path3, testID, classID FROM
                         tests_table WHERE userID == ? ORDER BY creationDate DESC
                         LIMIT 5 OFFSET ?""",
                        [callback.from_user.id, current_page*5]).fetchall()
    kb = []
    for i in range(len(fetch)):
        path = [fetch[i][0], fetch[i][1], fetch[i][2]]
        names = await get_name_by_id(path[0], path[1], path[2])
        class_name = cur.execute("SELECT name FROM classes_table WHERE classID == ?",
                                 [fetch[i][4]]).fetchall()[0][0]
        kb.append([types.InlineKeyboardButton(text    = "("+class_name+") "+names[2],
                                        callback_data = "teacher_tests_view_"+
                                                        str(fetch[i][3]))])

    kb.append([])
    if current_page != 0:
        kb[-1].append(types.InlineKeyboardButton(text = "Назад",
                                        callback_data = "teacher_tests_cmove_B"))
    if current_page != pages - 1:
        kb[-1].append(types.InlineKeyboardButton(text = "Вперёд",
                                        callback_data = "teacher_tests_cmove_F"))
    if kb[-1] == []:
        kb.pop()

    kb.append([types.InlineKeyboardButton(text = "Вернуться",
                                 callback_data = "menu_callback_redirect")])
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)

    await callback.message.edit_text("Просмотр и управление созданных Вами тестов:",
                                     reply_markup = keyboard)



# Implementing new scenes from aiogram 3.22.0

class TestsScene(Scene, state="test_manage"):
    @on.callback_query.enter()
    async def on_enter(self, callback: types.CallbackQuery, state: FSMContext,
                       entered_step: int = 0, identification: str = ''):
        if (await self.wizard.get_data())["logged_as"] == 1:
            match entered_step:
                case 1:
                    return await self.create_1(
                        callback=callback,
                        ident=identification
                    )
                case 2:
                    return await self.create_2(
                        callback=callback,
                        ident=identification
                    )
                case 3:
                    return await self.create_3(
                        callback=callback,
                        ident=identification
                    )
                case 4:
                    return await self.create_4(
                        callback=callback,
                        ident=identification
                    )
                case 5:
                    return await self.create_preview(
                        callback=callback,
                        ident=identification
                    )
                case 6:
                    return await self.create_settings(
                        callback=callback,
                        ident=identification
                    )
                case 7:
                    return await self.solve(
                        callback=callback,
                        ident=identification if identification != '' else '1'
                    )
                case 8:
                    return await self.check_solving(
                        callback=callback,
                        ident=identification if identification != '' else '1'
                    )
                case 9:
                    return await self.create_1_5(
                        callback=callback,
                        ident=identification
                    )

        elif (await self.wizard.get_data())["logged_as"] == 0:
            match entered_step:
                case 7:
                    pass

        await self.wizard.update_data(scene_data={})

        # Создать тест здесь или импортировать из файла?
        kb = [[types.InlineKeyboardButton(text = "Здесь",
                    callback_data = "create_0")],
              [types.InlineKeyboardButton(text = "Импортировать из файла", ########################
                    callback_data = "create_import")]] ############ заменить на что-нибудь ещё ####
        keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
        msg = "Вы хотите создать тест здесь или импортировать из файла?"  #########################

        await callback.message.edit_text(msg, reply_markup = keyboard)


    # Useful functions
    async def get_test_value(self, path):
        val = DATA_TESTS
        for i in path:
            val = val[i]
        return val

    @property
    def get_table_ids(self):
        global max_table_id
        if not len(empty_table_ids):
            empty_table_ids.append(list(range(max_table_id, max_table_id*2)))
            max_table_id *= 2
        return empty_table_ids

    async def create_base(self, callback: types.CallbackQuery, ident,
            function_name: str, mainmenu_text: str, step: int):
        scene_data = (await self.wizard.get_data())["scene_data"]
        path = scene_data["path"]
        data_tests = await self.get_test_value(path)
        ident = int(ident)
        if ident < 0 or ident >= len(data_tests):
            return await error_occured(callback.message, "wu")

        # Getting data to generate pages
        path.append(list(data_tests.keys())[ident])
        scene_data.update(path=path)
        await self.wizard.update_data(scene_data=scene_data)
        data_tests = data_tests[path[-1]]
        pages: list[types.InlineKeyboardButton] = []
        for i in range(len(data_tests)):
            if list(data_tests.keys())[i][0] == "_":
                continue
            pages.append(types.InlineKeyboardButton(
                text = list(data_tests.keys())[i],
                callback_data = f"back_to_scene{i}"
            ))
        await PagedView(event=self.wizard.event,
            permission="teacher",
            function_name=function_name,
            pages = pages,
            mainmenu_text = "/".join(path) + "/\n" + mainmenu_text,
            back_to = "menu_callback_redirect",
            forward_to = None,
            arguments = {"back_to": "TestsScene", "step": step}
        ).handle(state = self.wizard.state)

    @on.callback_query(F.data == "create_0")
    @flags.permission("teacher")
    async def create_0(self, callback: types.CallbackQuery):
        pages: list[types.InlineKeyboardButton] = []
        data_tests = DATA_TESTS
        for i in range(len(data_tests)):
            pages.append(types.InlineKeyboardButton(
                text = list(data_tests.keys())[i],
                callback_data = f"back_to_scene{i}"
            ))
        await PagedView(event=self.wizard.event,
            permission="teacher",
            function_name="test_create_0",
            pages = pages,
            mainmenu_text = "Выберите предмет",
            back_to = "menu_callback_redirect",
            forward_to = None,
            arguments = {"back_to": "TestsScene", "step": 1}
        ).handle(state = self.wizard.state)

    # This function is being started from `on_enter` only
    async def create_1(self, callback: types.CallbackQuery, ident):
        ident = int(ident)
        if ident < 0 or ident >= len(DATA_TESTS):
            return await error_occured(callback.message, "wu")
        val = list(DATA_TESTS.values())[ident]

        mainmenu_text = "Выберите параллель"
        step = 2
        if val.get("_has_subject_groups", False):
            mainmenu_text = "Выберите направление предмета"
            step = 9

        scene_data = (await self.wizard.get_data())["scene_data"]
        scene_data.update(path=[])
        await self.wizard.update_data(scene_data=scene_data)

        await self.create_base(
            callback = callback,
            ident = ident,
            function_name = "tests_create_1",
            mainmenu_text = mainmenu_text,
            step = step
        )

    async def create_1_5(self, callback: types.CallbackQuery, ident):
        await self.create_base(
            callback = callback,
            ident = ident,
            function_name = "tests_create_1_5",
            mainmenu_text = "Выберите параллель",
            step = 2
        )

    # This function is being started from `on_enter` only
    async def create_2(self, callback: types.CallbackQuery, ident):
        await self.create_base(
            callback = callback,
            ident = ident,
            function_name = "test_create_2",
            mainmenu_text = "Выберите категорию",
            step = 3
        )

    # This function is being started from `on_enter` only
    async def create_3(self, callback: types.CallbackQuery, ident):
        await self.create_base(
            callback = callback,
            ident = ident,
            mainmenu_text = "Выберите группу",
            function_name="test_create_3",
            step = 4
        )

    # This function is being started from `on_enter` only
    async def create_4(self, callback: types.CallbackQuery, ident):
        await self.create_base(
            callback = callback,
            ident = ident,
            mainmenu_text = "Выберите задание",
            function_name="test_create_4",
            step = 5
        )


    # This function is being started from `on_enter` only
    async def create_preview(self, callback: types.CallbackQuery, ident):
        scene_data = (await self.wizard.get_data())["scene_data"]
        path = scene_data["path"]
        data_tests = await self.get_test_value(path)
        ident = int(ident)
        cur.execute("DELETE FROM tests_table WHERE doneBy == ?", [[-1]]) ######################
        db.commit()

        if ident < 0 or ident >= len(data_tests):
            return error_occured(callback.message, "wu")

        # Getting important data
        path.append(list(data_tests.keys())[ident])
        scene_data.update(path=path)
        await self.wizard.update_data(scene_data=scene_data)
        data_tests = data_tests[path[-1]]

        msg = data_tests["text"]
        # Get len(p) in tests
        limit = data_tests["limits"].count(",") + 1
        for i in range(limit):
            msg = msg.replace(
                "<"+str(i)+">",
                string.ascii_letters[i]
            )

        kb = [[types.InlineKeyboardButton(text = "Создать вариант",
                    callback_data = "tests_create_5_")],
              [types.InlineKeyboardButton(text = "Прорешать вариант",
                    callback_data = "tests_create_5-")],
              [types.InlineKeyboardButton(text = "Вернуться",
                    callback_data = "menu_callback_redirect")]]

        keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
        msg = "/".join(path) + "/\nПредварительный просмотр задачи:\n"+msg
        await callback.message.edit_text(msg, reply_markup = keyboard)

    @on.callback_query(F.data[:14] == "tests_create_5")
    @flags.permission("teacher")
    async def create_5(self, callback: types.CallbackQuery):
        scene_data = (await self.wizard.get_data())["scene_data"]
        path = scene_data["path"]

        # Getting important data
        data_tests = await self.get_test_value(path)

        # Get maximum and minimum of unknown
        limits = data_tests["limits"].split(",")

        # Making limits for random generation from `tests.txt`
        for i in range(len(limits)):
            multiplier = 10
            if limits[i][:-1] != "" and limits[i][-1] != "c":
                multiplier = 10 * float(limits[i][:-1])

            if limits[i][-1].isdigit():
                limits[i] = [int(limits[i])]
            elif limits[i][-1] == "c":
                includ = limits[i][1:limits[i].find("\\")-1].split("!")
                includ = [float(includ[0]), float(includ[1])]
                if limits[i][-2] == "z":
                    includ = [int(includ[0]), int(includ[1])]

                if limits[i][limits[i].find("\\")+3:] == "c":
                    limits[i] = [limits[i][-2], *includ]
                else:
                    exclude = limits[i][limits[i].find("\\")+2:-3].split("!")
                    limits[i] = [limits[i][-2]+"c", *includ, list(map(int, exclude))]
            elif limits[i][-1] == "z":
                multiplier = round(multiplier)
                limits[i] = ["z", -1 * multiplier, multiplier]

        test_id = (self.get_table_ids).pop()
        scene_data.update(test_id=test_id)
        await self.wizard.update_data(scene_data=scene_data)
        cur.execute("""
            INSERT INTO
                tests_table
            VALUES
                (:userid,
                 :testid,
                 :path,
                 :modif,
                 :date,
                 :classid,
                 :parallel,
                 :doneby)
            """, {
            "userid":   callback.from_user.id,
            "testid":   test_id,
            "path":     path,
            "modif":    limits,
            "date":     datetime.today(),
            "classid":  0,
            "parallel": path[1] if len(path)==5 else path[2],
            "doneby":   [-1]
        })
        db.commit()
        if callback.data[14] == "-":
            scene_data.update(redirect_after_solving="create_preview")
            await self.wizard.update_data(scene_data=scene_data)
            return await self.solve(callback)
        elif callback.data[14] == "_":
            return await self.create_settings(callback)

    @router.callback_query(F.data[:20] == "teacher_tests_values")
    @flags.permission("teacher")
    async def create_settings(callback: types.CallbackQuery, ident = ''):
        scene_data = (await self.wizard.get_data())["scene_data"]
        test_id = scene_data["test_id"]
        if test_id in self.get_table_ids:
            return await error_occured(callback.message, "wu")

        path, limits, done_by = cur.execute("""
            SELECT
                path,
                modif,
                doneBy
            FROM
                tests_table
            WHERE
                testID == ?
        """, [test_id]).fetchall()[0]
        data_tests = await self.get_test_value(path)

        standart_limits = []
        pages: list[types.InlineKeyboardButton] = []
        if ident != '':
            ident = ident.split()
            if ident[0] == -1:
                ## finish creation + ask if need to add to colproblems/class ###################
                return
            if ident[0] < 0 or ident[0] >= len(limits):
                return error_occured(callback.message, "wu")
            limits[ident[0]] = ident[1]

        for i in range(len(limits)):
            if len(limits[i]) == 1:
                standart_limits.append(
                    string.ascii_letters[i]+" ∈ {"+limits[i][0]+"}"
                )
            elif len(limits[i]) == 3:
                standart_limits.append(
                    string.ascii_letters[i]+f" ∈ [{limits[i][1]}, {limits[i][2]}]"
                )
            else:
                standart_limits.append(
                    string.ascii_letters[i]+f" ∈ [{limits[i][1]}, {limits[i][2]}]"+\
                        " \\ {"+str(limits[i][3])[1:-1]+"}"
                )
            kb.append(types.InlineKeyboardButton(
                text = "Изменить "+string.ascii_letters[i],
                callback_data = "back_to_scene{i}" ############################################
            ))
        textMessage = "/".join(path) + "/\nВыберете максимальные границы чисел\n"
        if ident == '':
            textMessage += "По умолчанию:\n"
        else:
            textMessage += "Выбранные настройки:\n"
        textMessage += "\n".join(standart_limits)

        await PagedView(event=self.wizard.event,
            permission="teacher",
            function_name="test_create_settings",
            pages = pages,
            mainmenu_text = msg,
            back_to = "menu_callback_redirect",
            forward_to = "back_to_scene-1",
            arguments = {"back_to": "TestsScene", "step": 6}
        ).handle(state = self.wizard.state)

    async def create_settings_modify(self, callback: types.CallbackQuery, ident):
        scene_data = (await self.wizard.get_data())["scene_data"]
        test_id = scene_data["test_id"]
        if test_id in self.get_table_ids:
            return await error_occured(callback.message, "wu")
        ident = int(ident)
        limits = cur.execute("""
            SELECT
                modif
            FROM
                tests_table
            WHERE
                testID == ?
        """, [test_id]).fetchall()[0]
        if ident < 0 or ident >= len(limits):
            return await error_occured(callback.message, "wu")
        limits = limits[ident]
        parameter_type: str
        limits_type: str = ''
        if limits[0][0] == 'z':
            parameter_type = "[x, y]"
            limits_type = "Где x и y это левая и правая границы соответственно"

        if limits[0][1:] == 'c':
            limits_type += "\nОбратите внимание, что значения {" +\
                    "; ".join(limits[3]) + "} будут исключены"

        msg = f"""Изменение {string.ascii_letters[ident]}
Вы изменяете переменную
string.ascii_letters[ident]
Введите её параметры в виде {parameter_type}
{limits_type}"""

    @on.callback_query(F.data == "solve")
    @flags.permission("all")
    async def solve(self, callback: types.CallbackQuery, ident = '1'):
        scene_data = (await self.wizard.get_data())["scene_data"]
        test_id = scene_data["test_id"]
        if test_id in self.get_table_ids:
            return await error_occured(callback.message, "wu")

        path, limits, done_by = cur.execute("""
            SELECT
                path,
                modif,
                doneBy
            FROM
                tests_table
            WHERE
                testID == ?
        """, [test_id]).fetchall()[0]
        data_tests = await self.get_test_value(path)

        if callback.from_user.id in done_by:
            return await error_occured(callback.message, "wu")

        # Modifying answer's text to use modifier's values
        msg = data_tests["text"]
        test_values = []
        for i in range(len(limits)):
            if limits[i][0][0] == "z":
                test_values.append(random.randint(limits[i][1], limits[i][2]))

            if len(limits[i][0]) == 2 and test_values[-1] in set(limits[i][3]):
                if test_values[-1] != limits[i][1]:
                    test_values[-1] = limits[i][1]
                else:
                    test_values[-1] = limits[i][2]
            msg = msg.replace( f"<{i}>", str(test_values[-1]) )
        additional_info = (await self.wizard.get_data())["additional_info"]
        additional_info.update(b2s_args={
            "back_to": "TestsScene",
            "step": 8
        })
        additional_info.update(dataFor=3)
        scene_data.update(test_values=test_values)
        await self.wizard.update_data(additional_info = additional_info)
        await self.wizard.update_data(scene_data=scene_data)

        msg = "Решение задачи №"+ident+"\n(Если получилось дробное " + \
              "число, то его необходимо округлить до двух знаков после запятой):\n"+\
              msg
        await callback.message.edit_text(msg)

    # This function is being started from `on_enter` only
    # This function is being called by message_redirect in main.py
    async def check_solving(self, callback: types.CallbackQuery, ident = '1'):
        scene_data = (await self.wizard.get_data())["scene_data"]
        test_id = scene_data["test_id"]
        test_values = scene_data["test_values"]
        redirect_after_solving = scene_data["redirect_after_solving"]
        if test_id in self.get_table_ids:
            return await error_occured(message, "wu")

        # Getting important data
        path, done_by = cur.execute("""
            SELECT
                path,
                doneBy
            FROM
                tests_table
            WHERE
                testID == ?
        """, [test_id]).fetchall()[0]
        data_tests = await self.get_test_value(path)
        command = data_tests["func"]

        if message.from_user.id in done_by:
            await error_occured(message, "wu")
            return

        for_exec = "di=lambda x:int(x) if str(x)[-2:]=='.0'else round(x, ndigits=2);"
        for i in range(len(test_values)):
            for_exec += f"{string.ascii_letters[i]}={test_values[i]};"
            command = command.replace("<"+str(i)+">", string.ascii_letters[i])
        for_exec += command
        local_context = {}
        exec(for_exec, local_context)
        result = local_context["ans"] == additional_info["text"]
        if result:
            result = "верно."
        else:
            result = f"неверно.\nВерным ответом было \"{local_context['ans']}\""

        if self.redirect_after_solving == "create_preview":
            cur.execute("DELETE FROM tests_table WHERE testID == ?", [self.test_id])
            db.commit()
            callback_to = "create_preview"

        elif self.redirect_after_solving == "teacher_tests_view":   #############################
            callback_to = f"teacher_tests_view_{test_id}"           #############################
        elif self.redirect_after_solving == "student_tests_list":   #############################
            cur.execute("UPDATE tests_table SET doneBy = ? WHERE testID == ?", ##################
                        [done_by+[message.from_user.id], test_id])  #############################
            db.commit()  #################################
            callback_to = "student_tests_list"                      #############################

        kb = [[types.InlineKeyboardButton(text = "Продолжить",
                    callback_data = callback_to)]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
        msg = f"Решение задачи №{ident}:\nРешено - "+result

        await bot.send_message(text=msg,
                               chat_id = message.chat.id,
                               reply_markup = keyboard)


@router.callback_query(F.data == "tests_manage")
@flags.permission("teacher")
async def tests_manage(callback: types.CallbackQuery, scenes: ScenesManager,
        state: FSMContext) -> None:
    await scenes.close()
    await scenes.enter(TestsScene, state=FSMContext)

@router.callback_query(F.data == "tests_complete")
@flags.permission("student")
async def tests_complete(callback: types.CallbackQuery, scenes: ScenesManager,
        state: FSMContext) -> None:
    await scenes.close()
    await scenes.enter(TestsScene, state=FSMContext)
