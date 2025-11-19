#!/bin/bash
# ==============================================================================
# expose_to_network.sh - Exponer Sistema a Red Local
# ==============================================================================
# Solución definitiva para acceso desde cualquier dispositivo en la red
#
# Método: Port forwarding del host hacia Minikube
# ==============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

NAMESPACE="citus"
HOST_PORT=8000
MINIKUBE_PORT=30800

echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}  🌐 EXPONIENDO SISTEMA A RED LOCAL${NC}"
echo -e "${GREEN}================================================================${NC}\n"

# ==================== PASO 1: Verificar Sistema ====================
echo -e "${CYAN}[PASO 1/5]${NC} Verificando sistema..."

if ! minikube status | grep -q "Running"; then
    echo -e "${RED}✗ Minikube no está corriendo${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Minikube corriendo"

MINIKUBE_IP=$(minikube ip)
echo -e "${CYAN}IP Minikube:${NC} $MINIKUBE_IP"

# Obtener IP del host (primera IP no-loopback)
HOST_IP=$(ip route get 1.1.1.1 | grep -oP 'src \K\S+')
echo -e "${CYAN}IP Host:${NC} $HOST_IP"

# Verificar NodePort
NODE_PORT=$(kubectl get svc middleware-citus-service -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "")
if [ -z "$NODE_PORT" ]; then
    echo -e "${RED}✗ Servicio NodePort no encontrado${NC}"
    echo -e "${YELLOW}Ejecuta primero: ./enable_nodeport.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} NodePort configurado: $NODE_PORT"

# ==================== PASO 2: Limpiar Reglas Anteriores ====================
echo -e "\n${CYAN}[PASO 2/5]${NC} Limpiando reglas iptables anteriores..."

# Eliminar reglas duplicadas de PREROUTING
sudo iptables -t nat -D PREROUTING -p tcp --dport 8000 -j DNAT --to-destination ${MINIKUBE_IP}:${MINIKUBE_PORT} 2>/dev/null || true
sudo iptables -t nat -D PREROUTING -p tcp --dport 8000 -j DNAT --to-destination ${MINIKUBE_IP}:${MINIKUBE_PORT} 2>/dev/null || true

# Eliminar reglas de POSTROUTING
sudo iptables -t nat -D POSTROUTING -p tcp -d ${MINIKUBE_IP} --dport ${MINIKUBE_PORT} -j MASQUERADE 2>/dev/null || true

echo -e "${GREEN}✓${NC} Reglas anteriores eliminadas"

# ==================== PASO 3: Detener Port-Forwards Existentes ====================
echo -e "\n${CYAN}[PASO 3/5]${NC} Deteniendo port-forwards conflictivos..."

pkill -f "port-forward.*8000" 2>/dev/null || true
pkill -f "socat.*8000" 2>/dev/null || true
sleep 2

echo -e "${GREEN}✓${NC} Port-forwards detenidos"

# ==================== PASO 4: Crear Port Forward ====================
echo -e "\n${CYAN}[PASO 4/5]${NC} Creando port forward al NodePort..."

# Usamos socat para hacer el forwarding (más estable que iptables)
if ! command -v socat &> /dev/null; then
    echo -e "${YELLOW}Instalando socat...${NC}"
    sudo pacman -S --noconfirm socat 2>/dev/null || \
    sudo apt-get install -y socat 2>/dev/null || \
    sudo yum install -y socat 2>/dev/null || true
fi

# Crear script de forwarding
cat > /tmp/port_forward_api.sh << 'EOSCRIPT'
#!/bin/bash
MINIKUBE_IP="$(minikube ip)"
NODE_PORT="30800"
HOST_PORT="8000"

echo "🔄 Port forwarding activo: 0.0.0.0:${HOST_PORT} -> ${MINIKUBE_IP}:${NODE_PORT}"
echo "Presiona Ctrl+C para detener"

sudo socat TCP4-LISTEN:${HOST_PORT},fork,reuseaddr TCP4:${MINIKUBE_IP}:${NODE_PORT}
EOSCRIPT

chmod +x /tmp/port_forward_api.sh

# Iniciar en background con nohup
nohup /tmp/port_forward_api.sh > /tmp/port_forward.log 2>&1 &
FORWARD_PID=$!
sleep 3

# Verificar que el proceso esté corriendo
if ps -p $FORWARD_PID > /dev/null; then
    echo -e "${GREEN}✓${NC} Port forward activo (PID: $FORWARD_PID)"
    echo "$FORWARD_PID" > /tmp/port_forward.pid
else
    echo -e "${RED}✗ Error iniciando port forward${NC}"
    cat /tmp/port_forward.log
    exit 1
fi

# ==================== PASO 5: Verificar Conectividad ====================
echo -e "\n${CYAN}[PASO 5/5]${NC} Verificando conectividad..."

# Esperar 5 segundos para que el forwarding se estabilice
echo "⏳ Esperando 5 segundos..."
sleep 5

