#!/usr/bin/env python3
"""Check database contents"""
import sqlite3

DB_PATH = "db.sqlite"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 60)
print("DATABASE CONTENTS")
print("=" * 60)

# Check channels
cursor.execute("SELECT id, title, handle FROM channels")
channels = cursor.fetchall()

print(f"\n📊 Total channels in DB: {len(channels)}")
print("-" * 60)

if channels:
    for channel in channels:
        print(f"ID: {channel[0]:3d} | Title: {channel[1][:40]:40s} | Handle: {channel[2] or 'N/A'}")
else:
    print("⚠️  No channels found in database!")

print("=" * 60)

conn.close()
