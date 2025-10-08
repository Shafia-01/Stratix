import pandas as pd
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def connect_db():
    return mysql.connector.connect (
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        unix_socket=None,
        use_pure=True
    )

def save_to_db(conn, data):
    """Save keyword data with all computed fields."""
    cursor = conn.cursor()
    try:
        for row in data:
            cursor.execute("""
                INSERT INTO keywords (
                    seed, keyword, volume, competition, cpc, 
                    trend, score, difficulty, intent, competitors
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                row.get("seed"),
                row.get("keyword"),
                row.get("volume"),
                row.get("competition"),
                row.get("cpc"),
                row.get("trend"),
                row.get("score"),
                row.get("difficulty"),
                row.get("intent"),
                str(row.get("competitors"))
            ))
        conn.commit()
        print(f"✅ {len(data)} keywords saved successfully!")
    except Exception as e:
        print("⚠️ Database Save Error:", e)
        conn.rollback()


def fetch_past_results(limit=50):
    """
    Fetch last 'limit' keyword entries from the MySQL database.
    """
    try:
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE")
        )
        query = """
        SELECT seed, keyword, volume, competition, cpc, score, difficulty
        FROM keywords
        ORDER BY id DESC
        LIMIT %s;
        """
        df = pd.read_sql(query, conn, params=(limit,))
        conn.close()
        return df
    except Exception as e:
        print(f"DB Fetch Error: {e}")
        return pd.DataFrame()