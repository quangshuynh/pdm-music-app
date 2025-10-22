import psycopg2 
from psycopg2 import sql
import os
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')

def get_connection():
    return psycopg2.connect(
        host="starbug.cs.rit.edu",
        database="p320_48",
        user="DB_USER",
        password=os.getenv("DB_PASS"),
        sslmode="require"
    )
