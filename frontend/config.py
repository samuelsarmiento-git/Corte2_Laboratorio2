import os

# Configuración de conexión con Backend FastAPI
class Config:
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", 30))
    DEBUG = os.getenv("DEBUG", "False") == "True"
    
    # Endpoints principales
    ENDPOINTS = {
        "login": "/token",
        "me": "/me",
        "pacientes": "/pacientes",
        "paciente_por_doc": "/pacientes/{numero_documento}",
        "crear_paciente": "/pacientes",
        "actualizar_paciente": "/pacientes/{numero_documento}",
        "buscar_pacientes": "/pacientes/buscar/query",
        "exportar_pdf": "/pacientes/{numero_documento}/pdf",
        "usuarios": "/usuarios",
        "health": "/health",
    }