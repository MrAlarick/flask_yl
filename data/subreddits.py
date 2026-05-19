import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase


subreddit_moderators = sqlalchemy.Table(
    'subreddit_moderators',
    SqlAlchemyBase.metadata,
    sqlalchemy.Column('user_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), primary_key=True),
    sqlalchemy.Column('subreddit_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('subreddits.id'), primary_key=True)
)


subreddit_members = sqlalchemy.Table(
    'subreddit_members',
    SqlAlchemyBase.metadata,
    sqlalchemy.Column('user_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), primary_key=True),
    sqlalchemy.Column('subreddit_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('subreddits.id'), primary_key=True)
)

subreddit_banned = sqlalchemy.Table(
    'subreddit_banned',
    SqlAlchemyBase.metadata,
    sqlalchemy.Column('user_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), primary_key=True),
    sqlalchemy.Column('subreddit_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('subreddits.id'), primary_key=True)
)


class Subreddit(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'subreddits'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, index=True)
    description = sqlalchemy.Column(sqlalchemy.String)
    creator_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    creator = orm.relationship("User")
    moderators = orm.relationship("User", secondary=subreddit_moderators)
    no_members = sqlalchemy.Column(sqlalchemy.Integer, default=1)
    members = orm.relationship("User", secondary=subreddit_members)
    is_banned = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    banned_users = orm.relationship("User", secondary=subreddit_banned)
    posts = orm.relationship("Post", back_populates="subreddit")