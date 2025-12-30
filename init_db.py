import sqlite3

# Connect to database (creates if not exists)
conn = sqlite3.connect('crm.db')
c = conn.cursor()

# -------------------------
# Customers table
# -------------------------
c.execute('''
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    instagram_handle TEXT NOT NULL UNIQUE,
    email TEXT,
    phone TEXT,
    category TEXT DEFAULT 'Lead',
    stage TEXT DEFAULT 'New'  -- Lead Pipeline Stage
)
''')

# -------------------------
# Messages table
# -------------------------
c.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    message_text TEXT,
    direction TEXT,  -- inbound or outbound
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
)
''')

# -------------------------
# Orders table
# -------------------------
c.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    product_name TEXT,
    quantity INTEGER,
    price REAL,  -- Revenue Tracking
    status TEXT DEFAULT 'Pending',  -- Pending, Completed, Shipped
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
)
''')

# -------------------------
# AI Summaries table
# -------------------------
c.execute('''
CREATE TABLE IF NOT EXISTS ai_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    summary_text TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
)
        
''')

# -------------------------
# Message Templates table
# -------------------------
c.execute('''
CREATE TABLE IF NOT EXISTS message_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    content TEXT NOT NULL
)
''')

# -------------------------
# Customer Tags table
# -------------------------
c.execute('''
CREATE TABLE IF NOT EXISTS customer_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    tag TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
)
''')

# -------------------------
# Reminders table
# -------------------------
c.execute('''
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    reminder_text TEXT,
    reminder_date DATETIME,
    status TEXT DEFAULT 'Pending',
    FOREIGN KEY(customer_id) REFERENCES customers(id)
)
''')

# -------------------------
# Activity Timeline table
# -------------------------
c.execute('''
CREATE TABLE IF NOT EXISTS activity_timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    action TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
)
''')
# Create ai_replies table
c.execute('''
CREATE TABLE IF NOT EXISTS ai_replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    reply TEXT NOT NULL,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
)
''')

conn.commit()
conn.close()
print("ai_replies table created successfully.")

print("Database initialized successfully with Business Intelligence & AI features!")
