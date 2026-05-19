import sqlalchemy
from flask_login import UserMixin
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .db_session import SqlAlchemyBase

class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    username = sqlalchemy.Column(sqlalchemy.String, index=True, unique=True, nullable=False)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    bio = sqlalchemy.Column(sqlalchemy.String, nullable=True, default="")
    email = sqlalchemy.Column(sqlalchemy.String, index=True, unique=True, nullable=False)
    karma = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, default=0)
    posts = orm.relationship("Post", back_populates="author")
    is_admin = sqlalchemy.Column(sqlalchemy.Boolean, nullable=True, default=False)
    is_banned = sqlalchemy.Column(sqlalchemy.Boolean, nullable=True, default=False)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)


class UnverifiedUser(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'unverified_users'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    username = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    email = sqlalchemy.Column(sqlalchemy.String, index=True, unique=True, nullable=False)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    date = sqlalchemy.Column(sqlalchemy.DateTime)

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)