import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'club_management.db')
if not os.path.exists(db_path):
    db_path = os.path.join(os.path.dirname(__file__), 'club_management.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE events ADD COLUMN price FLOAT DEFAULT 0.0;")
    print("Added price to events")
except Exception as e:
    print(f"events table error: {e}")

try:
    cursor.execute("ALTER TABLE event_attendance ADD COLUMN ticket_id VARCHAR(100);")
    print("Added ticket_id to event_attendance")
except Exception as e:
    print(f"event_attendance table error: {e}")

conn.commit()
conn.close()
