from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import json, os, random
from flask import send_file
import reportlab

app = Flask(__name__)
app.secret_key = "clave_secreta_para_pruebas"

# === RUTAS DE ARCHIVOS JSON ===
BASE_DIR = os.path.dirname(__file__)
REGISTROS_PATH = os.path.join(BASE_DIR, "registros.json")
PACIENTES_PATH = os.path.join(BASE_DIR, "pacientes.json")
HISTORIAS_PATH = os.path.join(BASE_DIR, "historias_clinicas.json")


# === FUNCIONES AUXILIARES ===
def cargar_json(path):
    """Lee un JSON y siempre devuelve una lista válida."""
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except:
        return []


def guardar_json(path, data):
    """Guarda en JSON asegurando formato correcto."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# =====================================================
#                      LOGIN
# =====================================================
@app.route("/")
def home():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return redirect(url_for(session["rol"]))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]

        registros = cargar_json(REGISTROS_PATH)
        user = next((u for u in registros if u["usuario"] == usuario and u["contraseña"] == contraseña), None)

        if user:
            session["usuario"] = user["usuario"]
            session["rol"] = user["rol"]
            flash(f"Bienvenido {user['usuario']} ({user['rol']})", "success")
            return redirect(url_for(user["rol"]))
        else:
            flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("login"))


# =====================================================
#            REGISTRO DE USUARIOS
# =====================================================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json()
        registros = cargar_json(REGISTROS_PATH)

        if any(u["usuario"] == data["usuario"] for u in registros):
            return jsonify({"status": "error", "msg": "El usuario ya existe."}), 400

        registros.append(data)
        guardar_json(REGISTROS_PATH, registros)
        return jsonify({"status": "ok"}), 200

    return render_template("register.html")


# =====================================================
#                 PANEL MÉDICO
# =====================================================
@app.route("/medico")
def medico():
    if session.get("rol") != "medico":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("login"))
    return redirect(url_for("vista_medico"))


@app.route("/vista_medico")
def vista_medico():
    if session.get("rol") != "medico":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("login"))

    pacientes = cargar_json(PACIENTES_PATH)
    usuario = session.get("usuario")

    conteo = sum(1 for p in pacientes if p.get("medico") == usuario)

    return render_template("vista_medico.html", usuario=usuario, conteo=conteo)


# =====================================================
#       REGISTRO DE PACIENTE
# =====================================================
@app.route("/registrar_paciente")
def registrar_paciente():
    if session.get("rol") != "medico":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("login"))
    return render_template("registrar_paciente.html", usuario=session.get("usuario"))


@app.route("/guardar_paciente", methods=["POST"])
def guardar_paciente():
    data = request.get_json()

    data["medico"] = session.get("usuario")

    pacientes = cargar_json(PACIENTES_PATH)
    pacientes.append(data)
    guardar_json(PACIENTES_PATH, pacientes)

    return jsonify({"mensaje": "Paciente guardado correctamente"})


# =====================================================
#                VER IDS PACIENTES
# =====================================================
@app.route("/ver_ids_pacientes")
def ver_ids_pacientes():
    if session.get("rol") != "medico":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("login"))

    pacientes = cargar_json(PACIENTES_PATH)
    usuario = session.get("usuario")

    lista = [p for p in pacientes if p.get("medico") == usuario]

    return render_template("ver_ids_pacientes.html", pacientes=lista, usuario=usuario)


# API json
@app.route("/pacientes.json")
def pacientes_json():
    return jsonify(cargar_json(PACIENTES_PATH))


# =====================================================
#             VER HISTORIA CLÍNICA
# =====================================================
@app.route("/ver_historia_clinica")
def ver_historia_clinica():
    id_paciente = request.args.get("id") 

    pacientes = cargar_json(PACIENTES_PATH)
    paciente = next((p for p in pacientes if str(p["id"]) == str(id_paciente)), None)

    if not paciente:
        return "Paciente no encontrado", 404

    historias = cargar_json(HISTORIAS_PATH)
    historia = next((h for h in historias if str(h["idPaciente"]) == str(id_paciente)), None)

    return render_template("ver_historia_clinica.html",
                           paciente=paciente,
                           historia=historia)


# =====================================================
#             EDITAR HISTORIA CLÍNICA
# =====================================================
@app.route("/editar_historia_clinica")
def editar_historia_clinica():
    if session.get("rol") != "medico":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("login"))

    id_paciente = request.args.get("id")

    pacientes = cargar_json(PACIENTES_PATH)
    paciente = next((p for p in pacientes if str(p["id"]) == str(id_paciente)), None)

    historias = cargar_json(HISTORIAS_PATH)
    historia = next((h for h in historias if str(h["idPaciente"]) == str(id_paciente)), None)

    return render_template("editar_historia_clinica.html",
                           paciente=paciente,
                           historia=historia)


# =====================================================
#        GUARDAR HISTORIA CLÍNICA
# =====================================================
@app.route("/guardar_historia_clinica", methods=["POST"])
def guardar_historia_clinica():
    datos = request.get_json()

    historias = cargar_json(HISTORIAS_PATH)

    existente = next((h for h in historias if str(h["idPaciente"]) == str(datos["idPaciente"])), None)
    if existente:
        historias.remove(existente)

    historias.append(datos)
    guardar_json(HISTORIAS_PATH, historias)

    return jsonify({"status": "ok"})

# =====================================================
#             IMPRIMIR PDF
# =====================================================
@app.route("/imprimir_historia")
def imprimir_historia():
    id_paciente = request.args.get("id")

    pacientes = cargar_json(PACIENTES_PATH)
    historias = cargar_json(HISTORIAS_PATH)

    paciente = next((p for p in pacientes if str(p["id"]) == str(id_paciente)), None)
    historia = next((h for h in historias if str(h["idPaciente"]) == str(id_paciente)), None)

    if not paciente:
        return "Paciente no encontrado", 404

    # Ruta correcta al logo en static
    logo_path = url_for("static", filename="img/logo_medico.png")

    return render_template(
        "historia_pdf.html",
        paciente=paciente,
        historia=historia,
        logo_path=logo_path
    )





# =====================================================
#                    MAIN
# =====================================================
if __name__ == "__main__":
    app.run(debug=True)
