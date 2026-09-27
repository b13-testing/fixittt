#!/usr/bin/env python3
"""
FixItTT - Trinidad Service Request / Lead Platform Prototype
Single-file Flask app with SQLite. Zero cost to run locally.
"""

from flask import Flask, render_template_string, request, redirect, url_for, flash, g, session
import sqlite3
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "fixittt-demo-secret-change-in-production"
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixittt.db")

# ---------------------------------------------------------------------------
# Trinidad data
# ---------------------------------------------------------------------------
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
# Database helpers
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
    with app.app_context():
        db = get_db()
        db.executescript("""
            CREATE TABLE IF NOT EXISTS providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT NOT NULL,
                contact_name TEXT,
                phone TEXT NOT NULL,
                whatsapp TEXT,
                email TEXT,
                service TEXT NOT NULL,
                areas TEXT NOT NULL,
                description TEXT,
                rating REAL DEFAULT 4.5,
                is_featured INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT,
                customer_phone TEXT,
                service TEXT NOT NULL,
                area TEXT NOT NULL,
                description TEXT,
                urgency TEXT DEFAULT 'Normal',
                status TEXT DEFAULT 'Open',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER,
                provider_id INTEGER,
                status TEXT DEFAULT 'Sent',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (request_id) REFERENCES requests(id),
                FOREIGN KEY (provider_id) REFERENCES providers(id)
            );
        """)
        # Seed demo providers if empty
        count = db.execute("SELECT COUNT(*) FROM providers").fetchone()[0]
        if count == 0:
            demo = [
                ("QuickFix Plumbing", "Rajesh Singh", "868-555-0101", "8685550101", "rajesh@quickfix.tt", "Plumber", "Chaguanas,Couva,San Fernando", "24/7 emergency plumbing. Burst pipes, blocked drains, water heaters.", 4.8, 1),
                ("CoolAir TT", "Maria Dookeran", "868-555-0202", "8685550202", "maria@coolair.tt", "AC Repair / HVAC", "Port of Spain,Diego Martin,Westmoorings,Woodbrook", "Residential & commercial AC installation and repair. Same-day service.", 4.9, 1),
                ("Sparky Electrical", "Devon Charles", "868-555-0303", "8685550303", None, "Electrician", "Arima,Tunapuna,Arouca,Trincity", "Licensed electrician. Wiring, panels, outlets, generators.", 4.7, 0),
                ("WeldMasters", "Kevin Ali", "868-555-0404", "8685550404", "kevin@weldmasters.tt", "Welder", "San Fernando,Point Fortin,Princes Town,Gasparillo", "Gates, railings, structural welding, trailer repairs.", 4.6, 0),
                ("HandyPro Central", "Aisha Mohammed", "868-555-0505", "8685550505", None, "Handyman", "Chaguanas,Couva,Valsayn,Curepe", "Furniture assembly, minor repairs, painting touch-ups, odd jobs.", 4.5, 0),
                ("CaribCarpentry", "Leroy Baptiste", "868-555-0606", "8685550606", "leroy@caribcarp.tt", "Carpenter", "Port of Spain,Belmont,Laventille,San Juan", "Custom cabinets, doors, flooring, built-ins.", 4.8, 1),
                ("PaintPro TT", "Sharon Joseph", "868-555-0707", "8685550707", None, "Painter", "Arima,Sangre Grande,Tunapuna", "Interior/exterior painting. Free quotes.", 4.4, 0),
                ("TileRight", "Marcus Persad", "868-555-0808", "8685550808", "marcus@tileright.tt", "Tiler", "San Fernando,Marabella,Princes Town", "Floor & wall tiling. Bathrooms, kitchens, outdoor.", 4.7, 0),
                ("ApplianceFix 868", "Nalini Rampersad", "868-555-0909", "8685550909", None, "Appliance Repair", "Chaguanas,Port of Spain,San Fernando", "Washers, dryers, fridges, stoves. Home service.", 4.6, 0),
                ("AutoMech Express", "Ricky Seepersad", "868-555-1010", "8685551010", "ricky@automech.tt", "Auto Mechanic", "Couva,Chaguanas,Point Fortin", "Mobile mechanic. Diagnostics, brakes, AC, engines.", 4.5, 0),
                ("GenPower Repairs", "Trevor Khan", "868-555-1111", "8685551111", None, "Generator Repair", "All Trinidad", "Honda, Yamaha, diesel gens. On-site repairs.", 4.8, 1),
                ("RoofGuard TT", "Patricia Williams", "868-555-1212", "8685551212", "pat@roofguard.tt", "Roofing", "Diego Martin,Port of Spain,Westmoorings", "Leak repairs, new roofs, gutters. Insurance claims help.", 4.7, 0),
                ("GreenThumb Landscaping", "Andre Roberts", "868-555-1313", "8685551313", None, "Landscaping / Gardening", "Tobago - Scarborough,Tobago - Crown Point,Tobago - Plymouth", "Lawn care, tree trimming, garden design. Tobago only.", 4.9, 0),
                ("PestAway TT", "Sunita Maharaj", "868-555-1414", "8685551414", "sunita@pestaway.tt", "Pest Control", "Port of Spain,San Fernando,Chaguanas,Arima", "Termites, rodents, mosquitoes. Safe treatments.", 4.6, 0),
                ("Sparkle Clean", "Michelle George", "868-555-1515", "8685551515", None, "Cleaning Services", "Port of Spain,Woodbrook,Westmoorings,Diego Martin", "Deep cleaning, office, post-construction.", 4.5, 0),
                ("SecureCam Install", "Jason Lee", "868-555-1616", "8685551616", "jason@securecam.tt", "Security / CCTV Install", "All Trinidad", "CCTV, alarms, access control. Free site survey.", 4.8, 1),
                ("KeyMaster Locksmith", "Omar Hosein", "868-555-1717", "8685551717", None, "Locksmith", "Chaguanas,Couva,San Fernando,Arima", "24/7 lockouts, rekeying, security doors.", 4.7, 0),
                ("ClearView Glass", "Lisa Chen", "868-555-1818", "8685551818", "lisa@clearview.tt", "Glass / Windows", "Port of Spain,Tunapuna,Arima", "Window replacement, glass doors, shower enclosures.", 4.6, 0),
                ("SolidBuild Masonry", "David Ramlal", "868-555-1919", "8685551919", None, "Masonry / Concrete", "San Fernando,Princes Town,Mayaro", "Driveways, walls, foundations, plastering.", 4.5, 0),
                ("PoolCare Pro", "Angela Beckles", "868-555-2020", "8685552020", "angela@poolcare.tt", "Pool Maintenance", "Westmoorings,Diego Martin,Port of Spain", "Weekly service, repairs, chemical balancing.", 4.9, 1),
            ]
            for p in demo:
                db.execute(
                    "INSERT INTO providers (business_name, contact_name, phone, whatsapp, email, service, areas, description, rating, is_featured) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    p
                )
            db.commit()

