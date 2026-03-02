import json
import logging
from datetime import datetime, timezone
from typing import Optional

import mysql.connector
from mysql.connector import pooling, Error as MySQLError

from config import CONFIG

log = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.pool: Optional[pooling.MySQLConnectionPool] = None

    # ── Inicialización ─────────────────────────────────────
    def initialize(self):
        """Crea el pool de conexiones y las tablas si no existen."""
        db_cfg = CONFIG["database"]

        # Primero crea la base de datos si no existe
        self._create_database_if_missing(db_cfg)

        self.pool = pooling.MySQLConnectionPool(
            pool_name="cluster_pool",
            pool_size=5,
            host=db_cfg["host"],
            port=db_cfg["port"],
            user=db_cfg["user"],
            password=db_cfg["password"],
            database=db_cfg["database"],
            autocommit=True,
            charset="utf8mb4",
        )
        self._create_tables()
        log.info("Base de datos inicializada correctamente.")

    def _create_database_if_missing(self, cfg: dict):
        conn = mysql.connector.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
        )
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        conn.commit()
        cursor.close()
        conn.close()

    def _create_tables(self):
        ddl_statements = [
            # Nodos conocidos
            """
            CREATE TABLE IF NOT EXISTS nodes (
                client_id   VARCHAR(100) PRIMARY KEY,
                region      VARCHAR(150),
                hostname    VARCHAR(150),
                ip_address  VARCHAR(45),
                status      ENUM('active','no_reporta','disconnected') DEFAULT 'active',
                registered_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen_at   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """,
            # Historial de métricas
            """
            CREATE TABLE IF NOT EXISTS metrics_history (
                id           BIGINT AUTO_INCREMENT PRIMARY KEY,
                client_id    VARCHAR(100),
                disk_name    VARCHAR(100),
                disk_type    VARCHAR(20),
                total_gb     DECIMAL(12,2),
                used_gb      DECIMAL(12,2),
                free_gb      DECIMAL(12,2),
                utilization  DECIMAL(5,2),
                iops         INT,
                reported_at  DATETIME,
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES nodes(client_id) ON DELETE CASCADE,
                INDEX idx_client_time (client_id, reported_at)
            ) ENGINE=InnoDB;
            """,
            # Mensajes enviados por el servidor a los clientes
            """
            CREATE TABLE IF NOT EXISTS server_messages (
                id          BIGINT AUTO_INCREMENT PRIMARY KEY,
                client_id   VARCHAR(100),
                message_id  VARCHAR(100) UNIQUE,
                content     TEXT,
                ack_received TINYINT(1) DEFAULT 0,
                sent_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES nodes(client_id) ON DELETE CASCADE
            ) ENGINE=InnoDB;
            """,
        ]
        with self._conn() as conn:
            cursor = conn.cursor()
            for ddl in ddl_statements:
                cursor.execute(ddl)
            conn.commit()
            cursor.close()

    # ── Conexión helper ────────────────────────────────────
    def _conn(self):
        return self.pool.get_connection()

    # ── Nodos ──────────────────────────────────────────────
    def upsert_node(self, client_id: str, region: str, hostname: str, ip: str):
        sql = """
            INSERT INTO nodes (client_id, region, hostname, ip_address, status, last_seen_at)
            VALUES (%s, %s, %s, %s, 'active', NOW())
            ON DUPLICATE KEY UPDATE
                region       = VALUES(region),
                hostname     = VALUES(hostname),
                ip_address   = VALUES(ip_address),
                status       = 'active',
                last_seen_at = NOW();
        """
        self._execute(sql, (client_id, region, hostname, ip))

    def update_node_status(self, client_id: str, status: str):
        self._execute(
            "UPDATE nodes SET status = %s WHERE client_id = %s;",
            (status, client_id)
        )

    def get_all_nodes(self) -> list:
        sql = """
            SELECT
                n.client_id,
                n.region,
                n.hostname,
                n.ip_address,
                n.status,
                n.last_seen_at,
                m.total_gb,
                m.used_gb,
                m.free_gb,
                m.utilization,
                m.disk_type,
                m.iops,
                m.reported_at
            FROM nodes n
            LEFT JOIN metrics_history m ON m.id = (
                SELECT id FROM metrics_history
                WHERE client_id = n.client_id
                ORDER BY reported_at DESC
                LIMIT 1
            )
            ORDER BY n.region;
        """
        return self._fetchall(sql)

    # ── Métricas ───────────────────────────────────────────
    def save_metrics(self, client_id: str, metrics: dict, timestamp: str):
        # Actualizar last_seen_at del nodo
        self._execute(
            "UPDATE nodes SET status='active', last_seen_at=NOW() WHERE client_id=%s;",
            (client_id,)
        )

        # Parsear timestamp
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            reported_at = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            reported_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        total_gb = float(metrics.get("total_gb", 0))
        used_gb  = float(metrics.get("used_gb", 0))
        free_gb  = float(metrics.get("free_gb", 0))
        utilization = round((used_gb / total_gb * 100) if total_gb > 0 else 0, 2)

        sql = """
            INSERT INTO metrics_history
                (client_id, disk_name, disk_type, total_gb, used_gb, free_gb,
                 utilization, iops, reported_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        self._execute(sql, (
            client_id,
            metrics.get("disk_name", "unknown"),
            metrics.get("disk_type", "HDD"),
            total_gb,
            used_gb,
            free_gb,
            utilization,
            int(metrics.get("iops", 0)),
            reported_at,
        ))

    def get_node_history(self, client_id: str, limit: int = 50) -> list:
        sql = """
            SELECT disk_name, disk_type, total_gb, used_gb, free_gb,
                   utilization, iops, reported_at
            FROM metrics_history
            WHERE client_id = %s
            ORDER BY reported_at DESC
            LIMIT %s;
        """
        return self._fetchall(sql, (client_id, limit))

    def get_cluster_summary(self) -> dict:
        sql = """
            SELECT
                COUNT(DISTINCT n.client_id)                        AS total_nodes,
                SUM(CASE WHEN n.status='active' THEN 1 ELSE 0 END) AS active_nodes,
                SUM(CASE WHEN n.status='no_reporta' THEN 1 ELSE 0 END) AS unreported_nodes,
                COALESCE(SUM(latest.total_gb), 0)  AS cluster_total_gb,
                COALESCE(SUM(latest.used_gb), 0)   AS cluster_used_gb,
                COALESCE(SUM(latest.free_gb), 0)   AS cluster_free_gb
            FROM nodes n
            LEFT JOIN (
                SELECT mh.client_id, mh.total_gb, mh.used_gb, mh.free_gb
                FROM metrics_history mh
                INNER JOIN (
                    SELECT client_id, MAX(reported_at) AS max_t
                    FROM metrics_history
                    GROUP BY client_id
                ) latest_t ON mh.client_id = latest_t.client_id
                          AND mh.reported_at = latest_t.max_t
            ) latest ON n.client_id = latest.client_id;
        """
        rows = self._fetchall(sql)
        if not rows:
            return {}
        r = rows[0]
        total = float(r["cluster_total_gb"] or 0)
        used  = float(r["cluster_used_gb"]  or 0)
        return {
            "total_nodes":     int(r["total_nodes"] or 0),
            "active_nodes":    int(r["active_nodes"] or 0),
            "unreported_nodes":int(r["unreported_nodes"] or 0),
            "cluster_total_gb":round(total, 2),
            "cluster_used_gb": round(used, 2),
            "cluster_free_gb": round(float(r["cluster_free_gb"] or 0), 2),
            "utilization_pct": round((used / total * 100) if total > 0 else 0, 2),
        }

    # ── Mensajes ───────────────────────────────────────────
    def save_server_message(self, client_id: str, content: str, msg_id: str):
        sql = """
            INSERT INTO server_messages (client_id, message_id, content)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE content=content;
        """
        self._execute(sql, (client_id, msg_id, content))

    def mark_ack(self, message_id: str):
        self._execute(
            "UPDATE server_messages SET ack_received=1 WHERE message_id=%s;",
            (message_id,)
        )

    # ── Helpers internos ───────────────────────────────────
    def _execute(self, sql: str, params: tuple = ()):
        try:
            with self._conn() as conn:
                cur = conn.cursor()
                cur.execute(sql, params)
                conn.commit()
                cur.close()
        except MySQLError as e:
            log.error(f"DB error: {e} | SQL: {sql[:80]}")

    def _fetchall(self, sql: str, params: tuple = ()) -> list:
        try:
            with self._conn() as conn:
                cur = conn.cursor(dictionary=True)
                cur.execute(sql, params)
                rows = cur.fetchall()
                cur.close()
                return rows
        except MySQLError as e:
            log.error(f"DB fetchall error: {e}")
            return []
