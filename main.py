from telebot.custom_filters import StateFilter

import api
import keyboards
import states
from handlers import (base, history, movie_by_budget, movie_by_rating,
                      movie_by_title, tools)
from loader import bot, set_default_commands

bot.add_custom_filter(StateFilter(bot))

if __name__ == "__main__":

    set_default_commands(bot)
    bot.infinity_polling()
    print("Done!")
