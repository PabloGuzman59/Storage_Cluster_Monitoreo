import threading
import os
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from server import get_server
from config import CONFIG

app = Flask(__name__)
app.secret_key = "storage_cluster_secret_2024"

def _srv():
    return get_server()

# ── RUTA PARA EL FRONTEND: Lee el archivo log ──────────────
@app.route("/api/logs")
def get_terminal_logs():
    """Lee el log del servidor para alimentar la terminal de React."""
    log_path = "logs/server.log"
    if not os.path.exists(log_path):
        return jsonify(["[SYSTEM] Inicializando sistema de monitoreo..."])
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            # Leemos las últimas 15 líneas para que la terminal sea fluida
            lines = f.readlines()
            # Limpiamos los saltos de línea
            return jsonify([line.strip() for line in lines[-15:]])
    except Exception as e:
        return jsonify([f"[ERROR] No se pudo leer el historial: {str(e)}"])

# ── Páginas ────────────────────────────────────────────────
@app.route("/")
def index():
    nodes   = _srv().get_all_nodes()
    summary = _srv().get_cluster_summary()
    return render_template("dashboard.html", nodes=nodes, summary=summary)

@app.route("/api/summary")
def api_summary():
    return jsonify(_srv().get_cluster_summary())

@app.route("/api/nodes")
def api_nodes():
    nodes = _srv().get_all_nodes()
    for n in nodes:
        for key in ("last_seen_at", "reported_at"):
            if n.get(key): n[key] = str(n[key])
        for key in ("total_gb", "used_gb", "free_gb", "utilization"):
            if n.get(key) is not None: n[key] = float(n[key])
    return jsonify(nodes)

# ── Envío de mensajes ──────────────────────────────────────
@app.route("/send_message", methods=["POST"])
def send_message():
    client_id = request.form.get("client_id", "").strip()
    message   = request.form.get("message", "").strip()

    if not message:
        flash("El mensaje no puede estar vacío.", "error")
        return redirect(url_for("index"))

    if client_id == "__broadcast__":
        _srv().broadcast_message(message)
    else:
        _srv().send_message_to_client(client_id, message)

    return redirect(url_for("index"))

def run_dashboard():
    cfg = CONFIG["flask"]
    app.run(host=cfg["host"], port=cfg["port"], debug=cfg["debug"], use_reloader=False)

if __name__ == "__main__":
    run_dashboard()