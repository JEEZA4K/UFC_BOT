import sqlite3
import json
from datetime import datetime
import os

DB_PATH = os.getenv("DB_PATH", "ufc_pronos.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Table événements UFC
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            location TEXT,
            status TEXT DEFAULT 'upcoming',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Table combats
    c.execute("""
        CREATE TABLE IF NOT EXISTS fights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            fighter1 TEXT NOT NULL,
            fighter2 TEXT NOT NULL,
            weight_class TEXT,
            is_main_event INTEGER DEFAULT 0,
            max_rounds INTEGER DEFAULT 3,
            winner TEXT,
            method TEXT,
            round_ended INTEGER,
            position INTEGER DEFAULT 0,
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)
    
    # Table pronos
    c.execute("""
        CREATE TABLE IF NOT EXISTS pronos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            fight_id INTEGER NOT NULL,
            picked_fighter TEXT NOT NULL,
            picked_method TEXT,
            picked_round INTEGER,
            points_earned INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, fight_id),
            FOREIGN KEY (fight_id) REFERENCES fights(id)
        )
    """)
    
    # Table classement global
    c.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            total_points INTEGER DEFAULT 0,
            correct_winner INTEGER DEFAULT 0,
            correct_method INTEGER DEFAULT 0,
            correct_round INTEGER DEFAULT 0,
            total_pronos INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Table settings
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Base de données initialisée")

# ─── EVENTS ───────────────────────────────────────────────

def save_event(name, date, location=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO events (name, date, location) VALUES (?, ?, ?)",
        (name, date, location)
    )
    event_id = c.lastrowid
    conn.commit()
    conn.close()
    return event_id

def get_active_event():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM events WHERE status = 'active' ORDER BY date DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def set_event_status(event_id, status):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE events SET status = ? WHERE id = ?", (status, event_id))
    conn.commit()
    conn.close()

# ─── FIGHTS ───────────────────────────────────────────────

def save_fight(event_id, fighter1, fighter2, weight_class="", is_main_event=False, max_rounds=3, position=0):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO fights (event_id, fighter1, fighter2, weight_class, is_main_event, max_rounds, position)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (event_id, fighter1, fighter2, weight_class, int(is_main_event), max_rounds, position))
    fight_id = c.lastrowid
    conn.commit()
    conn.close()
    return fight_id

def get_fights_for_event(event_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM fights WHERE event_id = ? ORDER BY position DESC", (event_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def set_fight_result(fight_id, winner, method, round_ended):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE fights SET winner = ?, method = ?, round_ended = ? WHERE id = ?
    """, (winner, method, round_ended, fight_id))
    conn.commit()
    conn.close()

# ─── PRONOS ───────────────────────────────────────────────

def save_prono(user_id, username, fight_id, picked_fighter, picked_method=None, picked_round=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO pronos (user_id, username, fight_id, picked_fighter, picked_method, picked_round)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, fight_id) DO UPDATE SET
                picked_fighter = excluded.picked_fighter,
                picked_method = excluded.picked_method,
                picked_round = excluded.picked_round
        """, (str(user_id), username, fight_id, picked_fighter, picked_method, picked_round))
        conn.commit()
        success = True
    except Exception as e:
        print(f"Erreur save_prono: {e}")
        success = False
    conn.close()
    return success

def get_prono(user_id, fight_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM pronos WHERE user_id = ? AND fight_id = ?", (str(user_id), fight_id))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_pronos_for_fight(fight_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM pronos WHERE fight_id = ?", (fight_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_pronos_for_event(event_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT p.*, f.fighter1, f.fighter2, f.winner, f.method, f.round_ended
        FROM pronos p
        JOIN fights f ON p.fight_id = f.id
        WHERE f.event_id = ?
    """, (event_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── POINTS ───────────────────────────────────────────────

POINTS = {
    "winner": 1,
    "method": 1,
    "round": 2,
}

def calculate_and_save_points(fight_id):
    conn = get_connection()
    c = conn.cursor()
    
    c.execute("SELECT * FROM fights WHERE id = ?", (fight_id,))
    fight = c.fetchone()
    if not fight or not fight["winner"]:
        conn.close()
        return []
    
    c.execute("SELECT * FROM pronos WHERE fight_id = ?", (fight_id,))
    pronos = c.fetchall()
    
    results = []
    for prono in pronos:
        points = 0
        correct_winner = False
        correct_method = False
        correct_round = False
        
        if prono["picked_fighter"] == fight["winner"]:
            points += POINTS["winner"]
            correct_winner = True
            
            if prono["picked_method"] and prono["picked_method"] == fight["method"]:
                points += POINTS["method"]
                correct_method = True
                
                if prono["picked_round"] and prono["picked_round"] == fight["round_ended"]:
                    points += POINTS["round"]
                    correct_round = True
        
        c.execute("UPDATE pronos SET points_earned = ? WHERE id = ?", (points, prono["id"]))
        
        # Mise à jour classement
        c.execute("""
            INSERT INTO leaderboard (user_id, username, total_points, correct_winner, correct_method, correct_round, total_pronos)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                total_points = total_points + ?,
                correct_winner = correct_winner + ?,
                correct_method = correct_method + ?,
                correct_round = correct_round + ?,
                total_pronos = total_pronos + 1,
                updated_at = CURRENT_TIMESTAMP
        """, (
            prono["user_id"], prono["username"], points,
            int(correct_winner), int(correct_method), int(correct_round),
            points, int(correct_winner), int(correct_method), int(correct_round)
        ))
        
        results.append({
            "user_id": prono["user_id"],
            "username": prono["username"],
            "points": points,
            "correct_winner": correct_winner,
            "correct_method": correct_method,
            "correct_round": correct_round,
        })
    
    conn.commit()
    conn.close()
    return results

# ─── LEADERBOARD ──────────────────────────────────────────

def get_leaderboard(limit=10):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM leaderboard ORDER BY total_points DESC LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── SETTINGS ─────────────────────────────────────────────

def get_setting(key):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row["value"] if row else None

def set_setting(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

# Init au démarrage
init_db()
