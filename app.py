from flask import Flask, render_template, request, redirect, Response, jsonify
from flask_cors import CORS
import sqlite3
import os
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, OpenAIError
from datetime import datetime

# Load API Key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not found. Check your .env file.")

client = OpenAI(api_key=api_key)

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
    total_revenue = conn.execute('SELECT SUM(price) FROM orders').fetchone()[0] or 0

    rows = conn.execute('SELECT * FROM customers').fetchall()
    customers = []

    for r in rows:
        customer = dict(r)
        customer['category'] = calculate_lead_score(customer['id'])
        customers.append(customer)

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
        total_revenue=total_revenue,
        customers=customers,
        customer_orders=customer_orders,
        ai_enabled=os.getenv("AI_ENABLED", "true") == "true"
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
        stage = request.form.get('stage', 'New')

        conn = get_db_connection()
        existing = conn.execute(
            'SELECT * FROM customers WHERE instagram_handle=?',
            (instagram_handle,)
        ).fetchone()

        if existing:
            message = "Customer already exists!"
        else:
            conn.execute(
                'INSERT INTO customers (name, instagram_handle, email, phone, category, stage) VALUES (?, ?, ?, ?, ?, ?)',
                (name, instagram_handle, email, phone, category, stage)
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
        stage = request.form.get('stage', customer['stage'])

        existing = conn.execute(
            'SELECT * FROM customers WHERE instagram_handle=? AND id != ?',
            (instagram_handle, id)
        ).fetchone()
        if existing:
            message = "Another customer with this Instagram handle already exists!"
        else:
            conn.execute(
                'UPDATE customers SET name=?, instagram_handle=?, email=?, phone=?, category=?, stage=? WHERE id=?',
                (name, instagram_handle, email, phone, category, stage, id)
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

# ------------------- AUTO-TAGGING -------------------
def auto_tag_customer(customer_id, message_text):
    tags = []
    lower_msg = message_text.lower()
    if any(word in lower_msg for word in ['price', 'cost', 'how much']):
        tags.append('Interested')
    if any(word in lower_msg for word in ['available', 'stock', 'in stock']):
        tags.append('Hot Lead')
    if any(word in lower_msg for word in ['order', 'buy', 'purchase']):
        tags.append('Ready to Order')

    conn = get_db_connection()
    for tag in tags:
        conn.execute('INSERT INTO customer_tags (customer_id, tag) VALUES (?, ?)', (customer_id, tag))
        conn.execute('INSERT INTO activity_timeline (customer_id, action) VALUES (?, ?)', 
                     (customer_id, f'Auto-tagged: {tag}'))
    conn.commit()
    conn.close()

# ------------------- VIEW MESSAGES -------------------
@app.route('/messages/<int:customer_id>', methods=['GET', 'POST'])
def messages(customer_id):
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id=?', (customer_id,)).fetchone()

    if request.method == 'POST':
        message_text = request.form['message']
        direction = request.form['direction']
        conn.execute(
            'INSERT INTO messages (customer_id, message_text, direction) VALUES (?, ?, ?)',
            (customer_id, message_text, direction)
        )
        conn.commit()
        auto_tag_customer(customer_id, message_text)

    messages = conn.execute(
        'SELECT * FROM messages WHERE customer_id=? ORDER BY timestamp ASC',
        (customer_id,)
    ).fetchall()

    ai_summary = conn.execute(
        'SELECT summary_text FROM ai_summaries WHERE customer_id=? ORDER BY timestamp DESC LIMIT 1',
        (customer_id,)
    ).fetchone()
    ai_summary_text = ai_summary['summary_text'] if ai_summary else "No summary yet."

    conn.close()
    return render_template('messages.html', customer=customer, messages=messages, ai_summary=ai_summary_text)

# ------------------- VIEW ORDERS -------------------
@app.route('/orders/<int:customer_id>', methods=['GET', 'POST'])
def orders(customer_id):
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id=?', (customer_id,)).fetchone()

    if request.method == 'POST':
        product_name = request.form['product_name']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        status = request.form.get('status', 'Pending')
        conn.execute(
            'INSERT INTO orders (customer_id, product_name, quantity, price, status) VALUES (?, ?, ?, ?, ?)',
            (customer_id, product_name, quantity, price, status)
        )
        conn.execute("UPDATE customers SET stage='Ordered' WHERE id=?", (customer_id,))
        conn.commit()

    orders = conn.execute(
        'SELECT * FROM orders WHERE customer_id=? ORDER BY timestamp DESC',
        (customer_id,)
    ).fetchall()

    clv = conn.execute(
        'SELECT SUM(price) FROM orders WHERE customer_id=?',
        (customer_id,)
    ).fetchone()[0] or 0

    conn.close()
    return render_template('orders.html', customer=customer, orders=orders, clv=clv)

# ------------------- REMINDERS -------------------
@app.route('/reminders/<int:customer_id>', methods=['GET', 'POST'])
def reminders(customer_id):
    conn = get_db_connection()
    if request.method == 'POST':
        reminder_text = request.form['reminder_text']
        reminder_date = request.form['reminder_date']
        conn.execute('INSERT INTO reminders (customer_id, reminder_text, reminder_date) VALUES (?, ?, ?)',
                     (customer_id, reminder_text, reminder_date))
        conn.execute('INSERT INTO activity_timeline (customer_id, action) VALUES (?, ?)',
                     (customer_id, f'Reminder added: {reminder_text}'))
        conn.commit()
    reminders = conn.execute('SELECT * FROM reminders WHERE customer_id=?', (customer_id,)).fetchall()
    conn.close()
    return render_template('reminders.html', customer_id=customer_id, reminders=reminders)

# ------------------- CUSTOMER PROFILE -------------------
@app.route('/customer/<int:customer_id>')
def customer_profile(customer_id):
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id=?', (customer_id,)).fetchone()
    messages = conn.execute('SELECT * FROM messages WHERE customer_id=? ORDER BY timestamp ASC', (customer_id,)).fetchall()
    orders = conn.execute('SELECT * FROM orders WHERE customer_id=? ORDER BY timestamp DESC', (customer_id,)).fetchall()
    tags = conn.execute('SELECT tag FROM customer_tags WHERE customer_id=?', (customer_id,)).fetchall()
    reminders_list = conn.execute('SELECT * FROM reminders WHERE customer_id=?', (customer_id,)).fetchall()
    activities = conn.execute('SELECT * FROM activity_timeline WHERE customer_id=? ORDER BY timestamp DESC', (customer_id,)).fetchall()
    clv = conn.execute('SELECT SUM(price) FROM orders WHERE customer_id=?', (customer_id,)).fetchone()[0] or 0

    summary_row = conn.execute('SELECT summary_text FROM ai_summaries WHERE customer_id=? ORDER BY timestamp DESC LIMIT 1', 
                               (customer_id,)).fetchone()
    ai_summary = summary_row['summary_text'] if summary_row else ''

    conn.close()
    return render_template(
        'customer_profile.html',
        customer=customer,
        messages=messages,
        orders=orders,
        clv=clv,
        tags=[t['tag'] for t in tags],
        reminders=reminders_list,
        activities=activities,
        ai_summary=ai_summary
    )

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
    return render_template('index.html', customers=customers, total_customers=len(customers), total_messages=0, total_orders=0, customer_orders={}, total_revenue=0)

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

# ------------------- AI REPLY WITH CACHING -------------------
@app.route('/ai_reply', methods=['POST'])
def ai_reply():
    customer_id = request.form.get('customer_id')  # <-- read from form
    if not customer_id:
        return jsonify({"error": "Customer ID is required."}), 400

    user_message = request.form['message']
    tone = request.form.get('tone', 'professional')
   
    # Check if reply already cached
    conn = get_db_connection()
    cached = conn.execute(
        'SELECT reply FROM ai_replies WHERE customer_id=? AND message=?',
        (customer_id, user_message)
    ).fetchone()
    if cached:
        conn.close()
        return jsonify({"reply": cached['reply_text']})

    tone_prompt = {
        "professional": "Reply professionally and politely to this customer message:",
        "friendly": "Reply in a friendly and warm tone:",
        "sales": "Reply in a persuasive sales-focused tone:",
        "polite": "Reply politely with a gentle follow-up tone:"
    }.get(tone, "Reply professionally:")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"{tone_prompt} {user_message}"}],
            max_tokens=120
        )
        ai_text = response.choices[0].message.content

        # Cache the reply
        conn.execute(
            'INSERT INTO ai_replies (customer_id, message, reply) VALUES (?, ?, ?)',
            (customer_id, user_message, ai_text)
        )

        conn.commit()
        conn.close()

        return jsonify({"reply": ai_text})

    except RateLimitError:
        conn.close()
        return jsonify({"reply": "AI quota exceeded. Fallback: please reply manually."})
    except OpenAIError as e:
        conn.close()
        return jsonify({"reply": f"AI error: {str(e)}"})

