# начение времени по умоолчанию в collproblems
# Посмотреть приём значений с минусами
# Возможность проСМОТРЕТЬ


# == Что ещё можно сделать:
#     > Облегчить интерфейс
# ~~~> Добавить время максимального выполнения задачи~~~
# ~~~> Добавить выполнение нескольких задач подряд ( сборник задач - collection of problems[colProb] )~~~
# > Переделать все последовательные операции в scenes для aiogram
# > Проверять, было ли удалено сообщение в middleware
# > Добавить сортировку по цифре и литере класса
# > Добавить статистику
# > i18n на Fluent
#> Не показывать ученику задание, что он делает

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
import check_utils
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
    if type(fetch[-1][0]) == bytes:
        print(fetch[-1])
        max_table_id = 2**math.ceil(math.log2(int(fetch[-1][0][1:-1])+1))
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

class TestsScene(Scene, state = "tests_scene"):
    @on.callback_query.enter()
    async def on_enter_callback(self, callback: types.CallbackQuery,
            entered_step: int = 0, identification: str = ''):
        if (await self.wizard.get_data())["logged_as"] == 1:
            match entered_step:
                case 0:
                    return await self.create_0(
                        callback = callback
                    )
                case 1:
                    return await self.create_1(
                        callback = callback,
                        ident = identification
                    )
                case 2:
                    return await self.create_2(
                        callback = callback,
                        ident = identification
                    )
                case 3:
                    return await self.create_3(
                        callback = callback,
                        ident = identification
                    )
                case 4:
                    return await self.create_4(
                        callback = callback,
                        ident = identification
                    )
                case 5:
                    return await self.create_preview(
                        callback = callback,
                        ident = identification
                    )
                case 6:
                    return await self.create_settings_modify(
                        callback = callback,
                        ident = identification
                    )
                case 7:
                    return await self.solve(
                        callback = callback,
                        ident = identification if identification != '' else '1'
                    )
                case 9:
                    return await self.create_1_5(
                        callback = callback,
                        ident = identification
                    )
                case 11:
                    print("via callback")
                    return await self.create_final(
                        message = callback.message
                    )

        elif (await self.wizard.get_data())["logged_as"] == 0:
            match entered_step:
                case 0:
                    return await self.student_list(
                        callback = callback
                    )
                case 12:
                    return await self.student_tests_rsolve(
                        callback = callback,
                        ident = identification
                    )

        else:
            return

    @on.message.enter()
    async def on_enter_message(self, message: types.Message,
            entered_step: int = 0, identification: str = ''):
        if (await self.wizard.get_data())["logged_as"] == 1:
            match entered_step:
                case 8:
                    return await self.check_solving(
                        message = message
                    )
                case 10:
                    return await self.create_settings_set(
                        message = message,
                        ident = identification
                    )
                case 11:
                    print("via message")
                    return await self.create_final(
                        message = message
                    )

        elif (await self.wizard.get_data())["logged_as"] == 0:
            match entered_step:
                case 8:
                    return await self.check_solving(
                        message = message
                    )

    # Useful functions
    async def get_test_value(self, path) -> dict:
        val = DATA_TESTS
        for i in path:
            val = val[i]
        return val

    @property
    def get_table_ids(self) -> list:
        global max_table_id
        if not len(empty_table_ids):
            empty_table_ids.extend(list(range(max_table_id, max_table_id*2)))
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
        scene_data.update(path = path)
        await self.wizard.update_data(scene_data = scene_data)
        data_tests = data_tests[path[-1]]
        pages: list[types.InlineKeyboardButton, ...] = []
        for i in range(len(data_tests)):
            if list(data_tests.keys())[i][0] == "_":
                continue
            pages.append(types.InlineKeyboardButton(
                text = list(data_tests.keys())[i],
                callback_data = f"back_to_scene{i}"
            ))
        return await PagedView(event = self.wizard.event,
            permission = "teacher",
            function_name = function_name,
            pages = pages,
            mainmenu_text = "/".join(path) + "/\n" + mainmenu_text,
            back_to = "menu_callback_redirect",
            forward_to = None,
            arguments = {"back_to": "tests_scene", "step": step}
        ).handle(state = self.wizard.state)

    async def get_common_db_data(self, *additional_fields) -> list:
        # Returns scene_data and test_id by default and other fields from args
        # Of course this only works if we have `test_id` in `scene_data`
        scene_data = (await self.wizard.get_data())["scene_data"]
        test_id = scene_data.get("test_id")
        if test_id == None:
            return await error_occured(callback, "e")
        if test_id in self.get_table_ids:
            return await error_occured(callback, "wu")
        data = cur.execute(f"""
            SELECT
                {", ".join(additional_fields)}
            FROM
                tests_table
            WHERE
                testID == ?
        """, [test_id]).fetchall()
        if len(data) == 0:
            # Something is REALLY wrong and we should exit immedietly
            err_message = f"""Somehow data for testID {test_id} is empty, \
but this ID is not in list. Adding this entry to the list"""
            logger.error(err_message)
            self.get_table_ids.append(test_id)
            return await error_occured(data, "e", "get_common_db_data",
                f"data for testID {test_id} is empty")
        return [scene_data, test_id, *data[0]]


    # This function is being started from `on_enter` only
    async def create_0(self, callback: types.CallbackQuery):
        pages: list[types.InlineKeyboardButton, ...] = []
        data_tests = DATA_TESTS
        for i in range(len(data_tests)):
            pages.append(types.InlineKeyboardButton(
                text = list(data_tests.keys())[i],
                callback_data = f"back_to_scene{i}"
            ))
        return await PagedView(event = self.wizard.event,
            permission = "teacher",
            function_name = "test_create_0",
            pages = pages,
            mainmenu_text = "Выберите предмет",
            back_to = "menu_callback_redirect",
            forward_to = None,
            arguments = {"back_to": "tests_scene", "step": 1}
        ).handle(state = self.wizard.state)

    # This function is being started from `on_enter` only
    async def create_1(self, callback: types.CallbackQuery, ident: str):
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

        return await self.create_base(
            callback = callback,
            ident = ident,
            function_name = "tests_create_1",
            mainmenu_text = mainmenu_text,
            step = step
        )

    async def create_1_5(self, callback: types.CallbackQuery, ident: str):
        return await self.create_base(
            callback = callback,
            ident = ident,
            function_name = "tests_create_1_5",
            mainmenu_text = "Выберите параллель",
            step = 2
        )

    # This function is being started from `on_enter` only
    async def create_2(self, callback: types.CallbackQuery, ident: str):
        return await self.create_base(
            callback = callback,
            ident = ident,
            function_name = "test_create_2",
            mainmenu_text = "Выберите категорию",
            step = 3
        )

    # This function is being started from `on_enter` only
    async def create_3(self, callback: types.CallbackQuery, ident: str):
        return await self.create_base(
            callback = callback,
            ident = ident,
            mainmenu_text = "Выберите группу",
            function_name = "test_create_3",
            step = 4
        )

    # This function is being started from `on_enter` only
    async def create_4(self, callback: types.CallbackQuery, ident: str):
        return await self.create_base(
            callback = callback,
            ident = ident,
            mainmenu_text = "Выберите задание",
            function_name = "test_create_4",
            step = 5
        )


    # This function is being started from `on_enter` only
    async def create_preview(self, callback: types.CallbackQuery, ident: str):
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
        scene_data.update(path = path)
        await self.wizard.update_data(scene_data = scene_data)
        data_tests = data_tests[path[-1]]

        msg = data_tests["text"]
        # Get len(p) in tests
        limit = data_tests["limits"].count(",") + 1
        for i in range(limit):
            msg = msg.replace(
                "<"+str(i)+">",
                string.ascii_letters[i]
            )

        kb = [[types.InlineKeyboardButton(
                    text = "Создать вариант",
                    callback_data = "tests_create_5_"
                )],
              [types.InlineKeyboardButton(
                    text = "Прорешать вариант",
                    callback_data = "tests_create_5-"
                )],
              [types.InlineKeyboardButton(
                    text = "Вернуться",
                    callback_data = "menu_callback_redirect"
        )]]

        keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
        msg = "/".join(path) + "/\nПредварительный просмотр задачи:\n"+msg
        return await callback.message.edit_text(msg, reply_markup = keyboard)

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
                    limits[i] = [limits[i][-2]+"c", *includ, list(map(int,exclude))]
            elif limits[i][-1] == "z":
                multiplier = round(multiplier)
                limits[i] = ["z", -1 * multiplier, multiplier]

        test_id = (self.get_table_ids).pop()
        scene_data.update(test_id = test_id)
        await self.wizard.update_data(scene_data = scene_data)
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
            "parallel": path[1] if len(path) == 5 else path[2],
            "doneby":   {}
        })
        db.commit()
        if callback.data[14] == "-":
            scene_data.update(redirect_after_solving = "create_preview")
            await self.wizard.update_data(scene_data = scene_data)
            return await self.solve(callback)
        elif callback.data[14] == "_":
            return await self.create_settings(callback)

    @on.callback_query(F.data == "teacher_tests_values")
    @flags.permission("teacher")
    async def create_settings(self, callback: types.CallbackQuery, ident: str = ''):
        scene_data, test_id, path, limits, done_by = await self.get_common_db_data(
            "path", "modif", "doneBy"
        )
        data_tests = await self.get_test_value(path)

        standart_limits = []
        pages = []
        if ident == '-1':
            pages.append([types.InlineKeyboardButton(
                text = "Добавить в задачник",
                callback_data = "teacher_tests_values_addc"
            )])
            pages.append([types.InlineKeyboardButton(
                text = "Как отдельное задание",
                callback_data = "teacher_tests_values_addt"
            )])
            keyboard = types.InlineKeyboardMarkup(inline_keyboard = pages)
            return await callback.message.edit_text(
                text = "Как добавить задание?",
                reply_markup = keyboard
            )

        for i in range(len(limits)):
            if len(limits[i]) == 1:
                standart_limits.append(
                    string.ascii_letters[i] + " ∈ {"+limits[i][0]+"}"
                )
            elif len(limits[i]) == 3:
                standart_limits.append(
                    string.ascii_letters[i] + f" ∈ [{limits[i][1]}, {limits[i][2]}]"
                )
            elif min(limits[i][3]) > max(limits[i][1], limits[i][2]) or\
                    max(limits[i][3]) < min(limits[i][1], limits[i][2]):
                standart_limits.append(
                    string.ascii_letters[i] + f" ∈ [{limits[i][1]}, {limits[i][2]}]"
                )
            else:
                standart_limits.append(
                    string.ascii_letters[i] + f" ∈ [{limits[i][1]}, " +\
                        f"{limits[i][2]}]" + " \\ {" + str(limits[i][3])[1:-1] + "}"
                )
            pages.append(types.InlineKeyboardButton(
                text = "Изменить " + string.ascii_letters[i],
                callback_data = f"back_to_scene{i}"
            ))
        msg = "/".join(path) + "/\nВыберете максимальные границы чисел\n"
        if ident == '':
            msg += "По умолчанию:\n"
        else:
            msg += "Выбранные настройки:\n"
        msg += "\n".join(standart_limits)

        return await PagedView(event=self.wizard.event,
            permission = "teacher",
            function_name = "test_create_settings",
            pages = pages,
            mainmenu_text = msg,
            back_to = "menu_callback_redirect",
            forward_to = "back_to_scene-1",
            arguments = {"back_to": "tests_scene", "step": 6}
        ).handle(state = self.wizard.state)

    # This function is being started from `on_enter` only
    async def create_settings_modify(self, callback: types.CallbackQuery,
            ident: str):
        additional_info = (await self.wizard.get_data())["additional_info"]
        scene_data, test_id, limits = await self.get_common_db_data(
            "modif"
        )
        if ident == '-1':   # If user pressed next step button
            return await self.create_settings(callback = callback, ident = ident)
        ident = int(ident)
        if ident < 0 or ident >= len(limits):
            return await error_occured(callback.message, "wu")
        additional_info.update(b2s_args = {
            "back_to": "tests_scene",
            "step": 10,
            "identification": str(ident)
        })
        additional_info.update(dataFor = 3)
        await self.wizard.update_data(additional_info = additional_info)
        limits = limits[ident]
        parameter_type: str
        limits_type: str = ''
        if limits[0][0] == 'z':
            parameter_type = "[x, y]"
            limits_type = "где x и y это левая и правая границы соответственно"

        if limits[0][1:] == 'c':
            limits_type += "\nОбратите внимание, что значения {" +\
                "; ".join(map(str, limits[3])) + "} будут исключены"

        msg = f""".../Изменение {string.ascii_letters[ident]}/
Вы изменяете переменную {string.ascii_letters[ident]}
Введите её параметры в виде {parameter_type},
{limits_type}"""
        await callback.message.edit_text(msg)

    # This function is being started from `on_enter` only
    async def create_settings_set(self, message: types.Message, ident: str):
        additional_info = (await self.wizard.get_data())["additional_info"]
        text = additional_info["text"]
        ident = int(ident)

        # If wrong user input occured, then we should give way to give input again
        additional_info.update(b2s_args = {
            "back_to": "tests_scene",
            "step": 10,
            "identification": str(ident)
        })
        additional_info.update(dataFor = 3)
        await self.wizard.update_data(additional_info = additional_info)

        try:
            check = check_utils.Checking(text)
            if check.clear_scopes() != "[]":
                raise ValueError
            check.split_str_to_list()
            check.list_to_int()
            if len(check.data) != 2 or check.data[0] > check.data[1]:
                raise ValueError
        except ValueError:
            return await error_occured(message, "wi")
        scene_data, test_id, limits = await self.get_common_db_data(
            "modif"
        )
        if ident < 0 or ident >= len(limits):
            return await error_occured(callback.message, "wu")
        var_limit = limits[ident]
        if check.data[0] == check.data[1] and var_limit[0][1:] == 'c':
            if check.data[0] in var_limit[3]:
                return await error_occured(message, "wi")
        var_limit[1], var_limit[2] = check.data[0], check.data[1]
        limits[ident] = var_limit
        cur.execute("""
            UPDATE
                tests_table
            SET
                modif = :limits
            WHERE
                testID == :testID
        """, {"testID": test_id, "limits": limits})

        additional_info.update(dataFor = 10)
        await self.wizard.update_data(additional_info = additional_info)
        kb = [[types.InlineKeyboardButton(
            text = "Продолжить",
            callback_data = "teacher_tests_values"
        )]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)

        await bot.send_message(
            text = "Готово.",
            chat_id = message.chat.id,
            reply_markup = keyboard
        )

    @on.callback_query(F.data[:24] == "teacher_tests_values_add")
    @flags.permission("teacher")
    async def create_settings_redirect(self, callback: types.CallbackQuery):
        scene_data = (await self.wizard.get_data())["scene_data"]
        action = callback.data[24:]
        scene_data.update(test_action = "create_new")
        scene_data.update(exit_earlier = True)
        await self.wizard.update_data(scene_data = scene_data)
        if action == "t":
            return await self.wizard.goto(
                "collproblems_scene",
                entered_step = 1
            )
        scene_data.update(test_action = "modify_collprob")
        await self.wizard.update_data(scene_data = scene_data)
        return await self.wizard.goto(
                "collproblems_scene",
                entered_step = 4
            )

    # This function is being started from `on_enter` only
    async def create_final(self, message: types.Message):
        scene_data = (await self.wizard.get_data())["scene_data"]
        additional_info = (await self.wizard.get_data())["additional_info"]

        test_id = scene_data["test_id"]
        sel_options = scene_data["selected_options"].tolist()
        dedicated_time = scene_data["dedicated_time"]
        collprob_name = scene_data["name"]

        #####################################################################################
        '''for i in range(len(classes_ids)):
            old_tests_ids = []
            if not scene_data["exit_earlier"]:
                old_tests_ids = cur.execute("""
                    SELECT
                        testsID
                    FROM
                        collections_table
                    WHERE
                        rowid == ?""",
                [collprobs_ids[i]]).fetchall()'''
        ##############################################################################################

        if scene_data["test_action"] == "modify_collprob":
            for i in sel_options:
                tests_ids = cur.execute("""
                    SELECT
                        testsIDs
                    FROM
                        collections_table
                    WHERE
                        rowid == ?
                """, [i]).fetchone()[0] + test_id
                cur.execute("""
                    UPDATE
                        collections_table
                    SET
                        testsIDs == ?
                    WHERE
                        rowid == ?
                """, [tests_ids, i])
        else:
            cur.execute("""
                INSERT INTO
                    collections_table
                VALUES
                   (:classesIDs,
                    :testsIDs,
                    :timeCompl,
                    :creationDate,
                    :name,
                    :teacherID)
            """, {
                "classesIDs":   list(map(int, sel_options)),
                "testsIDs":     [test_id],
                "timeCompl":    dedicated_time,
                "creationDate": datetime.today(),
                "name":         collprob_name,
                "teacherID":    message.from_user.id
            })
        db.commit()

        kb = [[types.InlineKeyboardButton(
            text = "Вернуться",
            callback_data = "menu_callback_redirect"
        )]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
        return await bot.send_message(
            text = "Готово. Тест был добавлен",
            chat_id = message.chat.id,
            reply_markup = keyboard
        )

    @on.callback_query(F.data == "solve")
    @flags.permission("all")
    async def solve(self, callback: types.CallbackQuery):
        scene_data, test_id, path, limits, done_by = await self.get_common_db_data(
            "path", "modif", "doneBy"
        )
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
            "back_to": "tests_scene",
            "step": 8
        })
        additional_info.update(dataFor = 3)
        scene_data.update(test_values = test_values)
        await self.wizard.update_data(additional_info = additional_info)
        await self.wizard.update_data(scene_data = scene_data)

        msg = f"""Решение задачи №{scene_data.get('collprob_step', 0)}
(Если получилось дробное число, то его необходимо округлить до двух знаков после \
точки):\n{msg}"""
        await callback.message.edit_text(msg)

    # This function is being started from `on_enter` only
    # This function is being called by message_redirect in main.py
    async def check_solving(self, message: types.Message):
        scene_data, test_id, path, done_by = await self.get_common_db_data(
            "path", "doneBy"
        )
        additional_info = (await self.wizard.get_data())["additional_info"]

        # Getting important data
        test_values = scene_data["test_values"]
        redirect_after_solving = scene_data["redirect_after_solving"]
        data_tests = await self.get_test_value(path)
        command = data_tests["func"]

        if message.from_user.id in done_by:
            await error_occured(message, "wu")
            return

        # If we are using division, round it to 2 numbers after comma before answer
        for_exec = "di=lambda x:int(x)if str(x)[-2:]=='.0'else round(x,ndigits=2);"

        for i in range(len(test_values)):
            for_exec += f"{string.ascii_letters[i]}={test_values[i]};"
            command = command.replace("<"+str(i)+">", string.ascii_letters[i])
        for_exec += command
        local_context = {}
        exec(for_exec, local_context)
        result = additional_info["text"] in local_context["ans"]

        if redirect_after_solving == "create_preview":
            callback_to = "redirect_to_create_preview"
        elif redirect_after_solving == "collprob_continue":
            done_by[message.from_user.id] = result
            cur.execute("""
                UPDATE
                    tests_table
                SET
                    doneBy = ?
                WHERE
                    testID == ?
            """, [done_by, test_id])
            db.commit()
            callback_to = "redirect_to_next_test"
        elif redirect_after_solving == "teacher_collprob_continue": ############
            callback_to = "redirect_to_next_test"
            
        if result:
            result = "верно."
        else:
            result = f"неверно.\nВерным ответом было \"{local_context['ans']}\""
        kb = [[types.InlineKeyboardButton(
            text = "Продолжить",
            callback_data = callback_to
        )]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
        msg = f"""Решение задачи №{scene_data.get('collprob_step', 0)}:
Решено - {result}"""

        await bot.send_message(
            text = msg,
            chat_id = message.chat.id,
            reply_markup = keyboard
        )

    @on.callback_query(F.data == "redirect_to_create_preview")
    @flags.permission("teacher")
    async def redirect_to_create_preview(self, callback: types.CallbackQuery):
        scene_data, test_id, path = await self.get_common_db_data(
            "path"
        )
        cur.execute("DELETE FROM tests_table WHERE testID == ?", [test_id])
        db.commit()
        ident = list((await self.get_test_value(path[:-1])).values())
        ident = ident.index(await self.get_test_value(path))
        path = path[:-1]
        scene_data.update(path = path)
        await self.wizard.update_data(scene_data = scene_data)
        return await self.create_preview(callback = callback, ident = ident)


    # Students functions
    @on.callback_query(F.data == "redirect_to_next_test")
    @flags.permission("student")
    async def redirect_student_to_next_test(self, callback: types.CallbackQuery):
        scene_data = (await self.wizard.get_data())["scene_data"]
        collprob = cur.execute("""
            SELECT
                testsIDs, name
            FROM
                collections_table
            WHERE
                rowid == ? AND
                DATE('NOW', 'START OF DAY') <=
                    DATE(creationDate, CONCAT('+', timeCompl, ' DAY'))
            ORDER BY
                creationDate DESC
        """, [scene_data["collprob_rowid"]]).fetchone()

        if () == collprob:
            return await error_occured(callback, "wu")

        if len(collprob[0]) <= scene_data["collprob_step"]:
            msg = "Готово! Все задачи в этом сборнике были решены."
            kb = [[types.InlineKeyboardButton(
                text = "Продолжить",
                callback_data = "menu_callback_redirect"
            )]]
            keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
            return await callback.message.edit_text(
                text = msg,
                reply_markup = keyboard
            )

        scene_data.update(test_id = collprob[scene_data["collprob_step"]])
        scene_data.update(collprob_step = scene_data["collprob_step"] + 1)
        return await self.solve(callback)

    # This function is being started from `on_enter` only
    async def student_list(self, callback: types.CallbackQuery):
        scene_data = (await self.wizard.get_data())["scene_data"]
        fetch = cur.execute("""
            SELECT
                studentsID, classID
            FROM
                classes_table
        """).fetchall()
        classes = []
        for i in fetch:
            if callback.from_user.id in i[0]:
                classes.append(int(i[1]))
        classes = set(classes)

        fetch = cur.execute("""
            SELECT
                classIDs, name, rowid, testsIDs
            FROM
                collections_table
            WHERE
                DATE('NOW', 'START OF DAY') <=
                    DATE(creationDate, CONCAT('+', timeCompl, ' DAY'))
            ORDER BY
                creationDate DESC
        """).fetchall()

        # Getting all collprobs data where user is not in <doneBy> column
        pages = []
        collprobs_rowids = []
        for i in range(len(fetch)):
            inters_col_class = classes & set(map(int, fetch[i][0]))
            # If classes has same objects then proceed
            if len(inters_col_class) > 0:
                done_by = cur.execute(
                    "SELECT doneBy FROM tests_table WHERE testID == ?",
                    [fetch[i][3][-1]]
                ).fetchone()[0]
                if str(callback.from_user.id) in done_by.keys():
                    continue

                name = cur.execute(
                    "SELECT name FROM classes_table WHERE classID == ?",
                    [inters_col_class.pop()]
                ).fetchone()[0]
                pages.append(types.InlineKeyboardButton(
                    text = f"({name}) {fetch[i][1]}",
                    callback_data = f"back_to_scene{fetch[i][2]}"
                ))
                collprobs_rowids.append(fetch[i][2])
        scene_data.update(collprobs_rowids = collprobs_rowids)
        if len(pages) == 0:
            await error_occured(callback.message, "wu")
            return

        await self.wizard.update_data(scene_data = scene_data)

        return await PagedView(event = self.wizard.event,
            permission = "student",
            function_name = "test_student_list",
            pages = pages,
            mainmenu_text = "Невыполненные задания:",
            back_to = "menu_callback_redirect",
            forward_to = None,
            arguments = {"back_to": "tests_scene", "step": 12}
        ).handle(state = self.wizard.state)

    # This function is being started from `on_enter` only
    async def student_tests_rsolve(self, callback: types.CallbackQuery, ident: str):
        scene_data = (await self.wizard.get_data())["scene_data"]
        if int(ident) not in scene_data["collprobs_rowids"]:
            return await error_occured(callback, "wu")
        collprob = cur.execute("""
            SELECT
                testsIDs, name, creationDate,
                STRFTIME(
                    '%j %R',
                    UNIXEPOCH(creationDate) + timeCompl*86400 -
                        UNIXEPOCH('NOW', 'LOCALTIME'),
                    'UNIXEPOCH'
                )
            FROM
                collections_table
            WHERE
                rowid == ? AND
                DATE('NOW', 'START OF DAY') <=
                    DATE(creationDate, CONCAT('+', timeCompl, ' DAY'))
            ORDER BY
                creationDate DESC
        """, [int(ident)]).fetchone() # Don't forget to -1 day
        if () == collprob:
            return await error_occured(callback, "wu")

        kb = [[types.InlineKeyboardButton(
            text = "Вернуться",
            callback_data = "menu_callback_redirect"
        )]]

        fetch = cur.execute(
            "SELECT doneBy FROM tests_table WHERE testID == ?",
            [collprob[0][0]]
        ).fetchone()
        if callback.from_user.id in fetch[0]:
            keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
            return await callback.message.edit_text(
                text = "Вы уже решили этот сборник задач.",
                reply_markup = keyboard
            )

        scene_data.update(redirect_after_solving = "collprob_continue")
        scene_data.update(collprob_rowid = int(ident))
        scene_data.update(collprob_step = 1)
        scene_data.update(test_id = int(collprob[0][0]))
        await self.wizard.update_data(scene_data = scene_data)
        kb = [[types.InlineKeyboardButton(
                text = "Решить",
                callback_data = "solve"
            )]] + kb
        keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
        msg = f"{collprob[1]}\nОт {collprob[2]}\n\nНа решение остал"
        time = collprob[3].lstrip('0').split()
        if len(time) != 1:
            time[0] = int(time[0]) - 1
            if time[0] % 10 == 1 and time[0] % 100 != 11:
                msg += f"ся {time[0]} день"
            msg += "ось "
            if time[0]%10>=2 and time[0]%10<5 and(time[0]%100<11 or time[0]%100>14):
                msg += f"{time[0]} дней "
            else:
                msg += f"{time[0]} дней "
        else:
            msg += "ось "
        msg += time[-1]

        await callback.message.edit_text(
            text = msg,
            reply_markup = keyboard
        )


@router.callback_query(F.data == "tests_manage")
@flags.permission("teacher")
async def tests_manage(callback: types.CallbackQuery, scenes: ScenesManager,
        state: FSMContext) -> None:
    await scenes.close()
    await state.update_data(scene_data = {})
    await scenes.enter("tests_scene")

@router.callback_query(F.data == "tests_list")
@flags.permission("student")
async def tests_complete(callback: types.CallbackQuery, scenes: ScenesManager,
        state: FSMContext) -> None:
    await scenes.close()
    await state.update_data(scene_data = {})
    await scenes.enter("tests_scene")
