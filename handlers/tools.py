from telebot.apihelper import ApiHTTPException, ApiTelegramException

from db_operations import add_to_history
from keyboards import list_keyboard, movie_limit_markup
from loader import bot
from states import CommonStates


# ------------------------------------ Универсал ------------------------------------
# Генератор сообщений
def msg_generator(film):
    title = film.get("name", "Неизвестно")
    en_name = film.get("alternativeName", "Неизвестно")
    year = film.get("year", "Неизвестно")
    rating_kp = round(film.get("rating", {}).get("kp", "Нет рейтинга"), 1)
    rating_imdb = round(film.get("rating", {}).get("imdb", "Нет рейтинга"), 1)
    description = film.get("description", "Описание отсутствует.")
    genres = film.get("genres", [])
    genres_list = ", ".join([g["name"] for g in genres]) if genres else "—"
    age_rating = film.get("ageRating", "Неизвестно")
    budget = film.get("budget", {}).get("value", "—")
    currency = film.get("budget", {}).get("currency", "—")

    msg = (
        f"🎬 *{title}* ({year})\n\n"
        f"🇺🇸 *Английское название:* {en_name}\n"
        f"💰 *Бюджет:* {budget}{currency}\n"
        f"🎭 *Жанры:* {genres_list}\n"
        f"🔞 *Возрастной рейтинг:* {age_rating}+\n"
        f"⭐️ *Рейтинги:*\n"
        f"   └ 📊 *Кинопоиск:* {rating_kp}\n"
        f"   └ 🌍 *IMDB:* {rating_imdb}\n"
        f"📖 *Описание:*\n{description}"
    )

    return msg


