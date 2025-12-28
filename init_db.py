#!/usr/bin/env python3
"""Initialize database"""
from core import db

print("Initializing database...")
db.init_db()
print("✅ Database initialized successfully!")
