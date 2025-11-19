"""
Cliente para comunicarse con el Backend FastAPI
"""
import requests
from config import BACKEND_API_URL, REQUEST_TIMEOUT
from typing import Optional, Dict, List

class BackendClient:
    def __init__(self):
        self.base_url = BACKEND_API_URL
        self.timeout = REQUEST_TIMEOUT
        self.token = None
    
    def _get_headers(self):
        """Obtiene headers con token si está disponible"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def health_check(self) -> Dict:
        """Verifica si el backend está disponible"""
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            return {
                "success": True,
                "data": response.json(),
                "status_code": response.status_code
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "status_code": 503
            }
    
    def login(self, username: str, password: str) -> Dict:
        """
        Obtiene token JWT del backend
        """
        try:
            response = requests.post(
                f"{self.base_url}/token",
                json={"username": username, "password": password},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                return {
                    "success": True,
                    "token": self.token,
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "error": "Credenciales inválidas",
                    "status_code": response.status_code
                }
        
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Error de conexión: {str(e)}",
                "status_code": 503
            }
    
    def get_paciente(self, paciente_id: int) -> Dict:
        """
        Obtiene datos de un paciente del backend
        """
        try:
            response = requests.get(
                f"{self.base_url}/paciente/{paciente_id}",
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": "Paciente no encontrado",
                    "status_code": 404
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "error": "Token inválido o expirado",
                    "status_code": 401
                }
            else:
                return {
                    "success": False,
                    "error": "Error al obtener paciente",
                    "status_code": response.status_code
                }
        
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Error de conexión: {str(e)}",
                "status_code": 503
            }
    
    def list_pacientes(self, limit: int = 10) -> Dict:
        """
        Lista todos los pacientes
        """
        try:
            response = requests.get(
                f"{self.base_url}/pacientes",
                params={"limit": limit},
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "error": "Token inválido o expirado",
                    "status_code": 401
                }
            else:
                return {
                    "success": False,
                    "error": "Error al listar pacientes",
                    "status_code": response.status_code
                }
        
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Error de conexión: {str(e)}",
                "status_code": 503
            }
    
    def create_paciente(self, paciente_data: Dict) -> Dict:
        """
        Crea un nuevo paciente (cuando se implemente en el backend)
        """
        try:
            response = requests.post(
                f"{self.base_url}/pacientes",
                json=paciente_data,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 201:
                return {
                    "success": True,
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": "Error al crear paciente",
                    "status_code": response.status_code
                }
        
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Error de conexión: {str(e)}",
                "status_code": 503
            }

# Instancia global del cliente
backend_client = BackendClient()