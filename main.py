import secrets
from datetime import datetime, timedelta, timezone

import nh3
import sqlalchemy
from flask import Flask, request, render_template, redirect, abort, session
import os

from flask_restful import Api
from flask_wtf import FlaskForm, RecaptchaField
from flask_wtf.file import FileAllowed
from markdown import markdown
from wtforms import StringField, PasswordField, SubmitField, FileField, EmailField
from wtforms.fields.simple import TextAreaField
from wtforms.validators import DataRequired, Length
from data import db_session
from data.comments import Comment
from data.posts import Post
from data.send_email import send_verification_email, send_code_email, send_deletion_email, send_subreddit_deletion_email
from data.subreddits import Subreddit
from data.users import User, UnverifiedUser
from flask_login import LoginManager, login_user, login_required, logout_user, current_user


from itsdangerous import URLSafeTimedSerializer


def generate_secure_code(length=6):
    return ''.join(secrets.choice("1234567890") for _ in range(length))

def generate_verification_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='email-verification-salt')

def confirm_verification_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        user_id = serializer.loads(
            token,
            salt='email-verification-salt',
            max_age=expiration
        )
    except:
        return False
    return user_id


class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    password_again = PasswordField("Retype password", validators=[DataRequired()])
    recaptcha = RecaptchaField()
    submit = SubmitField("Submit")


class EditForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    bio = TextAreaField("Bio")
    profile_picture = FileField('Profile picture', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif', "webp"], 'Images only!')])
    submit = SubmitField("Save")


class EditSubredditForm(FlaskForm):
    description = TextAreaField("Description")
    image = FileField('Image', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif', "webp"], 'Images only!')])
    submit = SubmitField("Save")


class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    recaptcha = RecaptchaField()
    submit = SubmitField('Log in')


class DeleteForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Delete account')


class DeleteSubredditForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Delete subreddit')


class VerifyCodeForm(FlaskForm):
    code = StringField("Code", validators=[DataRequired(), Length(6, 6)])
    recaptcha = RecaptchaField()
    submit = SubmitField('Log in')


class RegisterSubredditForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    description = StringField("Description", validators=[DataRequired()])
    image = FileField('Image', validators=[DataRequired(), FileAllowed(['jpg', 'png', 'jpeg', 'gif', "webp"], 'Images only!')])
    submit = SubmitField("Create subreddit")


class PostForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    body = TextAreaField("Body (markdown formatting supported)", validators=[DataRequired()])
    images = FileField('Images', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif', "webp"], 'Images only!')])
    submit = SubmitField("Post")


class CommentForm(FlaskForm):
    text = TextAreaField("Text", validators=[DataRequired()])
    image = FileField('Image', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif', "webp"], 'Images only!')])
    submit = SubmitField("Leave comment")


class ModeratorForm(FlaskForm):
    username = TextAreaField("Username", validators=[DataRequired()])
    submit = SubmitField("Submit")



app = Flask(__name__, static_url_path="/yl_host/static")

app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config["RECAPTCHA_PUBLIC_KEY"] = "6LfI8eAsAAAAALyr2XFs9aarvBsKvsU3yGnjKz4a"
app.config["RECAPTCHA_PRIVATE_KEY"] = ""

api = Api(app)
# для списка объектов
# api.add_resource(users_resource.UserListResource, '/api/v2/users')
#
# # для одного объекта
# api.add_resource(users_resource.UserResource, '/api/v2/users/<int:user_id>')
#
# # для списка объектов
# api.add_resource(jobs_resource.JobsListResource, '/api/v2/jobs')
#
# # для одного объекта
# api.add_resource(jobs_resource.JobsResource, '/api/v2/jobs/<int:job_id>')



login_manager = LoginManager()
login_manager.init_app(app)

db_session.global_init("db/reddit.db")


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    try:
        user = db_sess.get(User, user_id)
        if user and user.is_banned:
            return None
        return user
    finally:
        db_sess.close()


@app.route("/yl_host/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect("/yl_host")
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Registration',
                                   form=form,
                                  error="Passwords don't match")
        db_sess = db_session.create_session()
        try:
            if db_sess.query(User).filter(User.email == form.email.data).first():
                return render_template('register.html', title='Registration',
                                       form=form,
                                       error="User with that email already exists")
            if db_sess.query(User).filter(User.username == form.username.data).first():
                return render_template('register.html', title='Registration',
                                       form=form,
                                       error="User with that username already exists")
            if db_sess.query(UnverifiedUser).filter(UnverifiedUser.email == form.email.data).first():
                return render_template('register.html', title='Registration',
                                       form=form,
                                       error="User with that is already pending approval")
            if db_sess.query(UnverifiedUser).filter(UnverifiedUser.username == form.username.data).first():
                return render_template('register.html', title='Registration',
                                       form=form,
                                       error="User with that username is already pending approval")
            user = UnverifiedUser()
            user.name = form.name.data
            user.username = form.username.data
            user.email = form.email.data
            user.date = datetime.now()
            user.set_password(form.password.data)

            db_sess.add(user)
            db_sess.commit()
            token = generate_verification_token(form.email.data)
            send_verification_email(form.email.data, token)
        finally:
            db_sess.close()
        return render_template("login.html", form=LoginForm(), message="Please check your inbox to confirm account registration")
    return render_template('register.html', title='Регистрация', form=form)


@app.route("/yl_host/register/<token>", methods=["GET"])
def verify_register(token):
    email = confirm_verification_token(token)
    if not email:
        return "The verification link is invalid or has expired.", 400
    db_sess = db_session.create_session()
    try:
        old_user = db_sess.query(UnverifiedUser).filter(UnverifiedUser.email == email).first()
        new_user = User()
        new_user.username = old_user.username
        new_user.email = old_user.email
        new_user.name = old_user.name
        new_user.hashed_password = old_user.hashed_password
        db_sess.add(new_user)
        db_sess.delete(old_user)
        db_sess.commit()
    finally:
        db_sess.close()
    return "Account verified"


@app.route('/yl_host/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect("/yl_host")
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).filter(User.email == form.email.data).first()
            if user and not user.is_banned and user.check_password(form.password.data):
                code = generate_secure_code()
                session["temp_user_id"] = user.id
                session["auth_code"] = code
                session["auth_code_date"] = datetime.now(timezone.utc)
                send_code_email(user.email, code)
                return redirect("/yl_host/login/verify_email")
            return render_template('login.html',
                                   error="Wrong email or password",
                                   form=form)
        finally:
            db_sess.close()
    return render_template('login.html', form=form)


@app.route('/yl_host/login/verify_email', methods=['GET', 'POST'])
def verify_code():
    if current_user.is_authenticated:
        return redirect("/yl_host")
    if 'temp_user_id' not in session:
        return redirect("/yl_host/login")
    form = VerifyCodeForm()
    if form.validate_on_submit():
        correct_code = session.get("auth_code")
        if form.code.data == correct_code:
            user_id = session.pop('temp_user_id')
            session.pop("auth_code")
            if (datetime.now(timezone.utc) - session.pop("auth_code_date")) > timedelta(minutes=10):
                return render_template('login.html',
                                       error="Code expired. Please try again",
                                       form=form)
            db_sess = db_session.create_session()
            try:
                user = db_sess.query(User).filter(User.id == user_id).first()
                login_user(user, remember=True)
            finally:
                db_sess.close()
            return redirect("/yl_host/")
        return render_template('verify.html',
                               error="Wrong code",
                               form=form)
    return render_template('verify.html', form=form)


@app.route("/yl_host/delete_account/<token>", methods=["GET"])
def verify_delete(token):
    email = confirm_verification_token(token)
    if not email:
        return "The verification link is invalid or has expired.", 400
    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).filter(User.email == email).first()
        db_sess.delete(user)
        db_sess.commit()
    finally:
        db_sess.close()
    return "Account deleted"


@app.route('/yl_host/logout')
@login_required
def logout():
    logout_user()
    return redirect("/yl_host")


@app.route('/yl_host/delete_account/', methods=["GET", "POST"])
@login_required
def delete_account():
    form = DeleteForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.password.data):
            return render_template('delete_account.html',
                                   form=form,
                                   error="Wrong password")
        token = generate_verification_token(current_user.email)
        send_deletion_email(current_user.email, token)
        logout_user()
        return render_template("login.html", form=LoginForm(),
                               message="Please check your inbox to confirm account deletion")
    return render_template('delete_account.html', form=form)


@app.route("/yl_host/")
def root():
    db_sess = db_session.create_session()
    try:
        posts = [post for post in db_sess.query(Post).filter(Post.date > (datetime.now(timezone.utc) - timedelta(weeks=1))).order_by(sqlalchemy.desc(Post.rating)).all() if not post.subreddit.is_banned]
        return render_template("home.html", posts=posts)
    finally:
        db_sess.close()


@app.route("/yl_host/user/<username>")
def get_user(username):
    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).filter(User.username == username).first()
        if user:
            posts = [post for post in db_sess.query(Post).filter(Post.author_id == user.id).order_by(sqlalchemy.desc(Post.rating)).all() if not post.subreddit.is_banned]
            return render_template("user.html", user=user, posts=posts)
    finally:
        db_sess.close()
    abort(404)


@app.route("/yl_host/edit_user/", methods=["GET", "POST"])
@login_required
def edit_user():
    form = EditForm()
    if request.method == "GET":
        form.bio.data = current_user.bio
        form.name.data = current_user.name
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).filter(User.id == current_user.id).first()
            user.bio = form.bio.data
            user.name = form.name.data
            db_sess.commit()
            if form.profile_picture.data:
                form.profile_picture.data.save(f"static/img/pfp/{user.username}")
            return redirect(f"/yl_host/user/{user.username}")
        finally:
            db_sess.close()
    return render_template("edit.html", form=form)


