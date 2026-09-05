import os
import sqlite3
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Sahayog-Gig Cooperative Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "sahayog.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Workers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            trade TEXT NOT NULL,
            phone TEXT NOT NULL,
            rating REAL DEFAULT 4.8,
            distance_km REAL DEFAULT 1.2,
            hourly_rate INTEGER NOT NULL,
            is_available INTEGER DEFAULT 1,
            completed_jobs INTEGER DEFAULT 0,
            total_earnings INTEGER DEFAULT 0,
            verification_badge TEXT DEFAULT 'e-Shram & Police Verified'
        )
    ''')
    # Bookings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            address TEXT NOT NULL,
            service_name TEXT NOT NULL,
            worker_id INTEGER,
            base_price INTEGER NOT NULL,
            coop_fee INTEGER NOT NULL,
            worker_payout INTEGER NOT NULL,
            status TEXT DEFAULT 'PENDING_ACCEPTANCE',
            scheduled_date TEXT NOT NULL,
            scheduled_slot TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (worker_id) REFERENCES workers (id)
        )
    ''')
    conn.commit()

    # Seed initial worker if table empty
    c.execute("SELECT COUNT(*) FROM workers")
    if c.fetchone()[0] == 0:
        seed_workers = [
            ("Priya Sharma", "Cleaning Expert", "+91 98765 01001", 4.9, 1.2, 299, 1, 48, 14352, "e-Shram Verified"),
            ("Rajan Kumar", "Plumbing Specialist", "+91 98765 01002", 4.8, 0.8, 249, 1, 62, 15438, "PMKVY Certified"),
            ("Arvind Patel", "Certified Electrician", "+91 98765 01003", 4.7, 1.9, 299, 1, 35, 10465, "e-Shram Verified")
        ]
        c.executemany('''
            INSERT INTO workers (name, trade, phone, rating, distance_km, hourly_rate, is_available, completed_jobs, total_earnings, verification_badge)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', seed_workers)
        conn.commit()
    conn.close()

init_db()

# Models
class BookingCreate(BaseModel):
    customer_name: str
    customer_phone: str
    address: str
    service_name: str
    worker_id: int
    base_price: int
    scheduled_date: str
    scheduled_slot: str

class BookingStatusUpdate(BaseModel):
    status: str

# API Endpoints
@app.get("/api/workers")
def get_workers():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM workers")
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

@app.get("/api/workers/{worker_id}")
def get_worker(worker_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM workers WHERE id = ?", (worker_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Worker not found")
    return dict(row)

@app.post("/api/bookings")
def create_booking(payload: BookingCreate):
    # Cooperative Escrow Math: 4% Platform Pool, 96% Direct Worker Retention
    coop_fee = int(round(payload.base_price * 0.04))
    worker_payout = payload.base_price - coop_fee

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO bookings (customer_name, customer_phone, address, service_name, worker_id, base_price, coop_fee, worker_payout, status, scheduled_date, scheduled_slot, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_ACCEPTANCE', ?, ?, ?)
    ''', (
        payload.customer_name, payload.customer_phone, payload.address,
        payload.service_name, payload.worker_id, payload.base_price,
        coop_fee, worker_payout, payload.scheduled_date, payload.scheduled_slot,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    booking_id = c.lastrowid
    conn.commit()
    conn.close()

    return {"booking_id": booking_id, "status": "PENDING_ACCEPTANCE", "worker_payout": worker_payout, "coop_fee": coop_fee}

@app.get("/api/bookings")
def get_bookings(worker_id: Optional[int] = None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if worker_id:
        c.execute("SELECT * FROM bookings WHERE worker_id = ? ORDER BY id DESC", (worker_id,))
    else:
        c.execute("SELECT * FROM bookings ORDER BY id DESC")
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

@app.patch("/api/bookings/{booking_id}/status")
def update_status(booking_id: int, payload: BookingStatusUpdate):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE bookings SET status = ? WHERE id = ?", (payload.status, booking_id))
    
    # If completed, update worker statistics
    if payload.status == "COMPLETED":
        c.execute("SELECT worker_id, worker_payout FROM bookings WHERE id = ?", (booking_id,))
        row = c.fetchone()
        if row:
            w_id, payout = row
            c.execute("UPDATE workers SET completed_jobs = completed_jobs + 1, total_earnings = total_earnings + ? WHERE id = ?", (payout, w_id))
    
    conn.commit()
    conn.close()
    return {"message": "Status updated successfully", "status": payload.status}

# Mount static files
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")