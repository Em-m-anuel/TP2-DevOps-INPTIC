"""
Gestion Étudiants API — INPTIC DevOps TP2
Flask + SQLite + Prometheus metrics
"""
import os
import time
import logging
from datetime import datetime
from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
START_TIME = time.time()

# ─── Base de données SQLite ───────────────────────────────────────────────────
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////data/students.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Student(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    nom        = db.Column(db.String(100), nullable=False)
    prenom     = db.Column(db.String(100), nullable=False)
    filiere    = db.Column(db.String(50),  nullable=False)
    note       = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':         self.id,
            'nom':        self.nom,
            'prenom':     self.prenom,
            'filiere':    self.filiere,
            'note':       self.note,
            'created_at': self.created_at.isoformat()
        }

# ─── Métriques HTTP ───────────────────────────────────────────────────────────
REQUEST_COUNT   = Counter('http_requests_total', 'Total HTTP Requests',
                          ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'Durée des requêtes',
                            ['method', 'endpoint'],
                            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5])
IN_PROGRESS     = Gauge('http_requests_inprogress', 'Requêtes en cours')

# ─── Métriques métier (étudiants) ─────────────────────────────────────────────
STUDENTS_TOTAL         = Gauge('students_total',               "Nombre total d'étudiants")
STUDENTS_AVG_GRADE     = Gauge('students_average_grade',       'Moyenne générale des notes')
STUDENTS_MAX_GRADE     = Gauge('students_max_grade',           'Note maximale')
STUDENTS_MIN_GRADE     = Gauge('students_min_grade',           'Note minimale')
STUDENTS_ABOVE_AVG     = Gauge('students_above_average_count', 'Étudiants avec note >= 10')
STUDENTS_BY_FILIERE    = Gauge('students_by_filiere',          'Étudiants par filière', ['filiere'])
STUDENT_OPS            = Counter('student_operations_total',   'Opérations CRUD', ['operation'])

def update_student_metrics():
    students = Student.query.all()
    total = len(students)
    STUDENTS_TOTAL.set(total)
    if total > 0:
        notes = [s.note for s in students]
        avg   = sum(notes) / total
        STUDENTS_AVG_GRADE.set(round(avg, 2))
        STUDENTS_MAX_GRADE.set(max(notes))
        STUDENTS_MIN_GRADE.set(min(notes))
        STUDENTS_ABOVE_AVG.set(sum(1 for n in notes if n >= 10))
        filieres = {}
        for s in students:
            filieres[s.filiere] = filieres.get(s.filiere, 0) + 1
        for filiere, count in filieres.items():
            STUDENTS_BY_FILIERE.labels(filiere=filiere).set(count)
    else:
        for g in [STUDENTS_AVG_GRADE, STUDENTS_MAX_GRADE,
                  STUDENTS_MIN_GRADE, STUDENTS_ABOVE_AVG]:
            g.set(0)

# ─── Middleware ───────────────────────────────────────────────────────────────
@app.before_request
def start_timer():
    request.start_time = time.time()
    IN_PROGRESS.inc()

@app.after_request
def stop_timer(response):
    resp_time = time.time() - request.start_time
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.path).observe(resp_time)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.path,
                         status=response.status_code).inc()
    IN_PROGRESS.dec()
    return response

# ─── Pages web ────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/students')
def students_page():
    return render_template('students.html')

# ─── API Routes ───────────────────────────────────────────────────────────────
@app.route('/health')
def health():
    update_student_metrics()
    return jsonify({
        "status":          "healthy",
        "uptime_seconds":  round(time.time() - START_TIME, 2),
        "timestamp":       datetime.now().isoformat(),
        "students_count":  Student.query.count()
    }), 200

@app.route('/metrics')
def metrics():
    update_student_metrics()
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/api/students', methods=['GET'])
def get_students():
    filiere = request.args.get('filiere')
    query   = Student.query.filter_by(filiere=filiere) if filiere else Student.query
    rows    = query.order_by(Student.id).all()
    return jsonify({"count": len(rows), "students": [s.to_dict() for s in rows]})

@app.route('/api/students/<int:sid>', methods=['GET'])
def get_student(sid):
    return jsonify(Student.query.get_or_404(sid).to_dict())

@app.route('/api/students', methods=['POST'])
def create_student():
    data = request.get_json() or {}
    if not all(k in data for k in ['nom', 'prenom', 'filiere']):
        return jsonify({"error": "Champs requis : nom, prenom, filiere"}), 400
    s = Student(nom=data['nom'], prenom=data['prenom'],
                filiere=data['filiere'], note=float(data.get('note', 0.0)))
    db.session.add(s)
    db.session.commit()
    STUDENT_OPS.labels(operation='create').inc()
    update_student_metrics()
    logger.info(f"Créé : {s.prenom} {s.nom} ({s.filiere}) note={s.note}")
    return jsonify(s.to_dict()), 201

@app.route('/api/students/<int:sid>', methods=['PUT'])
def update_student(sid):
    s    = Student.query.get_or_404(sid)
    data = request.get_json() or {}
    for field in ['nom', 'prenom', 'filiere']:
        if field in data: setattr(s, field, data[field])
    if 'note' in data:
        s.note = float(data['note'])
    db.session.commit()
    STUDENT_OPS.labels(operation='update').inc()
    update_student_metrics()
    return jsonify(s.to_dict())

@app.route('/api/students/<int:sid>', methods=['DELETE'])
def delete_student(sid):
    s = Student.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    STUDENT_OPS.labels(operation='delete').inc()
    update_student_metrics()
    return jsonify({"message": "Supprimé", "id": sid})

@app.route('/api/stats')
def get_stats():
    students = Student.query.all()
    total    = len(students)
    if total == 0:
        return jsonify({"total": 0, "moyenne": 0, "max": 0, "min": 0,
                        "above_average": 0, "by_filiere": {}})
    notes    = [s.note for s in students]
    filieres = {}
    for s in students:
        filieres[s.filiere] = filieres.get(s.filiere, 0) + 1
    return jsonify({
        "total":         total,
        "moyenne":       round(sum(notes) / total, 2),
        "max":           max(notes),
        "min":           min(notes),
        "above_average": sum(1 for n in notes if n >= 10),
        "by_filiere":    filieres
    })

# ─── Init base de données ─────────────────────────────────────────────────────
def init_db():
    os.makedirs('/data', exist_ok=True)
    with app.app_context():
        db.create_all()
        if Student.query.count() == 0:
            seeds = [
                Student(nom="G",       prenom="DesmonD",  filiere="LP-DAR",  note=15.5),
                Student(nom="D",       prenom="Emmanuel", filiere="LP-DAR",  note=14.0),
                Student(nom="Camara",  prenom="Ibrahim",  filiere="LP-INFO", note=13.5),
                Student(nom="Bah",     prenom="Mariama",  filiere="LP-DAR",  note=17.0),
                Student(nom="Diallo",  prenom="Aissatou", filiere="LP-INFO", note=11.5),
            ]
            for seed in seeds:
                db.session.add(seed)
            db.session.commit()
            logger.info("Base initialisée avec 5 étudiants")

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
