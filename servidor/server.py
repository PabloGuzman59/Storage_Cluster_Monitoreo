import socket
import threading
import json
import logging
import time
import os
from datetime import datetime, timezone
from database import Database
from config import CONFIG

# ── Logging ────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/server.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── Estado global del cluster ──────────────────────────────
# { client_id: { "conn": socket, "addr": tuple, "last_seen": float, "info": dict } }
connected_clients: dict = {}
clients_lock = threading.Lock()


class StorageClusterServer:
    def __init__(self):
        self.db = Database()
        self.host = CONFIG["server"]["host"]
        self.port = CONFIG["server"]["port"]
        self.max_clients = CONFIG["server"]["max_clients"]
        self.timeout_seconds = CONFIG["server"]["node_timeout"]
        self.server_socket = None
        self.running = False

    # ── Arranque ───────────────────────────────────────────
    def start(self):
        self.db.initialize()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(self.max_clients)
        self.running = True

        log.info(f"Servidor iniciado en {self.host}:{self.port} — esperando clientes...")

        # Hilo de watchdog: detecta nodos que dejan de reportar
        threading.Thread(target=self._watchdog, daemon=True).start()

        # Loop principal: acepta conexiones
        try:
            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
                    threading.Thread(
                        target=self._handle_client,
                        args=(conn, addr),
                        daemon=True
                    ).start()
                except OSError:
                    break
        except KeyboardInterrupt:
            log.info("Servidor detenido por el usuario.")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        log.info("Servidor cerrado.")

    # ── Manejo de cada cliente ─────────────────────────────
    def _handle_client(self, conn: socket.socket, addr: tuple):
        client_id = None
        log.info(f"Nueva conexión desde {addr}")

        try:
            conn.settimeout(CONFIG["server"]["socket_timeout"])
            buffer = ""

            while self.running:
                try:
                    data = conn.recv(4096).decode("utf-8")
                    if not data:
                        break

                    buffer += data
                    # Los mensajes están delimitados por '\n'
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            client_id = self._process_message(conn, addr, line, client_id)

                except socket.timeout:
                    continue
                except (ConnectionResetError, BrokenPipeError):
                    break

        except Exception as e:
            log.error(f"Error con cliente {addr}: {e}")
        finally:
            self._disconnect_client(client_id, addr, conn)

    def _process_message(self, conn, addr, raw: str, client_id) -> str:
        """Procesa un mensaje JSON recibido del cliente."""
        try:
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "register":
                client_id = self._register_client(conn, addr, msg)

            elif msg_type == "metrics":
                self._receive_metrics(conn, client_id, msg)

            elif msg_type == "ack":
                log.info(f"[{client_id}] ACK recibido: {msg.get('message_id', '?')}")

            else:
                log.warning(f"Tipo de mensaje desconocido: {msg_type}")

        except json.JSONDecodeError:
            log.warning(f"Mensaje malformado de {addr}: {raw[:80]}")

        return client_id

    # ── Registro de cliente ────────────────────────────────
    def _register_client(self, conn, addr, msg: dict) -> str:
        client_id = msg.get("client_id", f"node_{addr[0]}_{addr[1]}")
        region    = msg.get("region", "Desconocida")
        hostname  = msg.get("hostname", "unknown")

        with clients_lock:
            connected_clients[client_id] = {
                "conn":      conn,
                "addr":      addr,
                "last_seen": time.time(),
                "info":      msg,
                "region":    region,
                "hostname":  hostname,
            }

        self.db.upsert_node(client_id, region, hostname, addr[0])
        log.info(f"Cliente registrado: [{client_id}] región={region} host={hostname} ip={addr[0]}")

        # Confirmar registro
        self._send_to_client(conn, {
            "type":    "register_ack",
            "status":  "ok",
            "message": f"Bienvenido al cluster, {client_id}"
        })
        return client_id

    # ── Recepción de métricas ──────────────────────────────
    def _receive_metrics(self, conn, client_id: str, msg: dict):
        if not client_id:
            log.warning("Métricas recibidas sin registro previo, ignorando.")
            return

        metrics = msg.get("metrics", {})
        timestamp = msg.get("timestamp", datetime.now(timezone.utc).isoformat())

        with clients_lock:
            if client_id in connected_clients:
                connected_clients[client_id]["last_seen"] = time.time()
                connected_clients[client_id]["last_metrics"] = metrics

        self.db.save_metrics(client_id, metrics, timestamp)

        log.info(
            f"[{client_id}] Métricas: total={metrics.get('total_gb','?')}GB "
            f"usado={metrics.get('used_gb','?')}GB libre={metrics.get('free_gb','?')}GB"
        )

        # Confirmar recepción
        self._send_to_client(conn, {
            "type":      "metrics_ack",
            "status":    "ok",
            "timestamp": timestamp
        })

    # ── Envío de mensajes a clientes ───────────────────────
    def send_message_to_client(self, client_id: str, message: str) -> bool:
        """Envía un mensaje de texto a un cliente específico."""
        with clients_lock:
            client = connected_clients.get(client_id)

        if not client:
            log.warning(f"Cliente {client_id} no encontrado.")
            return False

        msg_id = f"msg_{int(time.time())}"
        payload = {
            "type":       "server_message",
            "message_id": msg_id,
            "content":    message,
            "timestamp":  datetime.now(timezone.utc).isoformat()
        }
        success = self._send_to_client(client["conn"], payload)
        if success:
            self.db.save_server_message(client_id, message, msg_id)
            log.info(f"Mensaje enviado a [{client_id}]: {message}")
        return success

    def broadcast_message(self, message: str):
        """Envía un mensaje a todos los clientes conectados."""
        with clients_lock:
            ids = list(connected_clients.keys())
        for cid in ids:
            self.send_message_to_client(cid, message)

    def _send_to_client(self, conn: socket.socket, payload: dict) -> bool:
        try:
            data = json.dumps(payload) + "\n"
            conn.sendall(data.encode("utf-8"))
            return True
        except Exception as e:
            log.error(f"Error al enviar mensaje: {e}")
            return False

    # ── Desconexión ────────────────────────────────────────
    def _disconnect_client(self, client_id, addr, conn):
        with clients_lock:
            if client_id and client_id in connected_clients:
                del connected_clients[client_id]

        if client_id:
            self.db.update_node_status(client_id, "disconnected")
            log.info(f"Cliente desconectado: [{client_id}] {addr}")
        else:
            log.info(f"Conexión cerrada: {addr}")

        try:
            conn.close()
        except Exception:
            pass