# Test 1: Desde localhost
echo -e "\n${CYAN}Test 1: Localhost${NC}"
if curl -s -f "http://localhost:${HOST_PORT}/health" > /dev/null; then
    echo -e "${GREEN}✓${NC} Accesible desde localhost"
else
    echo -e "${RED}✗${NC} No accesible desde localhost"
fi

# Test 2: Desde IP del host
echo -e "\n${CYAN}Test 2: IP del Host${NC}"
if curl -s -f "http://${HOST_IP}:${HOST_PORT}/health" > /dev/null; then
    echo -e "${GREEN}✓${NC} Accesible desde IP del host"
else
    echo -e "${YELLOW}⚠${NC} No accesible desde IP del host (puede ser firewall)"
fi

# ==================== CONFIGURAR FIREWALL ====================
echo -e "\n${CYAN}Configurando firewall...${NC}"

# Para Arch Linux (firewalld o iptables)
if command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --permanent --add-port=${HOST_PORT}/tcp 2>/dev/null || true
    sudo firewall-cmd --reload 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Firewalld configurado"
elif command -v ufw &> /dev/null; then
    sudo ufw allow ${HOST_PORT}/tcp 2>/dev/null || true
    echo -e "${GREEN}✓${NC} UFW configurado"
else
    # Usar iptables directamente
    sudo iptables -I INPUT -p tcp --dport ${HOST_PORT} -j ACCEPT 2>/dev/null || true
    echo -e "${GREEN}✓${NC} iptables configurado"
fi

# ==================== INFORMACIÓN FINAL ====================
echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  ✓ SISTEMA EXPUESTO A RED LOCAL${NC}"
echo -e "${GREEN}================================================================${NC}\n"

echo -e "${MAGENTA}📱 ACCESO DESDE OTROS DISPOSITIVOS:${NC}"
echo -e "  ${CYAN}URL Base:${NC}      ${YELLOW}http://${HOST_IP}:${HOST_PORT}${NC}"
echo -e "  ${CYAN}Health Check:${NC}  ${YELLOW}http://${HOST_IP}:${HOST_PORT}/health${NC}"
echo -e "  ${CYAN}Swagger UI:${NC}    ${YELLOW}http://${HOST_IP}:${HOST_PORT}/docs${NC}"
echo -e "  ${CYAN}ReDoc:${NC}         ${YELLOW}http://${HOST_IP}:${HOST_PORT}/redoc${NC}"

echo -e "\n${CYAN}📱 DESDE SMARTPHONE/TABLET:${NC}"
echo -e "  1. Conéctate a la misma red WiFi"
echo -e "  2. Abre el navegador"
echo -e "  3. Ingresa: ${YELLOW}http://${HOST_IP}:${HOST_PORT}/docs${NC}"

echo -e "\n${CYAN}🧪 PROBAR DESDE OTRO DISPOSITIVO:${NC}"
echo -e "  ${YELLOW}curl http://${HOST_IP}:${HOST_PORT}/health${NC}"

echo -e "\n${CYAN}🔧 GESTIÓN DEL PORT FORWARD:${NC}"
echo -e "  ${YELLOW}Ver logs:${NC}      tail -f /tmp/port_forward.log"
echo -e "  ${YELLOW}Detener:${NC}       kill \$(cat /tmp/port_forward.pid)"
echo -e "  ${YELLOW}Estado:${NC}        ps aux | grep socat"

echo -e "\n${CYAN}💡 TROUBLESHOOTING:${NC}"
echo -e "  ${YELLOW}Si no puedes acceder desde otro dispositivo:${NC}"
echo -e "    1. Verifica que estén en la misma red"
echo -e "    2. Desactiva temporalmente el firewall del host:"
echo -e "       ${CYAN}sudo systemctl stop firewalld${NC} (o similar)"
echo -e "    3. Verifica la IP del host:"
echo -e "       ${CYAN}ip addr show${NC}"
echo -e "    4. Prueba con ping desde el otro dispositivo:"
echo -e "       ${CYAN}ping ${HOST_IP}${NC}"

echo -e "\n${GREEN}¡Sistema accesible desde toda la red local!${NC}\n"

# Guardar información
cat > /tmp/network_access_info.txt << EOF
Sistema de Historia Clínica - Acceso Red Local
================================================================

Configuración:
- IP Host:       ${HOST_IP}
- Puerto Host:   ${HOST_PORT}
- IP Minikube:   ${MINIKUBE_IP}
- NodePort:      ${NODE_PORT}
- PID Forward:   ${FORWARD_PID}

URLs de Acceso:
- Base URL:      http://${HOST_IP}:${HOST_PORT}
- Swagger UI:    http://${HOST_IP}:${HOST_PORT}/docs
- Health Check:  http://${HOST_IP}:${HOST_PORT}/health

Para detener:
kill ${FORWARD_PID}

Fecha: $(date)
EOF

echo -e "${CYAN}Información guardada en:${NC} /tmp/network_access_info.txt"
