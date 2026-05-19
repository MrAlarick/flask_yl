from datetime import datetime

from flask import jsonify
from flask_restful import reqparse, abort, Api, Resource

from data import db_session
from data.departments import Department
from data.users import User
from data.users_parser import parser


def abort_if_user_not_found(user_id):
    session = db_session.create_session()
    user = session.query(User).get(user_id)
    if not user:
        abort(404, message=f"User {user_id} not found")


class UserResource(Resource):
    def get(self, user_id):
        abort_if_user_not_found(user_id)
        session = db_session.create_session()
        user = session.get(User, user_id)
        return jsonify({'user': user.to_dict(
            only=('name', 'surname', 'email', 'age', "position", "speciality", "address", "city_from", "departments", "modified_date"))})

    def delete(self, user_id):
        abort_if_user_not_found(user_id)
        session = db_session.create_session()
        user = session.get(User, user_id)
        session.delete(user)
        session.commit()
        return jsonify({'success': 'OK'})

class UserListResource(Resource):
    def get(self):
        session = db_session.create_session()
        users = session.query(User).all()
        return jsonify({'users': [item.to_dict(
            only=("name", "surname", "email")) for item in users]})

    def post(self):
        args = parser.parse_args()
        session = db_session.create_session()
        user = User(
            name=args["name"],
            surname=args["surname"],
            email=args["email"],
            position=args["position"],
            speciality=args["speciality"],
            address=args["address"],
            city_from=args["city_from"],
            age=args["age"],
            departments=session.query(Department).filter(Department.id.in_([] if args["departments"] is None else args["departments"])).all(),
            modified_date=datetime.now()
        )
        user.set_password(args["password"])
        session.add(user)
        session.commit()
        return jsonify({'id': user.id})
