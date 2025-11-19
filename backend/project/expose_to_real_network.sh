#!/bin/bash
# ==============================================================================
# expose_to_real_network.sh - VERSIÓN CORREGIDA
# ==============================================================================
# Expone la API a la red local usando la IP real de la VM
# ==============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}  🌐 EXPONIENDO API A RED LOCAL REAL${NC}"
echo -e "${GREEN}================================================================${NC}\n"

# ==================== PASO 1: Detectar IP Real ====================
echo -e "${CYAN}[PASO 1/6]${NC} Detectando IP de red local..."

# Detectar IP real (192.168.X.X o 10.X.X.X, excluyendo Docker/Minikube)
REAL_IP=$(ip addr show | grep "inet " | \
    grep -v "127.0.0.1" | \
    grep -v "172.17" | \
    grep -v "172.18" | \
    grep -v "172.19" | \
    grep -v "172.20" | \
    grep -v "172.21" | \
    grep -v "192.168.49" | \
    grep -oP '(?<=inet\s)\d+\.\d+\.\d+\.\d+' | \
    head -1)

if [ -z "$REAL_IP" ]; then
    echo -e "${RED}✗ No se pudo detectar IP de red local${NC}"
    echo "IPs disponibles:"
    ip addr show | grep "inet " | grep -v "127.0.0.1"
    exit 1
fi

echo -e "${GREEN}✓${NC} IP detectada: ${YELLOW}${REAL_IP}${NC}"

# Verificar que no sea una IP de Docker/Minikube
if [[ "$REAL_IP" =~ ^172\. ]] || [[ "$REAL_IP" == "192.168.49."* ]]; then
    echo -e "${RED}✗ IP detectada parece ser de Docker/Minikube${NC}"
    echo "Intenta con una IP de red local real (192.168.0.X o 10.0.X.X)"
    exit 1
fi

# ==================== PASO 2: Verificar Minikube ====================
echo -e "\n${CYAN}[PASO 2/6]${NC} Verificando Minikube..."

if ! minikube status | grep -q "Running"; then
    echo -e "${RED}✗ Minikube no está corriendo${NC}"
    exit 1
fi

MINIKUBE_IP=$(minikube ip)
echo -e "${GREEN}✓${NC} Minikube IP: ${MINIKUBE_IP}"

# Verificar NodePort
NODE_PORT=$(kubectl get svc middleware-citus-service -n citus -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "")
if [ -z "$NODE_PORT" ]; then
    echo -e "${RED}✗ Servicio NodePort no encontrado${NC}"
    echo -e "${YELLOW}Ejecuta: ./enable_nodeport.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} NodePort: ${NODE_PORT}"

# ==================== PASO 3: Detener Procesos Anteriores ====================
echo -e "\n${CYAN}[PASO 3/6]${NC} Limpiando procesos anteriores..."

# Detener socat
pkill -f "socat.*8000" 2>/dev/null && echo -e "${GREEN}✓${NC} Procesos socat detenidos" || echo -e "${YELLOW}ℹ${NC} No había procesos socat"

# Limpiar archivos PID
rm -f /tmp/socat_real.pid /tmp/socat_real_network.log

sleep 2

# ==================== PASO 4: Instalar socat ====================
echo -e "\n${CYAN}[PASO 4/6]${NC} Verificando socat..."

if ! command -v socat &> /dev/null; then
    echo -e "${YELLOW}Instalando socat...${NC}"
    sudo pacman -S --noconfirm socat
    echo -e "${GREEN}✓${NC} socat instalado"
else
    echo -e "${GREEN}✓${NC} socat ya está instalado"
fi

# ==================== PASO 5: Configurar Firewall ====================
echo -e "\n${CYAN}[PASO 5/6]${NC} Configurando firewall..."

HOST_PORT=8000

# Eliminar regla si existe (evitar duplicados)
sudo iptables -D INPUT -p tcp --dport ${HOST_PORT} -j ACCEPT 2>/dev/null || true

# Agregar regla nueva
sudo iptables -I INPUT -p tcp --dport ${HOST_PORT} -j ACCEPT
echo -e "${GREEN}✓${NC} Puerto ${HOST_PORT} permitido en firewall"

# ==================== PASO 6: Crear Port Forwarding ====================
echo -e "\n${CYAN}[PASO 6/6]${NC} Creando port forwarding..."

echo -e "${YELLOW}Configurando:${NC} ${REAL_IP}:${HOST_PORT} -> ${MINIKUBE_IP}:${NODE_PORT}"

