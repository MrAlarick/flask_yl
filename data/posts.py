import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase


upvotes = sqlalchemy.Table(
    'upvotes',
    SqlAlchemyBase.metadata,
    sqlalchemy.Column('user_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), primary_key=True),
    sqlalchemy.Column('post_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('posts.id'), primary_key=True),
    extend_existing=True
)

downvotes = sqlalchemy.Table(
    'downvotes',
    SqlAlchemyBase.metadata,
    sqlalchemy.Column('user_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), primary_key=True),
    sqlalchemy.Column('post_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('posts.id'), primary_key=True),
    extend_existing=True
)

class Post(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'posts'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    text = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    no_images = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    rating = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, default=1)
    upvoted_by = orm.relationship("User", secondary=upvotes)
    downvoted_by = orm.relationship("User", secondary=downvotes)
    date = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    author_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    author = orm.relationship("User", back_populates="posts")
    subreddit_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("subreddits.id"))
    subreddit = orm.relationship("Subreddit", back_populates="posts")
    no_comments = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, default=0)
    comments = orm.relationship("Comment", back_populates="post")