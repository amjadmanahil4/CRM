import sqlite3

# Connect to database (creates if not exists)
conn = sqlite3.connect('crm.db')
c = conn.cursor()

# Customers table
c.execute('''
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    instagram_handle TEXT NOT NULL UNIQUE,
    email TEXT,
    phone TEXT,
    category TEXT DEFAULT 'Lead'
)
''')

# Messages table
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

# Orders table
c.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    product_name TEXT,
    quantity INTEGER,
    status TEXT DEFAULT 'Pending',  -- Pending, Completed, Shipped
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
)
''')

conn.commit()
conn.close()
print("Database initialized successfully!")
