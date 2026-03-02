import socket
import json
import time
import random
import argparse
import threading
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def run_client(client_id: str, region: str, host: str, port: int, interval: int):
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            log.info(f"Conectado al servidor {host}:{port}")

            # 1. Registro
            register_msg = json.dumps({
                "type":      "register",
                "client_id": client_id,
                "region":    region,
                "hostname":  f"srv-{client_id}.cns.bo",
            }) + "\n"
            sock.sendall(register_msg.encode())

            # 2. Hilo para recibir mensajes del servidor
            def receiver():
                buffer = ""
                while True:
                    try:
                        data = sock.recv(4096).decode()
                        if not data:
                            break
                        buffer += data
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            if line.strip():
                                msg = json.loads(line.strip())
                                if msg.get("type") == "server_message":
                                    log.info(f"[MENSAJE DEL SERVIDOR] {msg.get('content')}")
                                    # Guardar en log
                                    with open(f"logs/{client_id}_messages.log", "a") as f:
                                        f.write(f"{datetime.now()} | {msg.get('content')}\n")
                                    # Enviar ACK
                                    ack = json.dumps({
                                        "type":       "ack",
                                        "message_id": msg.get("message_id"),
                                    }) + "\n"
                                    sock.sendall(ack.encode())
                                else:
                                    log.debug(f"Resp servidor: {msg.get('type')}")
                    except Exception as e:
                        log.warning(f"Receiver error: {e}")
                        break

            threading.Thread(target=receiver, daemon=True).start()

            # 3. Bucle de envío de métricas
            total_gb = random.uniform(500, 2000)
            while True:
                used_gb = random.uniform(total_gb * 0.2, total_gb * 0.95)
                free_gb = total_gb - used_gb
                metrics = {
                    "type":      "metrics",
                    "client_id": client_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metrics": {
                        "disk_name": "/dev/sda1",
                        "disk_type": random.choice(["SSD", "HDD"]),
                        "total_gb":  round(total_gb, 2),
                        "used_gb":   round(used_gb, 2),
                        "free_gb":   round(free_gb, 2),
                        "iops":      random.randint(100, 5000),
                    }
                }
                sock.sendall((json.dumps(metrics) + "\n").encode())
                log.info(f"Métricas enviadas: used={used_gb:.1f}GB / total={total_gb:.1f}GB")
                time.sleep(interval)

        except (ConnectionRefusedError, OSError) as e:
            log.error(f"No se pudo conectar: {e}. Reintentando en 5s...")
            time.sleep(5)
        except KeyboardInterrupt:
            log.info("Cliente detenido.")
            break
        finally:
            try:
                sock.close()
            except Exception:
                pass


if __name__ == "__main__":
    import os
    os.makedirs("logs", exist_ok=True)

    parser = argparse.ArgumentParser(description="Cliente de prueba del Storage Cluster")
    parser.add_argument("--id",       default="node_test",    help="ID del nodo")
    parser.add_argument("--region",   default="La Paz",       help="Región")
    parser.add_argument("--host",     default="127.0.0.1",    help="IP del servidor")
    parser.add_argument("--port",     default=9000, type=int, help="Puerto del servidor")
    parser.add_argument("--interval", default=10,  type=int,  help="Segundos entre reportes")
    args = parser.parse_args()

    run_client(args.id, args.region, args.host, args.port, args.interval)