@app.route("/yl_host/ban_user/<username>", methods=["GET"])
@login_required
def ban_user(username):
    if not current_user.is_admin:
        abort(403)
    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).filter(User.username == username).first()
        if user.is_banned:
            abort(400)
        user.is_banned = True
        db_sess.commit()
    finally:
        db_sess.close()
    return redirect(request.referrer or f"/yl_host/user/{username}")


@app.route("/yl_host/unban_user/<username>", methods=["GET"])
@login_required
def unban_user(username):
    if not current_user.is_admin:
        abort(403)
    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).filter(User.username == username).first()
        if not user.is_banned:
            abort(400)
        user.is_banned = False
        db_sess.commit()
    finally:
        db_sess.close()
    return redirect(request.referrer or f"/yl_host/user/{username}")


@app.route("/yl_host/create_post/<subreddit_name>", methods=["GET", "POST"])
@login_required
def create_post(subreddit_name):
    db_sess = db_session.create_session()
    try:
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == subreddit_name).first()
        if not subreddit:
            abort(404)
        if current_user not in subreddit.members or current_user in subreddit.banned_users:
            abort(403)
        if subreddit.is_banned:
            return "This subreddit is banned"
        form = PostForm()
        if form.validate_on_submit():
            user = db_sess.query(User).filter(User.id == current_user.id).first()
            post = Post()
            post.subreddit = subreddit
            post.title = form.title.data
            post.text = nh3.clean(markdown(form.body.data))
            post.author = user
            post.date = datetime.now(timezone.utc)
            post.upvoted_by.append(user)
            db_sess.add(post)
            db_sess.commit()
            uploaded_images = request.files.getlist(form.images.name)
            no_images = 0
            for image in uploaded_images:
                if image and image.filename:
                    image.save(f"static/img/post/{post.id}_{no_images}")
                    no_images += 1
            post.no_images = no_images
            db_sess.commit()
            return redirect(f"/yl_host/post/{post.id}")
        return render_template("create_post.html", form=form, subreddit=subreddit)
    finally:
        db_sess.close()


@app.route("/yl_host/post/<post_id>/")
def get_post(post_id):
    db_sess = db_session.create_session()
    try:
        post = db_sess.query(Post).filter(Post.id == post_id).first()
        if post:
            if post.subreddit.is_banned:
                return "This subreddit is banned"
            return render_template("post.html", post=post, form=CommentForm())
    finally:
        db_sess.close()
    abort(404)


