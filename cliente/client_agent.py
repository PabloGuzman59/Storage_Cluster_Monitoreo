"""
=============================================================================
STORAGE CLUSTER MONITOR - AGENTE CLIENTE (Nodo Regional)
Versión: 2.1.0  
=============================================================================
"""

import socket
import threading
import json
import sys
from datetime import datetime

from disk_collector import DiskCollector
from iops_simulator import IOPSSimulator
from log_manager    import LogManager
from config_manager import ConfigManager

MSG_TYPE_METRICS  = "metrics"
MSG_TYPE_ACK      = "ack"
MSG_TYPE_REGISTER = "register"


class MessageHandler:
    def __init__(self, log_manager, agent_ref):
        self.log   = log_manager
        self.agent = agent_ref

    def handle(self, raw: str, conn: socket.socket):
        timestamp  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_id = None
        content    = raw

        try:
            data       = json.loads(raw)
            message_id = data.get("message_id")
            content    = data.get("content", raw)
        except json.JSONDecodeError:
            pass

        self.log.write(f"[SERVER→CLIENT] {timestamp} | {content}")

        # [EXT-4] Descomentear si el docente pide cambio de intervalo dinámico:
        # if content.startswith("SET_INTERVAL:"):
        #     try:
        #         self.agent.set_interval(int(content.split(":")[1]))
        #     except ValueError:
        #         pass

        ack = json.dumps({
            "type":       MSG_TYPE_ACK,
            "client_id":  self.agent.client_id,
            "timestamp":  timestamp,
            "message_id": message_id,
            "ack_for":    content[:80]
        })
        try:
            conn.sendall((ack + "\n").encode("utf-8"))
        except Exception as e:
            self.log.write(f"[ERROR] No se pudo enviar ACK: {e}")