# хендлер для выбора обработки лимита
@bot.callback_query_handler(
    func=lambda call: call.data.startswith("set_limit_"), state="*"
)
def handle_set_limit_fsm(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    bot.answer_callback_query(call.id, text="Принято!")

    try:
        selected_limit = int(call.data.split("_")[2])
    except (IndexError, ValueError):
        bot.send_message(
            chat_id,
            "Ошибка при выборе количества фильмов. Пожалуйста, попробуйте снова.",
        )
        bot.delete_state(user_id, chat_id)
        return

    with bot.retrieve_data(user_id, chat_id) as state_data:
        # Теперь 'final_candidates' будет содержать фильмы, независимо от того, какая команда их нашла
        movies_to_display = state_data.get("final_candidates", [])

        if not movies_to_display:
            bot.send_message(
                chat_id,
                "Произошла ошибка. Список фильмов не найден. Начните поиск заново.",
            )
            bot.delete_state(user_id, chat_id)
            return

        display_movies = movies_to_display[:selected_limit]

        if not display_movies:
            bot.send_message(
                chat_id,
                "К сожалению, не удалось показать фильмы по вашему запросу и выбранному лимиту.",
            )
            bot.delete_state(user_id, chat_id)
            return

        # Отправляем список фильмов и кнопки для выбора конкретного фильма
        send_movie_list_and_ask_selection(chat_id, user_id, display_movies)


# хендлер для выбора конкретного фильма из списка
@bot.callback_query_handler(
    func=lambda call: call.data.startswith("select_movie_index_"), state="*"
)  # Сработает для ЛЮБОГО состояния
def handle_movie_selection_fsm(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)  # Важно ответить на колбэк

    try:
        selected_index = int(call.data.split("_")[3])
    except (IndexError, ValueError) as e:
        bot.send_message(
            chat_id,
            f"Ошибка обработки выбора фильма: {e}. Пожалуйста, попробуйте снова.",
        )
        bot.delete_state(user_id, chat_id)
        return

    with bot.retrieve_data(user_id, chat_id) as data:
        films = data.get(
            "current_movie_list"
        )  # Список фильмов, который был отправлен для выбора

        if not films or selected_index >= len(films):
            bot.send_message(
                chat_id,
                "Произошла ошибка. Список фильмов для выбора не найден или выбор некорректен. Пожалуйста, попробуйте снова или начните новый поиск.",
            )
            bot.delete_state(user_id, chat_id)
            return

        film = films[selected_index]
        poster = film.get("poster", {}).get("url", "—")
        msg = msg_generator(film)

        try:
            bot.send_photo(chat_id, photo=poster, caption=msg, parse_mode="Markdown")
            bot.answer_callback_query(
                call.id, text=f"Вы выбрали фильм №{selected_index + 1}"
            )
            add_to_history(user_id, film)
        except ApiHTTPException:
            bot.answer_callback_query(
                call.id,
                text=f"Вы выбрали фильм №{selected_index + 1}\n"
                f"Невозможно загрузить постер",
            )
            bot.send_message(chat_id, msg, parse_mode="Markdown")
        finally:
            bot.delete_state(
                user_id, chat_id
            )  # Сбрасываем состояние после завершения диалога


# Формирует список фильмов
def send_movie_list_and_ask_selection(chat_id, user_id, movies_to_display):
    if not movies_to_display:
        bot.send_message(chat_id, "К сожалению, фильмов для отображения нет.")
        bot.delete_state(user_id, chat_id)
        return

    # Сохраняем список фильмов в FSM контексте для дальнейшего выбора
    with bot.retrieve_data(user_id, chat_id) as state_data:
        state_data["current_movie_list"] = movies_to_display

    text = "\n".join(
        [
            f"{i+1}. {film['name']} ({film.get('year', '—')})"
            for i, film in enumerate(movies_to_display)
        ]
    )
    # Используй префикс, который ты ожидаешь в handle_movie_selection_fsm
    markup = list_keyboard(
        movies_to_display, "select_movie_index_"
    )  # Изменил префикс для универсальности
    bot.send_message(chat_id, text, reply_markup=markup)


@bot.message_handler(state=CommonStates.waiting_for_genre_name)
def filter_movies_by_genre(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    input_genre = message.text.strip().lower()

    with bot.retrieve_data(user_id, chat_id) as state_data:
        found_movies = state_data.get("found_movies", [])

        if not found_movies:
            bot.send_message(
                chat_id,
                "Произошла ошибка при поиске фильмов. Пожалуйста, начните заново.",
            )
            bot.delete_state(user_id, chat_id)
            return

        if input_genre == "-":
            bot.send_message(
                chat_id,
                f"Пропускаем фильтрацию. Показываю первые 10 фильмов по вашему запросу.",
            )
            movie = found_movies[0]
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
            return

        # Фильтруем фильмы по жанру
        filtered_movies = []
        for movie in found_movies:
            genres = movie.get("genres", [])
            # Проверяем, есть ли введенный жанр в списке жанров фильма
            if any(g.get("name", "").lower() == input_genre for g in genres):
                filtered_movies.append(movie)

        if filtered_movies:
            # Сохраняем отфильтрованный список для выбора
            state_data["current_movie_list"] = (
                filtered_movies  # Обновляем список в состоянии для колбэков выбора
            )

            message_text = (
                f"Найдено {len(filtered_movies)} фильмов в жанре {input_genre}"
            )

            state_data["final_candidates"] = filtered_movies

            markup = movie_limit_markup()
            bot.send_message(
                chat_id,
                f"{message_text}\nСколько фильмов показать?",
                reply_markup=markup,
            )
            bot.set_state(user_id, CommonStates.waiting_for_limit, chat_id)
        else:
            bot.send_message(
                chat_id,
                f"По вашему запросу фильмы в жанре '{input_genre}' не найдены. Пожалуйста, попробуйте другой жанр или начните новый поиск.",
            )
            bot.delete_state(user_id, chat_id)


def filter_or_not(films, chat_id, user_id):
    if len(films) > 1:
        bot.send_message(
            chat_id,
            f"Найдено {len(films)} фильмов по вашему запросу.\n"
            "Хотите отфильтровать по жанру? Введите название жанра (например, 'фантастика' или 'комедия').\n"
            "Или отправьте '-' (минус), чтобы пропустить фильтрацию и показать первый фильм.",
        )
        bot.set_state(user_id, CommonStates.waiting_for_genre_name, chat_id)
    else:
        movie = films[0]
        poster = movie.get("poster", {}).get("url", "—")
        msg = msg_generator(movie)
        try:
            bot.send_photo(chat_id, photo=poster, caption=msg, parse_mode="Markdown")
        except ApiTelegramException:
            bot.reply_to(chat_id, msg, parse_mode="Markdown")

        add_to_history(user_id, movie)
        bot.delete_state(user_id, chat_id)


# -----------------------------------------------------------------------------------