@app.route("/yl_host/create_subreddit/", methods=["GET", "POST"])
@login_required
def create_subreddit():
    form = RegisterSubredditForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            if db_sess.query(Subreddit).filter(Subreddit.name == form.name.data).first():
                return render_template('create_subreddit.html', form=form, error="Subreddit with that name already exists")
            user = db_sess.query(User).filter(User.id == current_user.id).first()
            subreddit = Subreddit()
            subreddit.name = form.name.data
            subreddit.description = form.description.data
            subreddit.creator = user
            subreddit.members.append(user)
            subreddit.moderators.append(user)
            form.image.data.save(f"static/img/srp/{form.name.data}")
            db_sess.add(subreddit)
            db_sess.commit()
            return redirect(f"/yl_host/subreddit/{form.name.data}")
        finally:
            db_sess.close()
    return render_template("create_subreddit.html", form=form)


@app.route("/yl_host/subreddit/<subreddit_name>")
def get_subreddit(subreddit_name):
    db_sess = db_session.create_session()
    try:
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == subreddit_name).first()
        if subreddit:
            if subreddit.is_banned:
                if current_user.is_authenticated and current_user.is_admin:
                    return render_template("subreddit.html", subreddit=subreddit)
                return "This subreddit is banned"
            return render_template("subreddit.html", subreddit=subreddit)
    finally:
        db_sess.close()
    abort(404)


@app.route("/yl_host/ban_subreddit/<subreddit_name>", methods=["GET"])
@login_required
def ban_subreddit(subreddit_name):
    if not current_user.is_admin:
        abort(403)
    db_sess = db_session.create_session()
    try:
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == subreddit_name).first()
        if subreddit.is_banned:
            abort(400)
        subreddit.is_banned = True
        db_sess.commit()
        return redirect(request.referrer or f"/yl_host/subreddit/{subreddit_name}")
    finally:
        db_sess.close()


@app.route("/yl_host/unban_subreddit/<subreddit_name>", methods=["GET"])
@login_required
def unban_subreddit(subreddit_name):
    if not current_user.is_admin:
        abort(403)
    db_sess = db_session.create_session()
    try:
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == subreddit_name).first()
        if not subreddit.is_banned:
            abort(400)
        subreddit.is_banned = False
        db_sess.commit()
        return redirect(request.referrer or f"/yl_host/subreddit/{subreddit_name}")
    finally:
        db_sess.close()


@app.route("/yl_host/edit_subreddit/<subreddit_name>", methods=["GET", "POST"])
@login_required
def edit_subreddit(subreddit_name):
    db_sess = db_session.create_session()
    try:
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == subreddit_name).first()
        if current_user not in subreddit.moderators:
            abort(403)
        form = EditSubredditForm()
        if request.method == "GET":
            form.description.data = subreddit.description
        if form.validate_on_submit():
            subreddit.description = form.description.data
            db_sess.commit()
            if form.image.data:
                form.image.data.save(f"static/img/srp/{subreddit.name}")
            return redirect(f"/yl_host/subreddit/{subreddit.name}")
        return render_template("edit_subreddit.html", form=form, subreddit=subreddit)
    finally:
        db_sess.close()


@app.route("/yl_host/confirm_subreddit_deletion/<token>", methods=["GET"])
def verify_delete_subreddit(token):
    name = confirm_verification_token(token)
    if not name:
        return "The verification link is invalid or has expired.", 400
    db_sess = db_session.create_session()
    try:
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == name).first()
        db_sess.delete(subreddit)
        db_sess.commit()
        return "Subreddit deleted"
    finally:
        db_sess.close()


@app.route('/yl_host/delete_subreddit/<subreddit_name>', methods=["GET", "POST"])
@login_required
def delete_subreddit(subreddit_name):
    db_sess = db_session.create_session()
    try:
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == subreddit_name).first()
        if current_user.id != subreddit.creator_id:
            abort(403)
        form = DeleteSubredditForm()
        if form.validate_on_submit():
            if not current_user.check_password(form.password.data):
                return render_template('delete_subreddit.html',
                                       form=form,
                                       error="Wrong password")
            token = generate_verification_token(subreddit.name)
            send_subreddit_deletion_email(current_user.email, token)
            return "Please check your inbox to confirm subreddit deletion"
        return render_template('delete_subreddit.html', form=form, subreddit=subreddit)
    finally:
        db_sess.close()


