from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "Velveta Bot is Alive! 🌟"

def run():
    # This now listens on Port 8000 (Koyeb's default)
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
