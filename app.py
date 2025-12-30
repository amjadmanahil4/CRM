from flask import Flask, render_template, request, redirect, Response
from flask_cors import CORS
import sqlite3
import csv
import openai
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ---------- CONFIG ----------
app = Flask(__name__)
CORS(app)
DB = 'crm.db'


# ------------------- DB CONNECTION -------------------
def get_db_connection():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# ------------------- LEAD SCORING -------------------
def calculate_lead_score(customer_id):
    conn = get_db_connection()
    orders_count = conn.execute(
        'SELECT COUNT(*) FROM orders WHERE customer_id=?', (customer_id,)
    ).fetchone()[0]
    messages_count = conn.execute(
        'SELECT COUNT(*) FROM messages WHERE customer_id=?', (customer_id,)
    ).fetchone()[0]
    conn.close()
    score = orders_count*2 + messages_count
    if score >= 10:
        return 'VIP'
    elif score >= 5:
        return 'Active'
    else:
        return 'Lead'

# ------------------- DASHBOARD -------------------
@app.route('/')
def index():
    conn = get_db_connection()
    
    total_customers = conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0]
    total_messages = conn.execute('SELECT COUNT(*) FROM messages').fetchone()[0]
    total_orders = conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0]

    rows = conn.execute('SELECT * FROM customers').fetchall()
    customers = []

    for r in rows:
        customer = dict(r)  # convert sqlite3.Row to a mutable dict
        customer['category'] = calculate_lead_score(customer['id'])
        customers.append(customer)

    # Orders per customer for chart
    customer_orders = {}
    for c in customers:
        count = conn.execute('SELECT COUNT(*) FROM orders WHERE customer_id=?', (c['id'],)).fetchone()[0]
        customer_orders[c['id']] = count

    conn.close()
    return render_template(
        'index.html',
        total_customers=total_customers,
        total_messages=total_messages,
        total_orders=total_orders,
        customers=customers,
        customer_orders=customer_orders
    )

# ------------------- ADD CUSTOMER -------------------
@app.route('/add', methods=['GET', 'POST'])
def add_customer():
    message = ''
    if request.method == 'POST':
        name = request.form['name']
        instagram_handle = request.form['instagram_handle']
        email = request.form.get('email')
        phone = request.form.get('phone')
        category = request.form.get('category', 'Lead')

        conn = get_db_connection()
        existing = conn.execute(
            'SELECT * FROM customers WHERE instagram_handle=?',
            (instagram_handle,)
        ).fetchone()

        if existing:
            message = "Customer already exists!"
        else:
            conn.execute(
                'INSERT INTO customers (name, instagram_handle, email, phone, category) VALUES (?, ?, ?, ?, ?)',
                (name, instagram_handle, email, phone, category)
            )
            conn.commit()
            conn.close()
            return redirect('/')
        conn.close()
    return render_template('add_customer.html', message=message)

# ------------------- EDIT CUSTOMER -------------------
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_customer(id):
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id=?', (id,)).fetchone()
    message = ''
    if request.method == 'POST':
        name = request.form['name']
        instagram_handle = request.form['instagram_handle']
        email = request.form.get('email')
        phone = request.form.get('phone')
        category = request.form.get('category', 'Lead')

        existing = conn.execute(
            'SELECT * FROM customers WHERE instagram_handle=? AND id != ?',
            (instagram_handle, id)
        ).fetchone()
        if existing:
            message = "Another customer with this Instagram handle already exists!"
        else:
            conn.execute(
                'UPDATE customers SET name=?, instagram_handle=?, email=?, phone=?, category=? WHERE id=?',
                (name, instagram_handle, email, phone, category, id)
            )
            conn.commit()
            conn.close()
            return redirect('/')
    conn.close()
    return render_template('edit_customer.html', customer=customer, message=message)

# ------------------- DELETE CUSTOMER -------------------
@app.route('/delete/<int:id>')
def delete_customer(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM customers WHERE id=?', (id,))
    conn.execute('DELETE FROM messages WHERE customer_id=?', (id,))
    conn.execute('DELETE FROM orders WHERE customer_id=?', (id,))
    conn.commit()
    conn.close()
    return redirect('/')

# ------------------- VIEW MESSAGES -------------------
@app.route('/messages/<int:customer_id>', methods=['GET', 'POST'])
def messages(customer_id):
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id=?', (customer_id,)).fetchone()

    if request.method == 'POST':
        message_text = request.form['message']
        direction = request.form['direction']  # 'inbound' or 'outbound'
        conn.execute(
            'INSERT INTO messages (customer_id, message_text, direction) VALUES (?, ?, ?)',
            (customer_id, message_text, direction)
        )
        conn.commit()

    messages = conn.execute(
        'SELECT * FROM messages WHERE customer_id=? ORDER BY timestamp ASC',
        (customer_id,)
    ).fetchall()
    conn.close()
    return render_template('messages.html', customer=customer, messages=messages)

# ------------------- VIEW ORDERS -------------------
@app.route('/orders/<int:customer_id>', methods=['GET', 'POST'])
def orders(customer_id):
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id=?', (customer_id,)).fetchone()

    if request.method == 'POST':
        product_name = request.form['product_name']
        quantity = request.form['quantity']
        status = request.form.get('status', 'Pending')
        conn.execute(
            'INSERT INTO orders (customer_id, product_name, quantity, status) VALUES (?, ?, ?, ?)',
            (customer_id, product_name, quantity, status)
        )
        conn.commit()

    orders = conn.execute(
        'SELECT * FROM orders WHERE customer_id=? ORDER BY timestamp DESC',
        (customer_id,)
    ).fetchall()
    conn.close()
    return render_template('orders.html', customer=customer, orders=orders)

# ------------------- SEARCH CUSTOMERS -------------------
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    conn = get_db_connection()
    customers = conn.execute(
        'SELECT * FROM customers WHERE name LIKE ? OR instagram_handle LIKE ?',
        ('%' + query + '%', '%' + query + '%')
    ).fetchall()
    conn.close()
    return render_template('index.html', customers=customers, total_customers=len(customers), total_messages=0, total_orders=0, customer_orders={})

# ------------------- EXPORT DATA -------------------
@app.route('/export/<string:table>')
def export_table(table):
    conn = get_db_connection()
    valid_tables = ['customers', 'orders', 'messages']
    if table not in valid_tables:
        return "Invalid table"
    data = conn.execute(f'SELECT * FROM {table}').fetchall()
    conn.close()

    def generate():
        yield ','.join(data[0].keys()) + '\n'
        for row in data:
            yield ','.join(str(row[k]) for k in row.keys()) + '\n'

    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": f"attachment;filename={table}.csv"})



@app.route('/ai_reply', methods=['POST'])
def ai_reply():
    user_message = request.form['message']

    # New API call
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": f"Reply professionally to this customer message: {user_message}"}],
        max_tokens=60
    )

    reply = response.choices[0].message.content
    return reply



@app.route('/summary/<int:customer_id>')
def summary(customer_id):
    conn = get_db_connection()
    messages = conn.execute(
        'SELECT message_text FROM messages WHERE customer_id=? ORDER BY timestamp ASC',
        (customer_id,)
    ).fetchall()
    conn.close()

    all_text = "\n".join([m['message_text'] for m in messages])

    # New API call
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user", "content": f"Summarize these messages: {all_text}"}],
        max_tokens=150
    )

    summary_text = response.choices[0].message.content
    return summary_text


# ------------------- RUN APP -------------------
if __name__ == '__main__':
    app.run(debug=True)