@app.route('/yl_host/join/<subreddit_name>', methods=["GET"])
@login_required
def join_subreddit(subreddit_name):
    db_sess = db_session.create_session()
    try:
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == subreddit_name).first()
        if current_user in subreddit.members:
            abort(400)
        subreddit.members.append(db_sess.query(User).filter(User.id == current_user.id).first())
        subreddit.no_members += 1
        db_sess.commit()
        return redirect(request.referrer or f"/yl_host/subreddit/{subreddit_name}")
    finally:
        db_sess.close()


@app.route('/yl_host/leave/<subreddit_name>', methods=["GET"])
@login_required
def leave_subreddit(subreddit_name):
    db_sess = db_session.create_session()
    try:
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == subreddit_name).first()
        if current_user not in subreddit.members or current_user.id == subreddit.creator_id:
            abort(400)
        subreddit.members.remove(current_user)
        if current_user in subreddit.moderators:
            subreddit.moderators.remove(current_user)
        subreddit.no_members -= 1
        db_sess.commit()
        return redirect(request.referrer or f"/yl_host/subreddit/{subreddit_name}")
    finally:
        db_sess.close()


@app.route('/yl_host/delete_post/<post_id>', methods=["GET"])
@login_required
def delete_post(post_id):
    db_sess = db_session.create_session()
    try:
        post = db_sess.query(Post).filter(Post.id == post_id).first()
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == post.subreddit.name).first()
        if current_user.id != post.author_id and current_user not in subreddit.moderators and not current_user.is_admin:
            abort(403)
        for i in range(post.no_images):
            os.remove(f"static/img/post/{post.id}_{i}")
        db_sess.delete(post)
        db_sess.commit()
        return redirect(f"/yl_host/subreddit/{subreddit.name}")
    finally:
        db_sess.close()


@app.route("/yl_host/ban_user_from_subreddit/<username>/<subreddit_name>", methods=["GET"])
@login_required
def ban_user_subreddit(username, subreddit_name):
    db_sess = db_session.create_session()
    try:
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == subreddit_name).first()
        if current_user not in subreddit.moderators:
            abort(403)
        user = db_sess.query(User).filter(User.username == username).first()
        if user in subreddit.banned_users:
            abort(400)
        subreddit.banned_users.append(user)
        db_sess.commit()
        return redirect(request.referrer or f"/yl_host/subreddit/{subreddit.name}")
    finally:
        db_sess.close()


@app.route("/yl_host/unban_user_from_subreddit/<username>/<subreddit_name>", methods=["GET"])
@login_required
def unban_user_subreddit(username, subreddit_name):
    db_sess = db_session.create_session()
    try:
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == subreddit_name).first()
        if current_user not in subreddit.moderators:
            abort(403)
        user = db_sess.query(User).filter(User.username == username).first()
        if user not in subreddit.banned_users:
            abort(400)
        subreddit.banned_users.remove(user)
        db_sess.commit()
        return redirect(request.referrer or f"/yl_host/subreddit/{subreddit.name}")
    finally:
        db_sess.close()


@app.route("/yl_host/upvote/<post_id>", methods=["GET"])
@login_required
def upvote(post_id):
    db_sess = db_session.create_session()
    try:
        post = db_sess.query(Post).filter(Post.id == post_id).first()
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        if user in post.downvoted_by:
            post.downvoted_by.remove(user)
            post.upvoted_by.append(user)
            post.rating += 2
            post.author.karma += 2
        elif user in post.upvoted_by:
            post.upvoted_by.remove(user)
            post.rating -= 1
            post.author.karma -= 1
        else:
            post.upvoted_by.append(user)
            post.rating += 1
            post.author.karma += 1
        db_sess.commit()
        return redirect(request.referrer or f"/yl_host/post/{post_id}")
    finally:
        db_sess.close()


