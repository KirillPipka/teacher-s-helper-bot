#
# Exit codes: -1 -invalid authorization
#             -2 -invalid data
#(Change to normal https request statuses)

from datetime import datetime
from aiogram.filters.command import Command, CommandStart
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.scene import SceneRegistry, ScenesManager
from aiogram import Bot, Dispatcher, types, F, flags
import logging
import asyncio
import json
import sys
from permission_middleware import PermissionMiddleware
from utils import cur, db, bot, error_occured
import authorization
import collproblems
import paged_view
import tests

class UserInfo(StatesGroup):
    logged_as = State()
    additional_info = State()
    scene_data = State()

dp = Dispatcher()
logger = logging.getLogger(__name__)


@dp.message(CommandStart())
@flags.skip_permission_middleware("True")
async def menu_start_redirect(message: types.Message, state: FSMContext,
                              scenes: ScenesManager) -> None:
    await state.set_state(UserInfo.logged_as)
    await state.set_state(UserInfo.additional_info)
    await state.set_state(UserInfo.scene_data)
    await state.update_data(additional_info = {"dataFor": 0, "text":""})
    await scenes.close()
    logged_as = await authorization.authorization_check(message, state)
    if logged_as == 0:
        await menu_student(message, state)
    elif logged_as == 1:
        await menu_teacher(message, state)

@dp.message(F.text[0] != "/")
@flags.permission("all")
async def message_redirect(message: types.Message, state: FSMContext,
                           scenes: ScenesManager) -> None:
    txt = message.text
    additional_inf = (await state.get_data())["additional_info"]
    if not ("text" in additional_inf.keys()):
        additional_inf.update({"text":""})

    if additional_inf in [3, 5, 6]:
        additional_inf["text"] = txt
        await state.update_data(additional_info = additional_inf)

    match additional_inf["dataFor"]:
        case 1:
            if txt[0] == "[" and txt[-1] == "]"  and \
               txt[1:txt.find(",")].lstrip("-").isdigit() and \
               txt[txt.find(" ")+1:-1].lstrip("-").isdigit():

                additional_inf["text"] = txt
                await state.update_data(additional_info = additional_inf)
                await tests.teacher_tests_set_modifies(message, state)
        case 3:
            additional_inf.update(dataFor=10)
            await state.update_data(additional_info=additional_inf)
            return await back_to_scene(data=message,scenes=scenes,state=state)
        case 5:
            return await collproblems.teacher_colprob_create_1(message, state)
        case 6:
            return await collproblems.teacher_colprob_create_2(message, state)
        case 7:
            return await collproblems.teacher_colprob_create_3(message, state)

@dp.callback_query(F.data[:13] == "back_to_scene")
@flags.permission("all")
async def back_to_scene(data: types.CallbackQuery | types.Message,
                        scenes: ScenesManager, state: FSMContext) -> None:
    if type(data) == types.CallbackQuery:
        identification = data.data[13:]
    elif type(data) == types.Message:
        identification = ''
    else:
        logger.ERROR("type(data) in back_to_scene is unknown: "+str(type(data)))
        return

    additional_info = (await state.get_data())["additional_info"]
    back_to: str
    step: int
    match additional_info["dataFor"]:
        case 9:
            back_to = additional_info["pagedview_args"]["back_to"]
            step = additional_info["pagedview_args"]["step"]
        case 10:
            back_to = additional_info["b2s_args"]["back_to"]
            step = additional_info["b2s_args"]["step"]
        case _:
            return
    if type(await scenes._get_active_scene()).__name__ != back_to:
        return

    await scenes.enter(
        scene_type=tests.TestsScene,
        _check_active=False,
        entered_step=step,
        identification=identification
    )

@dp.callback_query(F.data == "menu_callback_redirect")
@flags.permission("all")
async def menu_callback_redirect(callback: types.CallbackQuery, state: FSMContext,
                                 scenes: ScenesManager) -> None:
    logged_as = (await state.get_data())["logged_as"]
    await state.update_data(additional_info = {"dataFor": 0, "text":""})
    await scenes.close()
    await callback.message.edit_text(callback.message.text)
    if logged_as == 0:
        await menu_student(callback.message, state)
    elif logged_as == 1:
        await menu_teacher(callback.message, state)

async def menu_teacher(message, state) -> None | int:
    if (await state.get_data())["logged_as"] != 1:
        await error_occured(message, "lt", "menu_teacher")
    
    kb = [[types.InlineKeyboardButton(text = "Создание тестов",
                                      callback_data = "tests_manage")],
          [types.InlineKeyboardButton(text = "Управление тестами",
                                      callback_data = "teacher_tests_control")],
          [types.InlineKeyboardButton(text = "Создание сборника задач",
                                      callback_data = "teacher_colprob_create0")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
    await message.answer("Меню учителя.", reply_markup = keyboard)

async def menu_student(message, state):
    if (await state.get_data())["logged_as"] != 0:
        await error_occured(message, "ls", "menu_student")

    kb = [[types.InlineKeyboardButton(text = "Проверить задания",
                                      callback_data = "student_tests_list")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
    await message.answer("Меню ученика.", reply_markup = keyboard)

@dp.message(Command("stop"), flags={"skip_permission_middleware": True})   # Убрать в релизе
async def stop_bot(message: types.Message, state: FSMContext) -> None:
    logger.info("Closing database...")
    try:
        db.commit()
        db.close()
    except sqlite3.ProgrammingError:
        logger.WARN("Couldn't close database. Skipping.")
    logger.info("Clearing state...")
    await state.clear()
    await dp.stop_polling()
    logger.info("Program exited! Current time: "+str(datetime.today()))

async def main():
    logging.basicConfig(filename='logs.log', level=logging.INFO)
    dp.message.middleware(PermissionMiddleware())
    dp.callback_query.middleware(PermissionMiddleware())
    sr = SceneRegistry(dp)
    sr.add(tests.TestsScene)
    dp.include_routers(authorization.router, paged_view.router,
                       tests.router, collproblems.router)

    await dp.start_polling(bot)
    logger.info("Started polling at "+str(datetime.today()))

if __name__ == "__main__":
    asyncio.run(main())
