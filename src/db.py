import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "energy_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY,
            timestamp REAL,
            price_czk REAL,
            level TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consumption (
            id INTEGER PRIMARY KEY,
            timestamp REAL,
            wattage REAL,
            energy_wh REAL,
            cost_czk REAL
        )
    """)

    conn.commit()
    conn.close()


def save_price(price_czk, level):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO prices (timestamp, price_czk, level) VALUES (?, ?, ?)",
        (datetime.now().timestamp(), price_czk, level),
    )
    conn.commit()
    conn.close()


def save_consumption(wattage, energy_wh, cost_czk):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO consumption (timestamp, wattage, energy_wh, cost_czk) VALUES (?, ?, ?, ?)",
        (datetime.now().timestamp(), wattage, energy_wh, cost_czk),
    )
    conn.commit()
    conn.close()


def get_total_energy_and_cost():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(energy_wh), SUM(cost_czk) FROM consumption")
    result = cursor.fetchone()
    conn.close()
    energy = result[0] if result[0] else 0.0
    cost = result[1] if result[1] else 0.0
    return energy, cost


def get_total_cost():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(cost_czk) FROM consumption")
    total = cursor.fetchone()[0]
    conn.close()
    return total if total else 0.0


if __name__ == "__main__":
    init_db()
    print(f"Database ready at {DB_PATH}")
