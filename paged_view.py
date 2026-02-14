from aiogram.fsm.context import FSMContext
from aiogram.handlers import CallbackQueryHandler
from aiogram import flags, Router, F, types
from typing import Any
from utils import error_occured
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data[:10] == "pagedview_")
@flags.permission("all")
class PagedView(CallbackQueryHandler):
    async def handle(self, state: FSMContext = FSMContext) -> Any:
        """
        Required __init__ `kwargs` field with arguments
        permission   ="student"|"teacher"|"all",
        function_name=str  #handler where init was run from
        pages        =list[list[InlineKeyboardButton,...]] | list[InlineKeyboardButton,...]
        mainmenu_text=str
        back_to      =str  #CallbackQuery to go back to
        forward_to   =str  #CallbackQuery to go forward to(None to skip)

        Optional fields:
        arguments    =Any  #Will be passed in state
        """
        state = self.data.get("state", state)
        print("updated.")
        logged_as = (await state.get_data())["logged_as"]
        util_data = (await state.get_data()).get("util_data")
        # Storing all paged_view data in state putting it in self.data
        if util_data and util_data.get("util_name") == "paged_view" \
                and not self.data.get("function_name"):
            self.data.update(util_data)
        else:
            # If previous event wasn't paged_view's event or has another invoke
            # then we need to regenerate everything and put in state
            util_data = {}
            util_data.update(page = 0)
            util_data.update(util_name = "paged_view")
            util_data.update(permission = self.data["permission"])
            util_data.update(pages = self.data["pages"])
            util_data.update(mainmenu_text = self.data["mainmenu_text"])
            util_data.update(back_to = self.data["back_to"])
            util_data.update(forward_to = self.data["forward_to"])
            if self.data.get("arguments"):
                util_data.update(arguments = self.data["arguments"])
            # Only for debug. If no bugs presist then remove
            util_data.update(function_name = self.data["function_name"])
            await state.update_data(util_data = util_data)

            if len(self.data["pages"]) == 0:
                msg = "Pages could not be found in paged_view by name function"+\
                      self.data["function_name"]
                logger.error(msg)
                return await error_occured("e")
            await state.update_data(additional_info = {
                "dataFor": 9,
                "pagedview_args": self.data["arguments"]
            })
            await state.update_data(util_data = util_data)

        # If list[list[button],...] then skip, otherwise list[button,...]
        if type(self.data["pages"][0]) != list:
            print("updated")
            pages = []
            for i in range(0, len(self.data["pages"]), 5):
                pages.append(self.data["pages"][i:i+5])
            self.data["pages"] = pages

        if self.data["permission"] == "student" and logged_as != 0:
            return await error_occured("ls")
        elif self.data["permission"] == "teacher" and logged_as != 1:
            return await error_occured("lt")
        elif self.data["permission"] == "all" and logged_as == -1:
            return await error_occured("ln")

        additional_info = (await state.get_data())["additional_info"]

        if self.callback_data[10:] == "F": # Forward
            return await self.__page_change(direction = "forward", state = state)
        elif self.callback_data[10:] == "B": # Backward
            return await self.__page_change(direction = "backward", state = state)
        else:
            return await self.__main_menu(state=state)

    async def __page_change(self, direction: str, state: FSMContext) -> Any:
        util_data = (await state.get_data())["util_data"]
        current_page = util_data["page"]
        match direction:
            case "forward":
                current_page += 1
            case "backward":
                current_page -= 1
        if current_page < 0:
            current_page = 0
        elif current_page >= len(self.data["pages"]):
            current_page = len(self.data["pages"]) - 1
        util_data.update(page = current_page)
        await state.update_data(util_data = util_data)
        return await self.__main_menu(state=state)

    async def __main_menu(self, state: FSMContext) -> Any:
        util_data = (await state.get_data())["util_data"]
        current_page = util_data["page"]
        if current_page < 0:
            current_page = 0
        elif current_page >= len(self.data["pages"]):
            current_page = len(self.data["pages"]) - 1

        kb = []
        for row in self.data["pages"][current_page]:
            kb.append([row])
        kb.append([])

        if current_page != 0:
            kb[-1] = [types.InlineKeyboardButton(
                text = "Назад",
                callback_data = "pagedview_B"
            )]
        if current_page != len(self.data["pages"]) - 1:
            kb[-1].append(types.InlineKeyboardButton(
                text = "Вперёд",
                callback_data = "pagedview_F"
            ))

        if self.data["forward_to"] != None:
            kb.append([types.InlineKeyboardButton(
                text = "Далее",
                callback_data = self.data["forward_to"]
            )])
        kb.append([types.InlineKeyboardButton(
            text = "Вернуться",
            callback_data = self.data["back_to"]
        )])

        keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)

        await self.message.edit_text(
            self.data["mainmenu_text"],
            reply_markup = keyboard
        )
