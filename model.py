from datetime import datetime

from sqlalchemy import (Column, DateTime, Float, ForeignKey, Integer, String,
                        Text, create_engine)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}")

Base = declarative_base()


class Users(Base):
    __tablename__ = "users"
    users_id = Column(Integer, primary_key=True)
    username = Column(String(16), nullable=False)
    first_name = Column(String(16))
    last_name = Column(String(16), nullable=True)

    history = relationship(
        "UsersHistory", back_populates="user", cascade="all, delete-orphan"
    )


class UsersHistory(Base):
    __tablename__ = "users_history"
    id = Column(Integer, primary_key=True)
    users_id = Column(Integer, ForeignKey("users.users_id"), nullable=False)
    title = Column(String(128))
    description = Column(Text)
    rating_kp = Column(Float)
    rating_imdb = Column(Float)
    year = Column(Integer)
    genres = Column(String(128))
    age_rate = Column(Integer)
    poster = Column(String(256))
    data = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("Users", back_populates="history")


Base.metadata.create_all(engine)
