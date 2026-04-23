from flask import Flask, jsonify, request, render_template
import time
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
start_time = time.time()

# --- MÉTRIQUES ---
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'Temps de réponse en secondes', ['method', 'endpoint'])
IN_PROGRESS = Gauge('http_requests_inprogress', 'Nombre de requêtes en cours de traitement')

@app.before_request
def start_timer():
    request.start_time = time.time()
    IN_PROGRESS.inc()

@app.after_request
def stop_timer(response):
    resp_time = time.time() - request.start_time
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.path).observe(resp_time)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.path, status=response.status_code).inc()
    IN_PROGRESS.dec()
    return response

# --- ROUTES ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health():
    # Calcul de l'uptime pour le HTML
    uptime = time.time() - start_time
    return jsonify({"status": "healthy", "uptime_seconds": uptime}), 200

@app.route('/api/students')
def get_students():
    filiere = request.args.get('filiere', 'Toutes')
    students = [
        {"id": 1, "nom": "G", "prenom": "DesmonD", "filiere": "LP-DAR"},
        {"id": 2, "nom": "D", "prenom": "Emmanuel", "filiere": "LP-DAR"}
    ]
    if filiere != 'Toutes':
        students = [s for s in students if s['filiere'] == filiere]
    return jsonify(students)

@app.route('/api/students/<int:id>')
def get_student(id):
    if id == 1:
        return jsonify({"id": 1, "nom": "G", "prenom": "DesmonD"})
    return jsonify({"error": "Student not found"}), 404

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
