import threading
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from server import get_server
from config import CONFIG

app = Flask(__name__)
app.secret_key = "storage_cluster_secret_2024"


def _srv():
    return get_server()


# ── Páginas ────────────────────────────────────────────────
@app.route("/")
def index():
    nodes   = _srv().get_all_nodes()
    summary = _srv().get_cluster_summary()
    return render_template("dashboard.html", nodes=nodes, summary=summary)


@app.route("/node/<client_id>")
def node_detail(client_id):
    history = _srv().get_node_history(client_id, limit=20)
    return render_template("node_detail.html", client_id=client_id, history=history)


# ── API JSON (para auto-refresh) ───────────────────────────
@app.route("/api/summary")
def api_summary():
    return jsonify(_srv().get_cluster_summary())


@app.route("/api/nodes")
def api_nodes():
    nodes = _srv().get_all_nodes()
    # Convertir datetime a string para JSON
    for n in nodes:
        for key in ("last_seen_at", "reported_at"):
            if n.get(key):
                n[key] = str(n[key])
        for key in ("total_gb", "used_gb", "free_gb", "utilization"):
            if n.get(key) is not None:
                n[key] = float(n[key])
    return jsonify(nodes)


@app.route("/api/node/<client_id>/history")
def api_node_history(client_id):
    limit = request.args.get("limit", 50, type=int)
    history = _srv().get_node_history(client_id, limit)
    for row in history:
        for key in ("reported_at",):
            if row.get(key):
                row[key] = str(row[key])
        for key in ("total_gb", "used_gb", "free_gb", "utilization"):
            if row.get(key) is not None:
                row[key] = float(row[key])
    return jsonify(history)


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
        flash(f"Mensaje enviado a todos los nodos: '{message}'", "success")
    else:
        ok = _srv().send_message_to_client(client_id, message)
        if ok:
            flash(f"Mensaje enviado a [{client_id}]: '{message}'", "success")
        else:
            flash(f"No se pudo enviar a [{client_id}]. ¿Está conectado?", "error")

    return redirect(url_for("index"))


def run_dashboard():
    cfg = CONFIG["flask"]
    app.run(host=cfg["host"], port=cfg["port"], debug=cfg["debug"], use_reloader=False)


if __name__ == "__main__":
    run_dashboard()
