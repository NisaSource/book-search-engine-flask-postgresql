import os

from flask import (
    Flask,
    session,
    redirect,
    render_template,
    request,
    jsonify,
    flash,
    url_for,
)
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from werkzeug.security import check_password_hash, generate_password_hash

import requests

from helper import login_required

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template("register.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    message = None

    if request.method == "POST":
        usrname = request.form.get("username")
        psswrd = request.form.get("password")
        confirm = request.form.get("confirmation")

        if not usrname:
            return render_template(
                "register.html", message="please input a valid username!"
            )

        userCheck = db.execute(
            "SELECT * FROM users WHERE username= :u", {"u": usrname}
        ).fetchone()

        if userCheck:
            return render_template("register.html", message="username already exist!")

        elif not psswrd:
            return render_template("register.html", message="input your password!")

        elif not confirm:
            return render_template(
                "register.html", message="please confirm your password!"
            )

        elif not psswrd == confirm:
            return render_template("register.html", message="password did't match!")

        hashed_pass = generate_password_hash(psswrd)

        db.execute(
            "INSERT INTO users(username, password) VALUES(:u, :p)",
            {"u": usrname, "p": hashed_pass},
        )
        db.commit()

        return render_template("login.html")

    return render_template("register.html", message=message)


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        usrname = request.form.get("username")
        psswrd = request.form.get("password")

        if not usrname:
            return render_template("login.html", message="Must provide username")

        elif not psswrd:
            return render_template("login.html", message="Must provide password")

        rows = db.execute("SELECT * FROM users WHERE username= :u", {"u": usrname},)

        result = rows.fetchone()

        if result == None or not check_password_hash(result[2], psswrd):
            return render_template("login.html", message="Invalid username/ password.")

        session["user_id"] = result[0]
        session["user_name"] = result[1]

        return redirect("/search")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():

    bkrequest = request.args.get("searchbox")
    if not bkrequest:
        return render_template("search.html", message="You must provide a book!")

    query = "%" + bkrequest + "%"

    query = query.title()

    rows = db.execute(
        "SELECT isbn, title, author, year FROM books WHERE isbn LIKE :query OR title LIKE :query OR author LIKE :query LIMIT 15",
        {"query": query},
    )

    if rows.rowcount == 0:
        return render_template(
            "search.html",
            message="We're sorry, we can't find any book with your description.",
        )

    books = rows.fetchall()
    print("books ===", books)

    return render_template("booksresult.html", books=books)


@app.route("/booksresult", methods=["GET"])
def booksresult():
    print(session)
    if "user_name" not in session:
        return redirect("/login")

    query = request.values.get("searchbox")
    # print("q ===", query)
    query = "%" + query.lower() + "%"
    results = db.execute(
        "SELECT * FROM books WHERE lower(title) LIKE :q OR isbn LIKE :q OR lower(author) LIKE :q",
        {"q": query},
    )

    return render_template("booksresult.html", results=results)


@app.route("/b/<string:isbn>", methods=["GET", "POST"])
def bookinfo(isbn):
    if "user_name" not in session:
        return redirect("/login")

    if request.method == "POST":
        comment = request.form.get("comment")
        my_rating = request.form.get("rating")
        db.execute(
            "INSERT INTO reviews (acc_name, book_id, comment, rating) VALUES (:a, :b, :c, :r)",
            {"a": session["user_name"], "b": isbn, "c": comment, "r": my_rating},
        )
        db.commit()

    book = db.execute("SELECT * FROM books WHERE isbn = :q", {"q": isbn}).fetchone()
    reviews = db.execute(
        "SELECT * FROM reviews WHERE book_id = :q1", {"q1": isbn}
    ).fetchall()

    response = requests.get(
        "https://www.goodreads.com/book/review_counts.json",
        params={"key": "rjTuAoXwWDGvCab6TrY4Q", "isbns": isbn},
    )
    data = response.json()
    gr_rating = data["books"][0]["average_rating"]

    return render_template(
        "bookinfo.html", book_info=book, reviews=reviews, rating=gr_rating
    )


@app.route("/api/<string:isbn>")
def api(isbn):
    book = db.execute("SELECT * FROM books WHERE isbn = :q", {"q": isbn}).fetchone()

    if book is None:
        return jsonify({"error": "INVALID ISBN"}), 404

    db.execute("SELECT * FROM reviews WHERE book_id = :q1", {"q1": isbn}).fetchall()
    response = requests.get(
        "https://www.goodreads.com/book/review_counts.json",
        params={"key": "rjTuAoXwWDGvCab6TrY4Q", "isbns": isbn},
    )
    data = response.json()["books"][0]

    return jsonify(
        {
            "title": book.title,
            "author": book.author,
            "isbn": book.isbn,
            "review_count": data["reviews_count"],
            "average_rating": data["average_rating"],
        }
    )


@app.after_request
def after_request(response):
    if db is not None:
        db.close()
    return response
