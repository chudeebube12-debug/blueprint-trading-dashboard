from flask import Flask, jsonify, send_from_directory
from flask_socketio import SocketIO
import os

app = Flask(__name__, static_folder='public', static_url_path='/')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
socketio = SocketIO(app, cors_allowed_origins='*')

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

# Serve frontend static (if you deploy frontend subtree to backend)
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    # Use socketio.run to start the app with eventlet/gevent support
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