@app.route("/yl_host/downvote/<post_id>", methods=["GET"])
@login_required
def downvote(post_id):
    db_sess = db_session.create_session()
    try:
        post = db_sess.query(Post).filter(Post.id == post_id).first()
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        if user in post.downvoted_by:
            post.downvoted_by.remove(user)
            post.rating += 1
            post.author.karma += 1
        elif user in post.upvoted_by:
            post.upvoted_by.remove(user)
            post.downvoted_by.append(user)
            post.rating -= 2
            post.author.karma -= 2
        else:
            post.downvoted_by.append(user)
            post.rating -= 1
            post.author.karma -= 1
        db_sess.commit()
        return redirect(request.referrer or f"/yl_host/post/{post_id}")
    finally:
        db_sess.close()


@app.route("/yl_host/add_moderator/<subreddit_name>/<username>", methods=["GET"])
@login_required
def add_moderator(username, subreddit_name):
    db_sess = db_session.create_session()
    try:
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == subreddit_name).first()
        if not subreddit:
            abort(404)
        if current_user.id != subreddit.creator_id:
            abort(403)
        user = db_sess.query(User).filter(User.username == username).first()
        if user in subreddit.moderators:
            abort(400)
        subreddit.moderators.append(user)
        db_sess.commit()
        return redirect(f"/yl_host/subreddit/{subreddit.name}")
    finally:
        db_sess.close()


@app.route("/yl_host/add_moderator/<subreddit_name>", methods=["GET", "POST"])
@login_required
def add_moderator_form(subreddit_name):
    db_sess = db_session.create_session()
    try:
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == subreddit_name).first()
        if not subreddit:
            abort(404)
        if current_user.id != subreddit.creator_id:
            abort(403)
        form = ModeratorForm()
        if form.validate_on_submit():
            user = db_sess.query(User).filter(User.username == form.username.data).first()
            if not user:
                return render_template("add_moderator.html", form=form, error="This user does not exist",
                                       subreddit_name=subreddit_name)
            if user in subreddit.moderators:
                return render_template("add_moderator.html", form=form, error="This user is already a moderator", subreddit_name=subreddit_name)
            subreddit.moderators.append(user)
            db_sess.commit()
        return render_template("add_moderator.html", form=form, subreddit_name=subreddit_name)
    finally:
        db_sess.close()


@app.route("/yl_host/remove_moderator/<subreddit_name>/<username>", methods=["GET"])
@login_required
def remove_moderator(username, subreddit_name):
    db_sess = db_session.create_session()
    try:
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == subreddit_name).first()
        if not subreddit:
            abort(404)
        if current_user.id != subreddit.creator_id:
            abort(403)
        user = db_sess.query(User).filter(User.username == username).first()
        if user not in subreddit.moderators:
            abort(400)
        subreddit.moderators.remove(user)
        db_sess.commit()
        return redirect(f"/yl_host/subreddit/{subreddit.name}")
    finally:
        db_sess.close()


@app.route("/yl_host/remove_moderator/<subreddit_name>", methods=["GET", "POST"])
@login_required
def remove_moderator_form(subreddit_name):
    db_sess = db_session.create_session()
    try:
        subreddit = db_sess.query(Subreddit).filter(Subreddit.name == subreddit_name).first()
        if not subreddit:
            abort(404)
        if current_user.id != subreddit.creator_id:
            abort(403)
        form = ModeratorForm()
        if form.validate_on_submit():
            user = db_sess.query(User).filter(User.username == form.username.data).first()
            if not user:
                return render_template("add_moderator.html", form=form, error="This user does not exist",
                                       subreddit_name=subreddit_name)
            if user not in subreddit.moderators:
                return render_template("remove_moderator.html", form=form, error="This user is not a moderator", subreddit_name=subreddit_name)
            subreddit.moderators.remove(user)
            db_sess.commit()
        return render_template("remove_moderator.html", form=form, subreddit_name=subreddit_name)
    finally:
        db_sess.close()


