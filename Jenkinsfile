pipeline {
    agent any
    environment {
        APP_NAME    = 'flask-app'
        IMAGE_NAME  = 'devops-tp2-app'
        COMPOSE_DIR = '/home/devops_os/devops-tp2'
        APP_URL     = 'http://192.168.47.10:5000'
    }
    stages {
        stage('🔍 Checkout') {
            steps {
                sh "cp -r ${COMPOSE_DIR}/. ."
            }
        }
        stage('🔎 Lint') {
            steps {
                sh '''
                    cd app
                    python3 -m py_compile app.py && echo "✅ Syntaxe Python OK"
                '''
            }
        }
        stage('🏗️ Build Docker') {
            steps {
                sh "cd ${COMPOSE_DIR} && docker compose build --no-cache app"
            }
        }
        stage('🧪 Tests') {
            steps {
                sh """
                    docker run -d --name test-app -p 5001:5000 devops-tp2-app:latest
                    sleep 5
                    curl -sf http://localhost:5001/health
                    echo "✅ Health OK"
                """
            }
            post { always { sh "docker rm -f test-app || true" } }
        }
        stage('🚀 Deploy') {
            steps {
                sh """
                    cd ${COMPOSE_DIR}
                    docker compose up -d app
                    echo "✅ Déploiement effectué"
                """
            }
        }
    }
}
