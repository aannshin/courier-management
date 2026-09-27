import os
import sqlite3
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify
)

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "courier-secret-key"
COMMIT = os.getenv("RENDER_GIT_COMMIT", "local")[:7]


def get_db():
    connection = sqlite3.connect("courier.db")
    connection.row_factory = sqlite3.Row
    return connection


@app.route("/")
def home():
    connection = get_db()

    shipments = connection.execute(
        "SELECT * FROM shipments ORDER BY id DESC"
    ).fetchall()

    connection.close()

    return render_template(
        "index.html",
        shipments=shipments,
        commit=COMMIT
    )


@app.route("/api/items")
def api_items():
    connection = get_db()

    shipments = connection.execute(
        "SELECT * FROM shipments ORDER BY id DESC"
    ).fetchall()

    connection.close()

    return jsonify([dict(shipment) for shipment in shipments])


@app.route("/health")
def health():
    return {"status": "ok"}


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

    tracking_id = request.form.get("tracking_id", "").strip()
    customer_id = request.form.get("customer_id", "").strip()
    receiver_name = request.form.get("receiver_name", "").strip()
    origin = request.form.get("origin", "").strip()
    destination = request.form.get("destination", "").strip()

    # Input validation
    if (
        not tracking_id
        or not customer_id
        or not receiver_name
        or not origin
        or not destination
    ):
        return "All shipment fields are required.", 400

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


@app.route("/admin/assign-agent/<int:shipment_id>", methods=["POST"])
def assign_agent(shipment_id):
    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    agent_id = request.form["agent_id"]

    connection = get_db()

    connection.execute(
        "UPDATE shipments SET agent_id = ? WHERE id = ?",
        (agent_id, shipment_id)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/agent")
def agent_dashboard():
    if "user_id" not in session or session["role"] != "agent":
        return redirect(url_for("login"))

    connection = get_db()

    shipments = connection.execute("""
        SELECT * FROM shipments
        WHERE agent_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    connection.close()

    return render_template(
        "agent_dashboard.html",
        shipments=shipments
    )


@app.route("/agent/update/<int:shipment_id>", methods=["POST"])
def update_shipment(shipment_id):
    if "user_id" not in session or session["role"] != "agent":
        return redirect(url_for("login"))

    status = request.form["status"]
    location = request.form["location"]

    connection = get_db()

    # Make sure the shipment belongs to this agent
    shipment = connection.execute("""
        SELECT * FROM shipments
        WHERE id = ? AND agent_id = ?
    """, (shipment_id, session["user_id"])).fetchone()

    if shipment:

        connection.execute("""
            UPDATE shipments
            SET status = ?, current_location = ?
            WHERE id = ?
        """, (status, location, shipment_id))

        connection.execute("""
            INSERT INTO shipment_updates
            (shipment_id, status, location)
            VALUES (?, ?, ?)
        """, (shipment_id, status, location))

        connection.commit()

    connection.close()

    return redirect(url_for("agent_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
