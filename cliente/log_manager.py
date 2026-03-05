"""
=============================================================================
MÓDULO: log_manager.py
=============================================================================
Descripción:
    Gestiona la escritura de logs locales del agente cliente.

    Funciones:
        - Escribe logs en archivo .log local
        - Usa logging estándar de Python (thread-safe)
        - Formato: [NIVEL] YYYY-MM-DD HH:MM:SS | Mensaje
        - Muestra en consola (nivel INFO+)

    El archivo de log se configura en config.json → "log_file".
=============================================================================
"""

import logging
import os
from datetime import datetime


class LogManager:
    """Gestor de logs para el nodo cliente."""

    def __init__(self, log_path: str = "logs/client.log"):
        # Crear directorio de logs si no existe
        log_dir = os.path.dirname(log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        self.log_path = log_path

        # Configurar logger con nombre único para evitar conflictos
        self.logger = logging.getLogger("StorageClusterClient")
        self.logger.setLevel(logging.DEBUG)

        # Evitar duplicar handlers si se instancia múltiples veces
        if not self.logger.handlers:
            # Handler para archivo
            fh = logging.FileHandler(log_path, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))

            # Handler para consola (solo WARNING+)
            ch = logging.StreamHandler()
            ch.setLevel(logging.WARNING)
            ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

            self.logger.addHandler(fh)
            self.logger.addHandler(ch)

    def write(self, message: str, level: str = "INFO"):
        """
        Escribe un mensaje en el log.

        Args:
            message : Texto del mensaje
            level   : "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
        """
        getattr(self.logger, level.lower(), self.logger.info)(message)
