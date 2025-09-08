from aiogram.filters.command import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from utils import cur, db, error_occured
from aiogram import types, F, Router
from aiogram import flags

router = Router()

@router.message(Command("auth"))    # Добавить выполнение команды только администратору
@flags.permission("all")
async def add_user_authorization(message: types.Message, state: FSMContext,
                                 command: CommandObject) -> None:
    if command.args == "add student":
        cur.execute("INSERT INTO authorized VALUES (?, ?)", [message.from_user.id, 0])
        db.commit()
    elif command.args == "del student":
        cur.execute("DELETE FROM authorized WHERE authorizedAs == 0 AND userID == ?",
                    [message.from_user.id])
        db.commit()
    elif command.args == "add teacher":
        cur.execute("INSERT INTO authorized VALUES (?, ?)", [message.from_user.id, 1])
        db.commit()
    elif command.args == "del teacher":
        cur.execute("DELETE FROM authorized WHERE authorizedAs == 1 AND userID == ?",
                    [message.from_user.id])
        db.commit()
    else:
        await message.reply("Такой позиции не существует.")


async def authorization_menu(message: types.Message, state: FSMContext) -> None:
    kb = [[types.InlineKeyboardButton(text = "Ученика",
                                      callback_data = "authorization_student")],
          [types.InlineKeyboardButton(text = "Учителя",
                                      callback_data = "authorization_teacher")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
    
    await message.answer("В какой аккаунт Вы хотите зайти?",
                         reply_markup = keyboard)

@router.callback_query(F.data == "authorization_student")
@flags.skip_permission_middleware(True)
async def authorize_as_student(callback: types.CallbackQuery,
                               state: FSMContext) -> None:
    await state.update_data(logged_as = 0)
    kb = [[types.InlineKeyboardButton(text = "Продолжить",
                                      callback_data = "menu_callback_redirect")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
    await callback.message.edit_text("Готово! Вы вошли как ученик.",
                                     reply_markup = keyboard)

@router.callback_query(F.data == "authorization_teacher")
@flags.skip_permission_middleware(True)
async def authorize_as_teacher(callback: types.CallbackQuery,
                               state: FSMContext) -> None:
    await state.update_data(logged_as = 1)
    kb = [[types.InlineKeyboardButton(text = "Продолжить",
                                      callback_data = "menu_callback_redirect")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)
    await callback.message.edit_text("Готово! Вы вошли как учитель.",
                                     reply_markup = keyboard)

async def authorization_check(message: types.Message,
                              state: FSMContext) -> None | int:
    fetch = cur.execute("SELECT authorizedAs FROM authorized WHERE userID == ?",
                        [message.from_user.id]).fetchall()
    
    if len(fetch) != 0:
        # Fix corrupted data (might not need this)
        if len(fetch) != len(set(fetch)):
            cleared_from = []
            if 0 in fetch:
                cleared_from.append(0)
                cur.execute("""DELETE FROM authorized WHERE authorizedAs == 0
                               AND userID == ?""", [message.from_user.id])
            if 1 in fetch:
                cleared_from.append(1)
                cur.execute("""DELETE FROM authorized WHERE authorizedAs == 1
                               AND userID == ?""", [message.from_user.id])
            cur.execute("DELETE FROM authorized WHERE userID == ?",
                        [message.from_user.id])
            cur.executemany("INSERT INTO authorized VALUES (:userid, :loginas)",
                            [{"userid":message.from_user.id, "loginas":i} for \
                            i in range(2)])
        if ( (1,) in fetch ) and ( (0,) in fetch ):
            await authorization_menu(message, state)
            return None
        elif (0,) in fetch:
            await state.update_data(logged_as = 0)
            return 0
        elif (1,) in fetch:
            await state.update_data(logged_as = 1)
            return 1
    else:
        await state.update_data(logged_as = -1)
        await error_occured(message, "ln", "authorization_check")
