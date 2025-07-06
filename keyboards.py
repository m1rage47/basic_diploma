from telebot import types


def list_keyboard(films, callback_data):
    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = [
        types.InlineKeyboardButton(text=str(i + 1), callback_data=f"{callback_data}{i}")
        for i in range(len(films))
    ]

    # Добавляем кнопки по 5 в ряд
    for i in range(0, len(buttons), 5):
        markup.add(*buttons[i : i + 5])

    return markup


def choose_system_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn_kp = types.InlineKeyboardButton("Kinopoisk", callback_data="rating_kp")
    btn_imdb = types.InlineKeyboardButton("IMDB", callback_data="rating_imdb")
    markup.add(btn_kp, btn_imdb)

    return markup


def movie_limit_markup():
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("5", callback_data="set_limit_5"),
        types.InlineKeyboardButton("10", callback_data="set_limit_10"),
        types.InlineKeyboardButton("20", callback_data="set_limit_20"),
    )
    markup.add(
        types.InlineKeyboardButton("50", callback_data="set_limit_50"),
        types.InlineKeyboardButton("100", callback_data="set_limit_100"),
    )
    return markup
