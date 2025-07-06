from telebot.apihelper import ApiTelegramException

from db_operations import show_history
from keyboards import list_keyboard
from loader import bot
from states import history_data


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
