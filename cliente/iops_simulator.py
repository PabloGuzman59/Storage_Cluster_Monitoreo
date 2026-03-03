"""
=============================================================================
MÓDULO: iops_simulator.py
=============================================================================
Descripción:
    Genera valores de IOPS simulados realistas basados en el tipo de disco.
    Se usa porque Python/psutil no expone IOPS directamente.

Valores de referencia:
    HDD convencional : 80  – 180  IOPS
    SSD SATA         : 50000 – 100000 IOPS
    SSD NVMe         : 200000 – 700000 IOPS

La simulación agrega variación gaussiana para imitar fluctuaciones reales.
=============================================================================
"""

import random


# Rangos por tipo de disco (min, max) en IOPS
_IOPS_RANGES = {
    "HDD":  (80,    180),
    "SSD":  (50000, 100000),
    "NVMe": (200000, 700000),
}

# Variación estándar (±10% del rango medio)
_NOISE_FACTOR = 0.10


class IOPSSimulator:
    """Genera IOPS simulados con variación gaussiana."""

    def __init__(self):
        # Estado para tendencias suaves (el valor no salta abruptamente)
        self._last_values: dict[str, float] = {}

    def generate(self, disk_type: str = "HDD") -> int:
        """
        Genera un valor de IOPS simulado para el tipo de disco dado.

        Args:
            disk_type: "HDD", "SSD" o "NVMe"

        Returns:
            Entero representando IOPS simulados
        """
        disk_type = disk_type.upper()
        low, high = _IOPS_RANGES.get(disk_type, _IOPS_RANGES["HDD"])
        mid = (low + high) / 2
        noise = mid * _NOISE_FACTOR

        # Si hay un valor previo, hacer una transición suave
        prev = self._last_values.get(disk_type, mid)
        target = random.uniform(low, high)
        # Mezcla 70% valor anterior + 30% valor nuevo → curva más suave
        new_val = 0.7 * prev + 0.3 * target + random.gauss(0, noise)
        new_val = max(low, min(high, new_val))

        self._last_values[disk_type] = new_val
        return int(round(new_val))
