from aiogram.filters.command import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.scene import SceneRegistry, ScenesManager
from aiogram.utils.deep_linking import decode_payload, create_start_link
from aiogram import Dispatcher, types, F, flags
from datetime import datetime
import logging
import asyncio
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


@dp.message(CommandStart(deep_link = True))
@flags.skip_permission_middleware("True")
async def menu_start_ref_rredirect(message: types.Message, state: FSMContext,
        scenes: ScenesManager, command: CommandObject) -> None:
    payload = decode_payload(command.args)
    username = message.from_user.username
    # Some users don't have username, so assume it's id if no username
    if username == None:
        username = str(message.from_user.id)

    if payload[:len(username)] != username:
        return await message.answer("""Неправильная реферальная ссылка!
Проверьте, что вы правильно скопировали ссылку и попробуйте ещё раз""")
    payload = payload[len(username):]
    registered_as = '<пусто>'
    add_inf = ""
    if payload[0] == 't':
        cur.execute(
            "INSERT INTO authorized VALUES (?, ?)",
            [message.from_user.id, 1]
        )
        registered_as = "учитель"
        cur.execute("""
            INSERT INTO
                classes_table
            VALUES
                (?, ?, 9, '9Г')
        """, [message.from_user.id, [message.from_user.id, 3, 4, 5748567108]])
        add_inf = "\nК вам автоматически прикрепили класс <9Г>, пожалуйста, не \
прописывайте эту ссылку снова!"
    if payload[0] == 's':
        cur.execute(
            "INSERT INTO authorized VALUES (?, ?)",
            [message.from_user.id, 0]
        )
        registered_as = "ученик"
    db.commit()

    await message.answer(
        f"""Вы были зарегистрированны в систему как {registered_as}{add_inf}
Чтобы продолжить, напишите /start"""
    )

@dp.message(CommandStart(deep_link = False))
@flags.skip_permission_middleware("True")
async def menu_start_redirect(message: types.Message, state: FSMContext,
        scenes: ScenesManager) -> None:
    await state.set_state(UserInfo.logged_as)
    await state.set_state(UserInfo.additional_info)
    await state.set_state(UserInfo.scene_data)
    await state.update_data(additional_info = {
        "dataFor": 0,
        "text": ""
    })
    await scenes.close()

    logged_as = await authorization.authorization_check(message, state)
    if logged_as == 0:
        await menu_student(message, state)
    elif logged_as == 1:
        await menu_teacher(message, state)

@dp.message(Command("ref"))
@flags.permission("teacher")
async def ref_link_create(message: types.Message, command: CommandObject):
    args = command.args.split()
    if len(args) != 2 or args[1] not in ('s', 't'):
        return await message.reply(
            "Неправильный формат.\n/ref <username/userid> t/s"
        )
    link = await create_start_link(bot, ''.join(args), encode = True)

    return await message.reply("Сгенерированная ссылка: " + link)

@dp.message(F.text[0] != "/")
@flags.permission("all")
async def message_redirect(message: types.Message, state: FSMContext,
        scenes: ScenesManager) -> None:
    additional_info = (await state.get_data())["additional_info"]

    if additional_info["dataFor"] == 3:
        additional_info.update(text = message.text)
        additional_info.update(dataFor = 10)
        await state.update_data(additional_info = additional_info)
        return await back_to_scene(
            data = message,
            scenes = scenes,
            state = state
        )

@dp.callback_query(F.data[:13] == "back_to_scene")
@flags.permission("all")
async def back_to_scene(data: types.CallbackQuery | types.Message,
        scenes: ScenesManager, state: FSMContext) -> None:
    additional_info = (await state.get_data())["additional_info"]
    if type(data) == types.CallbackQuery:
        identification = data.data[13:]
    elif type(data) == types.Message:
        try:
            identification = additional_info["b2s_args"]["identification"]
        except KeyError:
            identification = ''
    else:
        logger.error("type(data) in back_to_scene is unknown: " + str(type(data)))
        return

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
    kwargs = {"entered_step": step, "identification": identification}

    # This check is here because it lets re-enter scene without waiting
    if not isinstance(
        await scenes._get_active_scene(),
        type(await scenes._get_scene(back_to))
    ):
        return

    await scenes.enter(
        scene_type = back_to,
        _check_active = False,
        **kwargs
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
    
    kb = [[types.InlineKeyboardButton(
            text = "Создание тестов",
            callback_data = "tests_manage"
        )],
        [types.InlineKeyboardButton(
            text = "Управление сборниками задач",
            callback_data = "collproblems_manage"
    )]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
    await message.answer("Меню учителя.", reply_markup = keyboard)

async def menu_student(message, state):
    if (await state.get_data())["logged_as"] != 0:
        await error_occured(message, "ls", "menu_student")

    kb = [[types.InlineKeyboardButton(
            text = "Проверить задания",
            callback_data = "tests_list"
    )]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
    await message.answer("Меню ученика.", reply_markup = keyboard)

@dp.message(Command("stop"), flags = {"skip_permission_middleware": True})   # Убрать в релизе
@flags.permission("all")
async def stop_bot(message: types.Message, state: FSMContext) -> None:
    logger.info("Closing database...")
    try:
        db.commit()
        db.close()
    except sqlite3.ProgrammingError:
        logger.warning("Couldn't close database. Skipping.")
    logger.info("Clearing state...")
    await state.clear()
    await dp.stop_polling()
    logger.info("Program exited! Current time: " + str(datetime.today()))

async def main():
    logging.basicConfig(filename = 'logs.log', level = logging.INFO)
    dp.message.middleware(PermissionMiddleware())
    dp.callback_query.middleware(PermissionMiddleware())
    sr = SceneRegistry(dp)
    sr.add(
        tests.TestsScene,
        collproblems.ColproblemsScene
    )
    dp.include_routers(
        authorization.router,
        paged_view.router,
        tests.router,
        collproblems.router
    )

    logger.info("Starting polling at " + str(datetime.today()))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
