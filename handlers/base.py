from config import DEFAULT_COMMANDS
from db_operations import add_user
from loader import bot, set_default_commands


@bot.message_handler(commands=["start"])
def handle_start(message):
    welcome = add_user(message)

    bot.send_message(message.chat.id, welcome)
    set_default_commands(bot)


@bot.message_handler(commands=["help"])
def handle_help(message):
    bot.send_message(message.chat.id, "Список команд:")
    bot.send_message(
        message.chat.id, "\n".join(f"{cmd} — {desc}" for cmd, desc in DEFAULT_COMMANDS)
    )
