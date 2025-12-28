#!/usr/bin/env python3
"""Debug channel ID issue"""
import sqlite3

DB_PATH = "db.sqlite"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 60)
print("DEBUGGING CHANNEL ID ISSUE")
print("=" * 60)

# Get all channels
cursor.execute("SELECT id, title FROM channels")
all_channels = cursor.fetchall()
print(f"\n1. All channels: {all_channels}")

# Try to query with ID 1
cursor.execute("SELECT id, title FROM channels WHERE id = ?", (1,))
result_int = cursor.fetchone()
print(f"2. Query with int 1: {result_int}")

# Try with string
cursor.execute("SELECT id, title FROM channels WHERE id = ?", ("1",))
result_str = cursor.fetchone()
print(f"3. Query with string '1': {result_str}")

# Check the actual type
cursor.execute("SELECT id, typeof(id), title FROM channels")
types = cursor.fetchall()
print(f"4. ID types: {types}")

# Check raw bytes
cursor.execute("SELECT id, quote(id), title FROM channels")
raw = cursor.fetchall()
print(f"5. Raw ID representation: {raw}")

# Try direct comparison
if all_channels:
    actual_id = all_channels[0][0]
    print(f"\n6. First channel ID value: {actual_id}")
    print(f"   Type: {type(actual_id)}")
    print(f"   Repr: {repr(actual_id)}")
    print(f"   Equal to 1? {actual_id == 1}")
    print(f"   Equal to '1'? {actual_id == '1'}")

    # Try querying with the exact value
    cursor.execute("SELECT id, title FROM channels WHERE id = ?", (actual_id,))
    result_exact = cursor.fetchone()
    print(f"7. Query with exact value: {result_exact}")

conn.close()

print("=" * 60)
