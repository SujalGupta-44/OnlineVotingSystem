# database.py
import pymysql
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")   # agar password set hai to yaha likho
DB_NAME = os.getenv("DB_NAME", "VotingSystem_db")
DB_PORT = int(os.getenv("DB_PORT", 3306))  # WAMP ke liye 3306

def get_connection():
    """Create and return a new database connection"""
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        port=DB_PORT,   
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

def init_db():
    """Check connection and ensure DB is accessible"""
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT DATABASE();")
            db = cursor.fetchone()
            print(f"✅ Connected to database: {db['DATABASE()']}")
        conn.close()
    except Exception as e:
        print("❌ Database connection failed:", str(e))
