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
                        sh 'cd app && python3 -m py_compile app.py'
                    }
                }
            }
        }

        stage('🏗️ Build Docker') {
            steps {
                sh """
                    echo "=== Build image Docker ==="

                    if docker image inspect ${IMAGE_NAME}:latest > /dev/null 2>&1; then
                        echo "Image existante -> tag backup"
                        docker tag ${IMAGE_NAME}:latest ${IMAGE_NAME}:build-${BUILD_NUMBER}
                    fi

                    docker build -t ${IMAGE_NAME}:latest ./app
                """
            }
        }

        stage('🧪 Tests') {
            steps {
                sh """
                    echo "=== Start test container ==="

                    docker run -d --name test-app \
                        -v /tmp/test-db-${BUILD_NUMBER}:/data \
                        ${IMAGE_NAME}:latest

                    echo "Waiting app startup..."

                    for i in \$(seq 1 20); do
                        sleep 3

                        STATUS=\$(docker inspect -f '{{.State.Running}}' test-app 2>/dev/null || echo false)

                        if [ "\$STATUS" != "true" ]; then
                            echo "Container crashed"
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

                        echo "[\$i/20] \$READY"

                        if [ "\$READY" = "ready" ]; then
                            break
                        fi

                        if [ \$i -eq 20 ]; then
                            echo "TIMEOUT"
                            docker logs test-app
                            exit 1
                        fi
                    done
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
                    echo "=== Deploy via Docker Compose ==="
                    cd ${COMPOSE_DIR}

                    # 🔥 FIX IMPORTANT : utilise docker compose V2
                    docker compose up -d app
                """
            }
        }
    }

    post {
        success {
            echo "Pipeline SUCCESS"
        }

        failure {
            echo "Pipeline FAILED - rollback"

            sh """
                cd ${COMPOSE_DIR}
                docker compose up -d app || true
            """
        }

        always {
            sh "docker system prune -f --filter 'until=24h' || true"
        }
    }
}