@app.route("/yl_host/create_comment/<post_id>", methods=["POST"])
@login_required
def create_comment(post_id):
    db_sess = db_session.create_session()
    try:
        post = db_sess.query(Post).filter(Post.id == post_id).first()
        if not post:
            abort(404)
        if current_user in post.subreddit.banned_users:
            abort(403)
        form = CommentForm()
        if form.validate_on_submit():
            user = db_sess.query(User).filter(User.id == current_user.id).first()
            comment = Comment()
            comment.text = form.text.data
            comment.author = user
            comment.post = post
            comment.date = datetime.now(timezone.utc)
            comment.upvoted_by.append(user)
            post.no_comments += 1
            db_sess.add(comment)
            db_sess.commit()
            if form.image.data:
                comment.has_image = True
                form.image.data.save(f"static/img/comment/{comment.id}")
                db_sess.commit()
            return redirect(request.referrer or f"/yl_host/post/{post.id}")
        return render_template("post.html", form=form, post=post)
    finally:
        db_sess.close()


@app.route("/yl_host/reply/<comment_id>", methods=["GET", "POST"])
@login_required
def reply_comment(comment_id):
    db_sess = db_session.create_session()
    try:
        parent = db_sess.query(Comment).filter(Comment.id == comment_id).first()
        if not parent:
            abort(404)
        if current_user in parent.post.subreddit.banned_users:
            abort(403)
        form = CommentForm()
        if form.validate_on_submit():
            user = db_sess.query(User).filter(User.id == current_user.id).first()
            comment = Comment()
            comment.text = form.text.data
            comment.author = user
            comment.post = parent.post
            comment.date = datetime.now(timezone.utc)
            comment.upvoted_by.append(user)
            comment.parent_id = parent.id
            parent.post.no_comments += 1
            db_sess.add(comment)
            db_sess.commit()
            if form.image.data:
                comment.has_image = True
                form.image.data.save(f"static/img/comment/{comment.id}")
                db_sess.commit()
            return redirect(f"/yl_host/post/{parent.post.id}")
        return render_template("reply.html", form=form, comment=parent)
    finally:
        db_sess.close()


@app.route("/yl_host/upvote_comment/<comment_id>", methods=["GET"])
@login_required
def upvote_comment(comment_id):
    db_sess = db_session.create_session()
    try:
        comment = db_sess.query(Comment).filter(Comment.id == comment_id).first()
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        if user in comment.downvoted_by:
            comment.downvoted_by.remove(user)
            comment.upvoted_by.append(user)
            comment.rating += 2
            comment.author.karma += 2
        elif user in comment.upvoted_by:
            comment.upvoted_by.remove(user)
            comment.rating -= 1
            comment.author.karma -= 1
        else:
            comment.upvoted_by.append(user)
            comment.rating += 1
            comment.author.karma += 1
        db_sess.commit()
        return redirect(request.referrer or f"/yl_host/post/{comment.post.id}")
    finally:
        db_sess.close()


@app.route("/yl_host/downvote_comment/<comment_id>", methods=["GET"])
@login_required
def downvote_comment(comment_id):
    db_sess = db_session.create_session()
    try:
        comment = db_sess.query(Comment).filter(Comment.id == comment_id).first()
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        if user in comment.upvoted_by:
            comment.upvoted_by.remove(user)
            comment.downvoted_by.append(user)
            comment.rating -= 2
            comment.author.karma -= 2
        elif user in comment.downvoted_by:
            comment.downvoted_by.remove(user)
            comment.rating += 1
            comment.author.karma += 1
        else:
            comment.downvoted_by.append(user)
            comment.rating -= 1
            comment.author.karma -= 1
        db_sess.commit()
        return redirect(request.referrer or f"/yl_host/post/{comment.post.id}")
    finally:
        db_sess.close()


def main():
    #app.run(port=8080, host='127.0.0.1')
    #app.register_blueprint(jobs_api.blueprint)
    #app.register_blueprint(user_api.blueprint)
    #app.run(port=8080)
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.email == "alarick@alarick.org").first()
    # # # user.karma = 0
    # # # user.bio = "https://alarick.org"
    user.is_admin = True
    db_sess.commit()


if __name__ == '__main__':
    main()
