"""
=============================================================================
MÓDULO: disk_collector.py
=============================================================================
Descripción:
    Captura información del primer disco detectado en el sistema.
    Multiplataforma: Windows y Linux.

Campos capturados:
    - name       : Nombre/letra del dispositivo  (C:\\ en Windows, /dev/sda en Linux)
    - type       : Tipo estimado del disco (SSD/HDD)
    - total_gb   : Capacidad total en GB
    - used_gb    : Espacio usado en GB
    - free_gb    : Espacio libre en GB
    - percent    : Porcentaje de uso (0-100)
    - mountpoint : Punto de montaje

[EXT-1] SOPORTE PARA MÚLTIPLES DISCOS
    El método get_all_disks() ya está implementado y retorna una lista de
    todos los discos. El agente principal solo llama get_first_disk().
    Para enviar múltiples discos (si el docente lo pide):
        1. En client_agent.py → _build_metrics_payload():
           Cambiar  "disk": disk_info
           Por      "disks": self.disk_col.get_all_disks()
        2. El servidor deberá actualizar su schema para recibir la lista.
        3. Agregar un campo "disk_id" a cada disco para identificarlos.
=============================================================================
"""

import sys
import psutil
from typing import Optional


class DiskCollector:
    """Recolector de información de disco multiplataforma."""

    # Sistemas de archivos que NO son discos reales (virtuales, proc, etc.)
    _EXCLUDED_FS = {
        "tmpfs", "devtmpfs", "sysfs", "proc", "cgroup",
        "devpts", "mqueue", "hugetlbfs", "pstore", "bpf",
        "squashfs", "overlay", "aufs"
    }

    def get_all_disks(self) -> list[dict]:
        """
        Retorna información de TODOS los discos físicos del sistema.

        [EXT-1] Este método es el punto de extensión para múltiples discos.
        Cada disco lleva un campo 'disk_id' (índice) para identificación.

        Returns:
            Lista de dicts con info de cada disco.
        """
        partitions = psutil.disk_partitions(all=False)
        disks = []

        for idx, part in enumerate(partitions):
            # Filtrar sistemas de archivos virtuales (solo Linux)
            if sys.platform != "win32" and part.fstype.lower() in self._EXCLUDED_FS:
                continue

            try:
                usage = psutil.disk_usage(part.mountpoint)
            except PermissionError:
                continue

            disk_type = self._detect_disk_type(part.device)

            disks.append({
                "disk_id"    : idx,                              # [EXT-1] ID único
                "name"       : part.device,
                "mountpoint" : part.mountpoint,
                "fstype"     : part.fstype,
                "type"       : disk_type,
                "total_gb"   : round(usage.total  / (1024**3), 2),
                "used_gb"    : round(usage.used   / (1024**3), 2),
                "free_gb"    : round(usage.free   / (1024**3), 2),
                "percent"    : usage.percent,
            })

        return disks

    def get_first_disk(self) -> dict:
        """
        Retorna información ÚNICAMENTE del primer disco detectado.
        Requisito del enunciado: "Reportar únicamente el primer disco".

        Returns:
            Dict con info del primer disco, o disco vacío si no hay ninguno.
        """
        all_disks = self.get_all_disks()

        if not all_disks:
            # Caso de seguridad: no se detectó ningún disco
            return {
                "disk_id"    : 0,
                "name"       : "UNKNOWN",
                "mountpoint" : "/",
                "fstype"     : "unknown",
                "type"       : "HDD",
                "total_gb"   : 0.0,
                "used_gb"    : 0.0,
                "free_gb"    : 0.0,
                "percent"    : 0.0,
            }

        return all_disks[0]

    def _detect_disk_type(self, device: str) -> str:
        """
        Intenta detectar si el disco es SSD o HDD.

        En Linux: lee /sys/block/<dev>/queue/rotational
            0 → SSD
            1 → HDD
        En Windows: psutil no expone esta info directamente,
            se usa heurística por nombre (nvme → SSD, etc.)

        Returns:
            "SSD" o "HDD"
        """
        if sys.platform == "linux":
            return self._linux_disk_type(device)
        elif sys.platform == "win32":
            return self._windows_disk_type(device)
        return "HDD"   # fallback

    def _linux_disk_type(self, device: str) -> str:
        """Detecta tipo de disco en Linux leyendo rotational."""
        import os
        try:
            # Obtener nombre base del dispositivo (ej: /dev/sda1 → sda)
            dev_name = os.path.basename(device).rstrip("0123456789")
            rotational_path = f"/sys/block/{dev_name}/queue/rotational"
            if os.path.exists(rotational_path):
                with open(rotational_path) as f:
                    return "HDD" if f.read().strip() == "1" else "SSD"
        except Exception:
            pass
        return "HDD"

    def _windows_disk_type(self, device: str) -> str:
        """
        Heurística para Windows.
        Una implementación más precisa usaría WMI, pero requiere dependencia extra.
        """
        device_lower = device.lower()
        if "nvme" in device_lower or "ssd" in device_lower:
            return "SSD"
        return "HDD"
