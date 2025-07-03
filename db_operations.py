from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from model import Users, UsersHistory, engine

Session = sessionmaker(bind=engine)
session = Session()


def add_user(message):
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

    return welcome


def add_to_history(user_id, films_details):
    poster = films_details.get("poster", {}).get("url", "Неизвестно")
    title = films_details.get("name", "Неизвестно")
    year = films_details.get("year", "Неизвестно")
    rating_kp = round(films_details.get("rating", {}).get("kp", "Нет рейтинга"), 1)
    rating_imdb = round(films_details.get("rating", {}).get("imdb", "Нет рейтинга"), 1)
    description = films_details.get("description", "Описание отсутствует.")
    genres = films_details.get("genres", [])
    genres_list = ", ".join([g["name"] for g in genres]) if genres else "—"
    age_rating = films_details.get("ageRating", "Неизвестно")

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


def show_history(user_id):
    history = (
        session.query(UsersHistory)
        .filter_by(users_id=user_id)
        .order_by(UsersHistory.data.desc())
        .limit(10)
        .all()
    )
    return history