# ------------------- MESSAGE TEMPLATES -------------------
@app.route('/templates', methods=['GET', 'POST'])
def templates():
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form['name']
        content = request.form['content']
        conn.execute('INSERT INTO message_templates (name, content) VALUES (?, ?)', (name, content))
        conn.commit()
    templates = conn.execute('SELECT * FROM message_templates').fetchall()
    conn.close()
    return render_template('templates.html', templates=templates)

# ------------------- AI MESSAGE SUMMARY WITH SAVING -------------------
@app.route('/summary/<int:customer_id>', methods=['GET'])
def summary(customer_id):
    if os.getenv("AI_ENABLED", "true") != "true":
        return jsonify({"error": "AI features are disabled."}), 403

    conn = get_db_connection()
    messages_list = conn.execute(
        'SELECT message_text FROM messages WHERE customer_id=? ORDER BY timestamp ASC',
        (customer_id,)
    ).fetchall()

    all_text = "\n".join([m['message_text'] for m in messages_list])

    existing_summary = conn.execute(
        'SELECT summary_text FROM ai_summaries WHERE customer_id=? ORDER BY timestamp DESC LIMIT 1',
        (customer_id,)
    ).fetchone()
    if existing_summary:
        conn.close()
        return jsonify({"summary": existing_summary['summary_text']})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Summarize these messages:\n{all_text}"}],
            max_tokens=150
        )
        summary_text = response.choices[0].message.content
        conn.execute(
            'INSERT INTO ai_summaries (customer_id, summary_text, timestamp) VALUES (?, ?, ?)',
            (customer_id, summary_text, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return jsonify({"summary": summary_text})

    except RateLimitError:
        conn.close()
        return jsonify({"error": "AI quota exceeded. Please try later."}), 429
    except OpenAIError as e:
        conn.close()
        return jsonify({"error": f"AI service error: {str(e)}"}), 500

# ------------------- RUN APP -------------------
if __name__ == '__main__':
    app.run(debug=True)
