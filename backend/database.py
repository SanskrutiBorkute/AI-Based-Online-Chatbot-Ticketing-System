import sqlite3
import os
import json
import random
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "railai.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tickets table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        description TEXT NOT NULL,
        route TEXT NOT NULL,
        train TEXT NOT NULL,
        priority TEXT NOT NULL,
        status TEXT NOT NULL,
        passenger TEXT NOT NULL,
        email TEXT NOT NULL,
        pnr TEXT,
        assignee TEXT NOT NULL,
        created_at TEXT NOT NULL,
        resolved_at TEXT,
        ai_suggestion TEXT,
        department TEXT NOT NULL,
        satisfaction_score INTEGER
    )
    """)
    
    # Create train status table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS train_status (
        train_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        route TEXT NOT NULL,
        status TEXT NOT NULL,
        delay INTEGER DEFAULT 0,
        occupancy INTEGER DEFAULT 0
    )
    """)
    
    # Create chat sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        session_id TEXT PRIMARY KEY,
        category TEXT,
        slots TEXT,
        messages TEXT,
        language TEXT DEFAULT 'en',
        updated_at TEXT NOT NULL
    )
    """)

    # Create chat messages table for persistent conversation storage
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # Create AI resolved conversations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_resolved_conversations (
        session_id TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        resolved_at TEXT NOT NULL
    )
    """)
    
    conn.commit()
    seed_data(conn)
    conn.close()

def seed_data(conn):
    cursor = conn.cursor()
    
    print("Performing clean database reset and seeding realistic operational data...")
    # Delete all existing data to start clean (Option A)
    cursor.execute("DELETE FROM tickets")
    cursor.execute("DELETE FROM train_status")
    cursor.execute("DELETE FROM ai_resolved_conversations")
    
    # 1. Seed Train Statuses
    trains = [
        ('12952', 'Rajdhani Express', 'MUM→DEL', 'on-time', 0, 94),
        ('12301', 'Howrah Rajdhani', 'HWH→DEL', 'delayed', 18, 87),
        ('12009', 'Shatabdi Express', 'MUM→AHM', 'on-time', 0, 100),
        ('11057', 'Amritsar Express', 'CSTM→ASR', 'delayed', 6, 76),
        ('12951', 'Mumbai Rajdhani', 'DEL→MUM', 'on-time', 0, 89)
    ]
    cursor.executemany("INSERT INTO train_status VALUES (?, ?, ?, ?, ?, ?)", trains)
    
    conn.commit()
    print("Database seeding completed (train statuses seeded, zero tickets).")

if __name__ == "__main__":
    init_db()
