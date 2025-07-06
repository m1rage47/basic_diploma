from api import requester
from handlers.tools import filter_or_not
from keyboards import choose_system_keyboard
from loader import bot
from states import RatingSearchStates


# Хендлер для команды /movie_by_rating и выбор системы
@bot.message_handler(commands=["movie_by_rating"])
def handle_movie_by_rating(message):
    markup = choose_system_keyboard()
    bot.send_message(
        message.chat.id, "Выберите систему оценивания:", reply_markup=markup
    )


# Колбэк-хендлер для обработки нажатий кнопок
@bot.callback_query_handler(func=lambda call: call.data in ["rating_kp", "rating_imdb"])
def rating_callback_handler(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)

    # Сохраняем выбранную систему в FSM контекст
    with bot.retrieve_data(user_id, chat_id) as data:
        data["rating_type"] = call.data

    if call.data == "rating_kp":
        bot.send_message(chat_id, "Вы выбрали Kinopoisk. Введите рейтинг поиска 🔍")
        bot.set_state(user_id, RatingSearchStates.waiting_for_rating_value_kp, chat_id)
    elif call.data == "rating_imdb":
        bot.send_message(chat_id, "Вы выбрали IMDB. Введите рейтинг поиска 🔍")
        bot.set_state(
            user_id, RatingSearchStates.waiting_for_rating_value_imdb, chat_id
        )


# Запрос и отправка 10 фильмов для kp
@bot.message_handler(state=RatingSearchStates.waiting_for_rating_value_kp)
def fetch_movies_by_kp_rating(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        rating = float(message.text)
    except ValueError:
        bot.send_message(
            message.chat.id, "Пожалуйста, введите корректное число (например, 8.1)."
        )
        return

    params = {
        "sortField": "rating.kp",
        "sortType": 1,
        "rating.kp": f"{rating}-10",
    }
    data = requester(False, params)
    films = data["docs"]
    with bot.retrieve_data(user_id, chat_id) as state_data:
        # Сохраняем список фильмов в FSM контекст для дальнейшего выбора
        state_data["found_movies"] = films

    if "docs" in data and data["docs"]:
        filter_or_not(films, chat_id, user_id)
    else:
        msg = "❌ Фильм не найден. Попробуйте другое название."
        bot.reply_to(chat_id, msg, parse_mode="Markdown")
        bot.delete_state(user_id, chat_id)


# Запрос и отправка 10 фильмов для imdb
@bot.message_handler(state=RatingSearchStates.waiting_for_rating_value_imdb)
def fetch_movies_by_imdb_rating(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        rating = float(message.text)
    except ValueError:
        bot.send_message(
            message.chat.id, "Пожалуйста, введите корректное число (например, 8.1)."
        )
        return

    params = {
        "sortField": "rating.imdb",
        "sortType": 1,
        "rating.imdb": f"{rating}-10",
    }
    data = requester(False, params)
    films = data["docs"]
    with bot.retrieve_data(user_id, chat_id) as state_data:
        # Сохраняем список фильмов в FSM контекст для дальнейшего выбора
        state_data["found_movies"] = films

    if "docs" in data and data["docs"]:
        filter_or_not(films, chat_id, user_id)
    else:
        msg = "❌ Фильм не найден. Попробуйте другое название."
        bot.reply_to(chat_id, msg, parse_mode="Markdown")
        bot.delete_state(user_id, chat_id)
