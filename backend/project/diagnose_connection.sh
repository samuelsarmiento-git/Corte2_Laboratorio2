#!/bin/bash
# diagnose_connection.sh - Diagnosticar problemas de conexión
# Guarda este archivo en: backend/project/diagnose_connection.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

NAMESPACE="citus"

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}  🔍 DIAGNÓSTICO DE CONEXIÓN - Historia Clínica${NC}"
echo -e "${CYAN}================================================================${NC}\n"

# ==================== TEST 1: PODS ====================
echo -e "${YELLOW}[TEST 1]${NC} Estado de los Pods"
kubectl get pods -n $NAMESPACE
echo ""

COORDINATOR_POD=$(kubectl get pod -n $NAMESPACE -l app=citus-coordinator -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
MIDDLEWARE_POD=$(kubectl get pod -n $NAMESPACE -l app=middleware-citus -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)

if [ -z "$COORDINATOR_POD" ]; then
    echo -e "${RED}✗ No se encontró el pod coordinator${NC}"
    exit 1
fi

if [ -z "$MIDDLEWARE_POD" ]; then
    echo -e "${RED}✗ No se encontró el pod middleware${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Coordinator Pod: $COORDINATOR_POD"
echo -e "${GREEN}✓${NC} Middleware Pod: $MIDDLEWARE_POD"
echo ""

# ==================== TEST 2: SERVICIOS ====================
echo -e "${YELLOW}[TEST 2]${NC} Estado de los Servicios"
kubectl get svc -n $NAMESPACE
echo ""

# ==================== TEST 3: SECRETS ====================
echo -e "${YELLOW}[TEST 3]${NC} Verificando Secrets"
echo "Secrets en namespace:"
kubectl get secrets -n $NAMESPACE

echo -e "\n${CYAN}Decodificando valores de app-secrets:${NC}"
kubectl get secret app-secrets -n $NAMESPACE -o jsonpath='{.data}' | python3 -c "
import json, sys, base64
data = json.load(sys.stdin)
for key, value in data.items():
    decoded = base64.b64decode(value).decode('utf-8')
    if 'PASSWORD' in key:
        print(f'{key}: *** (oculto)')
    else:
        print(f'{key}: {decoded}')
" 2>/dev/null || echo "Error decodificando secrets"
echo ""

# ==================== TEST 4: POSTGRESQL ====================
echo -e "${YELLOW}[TEST 4]${NC} Verificando PostgreSQL en Coordinator"
echo "Conectando a PostgreSQL..."
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -c "SELECT version();" 2>&1 | head -3
echo ""

echo "Verificando base de datos historiaclinica..."
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "\dt public.*" 2>&1 | grep -E "pacientes|usuarios" || echo "No se encontraron tablas"
echo ""

# ==================== TEST 5: CONECTIVIDAD ====================
echo -e "${YELLOW}[TEST 5]${NC} Verificando Conectividad Middleware -> Coordinator"
echo "Resolviendo DNS..."
kubectl exec -n $NAMESPACE $MIDDLEWARE_POD -- nslookup citus-coordinator 2>/dev/null || echo "nslookup no disponible"

echo -e "\nProbando conexión al puerto 5432..."
kubectl exec -n $NAMESPACE $MIDDLEWARE_POD -- timeout 5 bash -c "cat < /dev/null > /dev/tcp/citus-coordinator/5432" 2>&1 && echo -e "${GREEN}✓ Puerto 5432 accesible${NC}" || echo -e "${RED}✗ No se puede conectar al puerto 5432${NC}"
echo ""

# ==================== TEST 6: VARIABLES DE ENTORNO ====================
echo -e "${YELLOW}[TEST 6]${NC} Variables de Entorno del Middleware"
echo "Variables de conexión a BD:"
kubectl exec -n $NAMESPACE $MIDDLEWARE_POD -- env | grep -E "POSTGRES_|SECRET_" || echo "No se encontraron variables"
echo ""

# ==================== TEST 7: LOGS ====================
echo -e "${YELLOW}[TEST 7]${NC} Últimas líneas de logs del Middleware"
kubectl logs -n $NAMESPACE $MIDDLEWARE_POD --tail=20
echo ""

# ==================== TEST 8: PRUEBA DE CONEXIÓN PYTHON ====================
echo -e "${YELLOW}[TEST 8]${NC} Prueba de Conexión desde Python"
kubectl exec -n $NAMESPACE $MIDDLEWARE_POD -- python3 -c "
import os
from app.database import get_connection_info, test_connection

print('📊 Configuración de conexión:')
config = get_connection_info()
for key, value in config.items():
    print(f'  {key}: {value}')

print('\n🔌 Probando conexión...')
test_connection()
" 2>&1
echo ""

# ==================== RESUMEN ====================
echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}  📋 RESUMEN DEL DIAGNÓSTICO${NC}"
echo -e "${CYAN}================================================================${NC}"
echo ""
echo "Si todos los tests pasaron pero sigue habiendo error:"
echo "  1. Verifica que los secrets estén correctos"
echo "  2. Reconstruye la imagen del middleware"
echo "  3. Reinicia el pod del middleware"
echo ""
echo "Comandos útiles:"
echo "  ${YELLOW}kubectl logs -n citus $MIDDLEWARE_POD -f${NC}  # Ver logs en tiempo real"
echo "  ${YELLOW}kubectl delete pod -n citus $MIDDLEWARE_POD${NC}  # Reiniciar pod"
echo "  ${YELLOW}kubectl describe pod -n citus $MIDDLEWARE_POD${NC}  # Ver detalles del pod"
echo ""