# Iniciar socat en background
# bind=REAL_IP hace que escuche SOLO en esa IP (accesible desde red)
nohup sudo socat \
    TCP4-LISTEN:${HOST_PORT},bind=${REAL_IP},fork,reuseaddr \
    TCP4:${MINIKUBE_IP}:${NODE_PORT} \
    > /tmp/socat_real_network.log 2>&1 &

SOCAT_PID=$!
echo $SOCAT_PID > /tmp/socat_real.pid

# Esperar a que inicie
sleep 3

# Verificar que esté corriendo
if ! ps -p $SOCAT_PID > /dev/null 2>&1; then
    echo -e "${RED}✗ Error: socat no pudo iniciar${NC}"
    echo "Logs:"
    cat /tmp/socat_real_network.log
    exit 1
fi

echo -e "${GREEN}✓${NC} Port forwarding activo (PID: ${SOCAT_PID})"

# ==================== VERIFICACIÓN ====================
echo -e "\n${CYAN}Verificando conectividad...${NC}"
sleep 2

# Test 1: Desde localhost
if curl -s -f "http://${REAL_IP}:${HOST_PORT}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Accesible desde ${REAL_IP}"
else
    echo -e "${YELLOW}⚠${NC} No se pudo verificar (puede ser normal si el servicio está iniciando)"
fi

# ==================== INFORMACIÓN FINAL ====================
echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  ✓ SISTEMA EXPUESTO A RED LOCAL${NC}"
echo -e "${GREEN}================================================================${NC}\n"

echo -e "${MAGENTA}📱 ACCESO DESDE DISPOSITIVOS MÓVILES:${NC}"
echo -e "  ${CYAN}URL Base:${NC}      ${YELLOW}http://${REAL_IP}:${HOST_PORT}${NC}"
echo -e "  ${CYAN}Health Check:${NC}  ${YELLOW}http://${REAL_IP}:${HOST_PORT}/health${NC}"
echo -e "  ${CYAN}Swagger UI:${NC}    ${YELLOW}http://${REAL_IP}:${HOST_PORT}/docs${NC}"
echo -e "  ${CYAN}ReDoc:${NC}         ${YELLOW}http://${REAL_IP}:${HOST_PORT}/redoc${NC}"

echo -e "\n${CYAN}📱 INSTRUCCIONES PARA SMARTPHONE/TABLET:${NC}"
echo -e "  1. Conecta tu dispositivo a la misma red WiFi"
echo -e "  2. Abre el navegador"
echo -e "  3. Ingresa: ${YELLOW}http://${REAL_IP}:${HOST_PORT}/docs${NC}"

echo -e "\n${CYAN}🧪 PROBAR DESDE OTRO DISPOSITIVO:${NC}"
echo -e "  ${YELLOW}curl http://${REAL_IP}:${HOST_PORT}/health${NC}"

echo -e "\n${CYAN}🔧 GESTIÓN:${NC}"
echo -e "  ${YELLOW}Ver logs:${NC}      tail -f /tmp/socat_real_network.log"
echo -e "  ${YELLOW}Ver proceso:${NC}   ps aux | grep socat"
echo -e "  ${YELLOW}Detener:${NC}       kill \$(cat /tmp/socat_real.pid)"
echo -e "  ${YELLOW}Estado:${NC}        sudo netstat -tulnp | grep ${HOST_PORT}"

echo -e "\n${CYAN}💡 TROUBLESHOOTING:${NC}"
echo -e "  ${YELLOW}Si no puedes acceder desde móvil:${NC}"
echo -e "    1. Verifica que estén en la misma red WiFi"
echo -e "    2. Prueba hacer ping desde el móvil:"
echo -e "       ${CYAN}ping ${REAL_IP}${NC} (usa una app de ping)"
echo -e "    3. Verifica que no haya firewall en el router"

echo -e "\n${GREEN}¡Sistema listo para acceso desde red local!${NC}\n"

# Guardar información
cat > /tmp/network_access_info.txt << EOF
Sistema de Historia Clínica - Acceso Red Local
================================================================

Configuración:
- IP VM (Real):  ${REAL_IP}
- Puerto:        ${HOST_PORT}
- IP Minikube:   ${MINIKUBE_IP}
- NodePort:      ${NODE_PORT}
- PID socat:     ${SOCAT_PID}

URLs de Acceso:
- Base URL:      http://${REAL_IP}:${HOST_PORT}
- Swagger UI:    http://${REAL_IP}:${HOST_PORT}/docs
- Health Check:  http://${REAL_IP}:${HOST_PORT}/health

Para detener:
kill ${SOCAT_PID}

Fecha: $(date)
EOF

echo -e "${CYAN}Información guardada en:${NC} /tmp/network_access_info.txt"
