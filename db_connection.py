import psycopg2 
from psycopg2 import sql

def get_connection():
    return psycopg2.connect(
        host="starbug.cs.rit.edu",
        database="p320_48",
        user=" ",     # RIT database username (qth9368)
        password=" "
    )
