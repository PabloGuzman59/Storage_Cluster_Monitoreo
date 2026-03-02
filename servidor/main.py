import threading
import logging
from server import get_server
from dashboard import run_dashboard
from config import CONFIG

log = logging.getLogger(__name__)


def main():
    print("=" * 60)
    print("  STORAGE CLUSTER SERVER - Práctica 1")
    print("=" * 60)

    srv = get_server()

    # Hilo 1: Servidor TCP (blocking)
    tcp_thread = threading.Thread(target=srv.start, daemon=False, name="TCPServer")
    tcp_thread.start()

    # Hilo 2: Dashboard Flask
    flask_thread = threading.Thread(target=run_dashboard, daemon=True, name="FlaskDashboard")
    flask_thread.start()

    print(f"\n  ✓ Servidor TCP   → puerto {CONFIG['server']['port']}")
    print(f"  ✓ Dashboard web  → http://localhost:{CONFIG['flask']['port']}")
    print(f"  ✓ MySQL          → {CONFIG['database']['host']}:{CONFIG['database']['port']}")
    print("\n  Presiona Ctrl+C para detener.\n")

    tcp_thread.join()


if __name__ == "__main__":
    main()
