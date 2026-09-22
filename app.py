from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "courier-secret-key"


def get_db():
    connection = sqlite3.connect("courier.db")
    connection.row_factory = sqlite3.Row
    return connection


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/track")
def track():
    return render_template("track.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        connection = get_db()

        try:
            connection.execute(
                """
                INSERT INTO users (name, email, password, role)
                VALUES (?, ?, ?, ?)
                """,
                (name, email, hashed_password, "customer")
            )

            connection.commit()

        except sqlite3.IntegrityError:
            connection.close()
            return "Email already registered."

        connection.close()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_db()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        return "Invalid email or password."

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return f"Welcome {session['user_name']}!"


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)