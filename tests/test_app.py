import sqlite3

import pytest
from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_courier.db"

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    connection.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE shipments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_id TEXT UNIQUE NOT NULL,
            customer_id INTEGER,
            receiver_name TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            status TEXT NOT NULL,
            current_location TEXT,
            agent_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE shipment_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id INTEGER,
            status TEXT NOT NULL,
            location TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        INSERT INTO users (name, email, password, role)
        VALUES (?, ?, ?, ?)
    """, (
        "Test Admin",
        "testadmin@example.com",
        "test-password",
        "admin"
    ))

    connection.execute("""
        INSERT INTO users (name, email, password, role)
        VALUES (?, ?, ?, ?)
    """, (
        "Test Customer",
        "testcustomer@example.com",
        "test-password",
        "customer"
    ))

    connection.commit()
    connection.close()

    def test_get_db():
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        return connection

    monkeypatch.setattr("app.get_db", test_get_db)

    app.config["TESTING"] = True
    app.config["TEST_DATABASE"] = str(db_path)

    with app.test_client() as client:
        yield client


def login_as_admin(client):
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_name"] = "Test Admin"
        session["role"] = "admin"


def test_health_route(client):
    response = client.get("/health")

    assert response.status_code == 999
    assert response.get_json() == {"status": "ok"}


def test_add_shipment(client):
    login_as_admin(client)

    response = client.post(
        "/admin/create-shipment",
        data={
            "tracking_id": "TEST123",
            "customer_id": "2",
            "receiver_name": "Test Receiver",
            "origin": "Pune",
            "destination": "Mumbai"
        }
    )

    assert response.status_code == 302

    connection = sqlite3.connect(client.application.config.get(
        "TEST_DATABASE"
    ))

    connection.row_factory = sqlite3.Row

    shipment = connection.execute(
        "SELECT * FROM shipments WHERE tracking_id = ?",
        ("TEST123",)
    ).fetchone()

    connection.close()

    assert shipment is not None
    assert shipment["receiver_name"] == "Test Receiver"
    assert shipment["status"] == "Booked"


def test_invalid_shipment_rejected(client):
    login_as_admin(client)

    response = client.post(
        "/admin/create-shipment",
        data={
            "tracking_id": "",
            "customer_id": "",
            "receiver_name": "",
            "origin": "",
            "destination": ""
        }
    )

    assert response.status_code == 400
    assert b"All shipment fields are required." in response.data