def _watchdog(self):
        log.info("Watchdog inteligente iniciado.")
        while self.running:
            time.sleep(CONFIG["server"]["watchdog_interval"])
            now = time.time()
            with clients_lock:
                snapshot = dict(connected_clients)

            for cid, info in snapshot.items():
                elapsed = now - info.get("last_seen", now)
                
                # Alerta por desconexión
                if elapsed > self.timeout_seconds:
                    log.error(f"[CRITICAL] Nodo '{cid}' ha perdido conexión.")
                    self.db.update_node_status(cid, "no_reporta")
                    continue 

                # Alerta por disco lleno (Tu prueba del 45%)
                metrics = info.get("last_metrics", {})
                utilization = float(metrics.get("utilization", 0))

                if utilization > 45.0:
                    msg_auto = f"AVISO AUTOMÁTICO: Uso de disco crítico ({utilization}%)."
                    
                    # ESTO ES LO QUE APARECERÁ EN EL FRONTEND:
                    log.warning(f"[ALERTA] Nodo {cid} superó el 45% de uso. Enviando orden.")
                    
                    # ESTO LLEGA AL CLIENTE (client.log):
                    self.send_message_to_client(cid, msg_auto)
    # ── Utilidades para el dashboard ──────────────────────
    def get_cluster_summary(self) -> dict:
        return self.db.get_cluster_summary()

    def get_all_nodes(self) -> list:
        return self.db.get_all_nodes()

    def get_node_history(self, client_id: str, limit: int = 50) -> list:
        return self.db.get_node_history(client_id, limit)


# Instancia global accesible desde Flask
server_instance: StorageClusterServer = None


def get_server() -> StorageClusterServer:
    global server_instance
    if server_instance is None:
        server_instance = StorageClusterServer()
    return server_instance


if __name__ == "__main__":
    srv = get_server()
    srv.start()