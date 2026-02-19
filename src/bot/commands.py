"""Bot command definitions for localized menus."""

from aiogram.types import BotCommand


# Private chat commands per language
PRIVATE_COMMANDS = {
    "en": [
        BotCommand(command="start", description="Start / Show info"),
        BotCommand(command="key", description="Configure Pushover key"),
        BotCommand(command="list", description="List groups with notifications"),
        BotCommand(command="test_alarm", description="Send test alarm"),
        BotCommand(command="language", description="Change language"),
        BotCommand(command="help", description="Show help"),
    ],
    "ru": [
        BotCommand(command="start", description="Начать / Показать информацию"),
        BotCommand(command="key", description="Настроить Pushover ключ"),
        BotCommand(command="list", description="Список групп с уведомлениями"),
        BotCommand(command="test_alarm", description="Тестовая сирена"),
        BotCommand(command="language", description="Сменить язык"),
        BotCommand(command="help", description="Справка"),
    ],
    "uk": [
        BotCommand(command="start", description="Почати / Показати інформацію"),
        BotCommand(command="key", description="Налаштувати Pushover ключ"),
        BotCommand(command="list", description="Список груп зі сповіщеннями"),
        BotCommand(command="test_alarm", description="Тестова сирена"),
        BotCommand(command="language", description="Змінити мову"),
        BotCommand(command="help", description="Допомога"),
    ],
}

# Group chat commands per language
GROUP_COMMANDS = {
    "en": [
        BotCommand(command="gm", description="Wake up everyone"),
        BotCommand(command="enable", description="Enable notifications"),
        BotCommand(command="disable", description="Disable notifications"),
        BotCommand(command="test_alarm", description="Send test alarm to yourself"),
        BotCommand(command="only_admin", description="Only admins can use /gm"),
        BotCommand(command="language", description="Change group language"),
        BotCommand(command="help", description="Show help"),
    ],
    "ru": [
        BotCommand(command="gm", description="Разбудить всех"),
        BotCommand(command="enable", description="Включить уведомления"),
        BotCommand(command="disable", description="Выключить уведомления"),
        BotCommand(command="test_alarm", description="Тестовая сирена себе"),
        BotCommand(command="only_admin", description="Только админы могут /gm"),
        BotCommand(command="language", description="Изменить язык группы"),
        BotCommand(command="help", description="Справка"),
    ],
    "uk": [
        BotCommand(command="gm", description="Розбудити всіх"),
        BotCommand(command="enable", description="Увімкнути сповіщення"),
        BotCommand(command="disable", description="Вимкнути сповіщення"),
        BotCommand(command="test_alarm", description="Тестова сирена собі"),
        BotCommand(command="only_admin", description="Тільки адміни можуть /gm"),
        BotCommand(command="language", description="Змінити мову групи"),
        BotCommand(command="help", description="Допомога"),
    ],
}

# Admin commands (appended to private commands for admins)
ADMIN_COMMANDS = [
    BotCommand(command="broadcast", description="Send broadcast to all users"),
    BotCommand(command="stats", description="Show bot statistics"),
]
