from telebot.handler_backends import State, StatesGroup

history_data = {}


class MovieSearchStates(StatesGroup):
    """Состояния для команды /movie_search"""

    waiting_for_movie_name = State()  # Ожидаем название фильма


class RatingSearchStates(StatesGroup):
    """Состояния для команды /movie_by_rating"""

    waiting_for_rating_value_kp = State()  # Ожидаем рейтинг Kinopoisk
    waiting_for_rating_value_imdb = State()  # Ожидаем рейтинг IMDB


class BudgetSearchStates(StatesGroup):
    """Состояния для команд /low_budget_movie и /high_budget_movie"""

    waiting_for_min_budget = State()  # Ожидаем минимальный бюджет
    waiting_for_max_budget = State()  # Ожидаем максимальный бюджет


class HistoryStates(StatesGroup):
    """Состояния для команд /history"""

    main = State()


class CommonStates(StatesGroup):
    """Универсальные состояния"""

    waiting_for_genre_name = State()
    waiting_for_limit = State()  # Ожидаем выбор количества фильмов
