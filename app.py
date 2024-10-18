from flask import Flask, render_template, request, jsonify
import sqlite3
import requests
from datetime import datetime

app = Flask(__name__)

API_URL = "https://api.exchangeratesapi.io/latest?base=USD"
DATABASE = 'db.sqlite'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS rates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        currency TEXT NOT NULL,
                        rate REAL NOT NULL,
                        updated_at TEXT NOT NULL
                      )''')
    conn.commit()
    conn.close()

def update_exchange_rates():
    response = requests.get(API_URL)
    data = response.json()
    rates = data.get('rates', {})
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM rates")
    
    for currency, rate in rates.items():
        cursor.execute("INSERT INTO rates (currency, rate, updated_at) VALUES (?, ?, ?)",
                       (currency, rate, timestamp))
    
    conn.commit()
    conn.close()

def get_last_update():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT updated_at FROM rates LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def convert_currency(from_currency, to_currency, amount):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT rate FROM rates WHERE currency=?", (from_currency,))
    from_rate = cursor.fetchone()
    
    cursor.execute("SELECT rate FROM rates WHERE currency=?", (to_currency,))
    to_rate = cursor.fetchone()
    
    conn.close()
    
    if from_rate and to_rate:
        converted_amount = amount * (to_rate[0] / from_rate[0])
        return round(converted_amount, 2)
    else:
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/update_rates', methods=['POST'])
def update_rates():
    update_exchange_rates()
    return jsonify({'message': 'Курсы обновлены!'})

@app.route('/last_update', methods=['GET'])
def last_update():
    last_update = get_last_update()
    return jsonify({'last_update': last_update})

@app.route('/convert', methods=['POST'])
def convert():
    data = request.get_json()
    from_currency = data['from_currency']
    to_currency = data['to_currency']
    amount = float(data['amount'])
    
    result = convert_currency(from_currency, to_currency, amount)
    if result is not None:
        return jsonify({'converted_amount': result})
    else:
        return jsonify({'error': 'Ошибка конвертации!'}), 400

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
