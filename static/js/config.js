/**
 * config.js - Configuración Global del Frontend
 * 📌 Ubicación: frontend/static/js/config.js
 * 
 * Sincroniza con Backend FastAPI + PostgreSQL
 */

// ==================== CONFIGURACIÓN DE LA API ====================

const API_CONFIG = {
    // 🔧 CAMBIAR SEGÚN TU ENTORNO:
    
    // Opción 1: Localhost (si haces kubectl port-forward)
    //BASE_URL: 'http://localhost:8000',
    
    // Opción 2: Minikube con NodePort (RECOMENDADO)
    BASE_URL: 'http://192.168.49.2:30800',
    
    // Opción 3: Red local con IP de tu máquina
    // BASE_URL: 'http://TU_IP_LOCAL:8000',
    
    // Opción 4: Producción
    // BASE_URL: 'https://api.tudominio.com',
    
    // Timeouts
    TIMEOUT: 30000, // 30 segundos
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000, // 1 segundo
};

// ==================== ENUMS Y CONSTANTES ====================

const ROLES = {
    ADMIN: 'admin',
    MEDICO: 'medico',
    ADMISIONISTA: 'admisionista',
    RESULTADOS: 'resultados',
    PACIENTE: 'paciente'
};

const ENDPOINTS = {
    // Autenticación
    LOGIN: '/token',
    ME: '/me',
    
    // Pacientes
    PACIENTES_LIST: '/pacientes',
    PACIENTES_DETAIL: (doc) => `/pacientes/${doc}`,
    PACIENTES_SEARCH: '/pacientes/buscar/query',
    PACIENTES_CREATE: '/pacientes',
    PACIENTES_UPDATE: (doc) => `/pacientes/${doc}`,
    PACIENTES_DELETE: (doc) => `/pacientes/${doc}`,
    
    // PDF
    PACIENTES_PDF: (doc) => `/pacientes/${doc}/pdf`,
    
    // Usuarios
    USUARIOS_LIST: '/usuarios',
    USUARIOS_CREATE: '/usuarios',
    
    // Sistema
    HEALTH: '/health',
    ESTADISTICAS: '/estadisticas',
};

const TIPOS_DOCUMENTO = {
    CC: 'CC - Cédula de Ciudadanía',
    TI: 'TI - Tarjeta de Identidad',
    CE: 'CE - Cédula de Extranjería',
    PA: 'PA - Pasaporte',
    RC: 'RC - Registro Civil'
};

const GRUPOS_SANGUINEOS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];

const TIPOS_ATENCION = [
    'Urgencias',
    'Consulta Externa',
    'Hospitalizacion',
    'Cirugia',
    'Procedimiento'
];

// ==================== UTILIDADES DE AUTENTICACIÓN ====================

