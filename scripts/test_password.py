#!/usr/bin/env python3
"""Test password hashing."""

import bcrypt

# Test the password hash from database
stored_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5e"
password = "change-me"

# Check if password matches
result = bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
print(f"Password '{password}' matches stored hash: {result}")

# Generate new hash for comparison
new_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print(f"New hash for '{password}': {new_hash.decode('utf-8')}")

# Test new hash
result2 = bcrypt.checkpw(password.encode('utf-8'), new_hash)
print(f"Password '{password}' matches new hash: {result2}")