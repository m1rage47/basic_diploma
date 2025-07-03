from telebot import TeleBot, types
from telebot.storage import StateMemoryStorage

from config import BOT_TOKEN, DEFAULT_COMMANDS

storage = StateMemoryStorage()
bot = TeleBot(token=BOT_TOKEN, state_storage=storage)


def set_default_commands(bot):
    bot.set_my_commands([types.BotCommand(*i) for i in DEFAULT_COMMANDS])