const AUTH_UTILS = {
    /**
     * Obtiene el token almacenado
     */
    getToken() {
        return sessionStorage.getItem('auth_token');
    },

    /**
     * Obtiene el usuario almacenado
     */
    getUser() {
        const user = sessionStorage.getItem('auth_user');
        return user ? JSON.parse(user) : null;
    },

    /**
     * Obtiene toda la información de autenticación
     */
    getAuthInfo() {
        return {
            token: this.getToken(),
            user: this.getUser(),
            isAuthenticated: this.isAuthenticated()
        };
    },

    /**
     * Verifica si el usuario está autenticado
     */
    isAuthenticated() {
        const token = this.getToken();
        const user = this.getUser();
        return !!(token && user && user.id);
    },

    /**
     * Guarda credenciales después del login
     */
    saveAuth(token, user) {
        sessionStorage.setItem('auth_token', token);
        sessionStorage.setItem('auth_user', JSON.stringify(user));
        console.log('✅ Credenciales guardadas:', user.username);
    },

    /**
     * Limpia la sesión (logout)
     */
    clearAuth() {
        SESSION_STATUS_UTILS.stopTracking();
        sessionStorage.removeItem('auth_token');
        sessionStorage.removeItem('auth_user');
        console.log('🔓 Sesión cerrada');
    },

    /**
     * Valida si el token es válido (básico)
     */
    isTokenValid() {
        const token = this.getToken();
        if (!token) return false;
        
        try {
            // JWT tiene 3 partes separadas por puntos
            const parts = token.split('.');
            if (parts.length !== 3) return false;
            
            // Decodificar payload (segunda parte)
            const payload = JSON.parse(atob(parts[1]));
            
            // Verificar expiración
            if (payload.exp) {
                const now = Math.floor(Date.now() / 1000);
                if (now > payload.exp) {
                    console.warn('⚠️ Token expirado');
                    return false;
                }
            }
            
            return true;
        } catch (error) {
            console.error('❌ Error validando token:', error);
            return false;
        }
    },

    /**
     * Obtiene información del token (sin validar firma)
     */
    getTokenInfo() {
        const token = this.getToken();
        if (!token) return null;
        
        try {
            const parts = token.split('.');
            if (parts.length !== 3) return null;
            
            const payload = JSON.parse(atob(parts[1]));
            return {
                username: payload.sub,
                rol: payload.rol,
                userId: payload.user_id,
                issuedAt: new Date(payload.iat * 1000),
                expiresAt: new Date(payload.exp * 1000),
                expiresIn: Math.floor((payload.exp * 1000 - Date.now()) / 1000)
            };
        } catch (error) {
            console.error('❌ Error decodificando token:', error);
            return null;
        }
    }
};

// ==================== UTILIDADES DE API ====================

const API_UTILS = {
    /**
     * Construir headers autenticados
     */
    getHeaders(options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...options
        };

        const token = AUTH_UTILS.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        return headers;
    },

    /**
     * Hacer petición autenticada con reintentos
     */
    async fetchWithRetry(endpoint, options = {}, attempt = 1) {
        try {
            const url = `${API_CONFIG.BASE_URL}${endpoint}`;
            const timeout = new Promise((_, reject) =>
                setTimeout(() => reject(new Error('Request timeout')), API_CONFIG.TIMEOUT)
            );

            const response = await Promise.race([
                fetch(url, {
                    ...options,
                    headers: this.getHeaders(options.headers || {})
                }),
                timeout
            ]);

            // Si el token expiró (401), limpiar sesión y redirigir
            if (response.status === 401) {
                console.warn('⚠️ Token expirado o inválido');
                AUTH_UTILS.clearAuth();
                window.location.href = 'login.html';
                return null;
            }

            // Si hay error de servidor (5xx) y no es el último intento, reintentar
            if (response.status >= 500 && attempt < API_CONFIG.RETRY_ATTEMPTS) {
                console.warn(`⚠️ Error del servidor, reintentando (${attempt}/${API_CONFIG.RETRY_ATTEMPTS})...`);
                await this.delay(API_CONFIG.RETRY_DELAY * attempt);
                return this.fetchWithRetry(endpoint, options, attempt + 1);
            }

            return response;

        } catch (error) {
            if (attempt < API_CONFIG.RETRY_ATTEMPTS) {
                console.warn(`⚠️ Error de conexión, reintentando (${attempt}/${API_CONFIG.RETRY_ATTEMPTS})...`);
                await this.delay(API_CONFIG.RETRY_DELAY * attempt);
                return this.fetchWithRetry(endpoint, options, attempt + 1);
            }
            throw error;
        }
    },

    /**
     * Esperar cierto tiempo (para reintentos)
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    /**
     * Petición GET
     */
    async get(endpoint) {
        try {
            const response = await this.fetchWithRetry(endpoint, { method: 'GET' });
            if (!response) return null;
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`❌ GET ${endpoint}:`, error);
            throw error;
        }
    },

    /**
     * Petición POST
     */
    async post(endpoint, data) {
        try {
            const response = await this.fetchWithRetry(endpoint, {
                method: 'POST',
                body: JSON.stringify(data)
            });
            if (!response) return null;

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`❌ POST ${endpoint}:`, error);
            throw error;
        }
    },

    /**
     * Petición PUT
     */
    async put(endpoint, data) {
        try {
            const response = await this.fetchWithRetry(endpoint, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
            if (!response) return null;

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`❌ PUT ${endpoint}:`, error);
            throw error;
        }
    },

    /**
     * Petición DELETE
     */
    async delete(endpoint) {
        try {
            const response = await this.fetchWithRetry(endpoint, { method: 'DELETE' });
            if (!response) return null;

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`❌ DELETE ${endpoint}:`, error);
            throw error;
        }
    },

    /**
     * Descargar archivo (PDF, etc)
     */
    async downloadFile(endpoint, filename) {
        try {
            const response = await this.fetchWithRetry(endpoint, { method: 'GET' });
            if (!response) return false;

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename || 'download';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();

            return true;
        } catch (error) {
            console.error(`❌ Descarga ${endpoint}:`, error);
            throw error;
        }
    }
};

