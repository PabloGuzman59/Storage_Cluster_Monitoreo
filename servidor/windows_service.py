import sys
import os
import time
import subprocess
import logging

# Agregar el directorio del proyecto al path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# ── Logging ────────────────────────────────────────────────
os.makedirs(os.path.join(PROJECT_DIR, "logs"), exist_ok=True)
logging.basicConfig(
    filename=os.path.join(PROJECT_DIR, "logs", "service.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


if HAS_WIN32:
    class StorageClusterService(win32serviceutil.ServiceFramework):
        _svc_name_        = "StorageClusterServer"
        _svc_display_name_= "Storage Cluster Server - CNS"
        _svc_description_ = "Servidor central de monitoreo del Storage Cluster para la CNS."

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.process    = None

        def SvcStop(self):
            log.info("Deteniendo servicio...")
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=10)
            win32event.SetEvent(self.stop_event)
            log.info("Servicio detenido.")

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, "")
            )
            log.info("Servicio iniciado.")
            self._run()

        def _run(self):
            python_exe  = sys.executable
            main_script = os.path.join(PROJECT_DIR, "main.py")

            while True:
                # Verificar si se pidió parar
                rc = win32event.WaitForSingleObject(self.stop_event, 0)
                if rc == win32event.WAIT_OBJECT_0:
                    break

                log.info("Lanzando proceso principal...")
                try:
                    self.process = subprocess.Popen(
                        [python_exe, main_script],
                        cwd=PROJECT_DIR,
                        stdout=open(os.path.join(PROJECT_DIR, "logs", "stdout.log"), "a"),
                        stderr=open(os.path.join(PROJECT_DIR, "logs", "stderr.log"), "a"),
                    )
                    # Esperar a que termine (o a la señal de stop)
                    while True:
                        rc = win32event.WaitForSingleObject(self.stop_event, 2000)
                        if rc == win32event.WAIT_OBJECT_0:
                            return  # Se pidió parar
                        if self.process.poll() is not None:
                            break  # El proceso terminó inesperadamente

                    exit_code = self.process.returncode
                    log.warning(f"Proceso terminó con código {exit_code}. Reiniciando en 5s...")

                except Exception as e:
                    log.error(f"Error al lanzar proceso: {e}")

                time.sleep(5)  # Espera antes de reiniciar


def install_service():
    if not HAS_WIN32:
        print("ERROR: pywin32 no está instalado.")
        print("Ejecuta:  pip install pywin32")
        sys.exit(1)
    win32serviceutil.HandleCommandLine(StorageClusterService)


# ── Alternativa sin pywin32: bucle de reinicio simple ─────
def run_with_auto_restart():
    """
    Fallback si no se tiene pywin32.
    Relanza main.py automáticamente si crashea.
    Úsalo con el Programador de tareas de Windows.
    """
    python_exe  = sys.executable
    main_script = os.path.join(PROJECT_DIR, "main.py")
    restarts    = 0

    print("Modo auto-restart activo. Presiona Ctrl+C para detener.")
    log.info("Auto-restart iniciado.")

    while True:
        try:
            log.info(f"Iniciando servidor (intento #{restarts + 1})...")
            proc = subprocess.Popen([python_exe, main_script], cwd=PROJECT_DIR)
            proc.wait()
            exit_code = proc.returncode
            restarts += 1
            log.warning(f"Servidor terminó (código {exit_code}). Reiniciando en 5s... (total reinicios: {restarts})")
            time.sleep(5)

        except KeyboardInterrupt:
            log.info("Detenido por el usuario.")
            print("\nServidor detenido.")
            break
        except Exception as e:
            log.error(f"Error inesperado: {e}. Reintentando en 10s...")
            time.sleep(10)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Sin argumentos → auto-restart simple
        run_with_auto_restart()
    else:
        # Con argumentos → comandos del servicio Windows
        install_service()