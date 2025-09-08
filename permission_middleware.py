##from aiogram.dispatcher.event.bases import SkipHandler

from aiogram.dispatcher import flags
from typing import Any, Callable, Dict, Awaitable
from aiogram import types, BaseMiddleware
from utils import error_occured

class PermissionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if flags.get_flag(data, "skip_permission_middleware"):
            return await handler(event, data)
        logged_as = (await data["state"].get_data())["logged_as"]
        permission_for: str = flags.get_flag(data, "permission")
        if permission_for == "teacher" and logged_as == 1:
            return await handler(event, data)
        elif permission_for == "student" and logged_as == 0:
            return await handler(event, data)
        elif permission_for == "all" and logged_as != -1:
            return await handler(event, data)

        message: types.Message = data['event_update']
        if permission_for == "teacher":
            await error_occured(message, "lt") #### no return ###############################
        elif permission_for == "student":
            await error_occured(message, "ls") #### no return ###############################
        return await error_occured(message, "ln")

