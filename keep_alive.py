from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I am alive"

def run():
    # Render assigns a port automatically via the PORT environment variable
    # If not found, it defaults to 8080
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
