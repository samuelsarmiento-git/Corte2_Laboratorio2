#!/usr/bin/env python3
"""
prueba.py - Servidor Flask para Frontend
📌 Ubicación: frontend/prueba.py

Sirve archivos estáticos HTML del frontend y proporciona
conexión con la API FastAPI en el backend.

Uso:
    python3 prueba.py
    
Luego abrir en navegador:
    http://localhost:5000/login.html
"""

import os
import sys
from pathlib import Path
from flask import Flask, send_from_directory, render_template_string, jsonify
from flask_cors import CORS
import logging

# ==================== CONFIGURACIÓN BÁSICA ====================

# Configurar rutas
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / 'templates'
STATIC_DIR = BASE_DIR / 'static'

# Crear aplicación Flask
app = Flask(__name__, 
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path='/static'
)

# Configurar CORS
CORS(app)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== VALIDACIONES INICIALES ====================

def validar_estructura():
    """Valida que la estructura de carpetas sea correcta"""
    if not TEMPLATES_DIR.exists():
        logger.warning(f"⚠️  Directorio templates no existe: {TEMPLATES_DIR}")
        logger.info("📁 Creando directorio...")
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    
    if not STATIC_DIR.exists():
        logger.warning(f"⚠️  Directorio static no existe: {STATIC_DIR}")
        logger.info("📁 Creando directorio...")
        STATIC_DIR.mkdir(parents=True, exist_ok=True)
        (STATIC_DIR / 'js').mkdir(exist_ok=True)
        (STATIC_DIR / 'css').mkdir(exist_ok=True)
        (STATIC_DIR / 'img').mkdir(exist_ok=True)

# ==================== RUTAS PRINCIPALES ====================

@app.route('/')
def index():
    """Ruta raíz - redirige al login"""
    logger.info("📍 Acceso a raíz - redirigiendo a login")
    return send_from_directory(TEMPLATES_DIR, 'login.html')

@app.route('/login.html')
def login():
    """Página de inicio de sesión"""
    logger.info("🔐 Cargando login.html")
    return send_from_directory(TEMPLATES_DIR, 'login.html')

@app.route('/<filename>.html')
def serve_html(filename):
    """Sirve archivos HTML desde templates"""
    try:
        filepath = TEMPLATES_DIR / f"{filename}.html"
        
        if not filepath.exists():
            logger.warning(f"❌ Archivo no encontrado: {filepath}")
            return "Archivo no encontrado", 404
        
        logger.info(f"📄 Sirviendo: {filename}.html")
        return send_from_directory(TEMPLATES_DIR, f"{filename}.html")
        
    except Exception as e:
        logger.error(f"❌ Error sirviendo {filename}.html: {e}")
        return f"Error: {str(e)}", 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Sirve archivos estáticos (CSS, JS, imágenes)"""
    try:
        logger.debug(f"📦 Sirviendo estático: {filename}")
        return send_from_directory(STATIC_DIR, filename)
    except Exception as e:
        logger.warning(f"⚠️  No se encontró estático: {filename}")
        return "Archivo no encontrado", 404

@app.route('/api/config')
def get_config():
    """Retorna configuración del frontend (para validar conexiones)"""
    return jsonify({
        'frontend': {
            'version': '2.0.0',
            'base_url': 'http://localhost:5000',
            'templates': list(TEMPLATES_DIR.glob('*.html'))
        },
        'backend': {
            'api_url': 'http://192.168.49.2:30800',
            'endpoints': {
                'health': '/health',
                'login': '/token',
                'pacientes': '/pacientes'
            }
        }
    })

# ==================== MANEJO DE ERRORES ====================

@app.errorhandler(404)
def not_found(error):
    """Manejo de error 404"""
    logger.warning(f"404 - Recurso no encontrado: {error}")
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>404 - No Encontrado</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                background: white;
                color: #333;
                padding: 2rem;
                border-radius: 15px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }
            h1 { color: #e74c3c; font-size: 3rem; margin: 0; }
            p { color: #666; margin: 1rem 0; }
            a {
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 0.75rem 2rem;
                border-radius: 8px;
                text-decoration: none;
                margin-top: 1rem;
            }
            a:hover { background: #764ba2; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>404</h1>
            <p>La página que buscas no existe.</p>
            <a href="/">← Volver al inicio</a>
        </div>
    </body>
    </html>
    '''), 404

@app.errorhandler(500)
def server_error(error):
    """Manejo de error 500"""
    logger.error(f"500 - Error del servidor: {error}")
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>500 - Error del Servidor</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                background: white;
                color: #333;
                padding: 2rem;
                border-radius: 15px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }
            h1 { color: #e74c3c; font-size: 3rem; margin: 0; }
            p { color: #666; margin: 1rem 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>500</h1>
            <p>Error interno del servidor.</p>
        </div>
    </body>
    </html>
    '''), 500

# ==================== INICIALIZACIÓN ====================

def mostrar_informacion():
    """Muestra información de inicio"""
    print("\n" + "="*70)
    print("🏥 FRONTEND - SISTEMA DE HISTORIA CLÍNICA")
    print("="*70)
    
    print(f"""
📂 Configuración:
   • Base: {BASE_DIR}
   • Templates: {TEMPLATES_DIR}
   • Estáticos: {STATIC_DIR}

🌐 URLs disponibles:
   • http://localhost:5000/              (Raíz → Login)
   • http://localhost:5000/login.html    (Login)
   • http://localhost:5000/medico.html   (Panel Médico)
   • http://localhost:5000/paciente.html (Panel Paciente)
   • http://localhost:5000/admisionista.html (Panel Admisionista)
   • http://localhost:5000/panel_admin.html (Panel Admin)
   • http://localhost:5000/gestionar_usuarios.html (Gestion de Usuarios)
   • http://localhost:5000/reportes.html (Reportes)
   • http://localhost:5000/static/       (Recursos)

🔗 Backend (FastAPI):
   • URL: http://192.168.49.2:30800
   • Health: http://192.168.49.2:30800/health
   • Docs: http://192.168.49.2:30800/docs

⚙️  Configuración:
   • DEBUG: False
   • HOST: 0.0.0.0
   • PORT: 5000
   • CORS: Habilitado

📖 Comandos útiles:
   • Ver config: http://localhost:5000/api/config
   • Probar conexión: curl http://localhost:5000/health

✅ Servidor listo. Presiona Ctrl+C para detener.
""")
    print("="*70 + "\n")

if __name__ == '__main__':
    # Validar estructura
    validar_estructura()
    
    # Mostrar información
    mostrar_informacion()
    
    try:
        # Iniciar servidor
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            use_reloader=True,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor detenido por usuario.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)