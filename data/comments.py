import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase


comment_upvotes = sqlalchemy.Table(
    'comment_upvotes',
    SqlAlchemyBase.metadata,
    sqlalchemy.Column('user_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), primary_key=True),
    sqlalchemy.Column('comment_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('comments.id'), primary_key=True),
    extend_existing=True
)

comment_downvotes = sqlalchemy.Table(
    'comment_downvotes',
    SqlAlchemyBase.metadata,
    sqlalchemy.Column('user_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), primary_key=True),
    sqlalchemy.Column('comment_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('comments.id'), primary_key=True),
    extend_existing=True
)


class Comment(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'comments'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    post_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("posts.id"))
    text = sqlalchemy.Column(sqlalchemy.String)
    has_image = sqlalchemy.Column(sqlalchemy.Boolean, nullable=True, default=False)
    rating = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, default=1)
    date = sqlalchemy.Column(sqlalchemy.DateTime)
    author_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    upvoted_by = orm.relationship("User", secondary=comment_upvotes)
    downvoted_by = orm.relationship("User", secondary=comment_downvotes)
    author = orm.relationship("User")
    post = orm.relationship("Post")
    replies = orm.relationship("Comment", backref=orm.backref("parent", remote_side=[id]))
    parent_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('comments.id'), nullable=True)