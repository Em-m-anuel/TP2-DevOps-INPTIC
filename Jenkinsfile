pipeline {
    agent any

    environment {
        IMAGE_NAME   = 'devops-tp2-app'
        COMPOSE_DIR  = '/home/devops_os/devops-tp2'
        APP_URL      = 'http://192.168.47.10:5000'
        COMPOSE_CMD  = 'docker-compose'
        NOTIFY_EMAIL = 'REMPLACE_TON_EMAIL@gmail.com'
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
                echo "=== Recuperation du code depuis GitHub ==="
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

                    sh '''
                        echo "=== Verification requirements ==="
                        grep -q "flask-sqlalchemy"  app/requirements.txt && echo "flask-sqlalchemy present"
                        grep -q "prometheus-client" app/requirements.txt && echo "prometheus-client present"
                        grep -q "gunicorn"          app/requirements.txt && echo "gunicorn present"
                    '''

                    if (pythonOk == 'yes') {
                        sh '''
                            echo "=== Validation syntaxe Python ==="
                            cd app && python3 -m py_compile app.py && echo "Syntaxe Python OK"
                        '''
                    } else {
                        echo "python3 absent dans Jenkins — lint skipe (image validee au build)"
                    }
                }
            }
        }

        stage('🏗️ Build Docker') {
            steps {
                sh """
                    echo "=== Build image Docker ==="
                    if docker image inspect ${IMAGE_NAME}:latest > /dev/null 2>&1; then
                        echo "Image deja presente — tag build"
                        docker tag ${IMAGE_NAME}:latest ${IMAGE_NAME}:build-${BUILD_NUMBER}
                    else
                        echo "Image absente — build depuis cache local"
                        docker build --pull never -t ${IMAGE_NAME}:latest ./app
                    fi
                    echo "Image : ${IMAGE_NAME}:build-${BUILD_NUMBER}"
                """
            }
        }

        stage('🧪 Tests') {
            steps {
                sh """
                    echo "=== Demarrage conteneur de test ==="
                    docker run -d --name test-app \
                        -v /tmp/test-db-${BUILD_NUMBER}:/data \
                        --pull never \
                        ${IMAGE_NAME}:latest

                    sleep 10

                    STATUS=\$(docker inspect -f '{{.State.Running}}' test-app 2>/dev/null || echo false)
                    if [ "\$STATUS" != "true" ]; then
                        echo "FAIL : conteneur arrete. Logs :"
                        docker logs test-app
                        exit 1
                    fi

                    echo "=== Test /health ==="
                    docker exec test-app python3 -c "
import urllib.request, json, sys
r = urllib.request.urlopen('http://localhost:5000/health', timeout=10)
d = json.loads(r.read())
assert d['status'] == 'healthy', f'status={d[\"status\"]}'
print('Health OK — uptime:', round(d.get('uptime_seconds',0)), 's')
"
                """
            }
            post {
                always {
                    sh """
                        docker rm -f test-app 2>/dev/null || true
                        rm -rf /tmp/test-db-${BUILD_NUMBER} 2>/dev/null || true
                    """
                }
            }
        }

        stage('🚀 Deploy') {
            steps {
                sh """
                    echo "=== Deploiement ==="
                    docker stop flask-app 2>/dev/null || true
                    docker rm   flask-app 2>/dev/null || true
                    cd ${COMPOSE_DIR}
                    ${COMPOSE_CMD} up -d app
                """
            }
        }
    }

    post {
        success {
            echo "Pipeline #${BUILD_NUMBER} REUSSI"
        }
        failure {
            echo "Pipeline #${BUILD_NUMBER} ECHOUE — rollback"
            sh "cd ${COMPOSE_DIR} && ${COMPOSE_CMD} up -d app || true"
        }
        always {
            sh "docker system prune -f --filter 'until=24h' 2>/dev/null || true"
        }
    }
}
