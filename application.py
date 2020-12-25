import os

from flask import Flask, session,render_template,request,jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests

app = Flask(__name__)

# Check for environment variable
# if not os.getenv("DATABASE_URL"):
#     raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))




@app.route('/')
def index():
    return render_template("login.html")

@app.route('/register')
def register():
    return render_template("register.html")

@app.route('/login', methods=["POST","GET"])
def login():
    if request.method=="POST":
        user =request.form.get("name")
        email= request.form.get("email")
        phone= request.form.get("phone")
        password= request.form.get("pass")
        conpass= request.form.get("conpass")
        if db.execute("SELECT * FROM register where username = :user",{"user":user}).rowcount == 1:
            return render_template("register.html", namemessage="user has been used")
        
        if password != conpass:
            return render_template("register.html", passmessage="passwords are not the same")

        db.execute("INSERT INTO register (username,email,password,phone) VALUES (:user,:email,:password,:phone)",
            {"user":user,"email":email,"password":conpass,"phone":phone})
        db.commit()
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop('user_id',None)
    return render_template("login.html")

@app.route("/search", methods=["POST","GET"])
def search():
    if request.method=="POST":
        user=request.form.get("username")
        password=request.form.get("password")
        users = db.execute("select * from register where (username = :user) and (password = :passw)",
                        {"user":user,"passw":password}).fetchone()
        if users is None:
            return render_template("login.html", message="username or password is not right")
        id= db.execute("SELECT id FROM register WHERE (username = :user) and (password = :passw)",
                        {"user":user,"passw":password}).fetchone()
        session["user_id"]=id
    if session.get("user_id") is None:
        return render_template("error.html",messege="Please login first")
    return render_template("search.html")

@app.route("/list",methods=["POST","GET"])
def list():
    if session.get("user_id") is None:
        return render_template("error.html",messege="Please login first")
    if request.method=="POST":
        search0=request.form.get("search")
        try:
            year=int(search0)
        except:
            year = 0
        search="%"
        search+=search0
        search+="%"
        books= db.execute("SELECT * FROM books WHERE isbn = :search0 or title LIKE :search or author LIKE :search or year= :year",
            {"search0":search0,"search":search,"year":year}).fetchall()
        if not books:
            return render_template("search.html", error="no such thing matches")
    return render_template("search.html",books=books)

@app.route("/details/<book_id>")
def details(book_id):
    if session.get("user_id") is None: 
        return render_template("error.html",messege="Please login first")
    book=db.execute("SELECT * FROM books WHERE isbn = :book_id",
         {"book_id":book_id}).fetchone()
    avg=db.execute("SELECT AVG(rate) FROM review WHERE book_id=:book_id",{"book_id":book_id}).fetchone()
    if avg[0] is None:
        avg="no yet"
    else: avg=float(avg[0])
    return render_template("details.html",book=book,avg=avg)

@app.route("/review/<book_id>", methods=["POST","GET"])
def review(book_id):
    book=db.execute("SELECT * FROM books WHERE isbn = :book_id",
         {"book_id":book_id}).fetchone()
    if session.get("user_id") is None:
        return render_template("error.html",messege="Please login first")
    if request.method=="POST":
        if db.execute("SELECT * FROM review WHERE book_id=:book_id and user_id=:user_id",
        {"book_id":book_id,"user_id":session["user_id"][0]}).rowcount == 1:
            return  render_template("details.html",book=book,error="You rate this bock before")
        rate=request.form.get("rating")
        opinion=request.form.get("opinion")
        db.execute("INSERT INTO review (rate,opinion,book_id,user_id) VALUES (:rate,:opinion,:book_id,:user_id)",
            {"rate":rate,"opinion":opinion,"book_id":book_id,"user_id":session["user_id"][0]})
        db.commit()
        # aa=session["user_id"][0]
    return f"success: {rate}"

@app.route("/api/<isbn>")
def api(isbn):
    book=db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn":isbn}).fetchone()
    if book is None:
        return jsonify({"error": "Invalid isbn"}), 404 
    review_count=db.execute("SELECT COUNT(rate) FROM review WHERE book_id =:isbn",{"isbn":isbn}).fetchone()
    avg=db.execute("SELECT AVG(rate) FROM review WHERE book_id=:book_id",{"book_id":isbn}).fetchone()
    if avg[0] is None:
        avg="no yet"
    else: avg=float(avg[0])
    return jsonify({
            "title": book.title,
            "author": book.author,
            "year": book.year,
            "isbn": book.isbn,
            "review_count": review_count[0],
            "average_score": avg 
        })
@app.route("/apis/<isbn>")
def apis(isbn):
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                 params={"key": "RdOT6HYhFm8jmPpICqUodg", "isbns": isbn})
    data=res.json()
    return data
