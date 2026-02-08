# Short name of `collection of problems` is `colProb`

from datetime import datetime
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, ScenesManager, on
from aiogram import types, F, Router, flags
import numpy as np
from utils import cur, db, bot, error_occured
from paged_view import PagedView
import logging

router = Router()

# Teacher functions to make collections of problems


class ColproblemsScene(Scene, state = "collproblems_scene"):
    @on.callback_query.enter()
    async def on_enter_callback(self, callback: types.CallbackQuery,
            entered_step: int = 0, identification: str = ''):
        if (await self.wizard.get_data())["logged_as"] == 1:
            match entered_step:
                case 1:
                    return await self.create_0(
                        callback = callback,
                        ident = identification
                    )
                case 4:
                    return await self.view(
                        callback = callback,
                        ident = identification
                    )
                case 5:
                    return await self.edit(
                        callback = callback,
                        ident = identification
                    )
        elif (await self.wizard.get_data())["logged_as"] == 0:
            return
            

    @on.message.enter()
    async def on_enter_message(self, message: types.Message,
            entered_step: int = 0, identification: str = ''):
        if (await self.wizard.get_data())["logged_as"] == 1:
            match entered_step:
                case 2:
                    return await self.create_2(
                        message = message
                    )
                case 3:
                    return await self.create_3(
                        message = message
                    )

        elif (await self.wizard.get_data())["logged_as"] == 0:
            return
        else:
            return

    # This function is being started from `on_enter` only
    async def create_0(self, callback: types.CallbackQuery, ident: str):
        scene_data = (await self.wizard.get_data())["scene_data"]
        additional_info = (await self.wizard.get_data())["additional_info"]
        if ident == '-1':
            return await self.create_1(
                callback = callback
            )
        fetch = np.array(cur.execute("""
            SELECT
                classID,
                name
            FROM
                classes_table
            WHERE
                teacherID == ?
            """, [callback.from_user.id]
        ).fetchall(), dtype="<U21")

        # Creating mask for already marked options and new one
        if ident == '':
            msg = """Выберите классы, к которым нужно добавить задание
(Если ещё не знаете, к каким классам хотите добавить задания - нажмите "пропустить")"""
            selected = np.array([], dtype = "<U21")
        else:
            msg = "Выберите классы, к которым нужно добавить задание"
            selected = np.append(scene_data["selected_options"], int(ident))

        scene_data.update(selected_options = selected)
        additional_info.update(dataFor = 2)     # Empty dataFor to recreate pages
        await self.wizard.update_data(scene_data = scene_data)
        await self.wizard.update_data(additional_info = additional_info)

        # Marking fetch entries using previously created mask
        select_map = np.isin(fetch[:, 0], selected)
        fetch[select_map, 1] = [i.upper()+" (ВЫБРАН)" for i in fetch[select_map, 1]]

        pages: list[types.InlineKeyboardButton, ...] = []
        for i in range(len(fetch)):
            pages.append(types.InlineKeyboardButton(
                text = str(fetch[i, 1]),
                callback_data = f"back_to_scene{fetch[i, 0]}"
            ))

        # Using keyboard builder
        return await PagedView(event = self.wizard.event,
            permission = "teacher",
            function_name = "colproblems_create_0",
            pages = pages,
            mainmenu_text = msg,
            back_to = "menu_callback_redirect",
            forward_to = "back_to_scene-1",
            arguments = {"back_to": "collproblems_scene", "step": 1}
        ).handle(state = self.wizard.state)

    # This function is being started from `on_enter` only
    async def create_1(self, callback: types.CallbackQuery):
        scene_data = (await self.wizard.get_data())["scene_data"]
        additional_info = (await self.wizard.get_data())["additional_info"]
        additional_info.update(dataFor = 3)
        additional_info.update(b2s_args = {
            "back_to": "collproblems_scene",
            "step": 2
        })
        await self.wizard.update_data(scene_data = scene_data)
        await self.wizard.update_data(additional_info = additional_info)
        kb = [[types.InlineKeyboardButton(
            text = "Отмена",
            callback_data = "menu_callback_redirect"
        )]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
        msg = """Создание сборника задач.
Введите название сборника(по умолчанию берётся дата создания):
Чтобы взять значение по умолчанию, отправьте любой символ."""
        return await callback.message.edit_text(
            text = msg,
            reply_markup = keyboard
        )

    # This function is being started from `on_enter` only
    async def create_2(self, message: types.Message):
        scene_data = (await self.wizard.get_data())["scene_data"]
        additional_info = (await self.wizard.get_data())["additional_info"]
        name = additional_info["text"]

        kb = [[types.InlineKeyboardButton(
            text = "Отмена",
            callback_data = "menu_callback_redirect"
        )]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)

        # Ask user to try again
        additional_info.update(dataFor = 3)
        additional_info.update(b2s_args = {
            "back_to": "collproblems_scene",
            "step": 2
        })
        await self.wizard.update_data(additional_info = additional_info)

        if len(name) == 1:
            name = datetime.today().strftime("%H:%M %d.%m.%y")
        elif len(name) > 20:
            return await bot.send_message(
                text = """Имя слишком длинное(максимум 20 символов)
Попробуйте другое""",
                chat_id = message.chat.id,
                reply_markup = keyboard
            )
        elif len(name) < 5:
            return await bot.send_message(
                text = """Имя слишком короткое(минимум 5 символов
Попробуйте другое""",
                chat_id = message.chat.id,
                reply_markup = keyboard
            )

        additional_info.update(b2s_args = {
            "back_to": "collproblems_scene",
            "step": 3
        })
        scene_data.update(name = name)
        await self.wizard.update_data(additional_info = additional_info)
        await self.wizard.update_data(scene_data = scene_data)
        msg = """Создание сборника задач.
Введите время выполнения(по умолчанию одна неделя, для этого отправьте один символ)\
, время можно указать в днях(Д) и неделях(Н):
Принимается формат [число]Д или [число]Н"""
        return await bot.send_message(
            text = msg,
            chat_id = message.chat.id,
            reply_markup = keyboard
        )

    # This function is being started from `on_enter` only
    async def create_3(self, message: types.Message):
        additional_info = (await self.wizard.get_data())["additional_info"]
        scene_data = (await self.wizard.get_data())["scene_data"]
        text = additional_info["text"]
        msg = "Выберите задачи, которые необходимо добавить в сборник."

        if text[-1] == 'Н':
            days = 7
        elif text[-1] == 'Д':
            days = 1
        else:
            days = 1
            msg = """Вы не указали измерение времени - в днях(Д) или неделях(Н).
Автоматически выбирается измерение в днях.\n""" + msg

        if len(text) == 1 and text != 'Д':
            days = 7
        elif text[:-1].isdigit():
            days *= int(text[:-1])
        elif text.isdigit():
            days *= int(text)
        elif len(text) != 1:
            # Try again
            additional_info.update(dataFor = 3)
            additional_info.update(b2s_args = {
                "back_to": "collproblems_scene",
                "step": 3
            })
            return await error_occured(message, "wi")

        scene_data.update(dedicated_time = days)
        await self.wizard.update_data(scene_data = scene_data)

        if scene_data.get("exit_earlier"):
            return await self.wizard.goto(
                "tests_scene",
                entered_step = 11
            )

        kb = [[types.InlineKeyboardButton(
            text = "Отмена",
            callback_data = "menu_callback_redirect"
        )]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)

        return await bot.send_message(
            text = msg,
            chat_id = message.chat.id,
            reply_markup = keyboard
        )

    @on.callback_query(F.data == "view")
    @flags.permission("teacher")
    async def view(self, callback: types.CallbackQuery, ident: str = ''):
        pages = []
        size = max(map(lambda x: x[0], cur.execute(
            "SELECT LENGTH(name) FROM collections_table WHERE teacherID == ?",
            [callback.from_user.id]
        ).fetchall())) + 10
        fetch = np.array(
            cur.execute("""
                SELECT
                    rowid,
                    name
                FROM
                    collections_table
                WHERE
                    teacherID == ?
                ORDER BY
                    rowid ASC
            """, [callback.from_user.id]).fetchall(),
            dtype = [("f0", np.int32), ("f1", f"<U{size}")]
        )
        scene_data = (await self.wizard.get_data())["scene_data"]
        additional_info = (await self.wizard.get_data())["additional_info"]

        if len(fetch.shape) == 0:
            return await error_occured(callback.message, "wu")

        # Creating mask for already marked options and new one
        if ident == '':
            selected = np.array([], dtype = np.int32)
        else:
            selected = np.append(scene_data["selected_options"], int(ident))

        scene_data.update(selected_options = selected)
        additional_info.update(dataFor = 2)     # Empty dataFor to recreate pages
        await self.wizard.update_data(scene_data = scene_data)
        await self.wizard.update_data(additional_info = additional_info)

        # Marking fetch entries using previously created mask
        select_map = np.isin(fetch['f0'], selected)
        np.putmask(
            fetch['f1'],
            select_map,
            np.astype(fetch['f1'] + " (ВЫБРАН)", f"<U{size}")
        )

        for i in range(len(fetch)):
            pages.append(types.InlineKeyboardButton(
                text = str(fetch[i][1]),
                callback_data = f"back_to_scene{fetch[i][0]}"
            ))

        if len(pages) == 0:
            pages.append([types.InlineKeyboardButton(
                text = "Создать новый сборник задач[не работает]",
                callback_data = 'dasdas'
            )])
            pages.append([types.InlineKeyboardButton(
                text = "Вернуться",
                callback_data = "menu_callback_redirect"
            )])
            keyboard = types.InlineKeyboardMarkup(inline_keyboard = pages)
            return await callback.message.edit_text(
                text = "Похоже, здесь ещё ничего нет",
                reply_markup = keyboard
            )

        if scene_data.get("exit_earlier"):
            forward_to = "view_redirect"
            entering_step = 4
        else:
            forward_to = None
            entering_step = 5

        return await PagedView(event = self.wizard.event,
            permission = "teacher",
            function_name = "collproblems_view",
            pages = pages,
            mainmenu_text = "Созданные вами сборники задач:",
            back_to = "menu_callback_redirect",
            forward_to = forward_to,
            arguments = {"back_to": "collproblems_scene", "step": entering_step}
        ).handle(state = self.wizard.state)

    # This function is being started from `on_enter` only
    async def edit(self, callback: types.CallbackQuery, ident: str):
        msg = ""
        classes = []
        tasks_done = []
        kb = [[types.InlineKeyboardButton(
            text = "Вернуться",
            callback_data = "menu_callback_redirect"
        )]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
        
        fetch = cur.execute("""
            SELECT
                testsIDs,
                classIDs
            FROM
                collections_table
            WHERE
                rowid == ?
        """, [int(ident)]).fetchone()
        for i in fetch[1]:
            classes.append((lambda x: (x[0], set(x[1])))(cur.execute(
                "SELECT name, studentsID FROM classes_table WHERE classID == ?",
                [i]
            ).fetchone()))
        tasks_done.append(cur.execute(
            "SELECT doneBy FROM tests_table WHERE testID == ?",
            [fetch[0][0]]
        ).fetchone()[0].keys())
        tasks_done.append(cur.execute(
            "SELECT doneBy FROM tests_table WHERE testID == ?",
            [fetch[0][-1]]
        ).fetchone()[0].keys())

        for i in range(len(classes)):
            msg += f"\n\n=-=-= {classes[i][0]}\n"
            inters = len(tasks_done[0] & classes[i][1])
            if not inters:
                msg += "*Работу ещё никто не начал"
            else:
                msg += f"*Работу начали {inters} человек и закончили "
                msg += f"{len(tasks_done[1] & classes[i][1])}\n"
                msg += "*(больше статистики пока недоступно)"

        if classes == []:
            msg = "Вы не добавили классы для этого сборника"

        await callback.message.edit_text(
            text = msg,
            reply_markup = keyboard
        )

    @on.callback_query(F.data == "view_redirect")
    @flags.permission("teacher")
    async def view_redirect(self, callback: types.CallbackQuery):
        scene_data = (await self.wizard.get_data())["scene_data"]

        if scene_data.get("selected_options", []).size == 0:
            pages = [[types.InlineKeyboardButton(
                text = "Назад",
                callback_data = "view"
            )]]
            keyboard = types.InlineKeyboardMarkup(inline_keyboard = pages)
            return await callback.message.edit_text(
                text = "Вы не выбрали ни одного сборника!",
                reply_markup = keyboard
            )

        return await self.wizard.goto(
            "tests_scene",
            entered_step = 11
        )


@router.callback_query(F.data == "collproblems_manage")
@flags.permission("teacher")
async def collproblems_manage(callback: types.CallbackQuery, scenes: ScenesManager,
        state: FSMContext) -> None:
    await scenes.close()
    await state.update_data(scene_data = {})
    await scenes.enter("collproblems_scene", entered_step = 4)
