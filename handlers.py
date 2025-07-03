from telebot.apihelper import ApiTelegramException, ApiHTTPException

from api import requester
from config import DEFAULT_COMMANDS
from db_operations import add_to_history, add_user, show_history
from keyboards import choose_system_keyboard, list_keyboard, movie_limit_markup
from loader import bot, set_default_commands
from states import MovieSearchStates, RatingSearchStates, BudgetSearchStates, HistoryStates, CommonStates, history_data

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
@bot.callback_query_handler(func=lambda call: call.data.startswith("set_limit_"), state="*")
def handle_set_limit_fsm(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    bot.answer_callback_query(call.id, text="Принято!")

    try:
        selected_limit = int(call.data.split("_")[2])
    except (IndexError, ValueError):
        bot.send_message(chat_id, "Ошибка при выборе количества фильмов. Пожалуйста, попробуйте снова.")
        bot.delete_state(user_id, chat_id)
        return

    with bot.retrieve_data(user_id, chat_id) as state_data:
        # Теперь 'final_candidates' будет содержать фильмы, независимо от того, какая команда их нашла
        movies_to_display = state_data.get('final_candidates', [])

        if not movies_to_display:
            bot.send_message(chat_id, "Произошла ошибка. Список фильмов не найден. Начните поиск заново.")
            bot.delete_state(user_id, chat_id)
            return

        display_movies = movies_to_display[:selected_limit]

        if not display_movies:
            bot.send_message(chat_id, "К сожалению, не удалось показать фильмы по вашему запросу и выбранному лимиту.")
            bot.delete_state(user_id, chat_id)
            return

        # Отправляем список фильмов и кнопки для выбора конкретного фильма
        send_movie_list_and_ask_selection(chat_id, user_id, display_movies)

# хендлер для выбора конкретного фильма из списка
@bot.callback_query_handler(func=lambda call: call.data.startswith("select_movie_index_"), state="*") # Сработает для ЛЮБОГО состояния
def handle_movie_selection_fsm(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    bot.answer_callback_query(call.id) # Важно ответить на колбэк

    try:
        selected_index = int(call.data.split("_")[3])
    except (IndexError, ValueError) as e:
        bot.send_message(chat_id, f"Ошибка обработки выбора фильма: {e}. Пожалуйста, попробуйте снова.")
        bot.delete_state(user_id, chat_id)
        return

    with bot.retrieve_data(user_id, chat_id) as data:
        films = data.get('current_movie_list') # Список фильмов, который был отправлен для выбора

        if not films or selected_index >= len(films):
            bot.send_message(chat_id, "Произошла ошибка. Список фильмов для выбора не найден или выбор некорректен. Пожалуйста, попробуйте снова или начните новый поиск.")
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
            bot.delete_state(user_id, chat_id) # Сбрасываем состояние после завершения диалога

# Формирует список фильмов
def send_movie_list_and_ask_selection(chat_id, user_id, movies_to_display):
    if not movies_to_display:
        bot.send_message(chat_id, "К сожалению, фильмов для отображения нет.")
        bot.delete_state(user_id, chat_id)
        return

    # Сохраняем список фильмов в FSM контексте для дальнейшего выбора
    with bot.retrieve_data(user_id, chat_id) as state_data:
        state_data['current_movie_list'] = movies_to_display

    text = "\n".join(
        [f"{i+1}. {film['name']} ({film.get('year', '—')})" for i, film in enumerate(movies_to_display)]
    )
    # Используй префикс, который ты ожидаешь в handle_movie_selection_fsm
    markup = list_keyboard(movies_to_display, "select_movie_index_") # Изменил префикс для универсальности
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

            message_text = f"Найдено {len(filtered_movies)} фильмов в жанре {input_genre}"

            state_data['final_candidates'] = filtered_movies


            markup = movie_limit_markup()
            bot.send_message(chat_id, f"{message_text}\nСколько фильмов показать?", reply_markup=markup)
            bot.set_state(user_id, CommonStates.waiting_for_limit, chat_id)
        else:
            bot.send_message(
                chat_id,
                f"По вашему запросу фильмы в жанре '{input_genre}' не найдены. Пожалуйста, попробуйте другой жанр или начните новый поиск.",
            )
            bot.delete_state(user_id, chat_id)

# -----------------------------------------------------------------------------------


@bot.message_handler(commands=["start"])
def handle_start(message):
    welcome = add_user(message)

    bot.send_message(message.chat.id, welcome)
    set_default_commands(bot)

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


@bot.message_handler(commands=["low_budget_movie"])
def handle_low_budget_movie(message):
    bot.reply_to(message, "Введите максимальный бюджет:")
    bot.set_state(
        message.from_user.id, BudgetSearchStates.waiting_for_max_budget, message.chat.id
    )


@bot.message_handler(state=BudgetSearchStates.waiting_for_max_budget)
def low_budget_movie(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        budget = int(message.text)
        if budget < 1000 or budget > 6666666:
            bot.send_message(
                message.chat.id, "Бюджет должен быть в диапазоне 1000-6666666"
            )
    except ValueError:
        bot.send_message(
            message.chat.id, "Пожалуйста, введите корректное число (например, 6000)."
        )
        return
    params = {
        "sortField": "budget.value",
        "sortType": 1,
        "budget.value": f"1000-{budget}",
    }
    data = requester(False, params)
    films = data["docs"]
    with bot.retrieve_data(user_id, chat_id) as state_data:
        # Сохраняем список фильмов в FSM контекст для дальнейшего выбора
        state_data["found_movies"] = films

    if "docs" in data and data["docs"]:
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


@bot.message_handler(commands=["high_budget_movie"])
def handle_high_budget_movie(message):
    bot.reply_to(message, "Введите минимальный бюджет:")
    bot.set_state(
        message.from_user.id, BudgetSearchStates.waiting_for_min_budget, message.chat.id
    )


@bot.message_handler(state=BudgetSearchStates.waiting_for_min_budget)
def high_budget_movie(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        budget = int(message.text)
        if budget < 1000 or budget > 6666666:
            bot.send_message(
                message.chat.id, "Бюджет должен быть в диапазоне 1000-6666666"
            )
    except ValueError:
        bot.send_message(
            message.chat.id, "Пожалуйста, введите корректное число (например, 6000)."
        )
        return

    params = {
        "sortField": "budget.value",
        "sortType": -1,
        "budget.value": f"{budget}-6666666",
    }
    data = requester(False, params)
    films = data["docs"]
    with bot.retrieve_data(user_id, chat_id) as state_data:
        # Сохраняем список фильмов в FSM контекст для дальнейшего выбора
        state_data["found_movies"] = films

    if "docs" in data and data["docs"]:
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


@bot.callback_query_handler(func=lambda call: call.data.startswith("budget_movie_"))
def handle_budget_movie_selection(call):
    try:
        selected_index = int(call.data.split("_")[2])
    except (IndexError, ValueError):
        bot.answer_callback_query(call.id, text="Некорректный выбор.")
        return
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    with bot.retrieve_data(user_id, chat_id) as data:
        films = data.get('current_movie_list')

    if not films or selected_index >= len(films):
        bot.send_message(chat_id, "Произошла ошибка. Пожалуйста, попробуйте снова.")
        return

    film = films[selected_index]

    poster = film.get("poster", {}).get("url", "—")
    msg = msg_generator(film)

    add_to_history(user_id, film)
    try:
        bot.send_photo(chat_id, photo=poster, caption=msg, parse_mode="Markdown")
        bot.answer_callback_query(
            call.id, text=f"Вы выбрали фильм №{selected_index + 1}"
        )
    except ApiTelegramException:
        bot.answer_callback_query(
            call.id,
            text=f"Вы выбрали фильм №{selected_index + 1}\n"
            f"Невозможно загрузить постер",
        )
        bot.send_message(chat_id, msg, parse_mode="Markdown")
    finally:
        bot.delete_state(user_id, chat_id)


@bot.message_handler(commands=["history"])
def handle_history_command(message):
    user_id = message.from_user.id

    history = show_history(user_id)

    if not history:
        bot.send_message(message.chat.id, "История запросов пуста.")
        return

    # Сохраняем историю в словарь по chat_id для последующего использования
    history_data[message.chat.id] = history

    # Формируем список фильмов
    text_lines = []
    for i, record in enumerate(history, start=1):
        text_lines.append(
            f"Запрос от {record.data.strftime('%Y-%m-%d %H:%M')}\n"
            f"{i}. {record.title} ({record.year})"
        )
    text = "\n\n".join(text_lines)

    # Кнопки от 1 до 10
    markup = list_keyboard(history, "history_movie_")

    bot.send_message(
        message.chat.id,
        f"📜 *История запросов:*\n\n{text}",
        parse_mode="Markdown",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("history_movie_"))
def handle_history_movie_detail(call):
    chat_id = call.message.chat.id
    try:
        index = int(call.data.split("_")[-1])
        selected_record = history_data.get(chat_id, [])[index]
    except (IndexError, ValueError, TypeError):
        bot.answer_callback_query(call.id, text="Ошибка выбора.")
        return

    # Так как такое сообщение используется лишь раз я не стла делать функции
    msg = (
        f"🗓 *{selected_record.data.strftime('%Y-%m-%d %H:%M')}*\n"
        f"🎬 *{selected_record.title}* ({selected_record.year})\n\n"
        f"📖 *Описание:*\n{selected_record.description}\n\n"
        f"⭐️ *Рейтинги:*\n"
        f"   └ Кинопоиск: {selected_record.rating_kp or '—'}\n"
        f"   └ IMDB: {selected_record.rating_imdb or '—'}\n"
        f"🎭 *Жанры:* {selected_record.genres or '—'}\n"
        f"🔞 *Возрастной рейтинг:* {selected_record.age_rate or '—'}"
    )

    try:
        bot.send_photo(
            chat_id, photo=selected_record.poster, caption=msg, parse_mode="Markdown"
        )
    except ApiTelegramException as e:
        bot.send_message(chat_id, msg, parse_mode="Markdown")

    bot.answer_callback_query(call.id)


@bot.message_handler(commands=["help"])
def handle_help(message):
    bot.send_message(message.chat.id, "Список команд:")
    bot.send_message(
        message.chat.id, "\n".join(f"{cmd} — {desc}" for cmd, desc in DEFAULT_COMMANDS)
    )


# @bot.message_handler(commands=["history"])
# def handle_history_command(message):
#     user_id = message.from_user.id
#     chat_id = message.chat.id
#
#     history = show_history(user_id)
#
#     if not history:
#         bot.send_message(chat_id, "История запросов пуста.")
#         return
#
#     with bot.retrieve_data(user_id, chat_id) as state_data:
#         state_data['history_records_for_user'] = history # Используем универсальный ключ
#
#     text_lines = []
#     for i, record in enumerate(history, start=1):
#         text_lines.append(
#             f"Запрос от {record.data.strftime('%Y-%m-%d %H:%M')}\n"
#             f"{i}. {record.title} ({record.year})"
#         )
#     text = "\n\n".join(text_lines)
#
#     # Важно: здесь мы передаём полный префикс, который будет использоваться в callback_data
#     # "history_movie_detail" - это наш префикс
#     markup = list_keyboard(history, "history_movie_detail")
#
#     bot.send_message(
#         chat_id,
#         f"📜 *История запросов:*\n\n{text}",
#         parse_mode="Markdown",
#         reply_markup=markup,
#     )
#     bot.set_state(user_id, HistoryStates.main)
#
#
# @bot.callback_query_handler(func=lambda call: call.data.startswith("history_movie_detail"), state=HistoryStates.main)
# def handle_history_movie_detail(call):
#     chat_id = call.message.chat.id
#     user_id = call.from_user.id
#     bot.answer_callback_query(call.id)  # Всегда отвечаем на колбэк
#
#     try:
#         # Ожидаемый формат: "history_movie_detail0", "history_movie_detail1", ...
#         prefix = "history_movie_detail"
#
#         if not call.data.startswith(prefix) or len(call.data) <= len(prefix):
#             raise ValueError("Некорректный формат callback_data для истории.")
#
#         index_str = call.data[len(prefix):]
#         index = int(index_str)
#
#         with bot.retrieve_data(user_id, chat_id) as state_data:
#             history_list = state_data.get('history_records_for_user', [])
#
#             if not history_list or index < 0 or index >= len(history_list):
#                 raise IndexError("Выбранный индекс вне диапазона или история пуста.")
#
#             selected_record = history_list[index]  # <-- selected_record гарантированно получает значение здесь
#
#             # --- Весь код, использующий selected_record, перемещаем сюда ---
#             msg = (
#                 f"🗓 *Запрос от: {selected_record.data.strftime('%Y-%m-%d %H:%M')}*\n"
#                 f"🎬 *{selected_record.title}* ({selected_record.year})\n\n"
#                 f"📖 *Описание:*\n{selected_record.description}\n\n"
#                 f"⭐️ *Рейтинги:*\n"
#                 f"   └ Кинопоиск: {selected_record.rating_kp or '—'}\n"
#                 f"   └ IMDB: {selected_record.rating_imdb or '—'}\n"
#                 f"🎭 *Жанры:* {selected_record.genres or '—'}\n"
#                 f"🔞 *Возрастной рейтинг:* {selected_record.age_rate or '—'}"
#             )
#
#             try:
#                 bot.send_photo(
#                     chat_id, photo=selected_record.poster, caption=msg, parse_mode="Markdown"
#                 )
#             except ApiTelegramException as e:
#                 print(f"DEBUG: Telegram API Error sending photo for history: {e}")
#                 bot.send_message(chat_id, msg, parse_mode="Markdown")
#
#             # bot.answer_callback_query(call.id) # Уже ответили выше
#             bot.delete_state(user_id, chat_id)
#
#     except (IndexError, ValueError, TypeError) as e:
#         print(f"DEBUG: Error in handle_history_movie_detail: {e}")
#         bot.send_message(chat_id, "Ошибка выбора фильма из истории. Пожалуйста, попробуйте снова.")
#         # bot.delete_state(user_id, chat_id) # Не сбрасываем здесь, чтобы пользователь мог попробовать снова или продолжить
#         return


# ... остальные хендлеры


@bot.message_handler(commands=["help"])
def handle_help(message):
    bot.send_message(message.chat.id, "Список команд:")
    bot.send_message(
        message.chat.id, "\n".join(f"{cmd} — {desc}" for cmd, desc in DEFAULT_COMMANDS)
    )

