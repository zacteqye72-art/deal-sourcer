import sqlite3
from pathlib import Path
from typing import Optional

from src.models import Listing

DB_PATH = Path(__file__).resolve().parent.parent / "deal_sourcer.db"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path or DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    conn = get_connection(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            asking_price REAL,
            mrr REAL,
            annual_profit REAL,
            multiple REAL,
            monetization_type TEXT,
            platform TEXT,
            business_age_months INTEGER,
            description TEXT,
            raw_data TEXT,
            is_pet_related INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(source, source_id)
        )
    """)
    conn.commit()
    conn.close()


def upsert_listing(listing: Listing, db_path: Optional[Path] = None) -> bool:
    """Insert or update a listing. Returns True if it was a new insert."""
    conn = get_connection(db_path)
    cursor = conn.execute(
        "SELECT id FROM listings WHERE source = ? AND source_id = ?",
        (listing.source, listing.source_id),
    )
    existing = cursor.fetchone()

    if existing:
        conn.execute("""
            UPDATE listings SET
                title=?, url=?, asking_price=?, mrr=?, annual_profit=?,
                multiple=?, monetization_type=?, platform=?, business_age_months=?,
                description=?, raw_data=?, is_pet_related=?, updated_at=?
            WHERE source=? AND source_id=?
        """, (
            listing.title, listing.url, listing.asking_price, listing.mrr,
            listing.annual_profit, listing.multiple, listing.monetization_type,
            listing.platform, listing.business_age_months, listing.description,
            listing.raw_data, int(listing.is_pet_related), listing.updated_at,
            listing.source, listing.source_id,
        ))
        conn.commit()
        conn.close()
        return False
    else:
        conn.execute("""
            INSERT INTO listings (
                source, source_id, title, url, asking_price, mrr, annual_profit,
                multiple, monetization_type, platform, business_age_months,
                description, raw_data, is_pet_related, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            listing.source, listing.source_id, listing.title, listing.url,
            listing.asking_price, listing.mrr, listing.annual_profit,
            listing.multiple, listing.monetization_type, listing.platform,
            listing.business_age_months, listing.description, listing.raw_data,
            int(listing.is_pet_related), listing.created_at, listing.updated_at,
        ))
        conn.commit()
        conn.close()
        return True


def get_listings(new_only: bool = False, pet_only: bool = False,
                 db_path: Optional[Path] = None) -> list[dict]:
    """Query listings from DB."""
    conn = get_connection(db_path)
    query = "SELECT * FROM listings WHERE 1=1"
    params: list = []

    if pet_only:
        query += " AND is_pet_related = 1"
    if new_only:
        query += " AND date(created_at) = date(updated_at)"

    query += " ORDER BY created_at DESC"
    cursor = conn.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows
