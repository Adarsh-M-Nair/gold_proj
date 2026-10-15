import sqlite3
import os
import datetime
import json

DB_PATH = "customers.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pledge_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            aadhar TEXT NOT NULL,
            ornament_photo TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def generate_pledge_id():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    year = datetime.datetime.now().year
    prefix = f"GS-{year}-"
    cursor.execute("SELECT pledge_id FROM customers WHERE pledge_id LIKE ?", (f"{prefix}%",))
    rows = cursor.fetchall()
    conn.close()

    max_num = 0
    for (pid,) in rows:
        try:
            num_part = pid.replace(prefix, "")
            num = int(num_part)
            if num > max_num:
                max_num = num
        except Exception:
            pass

    return f"{prefix}{(max_num + 1):04d}"

def _format_customer_row(row_dict):
    """Normalize customer record dict to always have photos list and primary photo."""
    if not row_dict:
        return None
    d = dict(row_dict)
    photo_val = d.get("ornament_photo", "")
    photos = []
    if photo_val:
        photo_val_str = str(photo_val).strip()
        if photo_val_str.startswith("[") and photo_val_str.endswith("]"):
            try:
                parsed = json.loads(photo_val_str)
                if isinstance(parsed, list):
                    photos = [str(p).strip().replace("\\", "/") for p in parsed if str(p).strip()]
            except Exception:
                pass
        if not photos:
            if "," in photo_val_str:
                photos = [p.strip().replace("\\", "/") for p in photo_val_str.split(",") if p.strip()]
            else:
                photos = [photo_val_str.replace("\\", "/")]

    d["photos"] = photos
    d["photo_count"] = len(photos)
    d["primary_photo"] = photos[0] if photos else ""
    # Maintain backwards compatibility for templates accessing c.ornament_photo
    d["ornament_photo"] = d["primary_photo"]
    return d

def add_customer(name, phone, aadhar, ornament_photos):
    init_db()
    created_at_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Normalize ornament_photos to a list
    if isinstance(ornament_photos, str):
        photos_list = [ornament_photos.strip().replace("\\", "/")] if ornament_photos.strip() else []
    elif isinstance(ornament_photos, (list, tuple)):
        photos_list = [str(p).strip().replace("\\", "/") for p in ornament_photos if str(p).strip()]
    else:
        photos_list = []

    stored_value = json.dumps(photos_list)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Determine highest pledge ID
    year = datetime.datetime.now().year
    prefix = f"GS-{year}-"
    cursor.execute("SELECT pledge_id FROM customers WHERE pledge_id LIKE ?", (f"{prefix}%",))
    rows = cursor.fetchall()
    max_num = 0
    for (pid,) in rows:
        try:
            num_part = str(pid).replace(prefix, "")
            num = int(num_part)
            if num > max_num:
                max_num = num
        except Exception:
            pass

    customer_id = None
    final_pledge_id = None

    for offset in range(1, 20):
        final_pledge_id = f"{prefix}{(max_num + offset):04d}"
        try:
            cursor.execute(
                """
                INSERT INTO customers (pledge_id, name, phone, aadhar, ornament_photo, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (final_pledge_id, name.strip(), phone.strip(), aadhar.strip(), stored_value, created_at_str)
            )
            conn.commit()
            customer_id = cursor.lastrowid
            break
        except sqlite3.IntegrityError:
            continue

    conn.close()

    if not customer_id:
        raise RuntimeError("Failed to generate a unique pledge ID after multiple attempts.")
    
    formatted_date = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    return {
        "id": customer_id,
        "pledge_id": final_pledge_id,
        "name": name.strip(),
        "phone": phone.strip(),
        "aadhar": aadhar.strip(),
        "ornament_photo": photos_list[0] if photos_list else "",
        "primary_photo": photos_list[0] if photos_list else "",
        "photos": photos_list,
        "photo_count": len(photos_list),
        "created_at": formatted_date
    }

def get_all_customers():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [_format_customer_row(r) for r in rows]

def get_customer_by_id(customer_id):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
    row = cursor.fetchone()
    conn.close()
    return _format_customer_row(row) if row else None

def delete_customer(customer_id):
    """Delete a customer record by ID. Returns True if a row was deleted."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted
