"""
Yeh file Postgres database se connection banati hai.
.env file se DATABASE_URL uthati hai.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

# .env file load karo
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_engine():
    """
    Database engine return karta hai jise baad mein
    tables banane aur queries chalane ke liye use karenge.
    """
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL .env file mein set nahi hai!")
    
    engine = create_engine(DATABASE_URL)
    return engine


def test_connection():
    """
    Yeh function sirf test karta hai ke connection sahi hai ya nahi.
    Terminal mein 'python database.py' chala kar test kar sakti hain.
    """
    try:
        engine = get_engine()
        with engine.connect() as connection:
            print("✅ Database connection successful!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")


if __name__ == "__main__":
    test_connection()
