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


@app.route("/track", methods=["GET", "POST"])
def track():

    if request.method == "POST":

        tracking_id = request.form["tracking_id"]

        connection = get_db()

        shipment = connection.execute(
            "SELECT * FROM shipments WHERE tracking_id = ?",
            (tracking_id,)
        ).fetchone()

        connection.close()

        return render_template(
            "tracking.html",
            shipment=shipment
        )

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

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            elif user["role"] == "agent":
                return redirect(url_for("agent_dashboard"))
            else:
                return redirect(url_for("dashboard"))

        return "Invalid email or password."

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("dashboard.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))

@app.route("/admin")
def admin_dashboard():

    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    connection = get_db()

    shipments = connection.execute("""
        SELECT shipments.*, users.name AS customer_name
        FROM shipments
        LEFT JOIN users ON shipments.customer_id = users.id
        ORDER BY shipments.id DESC
    """).fetchall()

    customers = connection.execute(
        "SELECT * FROM users WHERE role = 'customer'"
    ).fetchall()

    agents = connection.execute(
        "SELECT * FROM users WHERE role = 'agent'"
    ).fetchall()

    connection.close()

    return render_template(
        "admin_dashboard.html",
        shipments=shipments,
        customers=customers,
        agents=agents
    )


@app.route("/admin/create-shipment", methods=["POST"])
def create_shipment():

    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    tracking_id = request.form["tracking_id"]
    customer_id = request.form["customer_id"]
    receiver_name = request.form["receiver_name"]
    origin = request.form["origin"]
    destination = request.form["destination"]

    connection = get_db()

    connection.execute("""
        INSERT INTO shipments
        (tracking_id, customer_id, receiver_name, origin,
         destination, status, current_location)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        tracking_id,
        customer_id,
        receiver_name,
        origin,
        destination,
        "Booked",
        origin
    ))

    connection.commit()
    connection.close()

    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)