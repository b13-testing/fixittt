#!/usr/bin/env python3
"""
FixItTT - Complete Version
Customers: no account needed
Providers: must register & login
Full Provider Dashboard + Leads system
"""

from flask import (Flask, render_template_string, request, redirect,
                   url_for, flash, g, session)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import secrets
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fixittt-change-this-in-production-please")

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixittt.db")

AREAS = [
    "Port of Spain", "San Fernando", "Chaguanas", "Arima", "Tunapuna",
    "Couva", "Point Fortin", "Sangre Grande", "Princes Town", "Diego Martin",
    "Marabella", "Tobago - Scarborough", "Tobago - Crown Point", "Tobago - Plymouth",
    "Mayaro", "Siparia", "Penal", "Gasparillo", "Arouca", "Curepe",
    "St. Augustine", "Trincity", "Valsayn", "Westmoorings", "Woodbrook",
    "Belmont", "Laventille", "Morvant", "Barataria", "San Juan"
]

SERVICES = [
    "Plumber", "Electrician", "AC Repair / HVAC", "Welder", "Handyman",
    "Carpenter", "Painter", "Tiler", "Appliance Repair", "Auto Mechanic",
    "Generator Repair", "Roofing", "Landscaping / Gardening", "Pest Control",
    "Cleaning Services", "Security / CCTV Install", "Locksmith", "Glass / Windows",
    "Masonry / Concrete", "Pool Maintenance"
]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT NOT NULL,
            contact_name TEXT,
            phone TEXT NOT NULL,
            whatsapp TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            service TEXT NOT NULL,
            areas TEXT NOT NULL,
            description TEXT,
            rating REAL DEFAULT 4.5,
            is_featured INTEGER DEFAULT 0,
            notify_email INTEGER DEFAULT 1,
            notify_whatsapp INTEGER DEFAULT 1,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            customer_phone TEXT NOT NULL,
            service TEXT NOT NULL,
            area TEXT NOT NULL,
            description TEXT,
            urgency TEXT DEFAULT 'Normal',
            status TEXT DEFAULT 'Open',
            tracking_code TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL,
            status TEXT DEFAULT 'New',
            provider_notes TEXT,
            notified_at TEXT,
            viewed_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (request_id) REFERENCES requests(id),
            FOREIGN KEY (provider_id) REFERENCES providers(id)
        );
    """)

    count = db.execute("SELECT COUNT(*) FROM providers").fetchone()[0]
    if count == 0:
        demo = [
            ("QuickFix Plumbing", "Rajesh Singh", "868-555-0101", "8685550101",
             "rajesh@quickfix.tt", generate_password_hash("password123"),
             "Plumber", "Chaguanas,Couva,San Fernando",
             "24/7 emergency plumbing. Burst pipes, blocked drains, water heaters.", 4.8, 1),
            ("CoolAir TT", "Maria Dookeran", "868-555-0202", "8685550202",
             "maria@coolair.tt", generate_password_hash("password123"),
             "AC Repair / HVAC", "Port of Spain,Diego Martin,Westmoorings,Woodbrook",
             "Residential & commercial AC. Same-day service.", 4.9, 1),
            ("Sparky Electrical", "Devon Charles", "868-555-0303", "8685550303",
             "devon@sparky.tt", generate_password_hash("password123"),
             "Electrician", "Arima,Tunapuna,Arouca,Trincity",
             "Licensed electrician. Wiring, panels, outlets.", 4.7, 0),
            ("WeldMasters", "Kevin Ali", "868-555-0404", "8685550404",
             "kevin@weldmasters.tt", generate_password_hash("password123"),
             "Welder", "San Fernando,Point Fortin,Princes Town",
             "Gates, railings, structural welding.", 4.6, 0),
            ("HandyPro Central", "Aisha Mohammed", "868-555-0505", "8685550505",
             "aisha@handypro.tt", generate_password_hash("password123"),
             "Handyman", "Chaguanas,Couva,Valsayn,Curepe",
             "Furniture assembly, minor repairs, odd jobs.", 4.5, 0),
        ]
        for p in demo:
            db.execute("""INSERT INTO providers
                (business_name, contact_name, phone, whatsapp, email, password_hash,
                 service, areas, description, rating, is_featured)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""", p)
        db.commit()

def generate_tracking_code():
    return "FIX-" + secrets.token_hex(2).upper()

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "provider_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("provider_login"))
        return f(*args, **kwargs)
    return decorated

def get_current_provider():
    if "provider_id" not in session:
        return None
    db = get_db()
    return db.execute("SELECT * FROM providers WHERE id = ?", (session["provider_id"],)).fetchone()

# ---------------------------------------------------------------------------
# Shared Style
# ---------------------------------------------------------------------------
STYLE = """
:root {
  --primary:#0d6efd; --primary-dark:#0a58ca; --success:#198754;
  --bg:#f8f9fa; --card:#fff; --text:#212529; --muted:#6c757d;
  --border:#dee2e6; --radius:12px; --shadow:0 4px 12px rgba(0,0,0,.08);
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);line-height:1.5;min-height:100vh}
a{color:var(--primary);text-decoration:none}
.container{max-width:960px;margin:0 auto;padding:1rem}
header{background:linear-gradient(135deg,#0d6efd,#0a58ca);color:#fff;padding:1rem 0;box-shadow:var(--shadow)}
header .container{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:.75rem}
.logo{font-size:1.4rem;font-weight:700}
nav{display:flex;flex-wrap:wrap;gap:.5rem}
nav a{color:#fff;background:rgba(255,255,255,.15);padding:.35rem .85rem;border-radius:20px;font-size:.9rem}
nav a:hover{background:rgba(255,255,255,.3)}
.btn{display:inline-block;background:var(--primary);color:#fff!important;padding:.6rem 1.15rem;border-radius:8px;border:none;font-weight:600;cursor:pointer;text-decoration:none!important;font-size:1rem}
.btn:hover{background:var(--primary-dark)}
.btn-success{background:var(--success)}
.btn-outline{background:transparent;color:var(--primary)!important;border:2px solid var(--primary)}
.btn-outline:hover{background:var(--primary);color:#fff!important}
.btn-sm{padding:.3rem .7rem;font-size:.85rem}
.btn-whatsapp{background:#25D366}
.btn-whatsapp:hover{background:#1da851}
.card{background:var(--card);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;box-shadow:var(--shadow);border:1px solid var(--border)}
.form-group{margin-bottom:1rem}
.form-group label{display:block;font-weight:600;margin-bottom:.3rem;font-size:.95rem}
.form-control{width:100%;padding:.55rem .8rem;border:1px solid var(--border);border-radius:8px;font-size:1rem}
.form-control:focus{outline:none;border-color:var(--primary);box-shadow:0 0 0 3px rgba(13,110,253,.15)}
.grid-2{display:grid;gap:1rem}
@media(min-width:600px){.grid-2{grid-template-columns:1fr 1fr}}
.alert{padding:.8rem 1rem;border-radius:8px;margin-bottom:1rem}
.alert-success{background:#d1e7dd;color:#0f5132}
.alert-warning{background:#fff3cd;color:#856404}
.alert-danger{background:#f8d7da;color:#842029}
.alert-info{background:#cff4fc;color:#055160}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:1rem;margin:1.25rem 0}
.stat-card{background:#fff;border-radius:var(--radius);padding:1.1rem;text-align:center;box-shadow:var(--shadow)}
.stat-card .num{font-size:1.6rem;font-weight:700;color:var(--primary)}
.stat-card .label{font-size:.85rem;color:var(--muted);margin-top:.2rem}
.badge{display:inline-block;padding:.15rem .5rem;border-radius:20px;font-size:.75rem;font-weight:600}
.badge-new{background:#cfe2ff;color:#084298}
.badge-viewed{background:#e2e3e5;color:#41464b}
.badge-contacted{background:#fff3cd;color:#856404}
.badge-quoted{background:#e7d6ff;color:#5a2d82}
.badge-won{background:#d1e7dd;color:#0f5132}
.badge-lost{background:#f8d7da;color:#842029}
.badge-featured{background:#fff3cd;color:#856404}
.badge-rating{background:#d1e7dd;color:#0f5132}
.lead-item{background:#fff;border-radius:var(--radius);padding:1rem;margin-bottom:.75rem;box-shadow:var(--shadow);border:1px solid var(--border);display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;align-items:flex-start}
.hero{background:#fff;border-radius:var(--radius);padding:1.5rem;margin:1.5rem 0;box-shadow:var(--shadow);text-align:center}
.hero h1{font-size:1.7rem;margin-bottom:.5rem}
.hero p{color:var(--muted);margin-bottom:1.2rem}
footer{text-align:center;padding:2rem 1rem;color:var(--muted);font-size:.85rem}
.provider-list{list-style:none}
.provider-list li{background:#fff;border-radius:var(--radius);padding:1rem;margin-bottom:.75rem;box-shadow:var(--shadow);border:1px solid var(--border);display:flex;flex-wrap:wrap;gap:.75rem;justify-content:space-between}
.section-title{font-size:1.25rem;margin:1.5rem 0 1rem}
.empty{text-align:center;padding:2rem;color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th,td{padding:.6rem .5rem;text-align:left;border-bottom:1px solid var(--border)}
th{background:#f1f3f5;font-weight:600}
"""

def page(content, title="FixItTT"):
    provider = get_current_provider()
    nav = ""
    if provider:
        nav = f"""
        <a href="{url_for('provider_dashboard')}">Dashboard</a>
        <a href="{url_for('provider_leads')}">My Leads</a>
        <a href="{url_for('provider_profile')}">Profile</a>
        <a href="{url_for('provider_logout')}">Logout</a>
        """
    else:
        nav = f"""
        <a href="{url_for('index')}">Home</a>
        <a href="{url_for('request_service')}">Request Help</a>
        <a href="{url_for('find_providers')}">Find Pros</a>
        <a href="{url_for('provider_login')}">Provider Login</a>
        <a href="{url_for('provider_register')}">Join as Pro</a>
        """

    flashes = ""
    for cat, msg in (get_flashed_messages(with_categories=True) or []):
        flashes += f'<div class="alert alert-{cat}">{msg}</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>{STYLE}</style>
</head>
<body>
  <header>
    <div class="container">
      <div class="logo">🔧 FixItTT</div>
      <nav>{nav}</nav>
    </div>
  </header>
  <main class="container">
    {flashes}
    {content}
  </main>
  <footer>FixItTT · Trinidad & Tobago Service Finder</footer>
</body>
</html>"""

# ---------------------------------------------------------------------------
# PUBLIC ROUTES
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    db = get_db()
    stats = {
        "providers": db.execute("SELECT COUNT(*) FROM providers WHERE is_active=1").fetchone()[0],
        "requests": db.execute("SELECT COUNT(*) FROM requests").fetchone()[0],
        "leads": db.execute("SELECT COUNT(*) FROM leads").fetchone()[0],
    }
    content = f"""
    <div class="hero">
      <h1>Need something fixed in Trinidad?</h1>
      <p>Tell us what you need. We match you with local pros — no account required.</p>
      <a href="{url_for('request_service')}" class="btn">Request a Service</a>
      &nbsp;
      <a href="{url_for('find_providers')}" class="btn btn-outline">Browse Pros</a>
    </div>
    <div class="stats">
      <div class="stat-card"><div class="num">{stats['providers']}</div><div class="label">Service Pros</div></div>
      <div class="stat-card"><div class="num">{stats['requests']}</div><div class="label">Requests</div></div>
      <div class="stat-card"><div class="num">{stats['leads']}</div><div class="label">Leads Sent</div></div>
    </div>
    <div class="card" style="background:#e7f1ff">
      <h3>How it works</h3>
      <ol style="margin:.75rem 0 0 1.25rem;color:var(--muted)">
        <li>You describe the job + your area (no account needed)</li>
        <li>We match you with relevant local providers</li>
        <li>You contact them directly via WhatsApp</li>
        <li>Providers get the lead in their dashboard</li>
      </ol>
    </div>
    """
    return page(content)

@app.route("/request", methods=["GET", "POST"])
def request_service():
    if request.method == "POST":
        db = get_db()
        name = request.form.get("customer_name", "").strip()
        phone = request.form.get("customer_phone", "").strip()
        service = request.form.get("service", "").strip()
        area = request.form.get("area", "").strip()
        description = request.form.get("description", "").strip()
        urgency = request.form.get("urgency", "Normal")

        if not phone or not service or not area or not description:
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("request_service"))

        tracking = generate_tracking_code()
        cur = db.execute(
            """INSERT INTO requests
               (customer_name, customer_phone, service, area, description, urgency, tracking_code)
               VALUES (?,?,?,?,?,?,?)""",
            (name, phone, service, area, description, urgency, tracking)
        )
        req_id = cur.lastrowid
        db.commit()

        providers = db.execute(
            "SELECT * FROM providers WHERE service=? AND is_active=1 ORDER BY is_featured DESC, rating DESC",
            (service,)
        ).fetchall()

        matches = []
        for p in providers:
            areas_list = [a.strip().lower() for a in (p["areas"] or "").split(",")]
            if area.lower() in areas_list or "all trinidad" in areas_list:
                matches.append(p)
                db.execute(
                    "INSERT INTO leads (request_id, provider_id, status, notified_at) VALUES (?,?, 'New', ?)",
                    (req_id, p["id"], datetime.utcnow().isoformat())
                )
        db.commit()

        # Build matches HTML
        if matches:
            items = ""
            for p in matches:
                wa = p["whatsapp"] or ""
                wa_link = f"https://wa.me/1{wa}?text=Hi%2C%20I%20found%20you%20on%20FixItTT.%20I%20need%20help%20with%20{service}%20in%20{area}." if wa else "#"
                featured = '<span class="badge badge-featured">Featured</span>' if p["is_featured"] else ""
                items += f"""
                <li>
                  <div>
                    <h3>{p['business_name']} {featured}
                      <span class="badge badge-rating">★ {p['rating']}</span></h3>
                    <div style="color:var(--muted);font-size:.9rem">{p['service']} · {p['areas']}</div>
                    <p style="margin:.4rem 0">{p['description'] or ''}</p>
                  </div>
                  <div style="display:flex;gap:.5rem;flex-wrap:wrap">
                    <a class="btn btn-whatsapp btn-sm" target="_blank" href="{wa_link}">WhatsApp</a>
                    <a class="btn btn-outline btn-sm" href="tel:{p['phone']}">Call</a>
                  </div>
                </li>"""
            matches_html = f"<ul class='provider-list'>{items}</ul>"
        else:
            matches_html = "<div class='card empty'>No providers matched this area yet. Your request has been saved.</div>"

        content = f"""
        <div class="hero" style="text-align:left">
          <h1>Matching Providers</h1>
          <p>We found <strong>{len(matches)}</strong> pro(s) for <strong>{service}</strong> in <strong>{area}</strong>.</p>
          <p style="color:var(--muted)">Your tracking code: <strong>{tracking}</strong></p>
        </div>
        {matches_html}
        <div style="margin-top:1.5rem">
          <a href="{url_for('request_service')}" class="btn btn-outline">← New Request</a>
        </div>
        """
        return page(content, "Matches – FixItTT")

    # GET form
    service_opts = "".join(f'<option value="{s}">{s}</option>' for s in SERVICES)
    area_opts = "".join(f'<option value="{a}">{a}</option>' for a in AREAS)
    content = f"""
    <div class="card">
      <h2>Request a Service</h2>
      <p style="color:var(--muted);margin-bottom:1rem">No account needed.</p>
      <form method="POST">
        <div class="grid-2">
          <div class="form-group">
            <label>Your Name (optional)</label>
            <input type="text" name="customer_name" class="form-control">
          </div>
          <div class="form-group">
            <label>Phone / WhatsApp *</label>
            <input type="text" name="customer_phone" class="form-control" required placeholder="868-xxx-xxxx">
          </div>
        </div>
        <div class="grid-2">
          <div class="form-group">
            <label>Service *</label>
            <select name="service" class="form-control" required>
              <option value="">— Select —</option>{service_opts}
            </select>
          </div>
          <div class="form-group">
            <label>Area *</label>
            <select name="area" class="form-control" required>
              <option value="">— Select —</option>{area_opts}
            </select>
          </div>
        </div>
        <div class="form-group">
          <label>Describe the problem *</label>
          <textarea name="description" class="form-control" required rows="3"
            placeholder="e.g. Washing machine leaking from bottom"></textarea>
        </div>
        <div class="form-group">
          <label>Urgency</label>
          <select name="urgency" class="form-control">
            <option>Normal</option><option>Soon</option><option>Emergency</option>
          </select>
        </div>
        <button type="submit" class="btn">Find Matching Pros →</button>
      </form>
    </div>
    """
    return page(content, "Request Service – FixItTT")

@app.route("/find")
def find_providers():
    service = request.args.get("service", "").strip()
    area = request.args.get("area", "").strip()
    db = get_db()
    query = "SELECT * FROM providers WHERE is_active=1"
    params = []
    if service:
        query += " AND service=?"
        params.append(service)
    if area:
        query += " AND (LOWER(areas) LIKE ? OR LOWER(areas) LIKE '%all trinidad%')"
        params.append(f"%{area.lower()}%")
    query += " ORDER BY is_featured DESC, rating DESC"
    providers = db.execute(query, params).fetchall()

    service_opts = "".join(
        f'<option value="{s}" {"selected" if s==service else ""}>{s}</option>' for s in SERVICES)
    area_opts = "".join(
        f'<option value="{a}" {"selected" if a==area else ""}>{a}</option>' for a in AREAS)

    items = ""
    for p in providers:
        wa = p["whatsapp"] or ""
        wa_link = f"https://wa.me/1{wa}?text=Hi%2C%20I%20found%20you%20on%20FixItTT." if wa else "#"
        featured = '<span class="badge badge-featured">Featured</span>' if p["is_featured"] else ""
        items += f"""
        <li>
          <div>
            <h3>{p['business_name']} {featured}
              <span class="badge badge-rating">★ {p['rating']}</span></h3>
            <div style="color:var(--muted);font-size:.9rem">{p['service']} · {p['areas']}</div>
            <p>{p['description'] or ''}</p>
          </div>
          <div style="display:flex;gap:.5rem;flex-wrap:wrap">
            <a class="btn btn-whatsapp btn-sm" target="_blank" href="{wa_link}">WhatsApp</a>
            <a class="btn btn-outline btn-sm" href="tel:{p['phone']}">Call</a>
          </div>
        </li>"""

    content = f"""
    <div class="hero" style="text-align:left">
      <h1>Find Service Pros</h1>
    </div>
    <form method="GET" class="card">
      <div class="grid-2">
        <div class="form-group">
          <label>Service</label>
          <select name="service" class="form-control">
            <option value="">All Services</option>{service_opts}
          </select>
        </div>
        <div class="form-group">
          <label>Area</label>
          <select name="area" class="form-control">
            <option value="">All Areas</option>{area_opts}
          </select>
        </div>
      </div>
      <button type="submit" class="btn">Filter</button>
    </form>
    <ul class="provider-list">{items if items else '<div class="card empty">No providers found.</div>'}</ul>
    """
    return page(content, "Find Pros – FixItTT")

# ---------------------------------------------------------------------------
# PROVIDER AUTH
# ---------------------------------------------------------------------------
@app.route("/provider/register", methods=["GET", "POST"])
def provider_register():
    if request.method == "POST":
        db = get_db()
        business_name = request.form.get("business_name", "").strip()
        contact_name = request.form.get("contact_name", "").strip()
        phone = request.form.get("phone", "").strip()
        whatsapp = request.form.get("whatsapp", "").strip().replace("+", "").replace("-", "").replace(" ", "")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        service = request.form.get("service", "").strip()
        areas = request.form.get("areas", "").strip()
        description = request.form.get("description", "").strip()

        if not all([business_name, phone, email, password, service, areas]):
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("provider_register"))

        existing = db.execute("SELECT id FROM providers WHERE email=?", (email,)).fetchone()
        if existing:
            flash("Email already registered. Please login.", "warning")
            return redirect(url_for("provider_login"))

        db.execute("""INSERT INTO providers
            (business_name, contact_name, phone, whatsapp, email, password_hash,
             service, areas, description)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (business_name, contact_name, phone, whatsapp or None, email,
             generate_password_hash(password), service, areas, description))
        db.commit()
        flash("Account created! You can now log in.", "success")
        return redirect(url_for("provider_login"))

    service_opts = "".join(f'<option value="{s}">{s}</option>' for s in SERVICES)
    content = f"""
    <div class="card">
      <h2>Join as a Service Pro</h2>
      <p style="color:var(--muted);margin-bottom:1rem">Create your free account to receive leads.</p>
      <form method="POST">
        <div class="grid-2">
          <div class="form-group">
            <label>Business Name *</label>
            <input type="text" name="business_name" class="form-control" required>
          </div>
          <div class="form-group">
            <label>Contact Person</label>
            <input type="text" name="contact_name" class="form-control">
          </div>
        </div>
        <div class="grid-2">
          <div class="form-group">
            <label>Phone *</label>
            <input type="text" name="phone" class="form-control" required>
          </div>
          <div class="form-group">
            <label>WhatsApp (digits only)</label>
            <input type="text" name="whatsapp" class="form-control" placeholder="8685550101">
          </div>
        </div>
        <div class="form-group">
          <label>Email * (used for login)</label>
          <input type="email" name="email" class="form-control" required>
        </div>
        <div class="form-group">
          <label>Password *</label>
          <input type="password" name="password" class="form-control" required minlength="6">
        </div>
        <div class="form-group">
          <label>Primary Service *</label>
          <select name="service" class="form-control" required>
            <option value="">— Select —</option>{service_opts}
          </select>
        </div>
        <div class="form-group">
          <label>Areas You Serve * (comma-separated)</label>
          <input type="text" name="areas" class="form-control" required
            placeholder="Chaguanas, Couva, San Fernando">
        </div>
        <div class="form-group">
          <label>Short Description</label>
          <textarea name="description" class="form-control" rows="3"></textarea>
        </div>
        <button type="submit" class="btn btn-success">Create Free Account</button>
      </form>
    </div>
    """
    return page(content, "Register – FixItTT")

@app.route("/provider/login", methods=["GET", "POST"])
def provider_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        provider = db.execute("SELECT * FROM providers WHERE email=?", (email,)).fetchone()
        if provider and provider["password_hash"] and check_password_hash(provider["password_hash"], password):
            session["provider_id"] = provider["id"]
            flash(f"Welcome back, {provider['business_name']}!", "success")
            return redirect(url_for("provider_dashboard"))
        flash("Invalid email or password.", "danger")

    content = """
    <div class="card" style="max-width:420px;margin:2rem auto">
      <h2>Provider Login</h2>
      <form method="POST">
        <div class="form-group">
          <label>Email</label>
          <input type="email" name="email" class="form-control" required>
        </div>
        <div class="form-group">
          <label>Password</label>
          <input type="password" name="password" class="form-control" required>
        </div>
        <button type="submit" class="btn">Log In</button>
      </form>
      <p style="margin-top:1rem;font-size:.9rem">
        Demo: rajesh@quickfix.tt / password123<br>
        <a href="/provider/register">Create an account</a>
      </p>
    </div>
    """
    return page(content, "Login – FixItTT")

@app.route("/provider/logout")
def provider_logout():
    session.pop("provider_id", None)
    flash("Logged out.", "info")
    return redirect(url_for("index"))

# ---------------------------------------------------------------------------
# PROVIDER DASHBOARD
# ---------------------------------------------------------------------------
@app.route("/provider/dashboard")
@login_required
def provider_dashboard():
    db = get_db()
    pid = session["provider_id"]
    provider = get_current_provider()

    stats = {
        "new": db.execute("SELECT COUNT(*) FROM leads WHERE provider_id=? AND status='New'", (pid,)).fetchone()[0],
        "total": db.execute("SELECT COUNT(*) FROM leads WHERE provider_id=?", (pid,)).fetchone()[0],
        "won": db.execute("SELECT COUNT(*) FROM leads WHERE provider_id=? AND status='Won'", (pid,)).fetchone()[0],
        "contacted": db.execute("SELECT COUNT(*) FROM leads WHERE provider_id=? AND status='Contacted'", (pid,)).fetchone()[0],
    }

    recent = db.execute("""
        SELECT l.*, r.service, r.area, r.urgency, r.description, r.customer_name, r.customer_phone, r.created_at as req_time
        FROM leads l
        JOIN requests r ON l.request_id = r.id
        WHERE l.provider_id = ?
        ORDER BY l.created_at DESC LIMIT 8
    """, (pid,)).fetchall()

    rows = ""
    for lead in recent:
        badge = f'<span class="badge badge-{lead["status"].lower()}">{lead["status"]}</span>'
        rows += f"""
        <div class="lead-item">
          <div>
            {badge}
            <strong>{lead['service']}</strong> · {lead['area']} · {lead['urgency']}<br>
            <span style="color:var(--muted);font-size:.9rem">{(lead['description'] or '')[:80]}...</span>
          </div>
          <a href="{url_for('provider_lead_detail', lead_id=lead['id'])}" class="btn btn-sm">Open</a>
        </div>"""

    content = f"""
    <div class="hero" style="text-align:left">
      <h1>Welcome, {provider['business_name']}</h1>
      <p>Manage your leads and profile.</p>
    </div>
    <div class="stats">
      <div class="stat-card"><div class="num">{stats['new']}</div><div class="label">New Leads</div></div>
      <div class="stat-card"><div class="num">{stats['total']}</div><div class="label">Total Leads</div></div>
      <div class="stat-card"><div class="num">{stats['contacted']}</div><div class="label">Contacted</div></div>
      <div class="stat-card"><div class="num">{stats['won']}</div><div class="label">Won</div></div>
    </div>
    <h2 class="section-title">Recent Leads</h2>
    {rows if rows else '<div class="card empty">No leads yet. They will appear here when customers request your service.</div>'}
    <div style="margin-top:1rem">
      <a href="{url_for('provider_leads')}" class="btn btn-outline">View All Leads</a>
    </div>
    """
    return page(content, "Dashboard – FixItTT")

@app.route("/provider/leads")
@login_required
def provider_leads():
    db = get_db()
    pid = session["provider_id"]
    status_filter = request.args.get("status", "")

    query = """
        SELECT l.*, r.service, r.area, r.urgency, r.description, r.customer_name, r.customer_phone
        FROM leads l JOIN requests r ON l.request_id = r.id
        WHERE l.provider_id = ?
    """
    params = [pid]
    if status_filter:
        query += " AND l.status=?"
        params.append(status_filter)
    query += " ORDER BY l.created_at DESC"

    leads = db.execute(query, params).fetchall()

    items = ""
    for lead in leads:
        badge = f'<span class="badge badge-{lead["status"].lower()}">{lead["status"]}</span>'
        items += f"""
        <div class="lead-item">
          <div>
            {badge}
            <strong>{lead['service']}</strong> · {lead['area']} · {lead['urgency']}<br>
            <span style="color:var(--muted)">{(lead['description'] or '')[:90]}</span>
          </div>
          <a href="{url_for('provider_lead_detail', lead_id=lead['id'])}" class="btn btn-sm">Open</a>
        </div>"""

    content = f"""
    <div class="hero" style="text-align:left">
      <h1>My Leads</h1>
    </div>
    <div style="margin-bottom:1rem">
      <a href="?status=" class="btn btn-sm btn-outline">All</a>
      <a href="?status=New" class="btn btn-sm btn-outline">New</a>
      <a href="?status=Contacted" class="btn btn-sm btn-outline">Contacted</a>
      <a href="?status=Won" class="btn btn-sm btn-outline">Won</a>
      <a href="?status=Lost" class="btn btn-sm btn-outline">Lost</a>
    </div>
    {items if items else '<div class="card empty">No leads found.</div>'}
    """
    return page(content, "My Leads – FixItTT")

@app.route("/provider/leads/<int:lead_id>", methods=["GET", "POST"])
@login_required
def provider_lead_detail(lead_id):
    db = get_db()
    pid = session["provider_id"]

    lead = db.execute("""
        SELECT l.*, r.service, r.area, r.urgency, r.description,
               r.customer_name, r.customer_phone, r.tracking_code, r.created_at as req_time
        FROM leads l JOIN requests r ON l.request_id = r.id
        WHERE l.id=? AND l.provider_id=?
    """, (lead_id, pid)).fetchone()

    if not lead:
        flash("Lead not found.", "danger")
        return redirect(url_for("provider_leads"))

    # Mark as viewed
    if lead["status"] == "New":
        db.execute("UPDATE leads SET status='Viewed', viewed_at=? WHERE id=?",
                   (datetime.utcnow().isoformat(), lead_id))
        db.commit()
        lead = dict(lead)
        lead["status"] = "Viewed"

    if request.method == "POST":
        new_status = request.form.get("status", lead["status"])
        notes = request.form.get("provider_notes", "")
        db.execute("UPDATE leads SET status=?, provider_notes=? WHERE id=?",
                   (new_status, notes, lead_id))
        db.commit()
        flash("Lead updated.", "success")
        return redirect(url_for("provider_lead_detail", lead_id=lead_id))

    wa = lead["customer_phone"].replace("-", "").replace(" ", "")
    wa_link = f"https://wa.me/1{wa}?text=Hi%2C%20I%20received%20your%20request%20on%20FixItTT%20regarding%20{lead['service']}."

    status_opts = ""
    for s in ["New", "Viewed", "Contacted", "Quoted", "Won", "Lost"]:
        sel = "selected" if s == lead["status"] else ""
        status_opts += f'<option value="{s}" {sel}>{s}</option>'

    content = f"""
    <div class="card">
      <h2>Lead #{lead['id']} 
        <span class="badge badge-{lead['status'].lower()}">{lead['status']}</span>
      </h2>
      <p style="color:var(--muted)">Received: {str(lead['created_at'])[:16]}</p>

      <div style="margin:1.2rem 0">
        <p><strong>Service:</strong> {lead['service']}</p>
        <p><strong>Area:</strong> {lead['area']}</p>
        <p><strong>Urgency:</strong> {lead['urgency']}</p>
        <p><strong>Description:</strong><br>{lead['description']}</p>
      </div>

      <div class="card" style="background:#f8f9fa">
        <h3>Customer</h3>
        <p>{lead['customer_name'] or '—'} · {lead['customer_phone']}</p>
        <div style="margin-top:.75rem;display:flex;gap:.5rem;flex-wrap:wrap">
          <a class="btn btn-whatsapp btn-sm" target="_blank" href="{wa_link}">WhatsApp Customer</a>
          <a class="btn btn-outline btn-sm" href="tel:{lead['customer_phone']}">Call</a>
        </div>
      </div>

      <form method="POST" style="margin-top:1.5rem">
        <div class="form-group">
          <label>Update Status</label>
          <select name="status" class="form-control">{status_opts}</select>
        </div>
        <div class="form-group">
          <label>Your Notes</label>
          <textarea name="provider_notes" class="form-control" rows="3">{lead['provider_notes'] or ''}</textarea>
        </div>
        <button type="submit" class="btn">Save Changes</button>
        <a href="{url_for('provider_leads')}" class="btn btn-outline">Back to Leads</a>
      </form>
    </div>
    """
    return page(content, f"Lead #{lead_id} – FixItTT")

@app.route("/provider/profile", methods=["GET", "POST"])
@login_required
def provider_profile():
    db = get_db()
    provider = get_current_provider()

    if request.method == "POST":
        business_name = request.form.get("business_name", "").strip()
        contact_name = request.form.get("contact_name", "").strip()
        phone = request.form.get("phone", "").strip()
        whatsapp = request.form.get("whatsapp", "").strip().replace("+", "").replace("-", "").replace(" ", "")
        service = request.form.get("service", "").strip()
        areas = request.form.get("areas", "").strip()
        description = request.form.get("description", "").strip()
        notify_email = 1 if request.form.get("notify_email") else 0
        notify_whatsapp = 1 if request.form.get("notify_whatsapp") else 0

        db.execute("""UPDATE providers SET
            business_name=?, contact_name=?, phone=?, whatsapp=?,
            service=?, areas=?, description=?,
            notify_email=?, notify_whatsapp=?
            WHERE id=?""",
            (business_name, contact_name, phone, whatsapp, service, areas,
             description, notify_email, notify_whatsapp, provider["id"]))
        db.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("provider_profile"))

    service_opts = "".join(
        f'<option value="{s}" {"selected" if s==provider["service"] else ""}>{s}</option>'
        for s in SERVICES)

    content = f"""
    <div class="card">
      <h2>Business Profile</h2>
      <form method="POST">
        <div class="grid-2">
          <div class="form-group">
            <label>Business Name</label>
            <input type="text" name="business_name" class="form-control" value="{provider['business_name'] or ''}" required>
          </div>
          <div class="form-group">
            <label>Contact Person</label>
            <input type="text" name="contact_name" class="form-control" value="{provider['contact_name'] or ''}">
          </div>
        </div>
        <div class="grid-2">
          <div class="form-group">
            <label>Phone</label>
            <input type="text" name="phone" class="form-control" value="{provider['phone'] or ''}" required>
          </div>
          <div class="form-group">
            <label>WhatsApp (digits only)</label>
            <input type="text" name="whatsapp" class="form-control" value="{provider['whatsapp'] or ''}">
          </div>
        </div>
        <div class="form-group">
          <label>Primary Service</label>
          <select name="service" class="form-control">{service_opts}</select>
        </div>
        <div class="form-group">
          <label>Areas You Serve (comma-separated)</label>
          <input type="text" name="areas" class="form-control" value="{provider['areas'] or ''}" required>
        </div>
        <div class="form-group">
          <label>Description</label>
          <textarea name="description" class="form-control" rows="3">{provider['description'] or ''}</textarea>
        </div>
        <div class="form-group">
          <label><input type="checkbox" name="notify_email" {"checked" if provider["notify_email"] else ""}> Email me new leads</label><br>
          <label><input type="checkbox" name="notify_whatsapp" {"checked" if provider["notify_whatsapp"] else ""}> WhatsApp me new leads</label>
        </div>
        <button type="submit" class="btn">Save Changes</button>
      </form>
    </div>
    """
    return page(content, "Profile – FixItTT")

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        init_db()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print("=" * 55)
    print("  FixItTT – Full Version")
    print(f"  http://127.0.0.1:{port}")
    print("  Demo login: rajesh@quickfix.tt / password123")
    print("=" * 55)
    app.run(host="0.0.0.0", port=port, debug=debug)