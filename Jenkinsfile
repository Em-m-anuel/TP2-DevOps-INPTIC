pipeline {
    agent any

    environment {
        IMAGE_NAME  = 'devops-tp2-app'
        COMPOSE_DIR = '/home/devops_os/devops-tp2'
        APP_URL     = 'http://192.168.47.10'
        // Remplace par ton repo GitHub
        GITHUB_REPO = 'https://github.com/TON_USERNAME/devops-tp2.git'
        // Email à notifier (configure dans Jenkins → Manage → Email)
        NOTIFY_EMAIL = 'TON_EMAIL@gmail.com'
    }

    options {
        timeout(time: 15, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
    }

    stages {

        stage('🔍 Checkout GitHub') {
            steps {
                echo "=== Récupération du code depuis GitHub ==="
                // Option A : depuis GitHub (quand ton repo est public)
                git branch: 'main', url: "${GITHUB_REPO}"

                // Option B : depuis le dossier local (garder si GitHub pas encore setup)
                // sh "cp -r ${COMPOSE_DIR}/. ."
            }
        }

        stage('🔎 Lint & Validation') {
            steps {
                sh '''
                    echo "=== Validation Python ==="
                    cd app
                    python3 -m py_compile app.py && echo "✅ Syntaxe Python OK"

                    echo "=== Vérification requirements ==="
                    grep -q "flask-sqlalchemy" requirements.txt && echo "✅ flask-sqlalchemy présent"
                    grep -q "prometheus-client"  requirements.txt && echo "✅ prometheus-client présent"
                    grep -q "gunicorn"           requirements.txt && echo "✅ gunicorn présent"
                '''
            }
        }

        stage('🏗️ Build Docker') {
            steps {
                sh """
                    echo "=== Build image Docker ==="
                    if docker image inspect ${IMAGE_NAME}:latest > /dev/null 2>&1; then
                        echo "✅ Image existante trouvée — rebuild depuis cache"
                    fi
                    docker build -t ${IMAGE_NAME}:latest ./app
                    docker tag ${IMAGE_NAME}:latest ${IMAGE_NAME}:build-${BUILD_NUMBER}
                    echo "✅ Image taguée : ${IMAGE_NAME}:build-${BUILD_NUMBER}"
                """
            }
        }

        stage('🧪 Tests') {
            steps {
                sh """
                    echo "=== Démarrage conteneur de test ==="
                    docker run -d --name test-app \
                        -v /tmp/test-db:/data \
                        --pull never \
                        ${IMAGE_NAME}:latest
                    sleep 8

                    echo "=== Test /health ==="
                    docker exec test-app python3 -c "
import urllib.request, json, sys
try:
    r = urllib.request.urlopen('http://localhost:5000/health', timeout=10)
    d = json.loads(r.read())
    assert d['status'] == 'healthy', 'Status pas healthy'
    print('✅ Health OK — uptime:', d.get('uptime_seconds', '?'), 's')
except Exception as e:
    print('❌ Health FAIL:', e); sys.exit(1)
"
                    echo "=== Test /api/students ==="
                    docker exec test-app python3 -c "
import urllib.request, json, sys
try:
    r = urllib.request.urlopen('http://localhost:5000/api/students', timeout=10)
    d = json.loads(r.read())
    assert d['count'] >= 0, 'count absent'
    print('✅ API Students OK — count:', d['count'])
except Exception as e:
    print('❌ API FAIL:', e); sys.exit(1)
"
                    echo "=== Test /metrics Prometheus ==="
                    docker exec test-app python3 -c "
import urllib.request, sys
try:
    r = urllib.request.urlopen('http://localhost:5000/metrics', timeout=10)
    content = r.read().decode()
    for metric in ['http_requests_total', 'students_total', 'students_average_grade']:
        assert metric in content, f'{metric} manquant dans /metrics'
        print(f'✅ Métrique {metric} présente')
except Exception as e:
    print('❌ Metrics FAIL:', e); sys.exit(1)
"
                    echo "=== Test POST /api/students ==="
                    docker exec test-app python3 -c "
import urllib.request, json, sys
try:
    data = json.dumps({'nom':'Test','prenom':'Jenkins','filiere':'LP-DAR','note':15.0}).encode()
    req  = urllib.request.Request('http://localhost:5000/api/students',
                                  data=data, headers={'Content-Type':'application/json'})
    r    = urllib.request.urlopen(req, timeout=10)
    d    = json.loads(r.read())
    assert 'id' in d, 'id absent de la réponse'
    print('✅ POST étudiant OK — id:', d['id'])
except Exception as e:
    print('❌ POST FAIL:', e); sys.exit(1)
"
                """
            }
            post {
                always {
                    sh """
                        docker rm -f test-app 2>/dev/null || true
                        rm -rf /tmp/test-db
                    """
                }
            }
        }

        stage('🚀 Deploy') {
            steps {
                sh """
                    echo "=== Déploiement ==="
                    cd ${COMPOSE_DIR}

                    # Arrêt propre de l'ancien conteneur
                    docker stop flask-app 2>/dev/null || true
                    docker rm   flask-app 2>/dev/null || true

                    # Relance via Docker Compose (conserve le volume SQLite)
                    docker-compose up -d app

                    echo "Attente du health check..."
                    for i in \$(seq 1 15); do
                        STATUS=\$(docker inspect --format='{{.State.Health.Status}}' flask-app 2>/dev/null || echo "starting")
                        echo "  [\$i/15] Statut : \$STATUS"
                        [ "\$STATUS" = "healthy" ] && break
                        sleep 5
                    done
                """
            }
        }

        stage('✅ Validation finale') {
            steps {
                sh """
                    sleep 3
                    curl -sf http://192.168.47.10/health | python3 -m json.tool
                    echo "✅ App accessible via Nginx sans port"

                    # Vérifier que les métriques étudiants remontent
                    METRICS=\$(curl -sf http://192.168.47.10:5000/metrics)
                    echo "\$METRICS" | grep -q "students_total"    && echo "✅ Métrique students_total OK"
                    echo "\$METRICS" | grep -q "students_average_grade" && echo "✅ Métrique moyenne OK"

                    echo "✅ Build #${BUILD_NUMBER} déployé avec succès"
                """
            }
        }
    }

    post {
        success {
            echo "🎉 Pipeline #${BUILD_NUMBER} réussi !"
            emailext(
                subject: "✅ [Jenkins] Build #${BUILD_NUMBER} RÉUSSI — DevOps TP2",
                body: """
                    <h2 style='color:#38a169'>✅ Build réussi</h2>
                    <p><b>Job :</b> ${JOB_NAME}</p>
                    <p><b>Build :</b> #${BUILD_NUMBER}</p>
                    <p><b>Durée :</b> ${currentBuild.durationString}</p>
                    <p><b>Branche :</b> main</p>
                    <hr>
                    <p>🌐 <a href='http://192.168.47.10'>Application</a> |
                       📈 <a href='http://192.168.47.10/grafana/'>Grafana</a> |
                       🔧 <a href='http://192.168.47.10/jenkins/'>Jenkins</a></p>
                """,
                to: "${NOTIFY_EMAIL}",
                mimeType: 'text/html'
            )
        }
        failure {
            echo "💥 Pipeline #${BUILD_NUMBER} ÉCHOUÉ — Rollback..."
            sh """
                cd ${COMPOSE_DIR}
                docker-compose up -d app || true
                echo "Rollback effectué"
            """
            emailext(
                subject: "❌ [Jenkins] Build #${BUILD_NUMBER} ÉCHOUÉ — DevOps TP2",
                body: """
                    <h2 style='color:#e53e3e'>❌ Build échoué</h2>
                    <p><b>Job :</b> ${JOB_NAME}</p>
                    <p><b>Build :</b> #${BUILD_NUMBER}</p>
                    <p><b>Durée :</b> ${currentBuild.durationString}</p>
                    <hr>
                    <p>⚠️ Un rollback automatique a été effectué.</p>
                    <p><a href='${BUILD_URL}console'>Voir les logs du build</a></p>
                """,
                to: "${NOTIFY_EMAIL}",
                mimeType: 'text/html'
            )
        }
        always {
            sh "docker system prune -f --filter 'until=24h' 2>/dev/null || true"
        }
    }
}
