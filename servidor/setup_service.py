import sys
import os
import subprocess
import platform

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
OS = platform.system()  # "Windows" o "Linux"


def print_step(msg):
    print(f"\n  {'='*50}")
    print(f"  {msg}")
    print(f"  {'='*50}")


# ════════════════════════════════════════════════
#  WINDOWS
# ════════════════════════════════════════════════
def windows_install():
    print_step("Instalando servicio en Windows")

    # Verificar permisos de administrador
    import ctypes
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("\n  ⚠️  Necesitas ejecutar esto como ADMINISTRADOR.")
        print("  Clic derecho en PowerShell → 'Ejecutar como administrador'")
        sys.exit(1)

    # Instalar pywin32 si no está
    try:
        import win32serviceutil
    except ImportError:
        print("  Instalando pywin32...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32-ctypes"])
        # Post-install de pywin32
        scripts_dir = os.path.join(os.path.dirname(sys.executable), "Scripts")
        postinstall = os.path.join(scripts_dir, "pywin32_postinstall.py")
        if os.path.exists(postinstall):
            subprocess.check_call([sys.executable, postinstall, "-install"])

    # Instalar el servicio
    service_script = os.path.join(PROJECT_DIR, "windows_service.py")
    result = subprocess.run(
        [sys.executable, service_script, "--startup", "auto", "install"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"  Error: {result.stderr}")
        sys.exit(1)

    # Arrancar el servicio
    subprocess.run([sys.executable, service_script, "start"])

    print("\n  ✅ Servicio instalado y arrancado.")
    print("  Para ver el estado: Administrador de Servicios (services.msc)")
    print("  Nombre del servicio: StorageClusterServer")


def windows_uninstall():
    print_step("Desinstalando servicio de Windows")
    service_script = os.path.join(PROJECT_DIR, "windows_service.py")
    subprocess.run([sys.executable, service_script, "stop"],  capture_output=True)
    subprocess.run([sys.executable, service_script, "remove"])
    print("\n  ✅ Servicio eliminado.")


def windows_status():
    service_script = os.path.join(PROJECT_DIR, "windows_service.py")
    subprocess.run([sys.executable, service_script, "status"])


# ════════════════════════════════════════════════
#  LINUX
# ════════════════════════════════════════════════
def linux_install():
    print_step("Instalando servicio en Linux (systemd)")

    if os.geteuid() != 0:
        print("\n  ⚠️  Necesitas ejecutar esto con sudo:")
        print(f"  sudo python3 {__file__} install")
        sys.exit(1)

    service_src  = os.path.join(PROJECT_DIR, "storage-cluster.service")
    service_dest = "/etc/systemd/system/storage-cluster.service"

    # Leer la plantilla y reemplazar rutas
    with open(service_src, "r") as f:
        content = f.read()

    # Detectar el usuario real (no root aunque se corra con sudo)
    real_user = os.environ.get("SUDO_USER", "root")
    python_path = subprocess.check_output(["which", "python3"]).decode().strip()

    content = content.replace("/ruta/completa/a/storage_cluster_server", PROJECT_DIR)
    content = content.replace("tu_usuario", real_user)
    content = content.replace("/usr/bin/python3", python_path)

    with open(service_dest, "w") as f:
        f.write(content)

    print(f"  Archivo de servicio copiado a: {service_dest}")
    print(f"  Usuario: {real_user}")
    print(f"  Python: {python_path}")
    print(f"  Directorio: {PROJECT_DIR}")

    # Activar e iniciar
    subprocess.check_call(["systemctl", "daemon-reload"])
    subprocess.check_call(["systemctl", "enable", "storage-cluster"])
    subprocess.check_call(["systemctl", "start",  "storage-cluster"])

    print("\n  ✅ Servicio instalado, habilitado y arrancado.")
    print("\n  Comandos útiles:")
    print("    sudo systemctl status  storage-cluster   ← ver estado")
    print("    sudo systemctl stop    storage-cluster   ← detener")
    print("    sudo systemctl restart storage-cluster   ← reiniciar")
    print("    journalctl -u storage-cluster -f         ← ver logs en tiempo real")


def linux_uninstall():
    print_step("Desinstalando servicio de Linux")

    if os.geteuid() != 0:
        print(f"\n  ⚠️  Usa: sudo python3 {__file__} uninstall")
        sys.exit(1)

    subprocess.run(["systemctl", "stop",    "storage-cluster"], capture_output=True)
    subprocess.run(["systemctl", "disable", "storage-cluster"], capture_output=True)

    service_file = "/etc/systemd/system/storage-cluster.service"
    if os.path.exists(service_file):
        os.remove(service_file)

    subprocess.run(["systemctl", "daemon-reload"])
    print("\n  ✅ Servicio eliminado.")


def linux_status():
    subprocess.run(["systemctl", "status", "storage-cluster"])


# ════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════
def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "install"

    if OS == "Windows":
        actions = {"install": windows_install, "uninstall": windows_uninstall, "status": windows_status}
    elif OS == "Linux":
        actions = {"install": linux_install, "uninstall": linux_uninstall, "status": linux_status}
    else:
        print(f"Sistema operativo no soportado: {OS}")
        sys.exit(1)

    fn = actions.get(action)
    if not fn:
        print(f"Acción desconocida: '{action}'. Usa: install | uninstall | status")
        sys.exit(1)

    fn()


if __name__ == "__main__":
    main()
