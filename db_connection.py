import os
from typing import Optional

from sshtunnel import SSHTunnelForwarder
import psycopg2 
from dotenv import load_dotenv

load_dotenv()
_DB_USER = os.getenv("DB_USER")
_DB_PASS = os.getenv("DB_PASS")

db_name = "p320_48"
ssh_host = "starbug.cs.rit.edu"
ssh_port = 22

# keep a single tunnel for the process
_TUNNEL: Optional[SSHTunnelForwarder] = None

def _start_tunnel() -> SSHTunnelForwarder:
    """Start (or reuse) an SSH tunnel to the DB host."""
    global _TUNNEL
    if _TUNNEL and getattr(_TUNNEL, "is_active", False):
        return _TUNNEL

    if not _DB_USER or not _DB_PASS:
        raise RuntimeError("DB_USER / DB_PASS are not set in the environment (.env).")

    # allocate any free local port (local_bind_address port=0)
    _TUNNEL = SSHTunnelForwarder(
        (ssh_host, ssh_port),
        ssh_username=_DB_USER,
        ssh_password=_DB_PASS,
        remote_bind_address=("127.0.0.1", 5432),
        local_bind_address=("127.0.0.1", 0),
    )
    _TUNNEL.start()
    return _TUNNEL

def get_connection():
    """
    open and return a new psycopg2 connection through the shared SSH tunnel.
    the caller owns the connection and should close it when finished (your App
    keeps one open and reuses it)
    """
    t = _start_tunnel()
    conn = psycopg2.connect(
        dbname=db_name,
        user=_DB_USER,
        password=_DB_PASS,
        host="127.0.0.1",
        port=t.local_bind_port,
        connect_timeout=10,
    )
    # let the app control transactions ( it calls commit() )
    conn.autocommit = False
    return conn

def close_tunnel():
    """stop the shared SSH tunnel (called on app shutdown)"""
    global _TUNNEL
    if _TUNNEL:
        try:
            _TUNNEL.stop()
        finally:
            _TUNNEL = None

if __name__ == "__main__":
    # test
    try:
        c = get_connection()
        with c.cursor() as cur:
            cur.execute("SELECT 1;")
            print("SSH + DB OK ->", cur.fetchone())
        c.close()
    finally:
        close_tunnel()
