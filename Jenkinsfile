
pipeline {

    agent any



    environment {

        IMAGE_NAME   = 'devops-tp2-app'

        COMPOSE_DIR  = '/home/devops_os/devops-tp2'

        APP_URL      = 'http://192.168.47.10:5000'

        NOTIFY_EMAIL = 'bane16738@gmail.com'

        GITHUB_REPO  = 'https://github.com/Em-m-anuel/TP2-DevOps-INPTIC.git'

    }



    options {

        timeout(time: 15, unit: 'MINUTES')

        buildDiscarder(logRotator(numToKeepStr: '10'))

        timestamps()

    }



    stages {



        stage('🔍 Checkout GitHub') {

            steps {

                git branch: 'main', url: "${GITHUB_REPO}"

            }

        }



        stage('🔎 Lint & Validation') {

            steps {

                script {

                    def pythonOk = sh(

                        script: 'command -v python3 > /dev/null 2>&1 && echo yes || echo no',

                        returnStdout: true

                    ).trim()

                    if (pythonOk == 'yes') {

                        sh 'cd app && python3 -m py_compile app.py && echo Syntaxe Python OK'

                    } else {

                        echo 'python3 absent - lint skipe'

                    }

                    sh '''

                        grep -q flask-sqlalchemy  app/requirements.txt && echo flask-sqlalchemy OK

                        grep -q prometheus-client app/requirements.txt && echo prometheus-client OK

                        grep -q gunicorn          app/requirements.txt && echo gunicorn OK

                        grep -q openpyxl          app/requirements.txt && echo openpyxl OK

                    '''

                }

            }

        }



        stage('🏗️ Build Docker') {

            steps {

                sh """

                    if docker image inspect ${IMAGE_NAME}:latest > /dev/null 2>&1; then

                        echo "Image existante - tag build-${BUILD_NUMBER}"

                        docker tag ${IMAGE_NAME}:latest ${IMAGE_NAME}:build-${BUILD_NUMBER}

                    fi

                    docker build -t ${IMAGE_NAME}:latest ./app

                    echo "Build termine"

                """

            }

        }



        stage('🧪 Tests') {
    steps {
        sh """
            IMAGE="devops-tp2-app:latest"

            # Nettoyer les volumes anonymes orphelins du build precedent
            docker rm -f test-app 2>/dev/null || true
            docker volume prune -f 2>/dev/null || true

            echo "=== Demarrage conteneur de test ==="
            docker run -d --name test-app \
                --pull never \
                \$IMAGE

            echo "Attente demarrage..."
            for i in \$(seq 1 20); do
                sleep 3
                STATUS=\$(docker inspect -f '{{.State.Running}}' test-app 2>/dev/null || echo false)
                if [ "\$STATUS" != "true" ]; then
                    echo "Conteneur crashe. Logs :"
                    docker logs test-app
                    exit 1
                fi
                READY=\$(docker exec test-app python3 -c "
import urllib.request
try:
    urllib.request.urlopen('http://localhost:5000/health', timeout=2)
    print('ready')
except:
    print('waiting')
" 2>/dev/null || echo waiting)
                echo "  [\$i/20] \$READY"
                [ "\$READY" = "ready" ] && break
                [ \$i -eq 20 ] && docker logs test-app && exit 1
            done

            docker exec test-app python3 -c "
import urllib.request, json
r = urllib.request.urlopen('http://localhost:5000/health', timeout=10)
d = json.loads(r.read())
assert d['status'] == 'healthy'
print('Health OK')
"
            docker exec test-app python3 -c "
import urllib.request, json
r = urllib.request.urlopen('http://localhost:5000/api/students', timeout=10)
d = json.loads(r.read())
assert 'count' in d
print('API OK -', d['count'], 'etudiants')
"
            docker exec test-app python3 -c "
import urllib.request
r = urllib.request.urlopen('http://localhost:5000/metrics', timeout=10)
c = r.read().decode()
for m in ['http_requests_total','students_total','students_average_grade']:
    assert m in c, f'{m} manquant'
    print('Metrique OK:', m)
"
        """
    }
    post {
        always {
            sh "docker rm -f test-app 2>/dev/null || true"
        }
    }
}

       stage('🚀 Deploy') {
    steps {
        sh """
            echo "=== Deploiement ==="
            IMAGE="devops-tp2-app:latest"
            NETWORK="devops-tp2_devops-net"
            VOLUME="devops-tp2_students_db"

            docker stop flask-app 2>/dev/null || true
            docker rm   flask-app 2>/dev/null || true

            docker run -d \
                --name flask-app \
                --network \$NETWORK \
                --restart unless-stopped \
                -p 5000:5000 \
                -v \$VOLUME:/data \
                -e ENV=production \
                --pull never \
                \$IMAGE

            echo "Attente health check..."
            for i in \$(seq 1 18); do
                STATUS=\$(docker inspect --format='{{.State.Health.Status}}' flask-app 2>/dev/null || echo starting)
                echo "  [\$i/18] \$STATUS"
                [ "\$STATUS" = "healthy" ] && break
                sleep 5
            done
            docker ps | grep flask-app
            echo "Deploiement OK"
        """
    }
}



        stage('✅ Validation') {

            steps {

                sh """

                    sleep 3

                    curl -sf ${APP_URL}/health && echo "App accessible"

                    curl -sf ${APP_URL}/metrics | grep -q students_total && echo "Metriques OK"

                """

            }

        }

    }



    post {

        success {

            echo "Pipeline #${BUILD_NUMBER} REUSSI"

        }

        failure {

            echo "Pipeline #${BUILD_NUMBER} ECHOUE - rollback"

            sh "docker start flask-app 2>/dev/null || true"

        }

        always {

            sh "docker system prune -f --filter 'until=24h' 2>/dev/null || true"

        }

    }

}

