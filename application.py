import os, json

from flask import Flask, session, render_template, request, jsonify, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required
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

	return render_template("index.html")

@app.route("/register")
def register():
	users = db.execute("SELECT * FROM users").fetchall()
	return render_template("register.html", user=users)


@app.route("/save", methods=["POST"])
def save():
	session.clear()

    # Ensure username was submitted
	if not request.form.get("username"):
		return render_template("errores/errornouser.html")

	# Query database for username	
	userCheck = db.execute("SELECT * FROM users WHERE username = :username",
						{"username":request.form.get("username")}).fetchone()

    # Check if username already exist
	if userCheck:
		return render_template("errores/erroruserexist.html")

	# Ensure password was submitted
	elif not request.form.get("password"):
		return render_template("errores/errornopass.html")

	# Hash user's password to store in DB
	hashedPassword = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)

	# Insert register into DB
	db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
			{"username": request.form.get("username"), "password": hashedPassword})
	db.commit()
		
	return render_template("login.html")


@app.route("/login")
def login():

    return render_template("login.html")

@app.route("/access", methods=["POST"])
def access():
	session.clear()

	username = request.form.get("username")

        # Ensure username was submitted
	if not request.form.get("username"):
		return render_template("errores/errornouser.html", message="must provide username")

        # Ensure password was submitted
	elif not request.form.get("password"):
		return render_template("errores/errornopass.html", message="must provide password")

        # Query database for username (http://zetcode.com/db/sqlalchemy/rawsql/)
        # https://docs.sqlalchemy.org/en/latest/core/connections.html#sqlalchemy.engine.ResultProxy
	rows = db.execute("SELECT * FROM users WHERE username = :username",
						{"username": username})
        
	result = rows.fetchone()

        # Ensure username exists and password is correct
	if result == None or not check_password_hash(result[2], request.form.get("password")):
		return render_template("errores/errorinvalid.html", message="invalid username and/or password")

        # Remember which user has logged in
	session["user_id"] = result[0]
	session["user_name"] = result[1]

	return render_template("book.html")

@app.route("/logout")
def logout():
    """ Log user out """

    # Forget any user ID
    session.clear()

    # Redirect user to login form
    return render_template("login.html")

@app.route("/results", methods=["POST"])
def results():
	book_column = request.form.get("book_column")
	query = '%'+request.form.get("query")+'%'

	comando="SELECT * FROM books WHERE year like :query OR isbn like :query OR author like :query OR title like :query"
	book_list=db.execute(comando,{"query":query}).fetchall()
	error_message="book not found"
	if len(book_list)==0:
		return render_template("errores/error404.html", error_message=error_message)

	return render_template("results.html", book_list=book_list) #falta lo del usuari


	"""

	if book_column == "year":
		book_list = db.execute("SELECT * FROM books WHERE year = :query", {"query": query}).fetchall()
	else:
		book_list = db.execute("SELECT * FROM books WHERE UPPER(" +book_column + ") = :query ORDER BY title",
							{"query": query.upper()}).fetchall()

	if len(book_list):
		return render_template("results.html", book_list=book_list) #falta lo del usuari

	elif book_column != "year":
		error_message = "We could not find the books you searched for"
		book_list = db.execute("SELECT * FROM books WHERE UPPER(" + book_column + ") LIKE :query ORDER BY title",
							{"query": "%" + query.upper() + "%"}).fetchall()

		if not len(book_list):
			return render_template("errores/error.html", error_message=error_message)
		message = "You might be searching for:"
		return render_template("results.html", error_message=error_message, book_list=book_list, message=message)
	else:
		return render_template("errores/error.html", error_message= "We dont find any book") """

@app.route("/description/<int:book_id>", methods=["GET", "POST"])
def description(book_id):

	#if "user_email" not in session:
	#	return render_template("login.html", error_message="Please Login First", work="Login")

	book = db.execute("SELECT * FROM books WHERE id = :book_id", {"book_id": book_id}).fetchone()
	if book is None:
		return render_template("errores/error404.html", error_message="We got an invalid book id"
			". Please check for the errors and try again.")

    # When review if submitted for the book.
	if request.method == "POST":
		user_id = session["user_id"]
		rating = request.form.get("rating")
		comment = request.form.get("comment")
		if db.execute("SELECT id FROM reviews WHERE user_id = :user_id AND book_id = :book_id",
			{"user_id": user_id, "book_id": book_id}).fetchone() is None:
			db.execute(
				"INSERT INTO reviews (user_id, book_id, rating, comment) VALUES (:user_id, :book_id, :rating, :comment)",
				{"book_id": book.id, "user_id": user_id, "rating": rating, "comment": comment})
			db.commit()
		else:
			flash('You already submitted a review for this book', 'error')
	return render_template("description.html", book=book)

    	

	#Goodreads API
    # Processing the json data


	res = requests.get("https://www.goodreads.com/book/review_counts.json",
		params={"key": "m4czDOSMV8CupWq8uROF8A", "isbns": book.isbn}).json()["books"][0]

	ratings_count = res["ratings_count"]
	average_rating = res["average_rating"]
	reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {"book_id": book.id}).fetchall()
	users = []
	for review in reviews:
		email = db.execute("SELECT email FROM users WHERE id = :user_id", {"user_id": review.user_id}).fetchone().email
		users.append((email, review))

		return render_template("description.html", book=book, users=users,
			ratings_count=ratings_count, average_rating=average_rating, user_email=session["user_email"])


# Page for the website's API"""

@app.route("/api/<ISBN>", methods=["GET"])
def api(ISBN):
	book = db.execute("SELECT * FROM books WHERE isbn = :ISBN", {"ISBN": ISBN}).fetchone()
	if book is None:
		return render_template("errores/error.html", error_message="ERROR 404 - no ISBN. "
                                                           "Please check for the errors and try again.")
	reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {"book_id": book.id}).fetchall()
	count = 0
	rating = 0
	for review in reviews:
		count += 1
		rating += review.rating
	if count:
		average_rating = rating / count
	else:
		average_rating = 0

	return jsonify(
		title=book.title,
		author=book.author,
		year=book.year,
		isbn=book.isbn,
		review_count=count,
		average_score=average_rating
	)