# ---------------------------------------------------------------------------
# Simple admin auth (demo only)
# ---------------------------------------------------------------------------
ADMIN_USER = "admin"
ADMIN_PASS = "fixittt2024"

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            flash("Please log in as admin.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# ---------------------------------------------------------------------------
# HTML Templates (all in one file)
# ---------------------------------------------------------------------------
BASE_STYLE = """
:root {
  --primary: #0d6efd;
  --primary-dark: #0a58ca;
  --success: #198754;
  --warning: #ffc107;
  --danger: #dc3545;
  --bg: #f8f9fa;
  --card: #ffffff;
  --text: #212529;
  --muted: #6c757d;
  --border: #dee2e6;
  --radius: 12px;
  --shadow: 0 4px 12px rgba(0,0,0,0.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  min-height: 100vh;
}
a { color: var(--primary); text-decoration: none; }
a:hover { text-decoration: underline; }
.container { max-width: 960px; margin: 0 auto; padding: 1rem; }
header {
  background: linear-gradient(135deg, #0d6efd, #0a58ca);
  color: white;
  padding: 1rem 0;
  box-shadow: var(--shadow);
}
header .container { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0.75rem; }
.logo { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.5px; }
.logo span { opacity: 0.9; font-weight: 400; }
nav { display: flex; flex-wrap: wrap; gap: 0.5rem; }
nav a {
  color: white;
  background: rgba(255,255,255,0.15);
  padding: 0.4rem 0.85rem;
  border-radius: 20px;
  font-size: 0.9rem;
  text-decoration: none;
  transition: background 0.2s;
}
nav a:hover { background: rgba(255,255,255,0.3); text-decoration: none; }
.hero {
  background: white;
  border-radius: var(--radius);
  padding: 1.5rem;
  margin: 1.5rem 0;
  box-shadow: var(--shadow);
  text-align: center;
}
.hero h1 { font-size: 1.75rem; margin-bottom: 0.5rem; }
.hero p { color: var(--muted); margin-bottom: 1.25rem; }
.btn {
  display: inline-block;
  background: var(--primary);
  color: white !important;
  padding: 0.65rem 1.25rem;
  border-radius: 8px;
  border: none;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none !important;
  transition: background 0.2s, transform 0.1s;
}
.btn:hover { background: var(--primary-dark); }
.btn:active { transform: scale(0.98); }
.btn-success { background: var(--success); }
.btn-success:hover { background: #157347; }
.btn-outline {
  background: transparent;
  color: var(--primary) !important;
  border: 2px solid var(--primary);
}
.btn-outline:hover { background: var(--primary); color: white !important; }
.btn-sm { padding: 0.35rem 0.75rem; font-size: 0.85rem; }
.btn-whatsapp {
  background: #25D366;
  color: white !important;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.btn-whatsapp:hover { background: #1da851; }
.card {
  background: var(--card);
  border-radius: var(--radius);
  padding: 1.25rem;
  margin-bottom: 1rem;
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
}
.card h3 { margin-bottom: 0.5rem; font-size: 1.15rem; }
.card .meta { color: var(--muted); font-size: 0.9rem; margin-bottom: 0.75rem; }
.badge {
  display: inline-block;
  padding: 0.2rem 0.55rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
}
.badge-featured { background: #fff3cd; color: #856404; }
.badge-rating { background: #d1e7dd; color: #0f5132; }
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; font-weight: 600; margin-bottom: 0.35rem; font-size: 0.95rem; }
.form-control {
  width: 100%;
  padding: 0.6rem 0.85rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 1rem;
  background: white;
}
.form-control:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(13,110,253,0.15);
}
select.form-control { appearance: auto; }
textarea.form-control { min-height: 100px; resize: vertical; }
.grid { display: grid; gap: 1rem; }
@media (min-width: 600px) {
  .grid-2 { grid-template-columns: 1fr 1fr; }
  .grid-3 { grid-template-columns: 1fr 1fr 1fr; }
}
.alert {
  padding: 0.85rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.95rem;
}
.alert-success { background: #d1e7dd; color: #0f5132; border: 1px solid #badbcc; }
.alert-warning { background: #fff3cd; color: #856404; border: 1px solid #ffecb5; }
.alert-danger { background: #f8d7da; color: #842029; border: 1px solid #f5c2c7; }
.alert-info { background: #cff4fc; color: #055160; border: 1px solid #b6effb; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1.5rem 0; }
.stat-card {
  background: white;
  border-radius: var(--radius);
  padding: 1.25rem;
  text-align: center;
  box-shadow: var(--shadow);
}
.stat-card .num { font-size: 1.75rem; font-weight: 700; color: var(--primary); }
.stat-card .label { font-size: 0.85rem; color: var(--muted); margin-top: 0.25rem; }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th, td { padding: 0.65rem 0.5rem; text-align: left; border-bottom: 1px solid var(--border); }
th { background: #f1f3f5; font-weight: 600; }
footer {
  text-align: center;
  padding: 2rem 1rem;
  color: var(--muted);
  font-size: 0.85rem;
}
.provider-list { list-style: none; }
.provider-list li {
  background: white;
  border-radius: var(--radius);
  padding: 1rem;
  margin-bottom: 0.75rem;
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: flex-start;
  justify-content: space-between;
}
.provider-info { flex: 1; min-width: 200px; }
.provider-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.empty { text-align: center; padding: 2rem; color: var(--muted); }
.section-title { font-size: 1.25rem; margin: 1.5rem 0 1rem; }
"""

LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}FixItTT{% endblock %} – Trinidad Service Finder</title>
  <style>{{ style }}</style>
