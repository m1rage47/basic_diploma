from datetime import datetime
from urllib.parse import quote

import requests
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from telebot import types
from telebot.apihelper import ApiTelegramException
from telebot.handler_backends import State, StatesGroup

from config import API_KEY, BASE_URL, DEFAULT_COMMANDS
from loader import bot
from model import Users, UsersHistory, engine


def set_default_commands(bot):
    bot.set_my_commands([types.BotCommand(*i) for i in DEFAULT_COMMANDS])


class CommandStates(StatesGroup):
    movie_search = State()
    movie_by_rating = State()
    low_budget_movie = State()
    high_budget_movie = State()
    history = State()


headers = {"accept": "application/json", "X-API-KEY": API_KEY}
Session = sessionmaker(bind=engine)
session = Session()


@bot.message_handler(commands=["start"])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "гость"
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    new_record = Users(
        users_id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
    )

    try:
        session.add(new_record)
        session.commit()
        welcome = (
            f"Здравствуйте 👋, {username}\n"
            f"Добро пожаловать в бот-кинопоиск🎬\n"
            f"Тут вы сможете получить подробную информацию о всём кинематографе быстро, удобно и без рекламы 🚫\n"
            f"Готовы начать? Отправьте первый запрос 🔍"
        )
    except IntegrityError:
        session.rollback()
        welcome = f"Рады снова вас видеть, {username}!"

    bot.send_message(message.chat.id, welcome)
    set_default_commands(bot)


@bot.message_handler(commands=["movie_search"])
def handle_movie_search(message):
    bot.reply_to(message, "Введите название фильма:")
    bot.register_next_step_handler(message, movie_searcher)


def movie_searcher(message):
    user_id = message.from_user.id
    movie_name = message.text.strip()

    response = requests.get(
        f"{BASE_URL}/movie/search?page=1&limit=10&query={quote(movie_name)}",
        headers=headers,
    )
    response.raise_for_status()  # Проверка на ошибки HTTP
    data = response.json()

    if "docs" in data and data["docs"]:
        movie = data["docs"][0]
        poster = movie.get("poster", {}).get("url", "Неизвестно")
        title = movie.get("name", "Неизвестно")
        en_name = movie.get("alternativeName", "Неизвестно")
        year = movie.get("year", "Неизвестно")
        rating_kp = round(movie.get("rating", {}).get("kp", "Нет рейтинга"), 1)
        rating_imdb = round(movie.get("rating", {}).get("imdb", "Нет рейтинга"), 1)
        description = movie.get("description", "Описание отсутствует.")
        genres = movie.get("genres", [])
        genres_list = ", ".join([g["name"] for g in genres]) if genres else "—"
        age_rating = movie.get("ageRating", "Неизвестно")

        msg = (
            f"🎬 *{title}* ({year})\n\n"
            f"🇺🇸 *Английское название:* {en_name}\n"
            f"🎭 *Жанры:* {genres_list}\n"
            f"🔞 *Возрастной рейтинг:* {age_rating}+\n"
            f"⭐️ *Рейтинги:*\n"
            f"   └ 📊 *Кинопоиск:* {rating_kp}\n"
            f"   └ 🌍 *IMDB:* {rating_imdb}\n"
            f"📖 *Описание:*\n{description}"
        )
        try:
            bot.send_photo(
                message.chat.id, photo=poster, caption=msg, parse_mode="Markdown"
            )
        except ApiTelegramException:
            bot.reply_to(message.chat.id, msg, parse_mode="Markdown")
    else:
        msg = "❌ Фильм не найден. Попробуйте другое название."
        bot.reply_to(message.chat.id, msg, parse_mode="Markdown")

    new_record = UsersHistory(
        users_id=user_id,
        title=title,
        description=description[:1000],
        rating_kp=rating_kp,
        rating_imdb=rating_imdb,
        year=year,
        genres=genres_list,
        age_rate=age_rating,
        poster=poster,
    )

    session.add(new_record)
    session.commit()


# Хендлер для команды /movie_by_rating и выбор системы
@bot.message_handler(commands=["movie_by_rating"])
def handle_movie_by_rating(message):
    markup = types.InlineKeyboardMarkup()
    btn_kp = types.InlineKeyboardButton("Kinopoisk", callback_data="rating_kp")
    btn_imdb = types.InlineKeyboardButton("IMDB", callback_data="rating_imdb")
    markup.add(btn_kp, btn_imdb)

    bot.send_message(
        message.chat.id, "Выберите систему оценивания:", reply_markup=markup
    )


# Колбэк-хендлер для обработки нажатий кнопок
@bot.callback_query_handler(func=lambda call: call.data in ["rating_kp", "rating_imdb"])
def rating_callback_handler(call):
    if call.data == "rating_kp":
        m_by_kp(call)
    elif call.data == "rating_imdb":
        m_by_imdb(call)


# Функция обработки выбора Kinopoisk
def m_by_kp(call):
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id, "Вы выбрали Kinopoisk. Введите рейтинг поиска 🔍"
    )
    bot.register_next_step_handler(call.message, fetch_movies_by_kp_rating)


user_movies = {}


# Запрос и отправка 10 фильмов для kp
def fetch_movies_by_kp_rating(message):
    try:
        rating = float(message.text)
    except ValueError:
        bot.send_message(
            message.chat.id, "Пожалуйста, введите корректное число (например, 8.1)."
        )
        return

    response = requests.get(
        f"{BASE_URL}/movie?page=1&limit=10&selectFields=name&selectFields=ageRating&selectFields=poster&selectFields=year&selectFields=enName&selectFields=rating&selectFields=description&selectFields=genres&notNullFields=description&notNullFields=enName&notNullFields=rating.kp&sortField=rating.kp&sortType=1&rating.kp={rating}-10",
        headers=headers,
    )
    response.raise_for_status()  # Проверка на ошибки HTTP
    data = response.json()
    films = data["docs"]
    user_movies[message.chat.id] = films  # сохраняем для дальнейшего доступа

    text = "\n".join(
        [
            f"{i+1}. {film['name']} ({film.get('year', '—')})"
            for i, film in enumerate(films)
        ]
    )

    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = [
        types.InlineKeyboardButton(text=str(i + 1), callback_data=f"movie_{i}")
        for i in range(len(films))
    ]

    # Добавляем кнопки по 5 в ряд
    for i in range(0, len(buttons), 5):
        markup.add(*buttons[i : i + 5])

    bot.send_message(message.chat.id, text, reply_markup=markup)


# Функция обработки выбора IMDB
def m_by_imdb(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "Вы выбрали IMDB. Введите рейтинг поиска 🔍")
    bot.register_next_step_handler(call.message, fetch_movies_by_imdb_rating)


# Запрос и отправка 10 фильмов для imdb
def fetch_movies_by_imdb_rating(message):
    try:
        rating = float(message.text)
    except ValueError:
        bot.send_message(
            message.chat.id, "Пожалуйста, введите корректное число (например, 8.1)."
        )
        return

    response = requests.get(
        f"{BASE_URL}/movie?page=1&limit=10&selectFields=name&selectFields=ageRating&selectFields=poster&selectFields=year&selectFields=enName&selectFields=rating&selectFields=description&selectFields=genres&notNullFields=description&notNullFields=enName&notNullFields=rating.imdb&sortField=rating.imdb&sortType=1&rating.imdb={rating}-10",
        headers=headers,
    )

    response.raise_for_status()  # Проверка на ошибки HTTP
    data = response.json()
    films = data["docs"]
    user_movies[message.chat.id] = films  # сохраняем для дальнейшего доступа

    text = "\n".join(
        [
            f"{i+1}. {film['name']} ({film.get('year', '—')})"
            for i, film in enumerate(films)
        ]
    )

    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = [
        types.InlineKeyboardButton(text=str(i + 1), callback_data=f"movie_{i}")
        for i in range(len(films))
    ]

    # Добавляем кнопки по 5 в ряд
    for i in range(0, len(buttons), 5):
        markup.add(*buttons[i : i + 5])

    bot.send_message(message.chat.id, text, reply_markup=markup)


# Обработка нажатий на кнопки
@bot.callback_query_handler(func=lambda call: call.data.startswith("movie_"))
def handle_movie_selection(call):
    selected_index = int(call.data.split("_")[1])
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    films = user_movies.get(chat_id)
    if not films or selected_index >= len(films):
        bot.send_message(chat_id, "Произошла ошибка. Пожалуйста, попробуйте снова.")
        return

    film = films[selected_index]

    poster = film.get("poster", {}).get("url", "—")
    title = film.get("name", "Неизвестно")
    en_name = film.get("alternativeName", "Неизвестно")
    year = film.get("year", "Неизвестно")
    rating_kp = round(film.get("rating", {}).get("kp", "Нет рейтинга"), 1)
    rating_imdb = round(film.get("rating", {}).get("imdb", "Нет рейтинга"), 1)
    description = film.get("description", "Описание отсутствует.")
    genres = film.get("genres", [])
    genres_list = ", ".join([g["name"] for g in genres]) if genres else "—"
    age_rating = film.get("ageRating", "Неизвестно")

    msg = (
        f"🎬 *{title}* ({year})\n\n"
        f"🇺🇸 *Английское название:* {en_name}\n"
        f"🎭 *Жанры:* {genres_list}\n"
        f"🔞 *Возрастной рейтинг:* {age_rating}+\n"
        f"⭐️ *Рейтинги:*\n"
        f"   └ 📊 *Кинопоиск:* {rating_kp}\n"
        f"   └ 🌍 *IMDB:* {rating_imdb}\n"
        f"📖 *Описание:*\n{description}"
    )

    new_record = UsersHistory(
        users_id=user_id,
        title=title,
        description=description[:1000],  # если всё же ограничение есть
        rating_kp=rating_kp,
        rating_imdb=rating_imdb,
        year=year,
        genres=genres_list,
        age_rate=age_rating,
        poster=poster,
    )

    session.add(new_record)
    session.commit()
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


