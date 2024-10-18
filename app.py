import threading
import time

from flask import Flask, render_template, request, jsonify
import sqlite3
import requests
from datetime import datetime

app = Flask(__name__)

API_URL = "https://api.exchangeratesapi.io/v1/latest?access_key=cd654fc7272b76520459442c784d15c7"
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
    try:
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
        print(f"Курсы валют обновлены в {timestamp}")
    except Exception as e:
        print(f"Ошибка обновления курсов: {e}")

def schedule_rate_updates():
    while True:
        update_exchange_rates()
        time.sleep(300)  

def get_saved_currencies():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT currency FROM rates")
    currencies = [row[0] for row in cursor.fetchall()]
    conn.close()
    return currencies

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
    currencies = get_saved_currencies()  # Получаем список валют для выпадающего списка
    return render_template('index.html', currencies=currencies)

@app.route('/update_rates', methods=['POST'])
def update_rates():
    update_exchange_rates()
    return jsonify({'message': 'Курсы обновлены!'})

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
    update_thread = threading.Thread(target=schedule_rate_updates)
    update_thread.daemon = True  # Устанавливаем поток как демона, чтобы он завершился при завершении основного потока
    update_thread.start()

    app.run(debug=True)
