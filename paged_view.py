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
    async def handle(self, state: FSMContext) -> Any:
        """
        Required __init__ `kwargs` field with arguments
        permission   ="student"|"teacher"|"all",
        function_name=str  #handler where init was run from
        pages        =list[list[InlineKeyboardButton]] | list[InlineKeyboardButton]
        mainmenu_text=str
        back_to      =str  #CallbackQuery to go back to
        forward_to   =str  #CallbackQuery to go forward to(None to skip)

        Optional fields:
        arguments    =Any  #Will be passed in state
        """
        logged_as = (await state.get_data())["logged_as"]

        if self.data["permission"] == "student" and logged_as != 0:
            return await error_occured("ls")
        elif self.data["permission"] == "teacher" and logged_as != 1:
            return await error_occured("lt")
        elif self.data["permission"] == "all" and logged_as == -1:
            return await error_occured("ln")

        additional_info = (await state.get_data())["additional_info"]

        # If between PagedView handlers there was one non-pagedview handler
        if not (additional_info["dataFor"] == 9 and
                additional_info["pagedview_name"] == self.data["function_name"]):
            if len(self.data["pages"]) == 0:
                msg = "Pages could not be found in paged_view by name function"+\
                      self.data["function_name"]
                logger.ERROR(msg)
                return await error_occured("e")

            await state.update_data(additional_info={
                "dataFor": 9,
                "pagedview_name": self.data["function_name"],
                "pagedview_page": 0,
                "pagedview_args": self.data["arguments"]
            })

            if type(self.data["pages"][0]) != list:
                pages = []
                for i in range(0, len(self.data["pages"]), 5):
                    pages.append(self.data["pages"][i:i+5])
                self.data["pages"] = pages

        if self.callback_data[10:] == "F": # Forward
            return await self.__page_change(direction="forward", state=state)
        elif self.callback_data[10:] == "B": # Backward
            return await self.__page_change(direction="backward", state=state)
        else:
            return await self.__main_menu(state=state)
        '''else:
            if "prev" not in additional_info.keys():
                additional_info.update(prev=[])
            additional_info.update(prev=additional_info["prev"]+
                                        self.callback_data()[10:])
            await self.state().update_data(additional_info=additional_info)'''

    async def __page_change(self, direction: str, state: FSMContext) -> Any:
        additional_info = (await state.get_data())["additional_info"]
        current_page = additional_info["pagedview_page"]
        match direction:
            case "forward":
                current_page += 1
            case "backward":
                current_page -= 1
        if current_page < 0:
            current_page = 0
        elif current_page >= len(self.data["pages"]):
            current_page = len(self.data["pages"]) - 1
        await state.update_data(additional_info={
            "dataFor": 9,
            "pagedview_name": self.data["function_name"],
            "pagedview_page": 0,
            "pagedview_args": self.data["arguments"]
        })
        return await self.__main_menu(state=state)

    async def __main_menu(self, state: FSMContext) -> Any:
        additional_info = (await state.get_data())["additional_info"]
        current_page = additional_info["pagedview_page"]
        if current_page < 0:
            current_page = 0
        elif current_page >= len(self.data["pages"]):
            current_page = len(self.data["pages"]) - 1

        kb = []
        for row in self.data["pages"][current_page]:
            kb.append([row])
        kb.append([])

        if current_page != 0:
            kb[-1] = [[types.InlineKeyboardButton(
                text = "Назад",
                callback_data = "pagedview_B"
            )]]
        if current_page != len(self.data["pages"]) - 1:
            kb[-1].append([types.InlineKeyboardButton(
                text = "Вперёд",
                callback_data = "pagedview_F"
            )])

        if self.data["forward_to"] != None:
            kb.append([types.InlineKeyboardButton(
                text = "Готово",
                callback_data = self.data["forward_to"]
            )])
        kb.append([types.InlineKeyboardButton(
            text = "Вернуться",
            callback_data = self.data["back_to"]
        )])

        keyboard = types.InlineKeyboardMarkup(inline_keyboard = kb)

        await self.message.edit_text(self.data["mainmenu_text"],
                                     reply_markup=keyboard)
