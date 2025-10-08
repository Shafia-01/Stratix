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

def save_keywords_to_db(data):
    db = connect_db()
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id INT AUTO_INCREMENT PRIMARY KEY,
            seed VARCHAR(255),
            keyword VARCHAR(255),
            volume INT,
            competition FLOAT,
            cpc FLOAT,
            score FLOAT
        )
    """)

    for row in data:
        cursor.execute("""
            INSERT INTO keywords (seed, keyword, volume, competition, cpc, score)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, row)

    db.commit()
    db.close()

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