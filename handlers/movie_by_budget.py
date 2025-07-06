from telebot.apihelper import ApiTelegramException

from api import requester
from handlers.tools import filter_or_not
from loader import bot
from states import BudgetSearchStates


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
        filter_or_not(films, chat_id, user_id)
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
        filter_or_not(films, chat_id, user_id)
    else:
        msg = "❌ Фильм не найден. Попробуйте другое название."
        bot.reply_to(message, msg, parse_mode="Markdown")
        bot.delete_state(user_id, chat_id)


# @bot.callback_query_handler(func=lambda call: call.data.startswith("budget_movie_"))
# def handle_budget_movie_selection(call):
#     try:
#         selected_index = int(call.data.split("_")[2])
#     except (IndexError, ValueError):
#         bot.answer_callback_query(call.id, text="Некорректный выбор.")
#         return
#     chat_id = call.message.chat.id
#     user_id = call.from_user.id

#     with bot.retrieve_data(user_id, chat_id) as data:
#         films = data.get("current_movie_list")

#     if not films or selected_index >= len(films):
#         bot.send_message(chat_id, "Произошла ошибка. Пожалуйста, попробуйте снова.")
#         return

#     film = films[selected_index]

#     poster = film.get("poster", {}).get("url", "—")
#     msg = msg_generator(film)

#     add_to_history(user_id, film)
#     try:
#         bot.send_photo(chat_id, photo=poster, caption=msg, parse_mode="Markdown")
#         bot.answer_callback_query(
#             call.id, text=f"Вы выбрали фильм №{selected_index + 1}"
#         )
#     except ApiTelegramException:
#         bot.answer_callback_query(
#             call.id,
#             text=f"Вы выбрали фильм №{selected_index + 1}\n"
#             f"Невозможно загрузить постер",
#         )
#         bot.send_message(chat_id, msg, parse_mode="Markdown")
#     finally:
#         bot.delete_state(user_id, chat_id)