class ClientAgent:
    def __init__(self, config_path: str = "config/config.json"):
        self.config   = ConfigManager(config_path)
        self.log_mgr  = LogManager(self.config.get("log_file", "logs/client.log"))
        self.disk_col = DiskCollector()
        self.iops_sim = IOPSSimulator()
        self.msg_hdlr = MessageHandler(self.log_mgr, self)

        self.client_id = self.config.get("client_id", f"CLIENT_{socket.gethostname().upper()}")
        self.interval  = self.config.get("send_interval_sec", 10)
        self._sock      = None
        self._connected = False
        self._stop_flag = threading.Event()

        self.log_mgr.write(
            f"[INIT] ID={self.client_id} | "
            f"Región={self.config.get('region','?')} | Intervalo={self.interval}s"
        )

    def set_interval(self, seconds: int):
        self.interval = seconds
        self.log_mgr.write(f"[CONFIG] Nuevo intervalo: {seconds}s")

    def _get_local_ip(self) -> str:
        """Detecta la IP local del cliente. Funciona en Windows y Linux."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.config.get("server_host", "8.8.8.8"), 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "0.0.0.0"

    def _connect(self) -> bool:
        """
        Conexión al servidor (intento único).
        [EXT-2] Para reconexión automática: envolver en while + sleep(10)
        """
        host = self.config.get("server_host", "127.0.0.1")
        port = self.config.get("server_port", 9000)
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(10)
            self._sock.connect((host, port))
            self._sock.settimeout(None)
            self._connected = True
            self.log_mgr.write(f"[CONN] Conectado a {host}:{port}")
            return True
        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            self.log_mgr.write(f"[ERROR] No se pudo conectar a {host}:{port} → {e}")
            self._connected = False
            return False

    def _disconnect(self):
        self._connected = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        self.log_mgr.write("[CONN] Socket cerrado.")

    def _send_raw(self, payload: str):
        if not self._connected or not self._sock:
            self.log_mgr.write("[WARN] Sin conexión, no se puede enviar.")
            return
        try:
            self._sock.sendall((payload + "\n").encode("utf-8"))
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            self.log_mgr.write(f"[ERROR] Conexión perdida al enviar: {e}")
            self._connected = False

    def _register(self):
        """
        Registro inicial. El servidor guarda en tabla 'nodes':
            client_id, region, hostname, ip_address
        """
        local_ip = self._get_local_ip()
        payload  = json.dumps({
            "type":       MSG_TYPE_REGISTER,
            "client_id":  self.client_id,
            "region":     self.config.get("region", "Sin Region"),
            "hostname":   socket.gethostname(),
            "ip_address": local_ip,
            "platform":   sys.platform,
            "timestamp":  datetime.now().isoformat()
        })
        self._send_raw(payload)
        self.log_mgr.write(
            f"[REG] Registro enviado | ID={self.client_id} | "
            f"Región={self.config.get('region')} | IP={local_ip}"
        )

    def _build_metrics_payload(self) -> str:
        """
        Campos planos = columnas de tabla 'metrics_history':
            disk_name, disk_type, total_gb, used_gb, free_gb, utilization, iops
        [EXT-1] Para múltiples discos: usar disk_col.get_all_disks() y enviar lista.
        """
        disk = self.disk_col.get_first_disk()
        iops = self.iops_sim.generate(disk.get("type", "HDD"))

        total       = disk.get("total_gb", 1) or 1
        used        = disk.get("used_gb", 0)
        utilization = round((used / total) * 100, 2)

        return json.dumps({
            "type":      MSG_TYPE_METRICS,          # ← ahora es "metrics"
            "client_id": self.client_id,
            "timestamp": datetime.now().isoformat(),
    
            "metrics": {                             # ← TODO dentro de "metrics": {}
                "disk_name":   disk.get("name",     "UNKNOWN"),
                "disk_type":   disk.get("type",     "HDD"),
                "total_gb":    disk.get("total_gb",  0.0),
                "used_gb":     disk.get("used_gb",   0.0),
                "free_gb":     disk.get("free_gb",   0.0),
                "utilization": disk.get("percent",   utilization),
                "iops":        iops,
            }
        })

    def _listen_server(self):
        """Hilo daemon que escucha mensajes del servidor."""
        buffer = ""
        while not self._stop_flag.is_set() and self._connected:
            try:
                chunk = self._sock.recv(4096).decode("utf-8")
                if not chunk:
                    self.log_mgr.write("[CONN] Servidor cerró la conexión.")
                    self._connected = False
                    break
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self.msg_hdlr.handle(line.strip(), self._sock)
            except (ConnectionResetError, OSError):
                self.log_mgr.write("[CONN] Conexión rota (listener).")
                self._connected = False
                break

    def run(self):
        host = self.config.get("server_host")
        port = self.config.get("server_port")

        print(f"\n{'='*55}")
        print(f"  CNS Monitor — Nodo Cliente Regional")
        print(f"  ID      : {self.client_id}")
        print(f"  Región  : {self.config.get('region', '?')}")
        print(f"  Servidor: {host}:{port}")
        print(f"{'='*55}\n")

        if not self._connect():
            print(f"[ERROR] No se pudo conectar a {host}:{port}")
            print("  → Verifica que el servidor esté corriendo")
            print("  → Revisa server_host en config/config.json")
            return

        self._register()

        threading.Thread(
            target=self._listen_server,
            name="ServerListener",
            daemon=True
        ).start()

        print(f"[OK] Conectado. Enviando cada {self.interval}s. Ctrl+C para parar.\n")

        try:
            while not self._stop_flag.is_set():
                if not self._connected:
                    # [EXT-2] Aquí iría reconexión automática si el docente lo pide
                    self.log_mgr.write("[WARN] Conexión perdida. Agente parado.")
                    print(f"\n[WARN] Conexión perdida.")
                    print(f"  Logs en: {self.config.get('log_file')}")
                    break

                payload = self._build_metrics_payload()
                self._send_raw(payload)

                m = json.loads(payload)
                d = m["metrics"]
                print(
                    f"[{m['timestamp'][:19]}] "
                    f"Disco={d['disk_name']} ({d['disk_type']}) | "
                    f"Libre={d['free_gb']:.1f}GB / {d['total_gb']:.1f}GB | "
                    f"Uso={d['utilization']}% | IOPS={d['iops']}"
                )
                self._stop_flag.wait(timeout=self.interval)

        except KeyboardInterrupt:
            print("\n[INFO] Detenido por el usuario.")
        finally:
            self._stop_flag.set()
            self._disconnect()
            self.log_mgr.write("[SHUTDOWN] Agente detenido.")
            print("[INFO] Agente finalizado.")

    def stop(self):
        self._stop_flag.set()


if __name__ == "__main__":
    ClientAgent(config_path="config/config.json").run()