@bot.message_handler(commands=["low_budget_movie"])
def handle_low_budget_movie(message):
    bot.reply_to(message, "Введите максимальный бюджет:")
    bot.register_next_step_handler(message, low_budget_movie)


budget_movies = {}


def low_budget_movie(message):
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

    response = requests.get(
        f"{BASE_URL}/movie?page=1&limit=10&selectFields=name&selectFields=ageRating&selectFields=poster&selectFields=enName&selectFields=year&selectFields=description&selectFields=rating&selectFields=budget&selectFields=genres&notNullFields=name&notNullFields=enName&notNullFields=description&notNullFields=rating.kp&notNullFields=rating.imdb&notNullFields=year&notNullFields=budget.value&sortField=budget.value&sortType=-1&budget.value=1000-{budget}",
        headers=headers,
    )

    response.raise_for_status()  # Проверка на ошибки HTTP
    data = response.json()
    films = data["docs"]
    budget_movies[message.chat.id] = films  # сохраняем для дальнейшего доступа

    text = "\n".join(
        [
            f"{i + 1}. {film['name']} ({film.get('year', '—')})"
            for i, film in enumerate(films)
        ]
    )

    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = [
        types.InlineKeyboardButton(text=str(i + 1), callback_data=f"budget_movie_{i}")
        for i in range(len(films))
    ]

    # Добавляем кнопки по 5 в ряд
    for i in range(0, len(buttons), 5):
        markup.add(*buttons[i : i + 5])

    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(commands=["high_budget_movie"])
def handle_high_budget_movie(message):
    bot.reply_to(message, "Введите минимальный бюджет:")
    bot.register_next_step_handler(message, high_budget_movie)


def high_budget_movie(message):
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

    response = requests.get(
        f"{BASE_URL}/movie?page=1&limit=10&selectFields=name&selectFields=ageRating&selectFields=poster&selectFields=enName&selectFields=year&selectFields=description&selectFields=rating&selectFields=budget&selectFields=genres&notNullFields=name&notNullFields=enName&notNullFields=description&notNullFields=rating.kp&notNullFields=rating.imdb&notNullFields=year&notNullFields=budget.value&sortField=budget.value&sortType=-1&budget.value={budget}-6666666",
        headers=headers,
    )

    response.raise_for_status()  # Проверка на ошибки HTTP
    data = response.json()
    films = data["docs"]
    budget_movies[message.chat.id] = films  # сохраняем для дальнейшего доступа

    text = "\n".join(
        [
            f"{i + 1}. {film['name']} ({film.get('year', '—')})"
            for i, film in enumerate(films)
        ]
    )

    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = [
        types.InlineKeyboardButton(text=str(i + 1), callback_data=f"budget_movie_{i}")
        for i in range(len(films))
    ]

    # Добавляем кнопки по 5 в ряд
    for i in range(0, len(buttons), 5):
        markup.add(*buttons[i : i + 5])

    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("budget_movie_"))
def handle_budget_movie_selection(call):
    try:
        selected_index = int(call.data.split("_")[2])
    except (IndexError, ValueError):
        bot.answer_callback_query(call.id, text="Некорректный выбор.")
        return
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    films = budget_movies.get(chat_id)
    if not films or selected_index >= len(films):
        bot.send_message(chat_id, "Произошла ошибка. Пожалуйста, попробуйте снова.")
        return

    film = films[selected_index]

    poster = film.get("poster", {}).get("url", "—")
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
    new_record = UsersHistory(
        users_id=user_id,
        title=title,
        description=description[:1000],  # если всё же ограничение есть
        rating_kp=rating_kp,
        rating_imdb=rating_imdb,
        year=year,
        genres=genres_list,
        age_rate=age_rating,
        poster=poster,
    )

    session.add(new_record)
    session.commit()
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


history_data = {}


@bot.message_handler(commands=["history"])
def handle_history_command(message):
    user_id = message.from_user.id

    history = (
        session.query(UsersHistory)
        .filter_by(users_id=user_id)
        .order_by(UsersHistory.data.desc())
        .limit(10)
        .all()
    )

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
    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = [
        types.InlineKeyboardButton(text=str(i + 1), callback_data=f"history_movie_{i}")
        for i in range(len(history))
    ]
    for i in range(0, len(buttons), 5):
        markup.add(*buttons[i : i + 5])

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


if __name__ == "__main__":

    set_default_commands(bot)
    bot.infinity_polling()
