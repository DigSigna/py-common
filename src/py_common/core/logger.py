# py_common/core/logger.py
import logging
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


class UnifiedLogger:
    """
    Logger unificado que:
    - Logs locales estructurados en JSON
    - Preparado para integración futura con audit-service
    - Soporta correlación de requests

    Extraído verbatim de certificate-service/signing-service, con un solo
    cambio deliberado: el "environment" del log entry ya no viene de
    get_settings() de la app consumidora (ese acoplamiento no puede vivir
    en una librería compartida) sino de la env var ENVIRONMENT directamente
    — mismo valor en la práctica, ya que config.yaml en ambos servicios
    fija "environment: development" (idéntico al default del Field), y en
    ningún entorno real se setea ENVIRONMENT solo vía YAML versionado en
    git en vez de una env var real.
    """

    def __init__(self, service_name: str):
        self.service_name = service_name

        # Configurar logger local
        self.logger = logging.getLogger(service_name)
        self._setup_local_logging()

    def _setup_local_logging(self):
        """Configura logging local estructurado en formato JSON"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(message)s"  # Solo el mensaje JSON, sin metadatos extra
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _create_log_entry(
        self,
        level: str,
        message: str,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crea una entrada de log estructurada"""
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": self.service_name,
            "level": level,
            "message": message,
            "action": action,
            "user_id": user_id,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "metadata": metadata or {},
            "environment": os.environ.get("ENVIRONMENT", "development"),
        }

    def _log_local(self, log_entry: Dict[str, Any]):
        """Log local estructurado"""
        log_json = json.dumps(log_entry, ensure_ascii=False)

        if log_entry["level"] == "ERROR":
            self.logger.error(log_json)
        elif log_entry["level"] == "WARNING":
            self.logger.warning(log_json)
        elif log_entry["level"] == "DEBUG":
            self.logger.debug(log_json)
        else:
            self.logger.info(log_json)

    def info(
        self,
        message: str,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **metadata,
    ):
        """Log nivel INFO"""
        log_entry = self._create_log_entry(
            "INFO", message, action, user_id, correlation_id, metadata
        )
        self._log_local(log_entry)

    def error(
        self,
        message: str,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **metadata,
    ):
        """Log nivel ERROR"""
        log_entry = self._create_log_entry(
            "ERROR", message, action, user_id, correlation_id, metadata
        )
        self._log_local(log_entry)

    def warning(
        self,
        message: str,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **metadata,
    ):
        """Log nivel WARNING"""
        log_entry = self._create_log_entry(
            "WARNING", message, action, user_id, correlation_id, metadata
        )
        self._log_local(log_entry)

    def debug(
        self,
        message: str,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **metadata,
    ):
        """Log nivel DEBUG"""
        log_entry = self._create_log_entry(
            "DEBUG", message, action, user_id, correlation_id, metadata
        )
        self._log_local(log_entry)


# Instancia nueva por nombre de servicio/módulo — mismo patrón que antes
def get_logger(service_name: str) -> UnifiedLogger:
    return UnifiedLogger(service_name)
