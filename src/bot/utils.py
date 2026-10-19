from aiogram.types import Message, User


def reply_target(message: Message) -> User | None:
    """Author of the replied message, ignoring bots and the forum topic root."""
    reply = message.reply_to_message
    if not reply or not reply.from_user or reply.from_user.is_bot or reply.forum_topic_created:
        return None
    return reply.from_user
