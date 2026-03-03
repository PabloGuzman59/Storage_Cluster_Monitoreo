"""
=============================================================================
MÓDULO: config_manager.py
=============================================================================
Descripción:
    Carga y provee acceso a la configuración del cliente desde config.json.
    Si el archivo no existe, crea uno con valores por defecto.

Campos del config:
    client_id        : Identificador único del cliente (ej: "CNS_REGIONAL_01")
    server_host      : IP o hostname del servidor central
    server_port      : Puerto TCP del servidor
    send_interval_sec: Segundos entre cada envío de métricas
    log_file         : Ruta al archivo de log local

[EXT-3] NUEVO SERVIDOR ADICIONAL
    Para soportar envío a múltiples servidores, agregar al config:
    {
        "servers": [
            {"host": "192.168.1.10", "port": 9000, "name": "CENTRAL"},
            {"host": "192.168.1.20", "port": 9000, "name": "BACKUP"}
        ]
    }
    Y modificar ClientAgent._connect() para iterar sobre la lista.
=============================================================================
"""

import json, os

DEFAULT_CONFIG = {
    "client_id"        : "CNS_REGIONAL_01",
    "region"           : "La Paz",            
    "server_host"      : "192.168.0.112",     
    "server_port"      : 9000,
    "send_interval_sec": 10,
    "log_file"         : "logs/client.log"
}

class ConfigManager:
    def __init__(self, config_path="config/config.json"):
        self.config_path = config_path
        self._data = self._load()

    def _load(self):
        if not os.path.exists(self.config_path):
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            return DEFAULT_CONFIG.copy()
        with open(self.config_path) as f:
            loaded = json.load(f)
        merged = DEFAULT_CONFIG.copy()
        merged.update(loaded)
        return merged

    def get(self, key, default=None):
        return self._data.get(key, default)

    def reload(self):
        self._data = self._load()