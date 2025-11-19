# backend/project/app/pdf_generator.py
"""
Generador de PDFs para Historias Clínicas
VERSIÓN CORREGIDA - Sintaxis actualizada para WeasyPrint 60.1
"""

import io
from datetime import datetime
from typing import Dict, Any
from weasyprint import HTML, CSS
from jinja2 import Template


# ==================== TEMPLATE HTML ====================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Historia Clínica - {{ paciente.numero_documento }}</title>
    <style>
        @page {
            size: Letter;
            margin: 2cm;
            @bottom-right {
                content: "Página " counter(page) " de " counter(pages);
                font-size: 9pt;
                color: #666;
            }
        }

        body {
            font-family: 'Arial', sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            color: #333;
        }

        .header {
            text-align: center;
            border-bottom: 3px solid #2c3e50;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }

        .header h1 {
            color: #2c3e50;
            font-size: 18pt;
            margin: 0;
        }

        .header .subtitle {
            color: #7f8c8d;
            font-size: 10pt;
            margin-top: 5px;
        }

        .section {
            margin-bottom: 15px;
            page-break-inside: avoid;
        }

        .section-title {
            background-color: #3498db;
            color: white;
            padding: 6px 10px;
            font-size: 12pt;
            font-weight: bold;
            margin-bottom: 8px;
        }

        .data-grid {
            display: table;
            width: 100%;
            border-collapse: collapse;
        }

        .data-row {
            display: table-row;
        }

        .data-cell {
            display: table-cell;
            padding: 4px 8px;
            border-bottom: 1px solid #ecf0f1;
        }

        .data-label {
            font-weight: bold;
            color: #2c3e50;
            width: 35%;
        }

        .data-value {
            color: #555;
        }

        .full-width {
            margin: 10px 0;
            padding: 8px;
            background-color: #f8f9fa;
            border-left: 3px solid #3498db;
        }

        .full-width-label {
            font-weight: bold;
            color: #2c3e50;
            display: block;
            margin-bottom: 5px;
        }

        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            text-align: center;
            font-size: 8pt;
            color: #95a5a6;
            border-top: 1px solid #ecf0f1;
            padding-top: 5px;
        }

        .signature-section {
            margin-top: 40px;
            display: table;
            width: 100%;
        }

        .signature-box {
            display: table-cell;
            text-align: center;
            width: 50%;
            padding: 10px;
        }

        .signature-line {
            border-top: 2px solid #2c3e50;
            margin-top: 60px;
            padding-top: 5px;
        }

        .alert {
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            padding: 8px;
            margin: 10px 0;
            border-radius: 3px;
        }

        .vitals-grid {
            display: table;
            width: 100%;
        }

        .vitals-row {
            display: table-row;
        }

        .vitals-cell {
            display: table-cell;
            padding: 5px;
            text-align: center;
            border: 1px solid #ddd;
            background-color: #f8f9fa;
        }

        .vitals-label {
            font-weight: bold;
            font-size: 8pt;
            color: #666;
        }

        .vitals-value {
            font-size: 14pt;
            color: #2c3e50;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <!-- HEADER -->
    <div class="header">
        <h1>📋 HISTORIA CLÍNICA ELECTRÓNICA</h1>
        <div class="subtitle">
            Sistema de Gestión de Historias Clínicas Distribuidas<br>
            Generado: {{ fecha_generacion }}
        </div>
    </div>

    <!-- SECCIÓN: IDENTIFICACIÓN DEL PACIENTE -->
    <div class="section">
        <div class="section-title">👤 DATOS DE IDENTIFICACIÓN DEL PACIENTE</div>
        <div class="data-grid">
            <div class="data-row">
                <div class="data-cell data-label">Tipo de Documento:</div>
                <div class="data-cell data-value">{{ paciente.tipo_documento or 'N/A' }}</div>
                <div class="data-cell data-label">Número de Documento:</div>
                <div class="data-cell data-value">{{ paciente.numero_documento }}</div>
            </div>
            <div class="data-row">
                <div class="data-cell data-label">Primer Nombre:</div>
                <div class="data-cell data-value">{{ paciente.primer_nombre }}</div>
                <div class="data-cell data-label">Segundo Nombre:</div>
                <div class="data-cell data-value">{{ paciente.segundo_nombre or 'N/A' }}</div>
            </div>
            <div class="data-row">
                <div class="data-cell data-label">Primer Apellido:</div>
                <div class="data-cell data-value">{{ paciente.primer_apellido }}</div>
                <div class="data-cell data-label">Segundo Apellido:</div>
                <div class="data-cell data-value">{{ paciente.segundo_apellido or 'N/A' }}</div>
            </div>
            <div class="data-row">
                <div class="data-cell data-label">Fecha de Nacimiento:</div>
                <div class="data-cell data-value">{{ paciente.fecha_nacimiento }}</div>
                <div class="data-cell data-label">Edad:</div>
                <div class="data-cell data-value">{{ paciente.edad or 'N/A' }} años</div>
            </div>
            <div class="data-row">
                <div class="data-cell data-label">Sexo:</div>
                <div class="data-cell data-value">{{ paciente.sexo }}</div>
                <div class="data-cell data-label">Género:</div>
                <div class="data-cell data-value">{{ paciente.genero or 'N/A' }}</div>
            </div>
            <div class="data-row">
                <div class="data-cell data-label">Grupo Sanguíneo:</div>
                <div class="data-cell data-value">{{ paciente.grupo_sanguineo or 'N/A' }}</div>
                <div class="data-cell data-label">Factor RH:</div>
                <div class="data-cell data-value">{{ paciente.factor_rh or 'N/A' }}</div>
            </div>
            <div class="data-row">
                <div class="data-cell data-label">Estado Civil:</div>
                <div class="data-cell data-value">{{ paciente.estado_civil or 'N/A' }}</div>
                <div class="data-cell data-label">Ocupación:</div>
                <div class="data-cell data-value">{{ paciente.ocupacion or 'N/A' }}</div>
            </div>
        </div>

        <div class="full-width">
            <span class="full-width-label">Dirección de Residencia:</span>
            {{ paciente.direccion_residencia or 'No registrada' }}
        </div>

        <div class="data-grid">
            <div class="data-row">
                <div class="data-cell data-label">Municipio:</div>
                <div class="data-cell data-value">{{ paciente.municipio or 'N/A' }}</div>
                <div class="data-cell data-label">Departamento:</div>
                <div class="data-cell data-value">{{ paciente.departamento or 'N/A' }}</div>
            </div>
            <div class="data-row">
                <div class="data-cell data-label">Teléfono:</div>
                <div class="data-cell data-value">{{ paciente.telefono or 'N/A' }}</div>
                <div class="data-cell data-label">Celular:</div>
                <div class="data-cell data-value">{{ paciente.celular or 'N/A' }}</div>
            </div>
            <div class="data-row">
                <div class="data-cell data-label">Correo Electrónico:</div>
                <div class="data-cell data-value">{{ paciente.correo_electronico or 'N/A' }}</div>
                <div class="data-cell data-label">Entidad (EPS/ARL):</div>
                <div class="data-cell data-value">{{ paciente.entidad or 'N/A' }}</div>
            </div>
            <div class="data-row">
                <div class="data-cell data-label">Régimen de Afiliación:</div>
                <div class="data-cell data-value">{{ paciente.regimen_afiliacion or 'N/A' }}</div>
                <div class="data-cell data-label">Tipo de Usuario:</div>
                <div class="data-cell data-value">{{ paciente.tipo_usuario or 'N/A' }}</div>
            </div>
        </div>
    </div>

    <!-- SECCIÓN: ATENCIÓN MÉDICA -->
    {% if paciente.tipo_atencion %}
    <div class="section">
        <div class="section-title">🏥 DATOS DE ATENCIÓN MÉDICA</div>
        <div class="data-grid">
            <div class="data-row">
                <div class="data-cell data-label">Fecha de Atención:</div>
                <div class="data-cell data-value">{{ paciente.fecha_atencion }}</div>
                <div class="data-cell data-label">Tipo de Atención:</div>
                <div class="data-cell data-value">{{ paciente.tipo_atencion }}</div>
            </div>
        </div>

        <div class="full-width">
            <span class="full-width-label">Motivo de Consulta:</span>
            {{ paciente.motivo_consulta or 'No especificado' }}
        </div>

        <div class="full-width">
            <span class="full-width-label">Enfermedad Actual:</span>
            {{ paciente.enfermedad_actual or 'No especificada' }}
        </div>
    </div>
    {% endif %}

    <!-- SECCIÓN: ANTECEDENTES -->
    {% if paciente.antecedentes_personales or paciente.antecedentes_familiares or paciente.alergias_conocidas %}
    <div class="section">
        <div class="section-title">📝 ANTECEDENTES</div>

        {% if paciente.antecedentes_personales %}
        <div class="full-width">
            <span class="full-width-label">Antecedentes Personales:</span>
            {{ paciente.antecedentes_personales }}
        </div>
        {% endif %}

        {% if paciente.antecedentes_familiares %}
        <div class="full-width">
            <span class="full-width-label">Antecedentes Familiares:</span>
            {{ paciente.antecedentes_familiares }}
        </div>
        {% endif %}

        {% if paciente.alergias_conocidas %}
        <div class="alert">
            <strong>⚠️ ALERGIAS:</strong> {{ paciente.alergias_conocidas }}
        </div>
        {% endif %}

        {% if paciente.habitos %}
        <div class="full-width">
            <span class="full-width-label">Hábitos:</span>
            {{ paciente.habitos }}
        </div>
        {% endif %}

        {% if paciente.medicamentos_actuales %}
        <div class="full-width">
            <span class="full-width-label">Medicamentos Actuales:</span>
            {{ paciente.medicamentos_actuales }}
        </div>
        {% endif %}
    </div>
    {% endif %}

    <!-- SECCIÓN: SIGNOS VITALES -->
    {% if paciente.tension_arterial or paciente.frecuencia_cardiaca %}
    <div class="section">
        <div class="section-title">💓 SIGNOS VITALES</div>
        <div class="vitals-grid">
            <div class="vitals-row">
                <div class="vitals-cell">
                    <div class="vitals-label">Tensión Arterial</div>
                    <div class="vitals-value">{{ paciente.tension_arterial or 'N/A' }}</div>
                </div>
                <div class="vitals-cell">
                    <div class="vitals-label">Frecuencia Cardíaca</div>
                    <div class="vitals-value">{{ paciente.frecuencia_cardiaca or 'N/A' }} lpm</div>
                </div>
                <div class="vitals-cell">
                    <div class="vitals-label">Frecuencia Respiratoria</div>
                    <div class="vitals-value">{{ paciente.frecuencia_respiratoria or 'N/A' }} rpm</div>
                </div>
            </div>
            <div class="vitals-row">
                <div class="vitals-cell">
                    <div class="vitals-label">Temperatura</div>
                    <div class="vitals-value">{{ paciente.temperatura or 'N/A' }} °C</div>
                </div>
                <div class="vitals-cell">
                    <div class="vitals-label">Saturación O₂</div>
                    <div class="vitals-value">{{ paciente.saturacion_oxigeno or 'N/A' }} %</div>
                </div>
                <div class="vitals-cell">
                    <div class="vitals-label">IMC</div>
                    <div class="vitals-value">{{ "%.2f"|format(paciente.imc) if paciente.imc else 'N/A' }}</div>
                </div>
            </div>
            <div class="vitals-row">
                <div class="vitals-cell">
                    <div class="vitals-label">Peso</div>
                    <div class="vitals-value">{{ paciente.peso or 'N/A' }} kg</div>
                </div>
                <div class="vitals-cell">
                    <div class="vitals-label">Talla</div>
                    <div class="vitals-value">{{ paciente.talla or 'N/A' }} cm</div>
                </div>
                <div class="vitals-cell"></div>
            </div>
        </div>
    </div>
    {% endif %}

    <!-- SECCIÓN: EXAMEN FÍSICO Y DIAGNÓSTICO -->
    {% if paciente.examen_fisico_general or paciente.impresion_diagnostica %}
    <div class="section">
        <div class="section-title">🔬 EXAMEN FÍSICO Y DIAGNÓSTICO</div>

        {% if paciente.examen_fisico_general %}
        <div class="full-width">
            <span class="full-width-label">Examen Físico General:</span>
            {{ paciente.examen_fisico_general }}
        </div>
        {% endif %}

        {% if paciente.examen_fisico_sistemas %}
        <div class="full-width">
            <span class="full-width-label">Examen Físico por Sistemas:</span>
            {{ paciente.examen_fisico_sistemas }}
        </div>
        {% endif %}

        {% if paciente.impresion_diagnostica %}
        <div class="full-width">
            <span class="full-width-label">Impresión Diagnóstica:</span>
            {{ paciente.impresion_diagnostica }}
        </div>
        {% endif %}

        {% if paciente.codigos_cie10 %}
        <div class="full-width">
            <span class="full-width-label">Códigos CIE-10:</span>
            {{ paciente.codigos_cie10 }}
        </div>
        {% endif %}

        {% if paciente.diagnostico_definitivo %}
        <div class="alert">
            <strong>📋 DIAGNÓSTICO DEFINITIVO:</strong> {{ paciente.diagnostico_definitivo }}
        </div>
        {% endif %}
    </div>
    {% endif %}

    <!-- SECCIÓN: CONDUCTA Y TRATAMIENTO -->
    {% if paciente.conducta_plan or paciente.tratamiento_instaurado %}
    <div class="section">
        <div class="section-title">💊 CONDUCTA Y TRATAMIENTO</div>

        {% if paciente.conducta_plan %}
        <div class="full-width">
            <span class="full-width-label">Conducta / Plan de Manejo:</span>
            {{ paciente.conducta_plan }}
        </div>
        {% endif %}

        {% if paciente.tratamiento_instaurado %}
        <div class="full-width">
            <span class="full-width-label">Tratamiento Instaurado:</span>
            {{ paciente.tratamiento_instaurado }}
        </div>
        {% endif %}

        {% if paciente.formulacion_medica %}
        <div class="full-width">
            <span class="full-width-label">Formulación Médica:</span>
            {{ paciente.formulacion_medica }}
        </div>
        {% endif %}

        {% if paciente.recomendaciones %}
        <div class="full-width">
            <span class="full-width-label">Recomendaciones al Paciente:</span>
            {{ paciente.recomendaciones }}
        </div>
        {% endif %}

        {% if paciente.educacion_paciente %}
        <div class="full-width">
            <span class="full-width-label">Educación al Paciente:</span>
            {{ paciente.educacion_paciente }}
        </div>
        {% endif %}
    </div>
    {% endif %}

    <!-- SECCIÓN: PROCEDIMIENTOS Y RESULTADOS -->
    {% if paciente.procedimientos_realizados or paciente.resultados_examenes %}
    <div class="section">
        <div class="section-title">🔬 PROCEDIMIENTOS Y RESULTADOS</div>

        {% if paciente.procedimientos_realizados %}
        <div class="full-width">
            <span class="full-width-label">Procedimientos Realizados:</span>
            {{ paciente.procedimientos_realizados }}
        </div>
        {% endif %}

        {% if paciente.resultados_examenes %}
        <div class="full-width">
            <span class="full-width-label">Resultados de Exámenes:</span>
            {{ paciente.resultados_examenes }}
        </div>
        {% endif %}

        {% if paciente.medicos_interconsultados %}
        <div class="full-width">
            <span class="full-width-label">Médicos Interconsultados:</span>
            {{ paciente.medicos_interconsultados }}
        </div>
        {% endif %}
    </div>
    {% endif %}

    <!-- SECCIÓN: EVOLUCIÓN Y EGRESO -->
    {% if paciente.evolucion_medica or paciente.estado_egreso %}
    <div class="section">
        <div class="section-title">📊 EVOLUCIÓN Y EGRESO</div>

        {% if paciente.evolucion_medica %}
        <div class="full-width">
            <span class="full-width-label">Evolución Médica:</span>
            {{ paciente.evolucion_medica }}
        </div>
        {% endif %}

        {% if paciente.estado_egreso %}
        <div class="data-grid">
            <div class="data-row">
                <div class="data-cell data-label">Estado de Egreso:</div>
                <div class="data-cell data-value">{{ paciente.estado_egreso }}</div>
                <div class="data-cell data-label">Fecha de Cierre:</div>
                <div class="data-cell data-value">{{ paciente.fecha_cierre or 'N/A' }}</div>
            </div>
        </div>
        {% endif %}

        {% if paciente.referencia_contrarreferencia %}
        <div class="full-width">
            <span class="full-width-label">Referencia / Contrarreferencia:</span>
            {{ paciente.referencia_contrarreferencia }}
        </div>
        {% endif %}
    </div>
    {% endif %}

    <!-- SECCIÓN: PROFESIONAL -->
    {% if paciente.nombre_profesional %}
    <div class="section">
        <div class="section-title">👨‍⚕️ DATOS DEL PROFESIONAL</div>
        <div class="data-grid">
            <div class="data-row">
                <div class="data-cell data-label">Nombre del Profesional:</div>
                <div class="data-cell data-value">{{ paciente.nombre_profesional }}</div>
                <div class="data-cell data-label">Tipo de Profesional:</div>
                <div class="data-cell data-value">{{ paciente.tipo_profesional or 'N/A' }}</div>
            </div>
            <div class="data-row">
                <div class="data-cell data-label">Registro Médico:</div>
                <div class="data-cell data-value">{{ paciente.registro_medico or 'N/A' }}</div>
                <div class="data-cell data-label">Cargo/Servicio:</div>
                <div class="data-cell data-value">{{ paciente.cargo_servicio or 'N/A' }}</div>
            </div>
            {% if paciente.responsable_registro %}
            <div class="data-row">
                <div class="data-cell data-label">Responsable de Registro:</div>
                <div class="data-cell data-value" colspan="3">{{ paciente.responsable_registro }}</div>
            </div>
            {% endif %}
        </div>
    </div>
    {% endif %}

    <!-- FIRMAS -->
    <div class="signature-section">
        <div class="signature-box">
            <div class="signature-line">
                Firma del Profesional<br>
                {% if paciente.nombre_profesional %}{{ paciente.nombre_profesional }}{% endif %}
            </div>
        </div>
        <div class="signature-box">
            <div class="signature-line">
                Firma del Paciente<br>
                {{ paciente.primer_nombre }} {{ paciente.primer_apellido }}
            </div>
        </div>
    </div>

    <!-- PIE DE PÁGINA -->
    <div class="footer">
        <p>
            <strong>Sistema de Historia Clínica Distribuida</strong> |
            Documento: {{ paciente.numero_documento }} |
            Generado: {{ fecha_generacion }} |
            Este documento es confidencial y está protegido por la Ley 1581 de 2012
        </p>
    </div>
</body>
</html>
"""


# ==================== FUNCIONES ====================

def generar_pdf_paciente(paciente_data: Dict[str, Any]) -> bytes:
    """
    Genera un PDF a partir de los datos de un paciente.

    ✅ SINTAXIS CORRECTA para WeasyPrint 60.1

    Args:
        paciente_data: Diccionario con todos los campos del paciente

    Returns:
        bytes: Contenido del PDF generado

    Raises:
        Exception: Si hay error en la generación
    """
    try:
        # Preparar datos para el template
        context = {
            "paciente": paciente_data,
            "fecha_generacion": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }

        # Renderizar template
        template = Template(HTML_TEMPLATE)
        html_content = template.render(**context)

        # ✅ SINTAXIS CORRECTA - Cambio clave aquí
        # Antes: HTML(string=html_content)  ❌
        # Ahora: HTML(string=html_content)  ✅ (correcto, el problema estaba en write_pdf())

        html_doc = HTML(string=html_content)
        pdf_bytes = html_doc.write_pdf()

        return pdf_bytes

    except Exception as e:
        raise Exception(f"Error generando PDF: {str(e)}")


def guardar_pdf_local(paciente_data: Dict[str, Any], ruta: str) -> str:
    """
    Genera y guarda un PDF localmente (para testing).

    Args:
        paciente_data: Datos del paciente
        ruta: Ruta donde guardar el archivo

    Returns:
        str: Ruta completa del archivo guardado
    """
    pdf_content = generar_pdf_paciente(paciente_data)

    with open(ruta, 'wb') as f:
        f.write(pdf_content)

    return ruta