// ==================== UTILIDADES DE INTERFAZ ====================

const UI_UTILS = {
    /**
     * Mostrar alerta
     */
    showAlert(message, type = 'info', duration = 5000) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <span>${this.getIconForType(type)}</span>
                <span>${message}</span>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        let container = document.getElementById('alertContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'alertContainer';
            container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
            document.body.appendChild(container);
        }

        container.appendChild(alertDiv);

        if (duration > 0) {
            setTimeout(() => alertDiv.remove(), duration);
        }

        return alertDiv;
    },

    /**
     * Obtener icono por tipo de alerta
     */
    getIconForType(type) {
        const icons = {
            'success': '✅',
            'danger': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        };
        return icons[type] || '📌';
    },

    /**
     * Mostrar modal de confirmación
     */
    async confirm(message, title = 'Confirmación') {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">${message}</div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                            <button type="button" class="btn btn-primary" id="confirmBtn">Aceptar</button>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
            const bootstrapModal = new bootstrap.Modal(modal);

            document.getElementById('confirmBtn').addEventListener('click', () => {
                bootstrapModal.hide();
                resolve(true);
            });

            modal.addEventListener('hidden.bs.modal', () => {
                modal.remove();
                resolve(false);
            });

            bootstrapModal.show();
        });
    },

    /**
     * Mostrar loading
     */
    showLoading(message = 'Cargando...') {
        const div = document.createElement('div');
        div.id = 'loadingOverlay';
        div.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;
        div.innerHTML = `
            <div style="text-align: center; background: white; padding: 2rem; border-radius: 10px;">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Cargando...</span>
                </div>
                <p class="text-muted">${message}</p>
            </div>
        `;
        document.body.appendChild(div);
    },

    /**
     * Ocultar loading
     */
    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) overlay.remove();
    },

    /**
     * Formatear fecha
     */
    formatDate(dateString) {
        if (!dateString) return 'N/A';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('es-CO', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            });
        } catch {
            return dateString;
        }
    },

    /**
     * Formatear fecha y hora
     */
    formatDateTime(dateString) {
        if (!dateString) return 'N/A';
        try {
            const date = new Date(dateString);
            return date.toLocaleString('es-CO', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return dateString;
        }
    }
};

// ==================== GESTIÓN DE ESTADO DE SESIÓN ====================

