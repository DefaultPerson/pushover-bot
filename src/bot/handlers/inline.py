"""Inline mode: '@bot [name] [text]' in a group picks whom to wake.

Telegram delivers messages posted through the bot's inline mode even to a
non-admin bot in privacy mode, so this path never loses an alert. The
posted message carries the target in its button; group.on_inline_gm sends it.
"""

import html
from collections.abc import Callable

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultsButton,
    InputTextMessageContent,
)

from src.bot.keyboards import get_inline_gm_keyboard
from src.db.models import User
from src.db.repositories import SubscriptionRepository

router = Router()

# Telegram accepts at most 50 results per answer
MAX_RESULTS = 50


def _article(
    target: str, title: str, header: str, text: str, _: Callable
) -> InlineQueryResultArticle:
    return InlineQueryResultArticle(
        id=target,
        title=title,
        description=text or _("inline_default_text"),
        input_message_content=InputTextMessageContent(
            message_text=f"{html.escape(header)}\n{html.escape(text)}".rstrip()
        ),
        reply_markup=get_inline_gm_keyboard(target),
    )


def _matches(user: User, name_filter: str) -> bool:
    return (
        name_filter in (user.full_name or "").lower()
        or name_filter in (user.username or "").lower()
    )


@router.inline_query()
async def inline_gm(query: InlineQuery, _: Callable) -> None:
    """'Everyone in this chat' first, then people whose name contains the first word."""
    if query.chat_type not in ("group", "supergroup"):
        await query.answer(
            [],
            cache_time=0,
            is_personal=True,
            button=InlineQueryResultsButton(text=_("inline_only_groups"), start_parameter="inline"),
        )
        return

    text = query.query.strip()
    parts = text.split(maxsplit=1)
    name_filter = parts[0].lower().removeprefix("@") if parts else ""
    person_text = parts[1] if len(parts) > 1 else ""

    # "Everyone" names nobody, so the whole query is its text
    results = [_article("all", _("inline_all_title"), _("inline_all_header"), text, _)]
    for user in await SubscriptionRepository.get_inline_candidates(query.from_user.id):
        if len(results) == MAX_RESULTS:
            break
        if name_filter and not _matches(user, name_filter):
            continue
        name = user.display_name
        results.append(
            _article(
                str(user.id),
                name,
                _("inline_user_header", name=name),
                person_text,
                _,
            )
        )

    await query.answer(results, cache_time=0, is_personal=True)


@router.callback_query(F.data.startswith("ig:"))
async def inline_gm_button(callback: CallbackQuery) -> None:
    """The button only carries the target; pressing it does nothing."""
    await callback.answer()
