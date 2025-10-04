import mysql.connector, os
from dotenv import load_dotenv

load_dotenv()

def connect_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )

def save_keywords(data):
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
        cursor.execute("INSERT INTO keywords (seed, keyword, volume, competition, cpc, score) VALUES (%s,%s,%s,%s,%s,%s)", row)
    db.commit()
    db.close()
