import sqlite3

connection = sqlite3.connect("courier.db")
cursor = connection.cursor()

# Users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
""")

# Shipments table
cursor.execute("""
CREATE TABLE IF NOT EXISTS shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracking_id TEXT UNIQUE NOT NULL,
    customer_id INTEGER,
    receiver_name TEXT NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    status TEXT NOT NULL,
    current_location TEXT,
    agent_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(id),
    FOREIGN KEY (agent_id) REFERENCES users(id)
)
""")

# Shipment status history
cursor.execute("""
CREATE TABLE IF NOT EXISTS shipment_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id INTEGER,
    status TEXT NOT NULL,
    location TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id)
)
""")

connection.commit()
connection.close()

print("Database setup complete!")