const SESSION_STATUS_UTILS = {
    ACTIVE_USERS_KEY: 'activeUsers',
    HEARTBEAT_INTERVAL: 15000, // 15 seconds
    USER_TIMEOUT: 35000, // 35 seconds, slightly more than 2x heartbeat
    intervalId: null,

    _getUsers() {
        try {
            const users = localStorage.getItem(this.ACTIVE_USERS_KEY);
            return users ? JSON.parse(users) : {};
        } catch (e) {
            console.error("Error reading active users from localStorage", e);
            return {};
        }
    },

    _saveUsers(users) {
        try {
            localStorage.setItem(this.ACTIVE_USERS_KEY, JSON.stringify(users));
        } catch(e) {
            console.error("Error saving active users to localStorage", e);
        }
    },

    startTracking() {
        const user = AUTH_UTILS.getUser();
        if (!user || !user.id) return;
        
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }

        const updateStatus = () => {
            const users = this._getUsers();
            users[user.id] = { lastSeen: Date.now(), rol: user.rol };
            this._saveUsers(users);
        };

        updateStatus(); // Initial update
        this.intervalId = setInterval(updateStatus, this.HEARTBEAT_INTERVAL);

        window.addEventListener('beforeunload', () => {
            this.stopTracking();
        });
    },

    stopTracking() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        const user = AUTH_UTILS.getUser();
        // Use a locally stored user if available, as AUTH_UTILS might be cleared already
        const userId = user ? user.id : (JSON.parse(sessionStorage.getItem('auth_user')) || {}).id;
        if (!userId) return;
        
        const users = this._getUsers();
        delete users[userId];
        this._saveUsers(users);
    },

    getActiveUserIds() {
        const users = this._getUsers();
        const activeUserIds = [];
        const now = Date.now();

        const cleanedUsers = {};
        for (const userId in users) {
            if (now - users[userId].lastSeen < this.USER_TIMEOUT) {
                activeUserIds.push(parseInt(userId, 10));
                cleanedUsers[userId] = users[userId];
            }
        }
        
        if (Object.keys(cleanedUsers).length < Object.keys(users).length) {
            this._saveUsers(cleanedUsers);
        }

        return activeUserIds;
    }
};

// ==================== VALIDACIÓN DE ACCESO ===================

const ACCESS_CONTROL = {
    /**
     * Requiere autenticación
     */
    requireAuth(redirectTo = 'login.html') {
        if (!AUTH_UTILS.isAuthenticated()) {
            window.location.href = redirectTo;
            return false;
        }
        return true;
    },

    /**
     * Requiere rol específico
     */
    requireRole(requiredRoles, redirectTo = 'login.html') {
        const user = AUTH_UTILS.getUser();
        
        if (!user) {
            window.location.href = redirectTo;
            return false;
        }

        const roles = Array.isArray(requiredRoles) ? requiredRoles : [requiredRoles];
        
        if (!roles.includes(user.rol)) {
            UI_UTILS.showAlert('❌ Acceso denegado. Rol insuficiente.', 'danger');
            setTimeout(() => window.location.href = redirectTo, 2000);
            return false;
        }

        return true;
    },

    /**
     * Verifica si el usuario puede acceder a un paciente
     */
    canAccessPatient(documentoPaciente) {
        const user = AUTH_UTILS.getUser();
        
        // Admin y staff pueden acceder a todos
        if ([ROLES.ADMIN, ROLES.MEDICO, ROLES.ADMISIONISTA, ROLES.RESULTADOS].includes(user.rol)) {
            return true;
        }

        // Paciente solo su propia historia
        if (user.rol === ROLES.PACIENTE) {
            return user.documento_vinculado === documentoPaciente;
        }

        return false;
    }
};

// ==================== INICIALIZACIÓN ====================

console.log('✅ Config.js cargado');
console.log('📡 API URL:', API_CONFIG.BASE_URL);
console.log('🔐 Token válido:', AUTH_UTILS.isTokenValid());

// Exportar para uso en otros archivos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        API_CONFIG,
        ROLES,
        ENDPOINTS,
        AUTH_UTILS,
        API_UTILS,
        UI_UTILS,
        ACCESS_CONTROL,
        SESSION_STATUS_UTILS
    };
}