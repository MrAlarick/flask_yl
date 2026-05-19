from datetime import datetime

import flask
from click.types import convert_type
from flask import jsonify, make_response, request, render_template

from . import db_session
from .category import Category
from .departments import Department
from .jobs import Jobs
from .users import User

blueprint = flask.Blueprint(
    'user_api',
    __name__,
    template_folder='templates'
)

@blueprint.route('/api/users', methods=["GET", "POST"])
def get_users():
    db_sess = db_session.create_session()
    if request.method == "GET":
        return jsonify({"users": [item.to_dict() for item in db_sess.query(User).all()]})
    else:
        if not request.json:
            return make_response(jsonify({'error': 'Empty request'}), 400)
        elif not all(key in request.json for key in
                     ["surname", "name", "age", "position", "speciality", "address", "email", "password", "city_from", "departments"]):
            return make_response(jsonify({'error': 'Bad request'}), 400)
        user = User(
            surname=request.json["surname"],
            name=request.json['name'],
            age= request.json['age'],
            position=request.json['position'],
            speciality=request.json['speciality'],
            address=request.json['address'],
            email=request.json['email'],
            city_from=request.json["city_from"],
            modified_date=datetime.now(),
            departments=db_sess.query(Department).filter(Department.id.in_(request.json["departments"])).all()
        )
        user.set_password(request.json["password"])
        db_sess.add(user)
        db_sess.commit()
        return jsonify({'id': user.id})


@blueprint.route('/api/users/<int:user_id>', methods=["GET", "PATCH", "DELETE"])
def get_user(user_id):
    db_sess = db_session.create_session()
    if request.method == "GET":
        user = db_sess.get(User, user_id)
        if not user:
            return make_response(jsonify({'error': 'Not found'}), 404)
        return jsonify(
            {
                'user': user.to_dict()
            }
        )
    elif request.method == "PATCH":
        if not request.json:
            return make_response(jsonify({'error': 'Empty request'}), 400)
        elif not all(key in ["surname", "name", "email", "password", "departments", "city_from", "position", "speciality", "age", "address"]
                     for key in request.json):
            return make_response(jsonify({'error': 'Bad request'}), 400)
        user = db_sess.get(User, user_id)
        if not user:
            return make_response(jsonify({'error': 'Not found'}), 404)
        for key, value in request.json.items():
            if key == "departments":
                user.departments = db_sess.query(Department).filter(Department.id.in_(value))
            elif key == "password":
                user.set_password(value)
            else:
                setattr(user, key, value)
        user.modified_date = datetime.now()
        db_sess.commit()
        return jsonify({'success': 'OK'})
    user = db_sess.get(User, user_id)
    if not user:
        return make_response(jsonify({'error': 'Not found'}), 404)
    db_sess.delete(user)
    db_sess.commit()
    return jsonify({'success': 'OK'})
