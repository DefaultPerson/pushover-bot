from aiogram.types import CallbackQuery, Message, User


def reply_target(message: Message) -> User | None:
    """Author of the replied message, ignoring bots and the forum topic root."""
    reply = message.reply_to_message
    if not reply or not reply.from_user or reply.from_user.is_bot or reply.forum_topic_created:
        return None
    return reply.from_user


def button_is_real(callback: CallbackQuery) -> bool:
    """True if the pressed data belongs to a button on the message.

    Clients can send any callback data, so data that names its owner must be checked
    against the keyboard Telegram stored with the message.
    """
    markup = getattr(callback.message, "reply_markup", None)
    if not markup:
        return False
    return any(
        button.callback_data == callback.data for row in markup.inline_keyboard for button in row
    )
