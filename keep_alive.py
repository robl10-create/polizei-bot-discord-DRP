from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot ist online!"

def run():
    # Schaltet das Logging in der Konsole stumm, damit sie sauber bleibt
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    # Startet den Server auf Port 8080
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()