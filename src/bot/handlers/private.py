import re
from pathlib import Path
from typing import Callable

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

from src.bot.filters import IsPrivate
from src.bot.keyboards import get_groups_keyboard, get_language_keyboard
from src.db.repositories import SubscriptionRepository, UserRepository
from src.services.pushover import pushover_client

router = Router()
router.message.filter(IsPrivate())

# Path to image showing Pushover settings
KEY_IMAGE_PATH = Path(__file__).parent.parent.parent.parent / "assets" / "image.png"


class KeySetup(StatesGroup):
    waiting_for_key = State()


@router.message(Command("key"))
async def cmd_key(message: Message, state: FSMContext, _: Callable) -> None:
    await state.set_state(KeySetup.waiting_for_key)
    if KEY_IMAGE_PATH.exists():
        await message.answer_photo(
            FSInputFile(KEY_IMAGE_PATH),
            caption=_("key_prompt"),
        )
    else:
        await message.answer(_("key_prompt"))


@router.message(Command("cancel"), StateFilter(KeySetup.waiting_for_key))
async def cmd_cancel_key(message: Message, state: FSMContext, _: Callable) -> None:
    await state.clear()
    await message.answer(_("key_cancelled"))


@router.message(KeySetup.waiting_for_key, F.text, ~F.text.startswith("/"))
async def process_key(message: Message, state: FSMContext, _: Callable) -> None:
    key = message.text.strip()

    # Validate format (30 alphanumeric characters)
    if not re.match(r"^[a-zA-Z0-9]{30}$", key):
        await message.answer(_("key_invalid"))
        return

    # Validate with Pushover API
    is_valid = await pushover_client.validate_user_key(key)
    if not is_valid:
        await message.answer(_("key_validation_failed"))
        return

    # Save key
    await UserRepository.set_pushover_key(message.from_user.id, key)
    await state.clear()

    # Check if user already has active subscriptions
    sub_count = await SubscriptionRepository.get_active_subscription_count(message.from_user.id)
    if sub_count > 0:
        await message.answer(_("key_updated_existing", count=sub_count))
    else:
        await message.answer(_("key_saved"))


@router.callback_query(F.data == "cancel", StateFilter(KeySetup.waiting_for_key))
async def cancel_key_setup(callback: CallbackQuery, state: FSMContext, _: Callable) -> None:
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(_("key_cancelled"))
    await callback.answer()


@router.message(Command("list"))
async def cmd_list(message: Message, _: Callable) -> None:
    groups = await SubscriptionRepository.get_user_groups(message.from_user.id)

    if not groups:
        await message.answer(_("list_empty"))
        return

    # Normalize groups: replace None titles with ID fallback
    normalized_groups = [
        (group_id, title or f"ID: {group_id}", bot_active)
        for group_id, title, bot_active in groups
    ]

    await message.answer(
        _("list_header"),
        reply_markup=get_groups_keyboard(normalized_groups),
    )


@router.message(Command("language"))
async def cmd_language(message: Message, _: Callable) -> None:
    await message.answer(_("language_select"), reply_markup=get_language_keyboard())


@router.callback_query(F.data.startswith("lang:"), F.message.chat.type == "private")
async def process_language(callback: CallbackQuery, _: Callable) -> None:
    """Process language selection in private chat only."""
    lang = callback.data.split(":")[1]
    await UserRepository.set_language(callback.from_user.id, lang)

    # Update command menu for this user
    from aiogram.types import BotCommandScopeChat
    from src.bot.commands import PRIVATE_COMMANDS, ADMIN_COMMANDS
    from src.config import settings

    commands = PRIVATE_COMMANDS.get(lang, PRIVATE_COMMANDS["en"])
    if callback.from_user.id in settings.admin_ids_list:
        commands = commands + ADMIN_COMMANDS

    await callback.bot.set_my_commands(
        commands,
        scope=BotCommandScopeChat(chat_id=callback.from_user.id),
    )

    # Get new locale text
    from src.i18n import get_text

    await callback.message.edit_text(get_text("language_changed", lang))
    await callback.answer()
