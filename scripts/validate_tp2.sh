#!/bin/bash
echo "════════════════════════════════════════════"
echo "  Validation TP2 Linux — Partie 6"
echo "════════════════════════════════════════════"
pass=0; fail=0

check() {
    if eval "$2" > /dev/null 2>&1; then
        echo "  ✅ $1"; ((pass++))
    else
        echo "  ❌ $1"; ((fail++))
    fi
}

echo ""
echo "── L'application répond ─────────────────────"
check "Flask /health répond 200"     "curl -sf http://192.168.47.10:5000/health"
check "Flask /api/students répond"   "curl -sf http://192.168.47.10:5000/api/students"
check "Flask /metrics répond"        "curl -sf http://192.168.47.10:5000/metrics"
check "Flask accessible via Nginx"   "curl -sf http://192.168.47.10/"

echo ""
echo "── Les métriques remontent ──────────────────"
check "Prometheus est UP" \
    "curl -sf http://192.168.47.10:9090/prometheus/-/healthy"
check "Flask scrapé par Prometheus" \
    "curl -sf 'http://192.168.47.10:9090/prometheus/api/v1/query?query=up{job=\"flask-app\"}' | grep -q '\"1\"'"
check "Métrique http_requests_total présente" \
    "curl -sf http://192.168.47.10:5000/metrics | grep -q http_requests_total"
check "Métrique students_total présente" \
    "curl -sf http://192.168.47.10:5000/metrics | grep -q students_total"
check "Métrique students_average_grade présente" \
    "curl -sf http://192.168.47.10:5000/metrics | grep -q students_average_grade"

echo ""
echo "── Les tableaux de bord ─────────────────────"
check "Grafana accessible" \
    "curl -sf http://192.168.47.10:3000/api/health"
check "Grafana datasource Prometheus configurée" \
    "curl -sf -u admin:devops2026 http://192.168.47.10:3000/api/datasources | grep -q Prometheus"

echo ""
echo "── Le pipeline automatise ───────────────────"
check "Jenkins accessible" \
    "curl -sf http://192.168.47.10:8080/jenkins/api/json -u admin:devops2026"
check "Conteneur Jenkins running" \
    "docker inspect jenkins | grep -q '\"Running\": true'"

echo ""
echo "── Bonus ────────────────────────────────────"
check "SQLite : étudiants en base" \
    "curl -sf http://192.168.47.10:5000/api/students | python3 -c 'import sys,json; d=json.load(sys.stdin); exit(0 if d[\"count\"]>0 else 1)'"
check "Page /students accessible" \
    "curl -sf http://192.168.47.10/students | grep -q etudiant"
check "cAdvisor running"           "docker inspect cadvisor   | grep -q '\"Running\": true'"
check "Node Exporter running"      "docker inspect node-exporter | grep -q '\"Running\": true'"
check "Alertmanager running"       "docker inspect alertmanager  | grep -q '\"Running\": true'"

echo ""
echo "════════════════════════════════════════════"
echo "  Résultat : ${pass} ✅  /  ${fail} ❌"
echo "════════════════════════════════════════════"