</head>
<body>
  <header>
    <div class="container">
      <div class="logo">🔧 FixIt<span>TT</span></div>
      <nav>
        <a href="{{ url_for('index') }}">Home</a>
        <a href="{{ url_for('request_service') }}">Request Help</a>
        <a href="{{ url_for('find_providers') }}">Find Pros</a>
        <a href="{{ url_for('register_provider') }}">Join as Pro</a>
        <a href="{{ url_for('admin_dashboard') }}">Admin</a>
      </nav>
    </div>
  </header>
  <main class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for cat, msg in messages %}
          <div class="alert alert-{{ cat }}">{{ msg }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
  </main>
  <footer>
    FixItTT Prototype · Built for Trinidad & Tobago · Free to launch · No payments required in v1
  </footer>
</body>
</html>
"""

INDEX_HTML = LAYOUT.replace("{% block content %}{% endblock %}", """
{% block content %}
<div class="hero">
  <h1>Need something fixed in Trinidad?</h1>
  <p>Tell us what you need. We'll match you with local plumbers, electricians, AC techs, welders and more — then connect you by WhatsApp.</p>
  <a href="{{ url_for('request_service') }}" class="btn">Request a Service →</a>
  &nbsp;
  <a href="{{ url_for('find_providers') }}" class="btn btn-outline">Browse Pros</a>
</div>

<div class="stats">
  <div class="stat-card">
    <div class="num">{{ stats.providers }}</div>
    <div class="label">Service Pros</div>
  </div>
  <div class="stat-card">
    <div class="num">{{ stats.requests }}</div>
    <div class="label">Requests</div>
  </div>
  <div class="stat-card">
    <div class="num">{{ stats.leads }}</div>
    <div class="label">Leads Sent</div>
  </div>
  <div class="stat-card">
    <div class="num">{{ stats.services }}</div>
    <div class="label">Categories</div>
  </div>
</div>

<h2 class="section-title">Popular Services</h2>
<div class="grid grid-3">
  {% for s in popular %}
  <a href="{{ url_for('find_providers', service=s) }}" class="card" style="text-align:center; text-decoration:none; color:inherit;">
    <h3>{{ s }}</h3>
    <p style="color:var(--muted); font-size:0.9rem;">Find local pros →</p>
  </a>
  {% endfor %}
</div>

<div class="card" style="margin-top:1.5rem; background:#e7f1ff;">
  <h3>How it works</h3>
  <ol style="margin:0.75rem 0 0 1.25rem; color:var(--muted);">
    <li>You describe the job + your area</li>
    <li>We match you with relevant local providers</li>
    <li>You contact them directly via WhatsApp</li>
    <li>No middleman fees for customers</li>
  </ol>
</div>
{% endblock %}
""")

REQUEST_HTML = LAYOUT.replace("{% block content %}{% endblock %}", """
{% block content %}
<div class="hero" style="text-align:left;">
  <h1>Request a Service</h1>
  <p>Fill this short form. Matching providers will appear instantly so you can WhatsApp them.</p>
</div>

<form method="POST" class="card">
  <div class="grid grid-2">
    <div class="form-group">
      <label>Your Name (optional)</label>
      <input type="text" name="customer_name" class="form-control" placeholder="e.g. John">
    </div>
    <div class="form-group">
      <label>Your Phone / WhatsApp</label>
      <input type="text" name="customer_phone" class="form-control" placeholder="868-xxx-xxxx" required>
    </div>
  </div>
  <div class="grid grid-2">
    <div class="form-group">
      <label>Service Needed *</label>
      <select name="service" class="form-control" required>
        <option value="">— Select —</option>
        {% for s in services %}
        <option value="{{ s }}" {% if request.args.get('service')==s %}selected{% endif %}>{{ s }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="form-group">
      <label>Area *</label>
      <select name="area" class="form-control" required>
        <option value="">— Select —</option>
        {% for a in areas %}
        <option value="{{ a }}">{{ a }}</option>
        {% endfor %}
      </select>
    </div>
  </div>
  <div class="form-group">
    <label>Describe the problem *</label>
    <textarea name="description" class="form-control" placeholder="e.g. Washing machine leaking from bottom, need someone today if possible" required></textarea>
  </div>
  <div class="form-group">
    <label>Urgency</label>
    <select name="urgency" class="form-control">
      <option value="Normal">Normal (within a few days)</option>
      <option value="Soon">Soon (today / tomorrow)</option>
      <option value="Emergency">Emergency (ASAP)</option>
    </select>
  </div>
  <button type="submit" class="btn">Find Matching Pros →</button>
</form>
{% endblock %}
""")

MATCHES_HTML = LAYOUT.replace("{% block content %}{% endblock %}", """
{% block content %}
<div class="hero" style="text-align:left;">
  <h1>Matching Providers</h1>
  <p>We found <strong>{{ matches|length }}</strong> pro(s) for <strong>{{ req.service }}</strong> in/near <strong>{{ req.area }}</strong>.</p>
</div>

{% if matches %}
<ul class="provider-list">
  {% for p in matches %}
  <li>
    <div class="provider-info">
      <h3>
        {{ p.business_name }}
        {% if p.is_featured %}<span class="badge badge-featured">Featured</span>{% endif %}
        <span class="badge badge-rating">★ {{ p.rating }}</span>
      </h3>
      <div class="meta">{{ p.service }} · Serves: {{ p.areas }}</div>
      {% if p.description %}<p style="font-size:0.95rem; margin-bottom:0.5rem;">{{ p.description }}</p>{% endif %}
      <div class="meta">Contact: {{ p.contact_name or '—' }} · {{ p.phone }}</div>
    </div>
    <div class="provider-actions">
      {% if p.whatsapp %}
      <a class="btn btn-whatsapp btn-sm" target="_blank"
         href="https://wa.me/1{{ p.whatsapp }}?text={{ wa_text|urlencode }}">
        WhatsApp
      </a>
      {% endif %}
      <a class="btn btn-outline btn-sm" href="tel:{{ p.phone }}">Call</a>
    </div>
  </li>
  {% endfor %}
</ul>
{% else %}
<div class="card empty">
  <p>No providers matched this area + service yet.</p>
  <p style="margin-top:0.75rem;">We've logged your request. Check back soon or try a nearby area.</p>
  <a href="{{ url_for('request_service') }}" class="btn" style="margin-top:1rem;">Try Another Request</a>
</div>
{% endif %}

<div style="margin-top:1.5rem;">
  <a href="{{ url_for('request_service') }}" class="btn btn-outline">← New Request</a>
</div>
{% endblock %}
""")

FIND_HTML = LAYOUT.replace("{% block content %}{% endblock %}", """
{% block content %}
<div class="hero" style="text-align:left;">
  <h1>Find Service Pros</h1>
  <p>Browse or filter by service and area.</p>
</div>

<form method="GET" class="card">
  <div class="grid grid-2">
    <div class="form-group">
      <label>Service</label>
      <select name="service" class="form-control">
        <option value="">All Services</option>
        {% for s in services %}
        <option value="{{ s }}" {% if filters.service==s %}selected{% endif %}>{{ s }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="form-group">
      <label>Area</label>
      <select name="area" class="form-control">
        <option value="">All Areas</option>
        {% for a in areas %}
        <option value="{{ a }}" {% if filters.area==a %}selected{% endif %}>{{ a }}</option>
        {% endfor %}
      </select>
    </div>
  </div>
  <button type="submit" class="btn">Filter</button>
</form>

{% if providers %}
<ul class="provider-list">
  {% for p in providers %}
  <li>
    <div class="provider-info">
      <h3>
        {{ p.business_name }}
        {% if p.is_featured %}<span class="badge badge-featured">Featured</span>{% endif %}
        <span class="badge badge-rating">★ {{ p.rating }}</span>
      </h3>
      <div class="meta">{{ p.service }} · Serves: {{ p.areas }}</div>
      {% if p.description %}<p style="font-size:0.95rem;">{{ p.description }}</p>{% endif %}
    </div>
    <div class="provider-actions">
      {% if p.whatsapp %}
      <a class="btn btn-whatsapp btn-sm" target="_blank"
         href="https://wa.me/1{{ p.whatsapp }}?text=Hi%2C%20I%20found%20you%20on%20FixItTT.%20I%20need%20help%20with%20{{ p.service|urlencode }}.">
        WhatsApp
      </a>
      {% endif %}
      <a class="btn btn-outline btn-sm" href="tel:{{ p.phone }}">Call</a>
    </div>
  </li>
  {% endfor %}
</ul>
{% else %}
<div class="empty card">No providers match those filters.</div>
{% endif %}
{% endblock %}
""")

REGISTER_HTML = LAYOUT.replace("{% block content %}{% endblock %}", """
{% block content %}
<div class="hero" style="text-align:left;">
  <h1>Join as a Service Pro</h1>
  <p>List your business for free. Get leads from customers who need your skills.</p>
</div>

<form method="POST" class="card">
  <div class="grid grid-2">
    <div class="form-group">
      <label>Business Name *</label>
      <input type="text" name="business_name" class="form-control" required placeholder="e.g. QuickFix Plumbing">
    </div>
    <div class="form-group">
      <label>Contact Person</label>
      <input type="text" name="contact_name" class="form-control" placeholder="Your name">
    </div>
  </div>
  <div class="grid grid-2">
    <div class="form-group">
      <label>Phone *</label>
      <input type="text" name="phone" class="form-control" required placeholder="868-xxx-xxxx">
    </div>
    <div class="form-group">
      <label>WhatsApp Number (digits only, no +)</label>
      <input type="text" name="whatsapp" class="form-control" placeholder="8685550101">
    </div>
  </div>
  <div class="form-group">
    <label>Email</label>
    <input type="email" name="email" class="form-control" placeholder="you@example.com">
  </div>
  <div class="form-group">
    <label>Primary Service *</label>
    <select name="service" class="form-control" required>
      <option value="">— Select —</option>
      {% for s in services %}
      <option value="{{ s }}">{{ s }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="form-group">
    <label>Areas You Serve * (comma-separated)</label>
    <input type="text" name="areas" class="form-control" required placeholder="e.g. Chaguanas, Couva, San Fernando">
    <small style="color:var(--muted);">Use exact names from the list if possible.</small>
  </div>
  <div class="form-group">
    <label>Short Description</label>
    <textarea name="description" class="form-control" placeholder="What you offer, years of experience, specialities..."></textarea>
  </div>
  <button type="submit" class="btn btn-success">Register Free →</button>
</form>
{% endblock %}
""")

ADMIN_LOGIN_HTML = LAYOUT.replace("{% block content %}{% endblock %}", """
{% block content %}
<div class="card" style="max-width:400px; margin:2rem auto;">
  <h2 style="margin-bottom:1rem;">Admin Login</h2>
  <form method="POST">
    <div class="form-group">
      <label>Username</label>
      <input type="text" name="username" class="form-control" required>
    </div>
    <div class="form-group">
      <label>Password</label>
      <input type="password" name="password" class="form-control" required>
    </div>
    <button type="submit" class="btn">Log In</button>
  </form>
  <p style="margin-top:1rem; font-size:0.85rem; color:var(--muted);">Demo: admin / fixittt2024</p>
</div>
{% endblock %}
""")

ADMIN_DASH_HTML = LAYOUT.replace("{% block content %}{% endblock %}", """
{% block content %}
<div class="hero" style="text-align:left;">
  <h1>Admin Dashboard</h1>
  <p>Overview of requests, providers and leads.</p>
  <a href="{{ url_for('admin_logout') }}" class="btn btn-outline btn-sm">Logout</a>
</div>

<div class="stats">
  <div class="stat-card"><div class="num">{{ stats.providers }}</div><div class="label">Providers</div></div>
  <div class="stat-card"><div class="num">{{ stats.requests }}</div><div class="label">Requests</div></div>
  <div class="stat-card"><div class="num">{{ stats.leads }}</div><div class="label">Leads</div></div>
  <div class="stat-card"><div class="num">{{ stats.open }}</div><div class="label">Open Requests</div></div>
</div>

<h2 class="section-title">Recent Requests</h2>
<div class="card" style="overflow-x:auto;">
  <table>
    <thead>
      <tr><th>ID</th><th>Service</th><th>Area</th><th>Urgency</th><th>Status</th><th>When</th></tr>
    </thead>
    <tbody>
      {% for r in recent_requests %}
      <tr>
        <td>{{ r.id }}</td>
        <td>{{ r.service }}</td>
        <td>{{ r.area }}</td>
        <td>{{ r.urgency }}</td>
        <td>{{ r.status }}</td>
        <td>{{ r.created_at[:16] if r.created_at else '—' }}</td>
      </tr>
      {% else %}
      <tr><td colspan="6" class="empty">No requests yet.</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<h2 class="section-title">Providers (Featured first)</h2>
<div class="card" style="overflow-x:auto;">
  <table>
    <thead>
      <tr><th>ID</th><th>Business</th><th>Service</th><th>Areas</th><th>Featured</th><th>Rating</th></tr>
    </thead>
    <tbody>
      {% for p in providers %}
      <tr>
        <td>{{ p.id }}</td>
        <td>{{ p.business_name }}</td>
        <td>{{ p.service }}</td>
        <td style="max-width:180px; overflow:hidden; text-overflow:ellipsis;">{{ p.areas }}</td>
        <td>{{ 'Yes' if p.is_featured else 'No' }}</td>
        <td>{{ p.rating }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
""")

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    db = get_db()
    stats = {
        "providers": db.execute("SELECT COUNT(*) FROM providers").fetchone()[0],
        "requests": db.execute("SELECT COUNT(*) FROM requests").fetchone()[0],
        "leads": db.execute("SELECT COUNT(*) FROM leads").fetchone()[0],
        "services": len(SERVICES),
    }
    popular = ["Plumber", "Electrician", "AC Repair / HVAC", "Welder", "Handyman", "Auto Mechanic"]
    return render_template_string(INDEX_HTML, style=BASE_STYLE, stats=stats, popular=popular)

@app.route("/request", methods=["GET", "POST"])
def request_service():
    if request.method == "POST":
        db = get_db()
        customer_name = request.form.get("customer_name", "").strip()
        customer_phone = request.form.get("customer_phone", "").strip()
        service = request.form.get("service", "").strip()
        area = request.form.get("area", "").strip()
        description = request.form.get("description", "").strip()
        urgency = request.form.get("urgency", "Normal")

        if not service or not area or not description or not customer_phone:
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("request_service"))

        cur = db.execute(
            "INSERT INTO requests (customer_name, customer_phone, service, area, description, urgency) VALUES (?,?,?,?,?,?)",
            (customer_name, customer_phone, service, area, description, urgency)
        )
        req_id = cur.lastrowid
        db.commit()

        # Match providers: service exact + area contained in their areas string
        providers = db.execute(
            "SELECT * FROM providers WHERE service = ? ORDER BY is_featured DESC, rating DESC",
            (service,)
        ).fetchall()

        matches = []
        for p in providers:
            provider_areas = [a.strip().lower() for a in p["areas"].split(",")]
            if area.lower() in provider_areas or "all trinidad" in provider_areas:
                matches.append(p)
                # Log lead
                db.execute(
                    "INSERT INTO leads (request_id, provider_id) VALUES (?,?)",
                    (req_id, p["id"])
                )
        db.commit()

        req = db.execute("SELECT * FROM requests WHERE id = ?", (req_id,)).fetchone()
        wa_text = f"Hi, I found you on FixItTT. I need help with: {service} in {area}. {description}"
        return render_template_string(
            MATCHES_HTML, style=BASE_STYLE, matches=matches, req=req, wa_text=wa_text
        )

    return render_template_string(
        REQUEST_HTML, style=BASE_STYLE, services=SERVICES, areas=AREAS
    )

@app.route("/find")
def find_providers():
    service = request.args.get("service", "").strip()
    area = request.args.get("area", "").strip()
    db = get_db()
    query = "SELECT * FROM providers WHERE 1=1"
    params = []
    if service:
        query += " AND service = ?"
        params.append(service)
    if area:
        query += " AND (LOWER(areas) LIKE ? OR LOWER(areas) LIKE '%all trinidad%')"
        params.append(f"%{area.lower()}%")
    query += " ORDER BY is_featured DESC, rating DESC"
    providers = db.execute(query, params).fetchall()
    return render_template_string(
        FIND_HTML, style=BASE_STYLE, providers=providers,
        services=SERVICES, areas=AREAS,
        filters={"service": service, "area": area}
    )

@app.route("/register", methods=["GET", "POST"])
def register_provider():
    if request.method == "POST":
        db = get_db()
        business_name = request.form.get("business_name", "").strip()
        contact_name = request.form.get("contact_name", "").strip()
        phone = request.form.get("phone", "").strip()
        whatsapp = request.form.get("whatsapp", "").strip().replace("+", "").replace("-", "").replace(" ", "")
        email = request.form.get("email", "").strip()
        service = request.form.get("service", "").strip()
        areas = request.form.get("areas", "").strip()
        description = request.form.get("description", "").strip()

        if not business_name or not phone or not service or not areas:
            flash("Please fill required fields.", "danger")
            return redirect(url_for("register_provider"))

        db.execute(
            """INSERT INTO providers
               (business_name, contact_name, phone, whatsapp, email, service, areas, description)
               VALUES (?,?,?,?,?,?,?,?)""",
            (business_name, contact_name, phone, whatsapp or None, email or None, service, areas, description)
        )
        db.commit()
        flash("Thanks! Your business is now listed. Customers can find you.", "success")
        return redirect(url_for("find_providers", service=service))

    return render_template_string(
        REGISTER_HTML, style=BASE_STYLE, services=SERVICES
    )

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USER and request.form.get("password") == ADMIN_PASS:
            session["admin"] = True
            flash("Logged in.", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid credentials.", "danger")
    return render_template_string(ADMIN_LOGIN_HTML, style=BASE_STYLE)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    flash("Logged out.", "info")
    return redirect(url_for("index"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    stats = {
        "providers": db.execute("SELECT COUNT(*) FROM providers").fetchone()[0],
        "requests": db.execute("SELECT COUNT(*) FROM requests").fetchone()[0],
        "leads": db.execute("SELECT COUNT(*) FROM leads").fetchone()[0],
        "open": db.execute("SELECT COUNT(*) FROM requests WHERE status='Open'").fetchone()[0],
    }
    recent_requests = db.execute(
        "SELECT * FROM requests ORDER BY id DESC LIMIT 20"
    ).fetchall()
    providers = db.execute(
        "SELECT * FROM providers ORDER BY is_featured DESC, rating DESC"
    ).fetchall()
    return render_template_string(
        ADMIN_DASH_HTML, style=BASE_STYLE, stats=stats,
        recent_requests=recent_requests, providers=providers
    )

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print("=" * 50)
    print("  FixItTT – Trinidad Service Finder")
    print("  Running at http://127.0.0.1:5000")
    print("  Admin: admin / fixittt2024")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)