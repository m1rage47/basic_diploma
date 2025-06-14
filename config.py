import os

from dotenv import find_dotenv, load_dotenv

if not find_dotenv():
    exit("Переменные окружения не загружены т.к отсутствует файл .env")
else:
    load_dotenv()

BASE_URL = "https://api.kinopoisk.dev/v1.4"
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("RAPID_API")

DB_PATH = "database.db"

DEFAULT_COMMANDS = (
    ("start", "Запустить бота"),
    ("help", "Вывести справку"),
    ("movie_search", "поиск фильма/сериала по названию"),
    ("movie_by_rating", "поиск фильмов/сериалов по рейтингу"),
    ("low_budget_movie", "поиск фильмов/сериалов с низким бюджетом"),
    ("high_budget_movie", "поиск фильмов/сериалов с высоким бюджетом"),
    ("history", "возможность просмотра истории запросов и поиска фильма/сериала"),
)
