from telebot.apihelper import ApiTelegramException

from api import requester
from db_operations import add_to_history
from handlers.tools import msg_generator
from loader import bot
from states import CommonStates, MovieSearchStates


@bot.message_handler(commands=["movie_search"])
def handle_movie_search(message):
    bot.reply_to(message, "Введите название фильма:")
    bot.set_state(
        message.from_user.id, MovieSearchStates.waiting_for_movie_name, message.chat.id
    )


@bot.message_handler(state=MovieSearchStates.waiting_for_movie_name)
def movie_searcher(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    movie_name = message.text.strip()

    query_params = {"query": movie_name}
    data = requester(True, query_params)
    films_found = data["docs"]
    with bot.retrieve_data(user_id, chat_id) as state_data:
        state_data["found_movies"] = films_found

    if "docs" in data and data["docs"]:
        if len(films_found) > 1:
            bot.send_message(
                chat_id,
                f"Найдено {len(films_found)} фильмов по запросу '{movie_name}'.\n"
                "Хотите отфильтровать по жанру? Введите название жанра (например, 'фантастика' или 'комедия').\n"
                "Или отправьте '-' (минус), чтобы пропустить фильтрацию и показать первый фильм.",
            )
            bot.set_state(user_id, CommonStates.waiting_for_genre_name, chat_id)
        else:
            movie = films_found[0]
            poster = movie.get("poster", {}).get("url", "—")
            msg = msg_generator(movie)
            try:
                bot.send_photo(
                    chat_id, photo=poster, caption=msg, parse_mode="Markdown"
                )
            except ApiTelegramException:
                bot.reply_to(chat_id, msg, parse_mode="Markdown")

            add_to_history(user_id, movie)
            bot.delete_state(user_id, chat_id)
    else:
        msg = "❌ Фильм не найден. Попробуйте другое название."
        bot.reply_to(chat_id, msg, parse_mode="Markdown")
        bot.delete_state(user_id, chat_id)
