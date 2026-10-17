# CLAUDE.md — py-common

Instrucciones para Claude Code (y otros agentes de IA) trabajando en este repositorio.

## Qué es este repo

Librería Python compartida por los microservicios Python de DigSigna (`certificate-service`, `signing-service`, futuros). Extraída de `certificate-service` el 2026-10-16/17 — en ese momento, cada módulo de acá era idéntico byte a byte en `certificate-service` y `signing-service`, salvo dos diferencias de una línea (ahora parámetros `service_name` en vez de strings hardcodeadas). Ver `README.md` para el detalle de qué vive en cada submódulo y los cambios de comportamiento deliberados introducidos durante la extracción.

Hermana en espíritu (no en código: nunca se comparte código entre Python y Go) de un futuro `digsigna-go-common` para `hsm-service` y los próximos servicios Go (`audit-service`, `gateway-service`) — ambos lados deben mantener el mismo contrato conceptual (forma de los claims JWT, esquema de `audit_logs`/`idempotency_keys`), pero son paquetes independientes.

## Reglas

Mismo espíritu que `certificate-service/CLAUDE.md` y `hsm-service/CLAUDE.md` (adaptado: acá no hay HSM, DB en producción, ni endpoints HTTP propios — es una librería, no un servicio):

1. **No reintroduzcas acoplamiento a una app consumidora.** Nada en `py_common` debe importar `app.*` de ningún servicio, ni depender de que exista una instancia de `Settings`/`get_settings()` de un consumidor. Todo lo que un caller necesita configurar entra por parámetros de constructor (`KeyManagerConfig`, `WorkerConfig`, `TokenCacheConfig`, `service_name`, etc.), nunca leyendo variables de entorno o config files directamente excepto donde ya está documentado como deliberado (`core/logger.py`'s `ENVIRONMENT`).
2. **No hardcodees un nombre de servicio.** Si agregás código nuevo que necesita saber "quién lo está llamando" (para logs, headers HTTP, etc.), pasalo como parámetro explícito — ver el bug de `LoggingMiddleware`/`"api-gateway"` que esto reemplazó (README).
3. **Cambios que rompen compatibilidad con un consumidor existente requieren bump de versión mayor** y coordinación explícita (un PR en `certificate-service`/`signing-service` que actualice el pin), nunca un cambio silencioso bajo el mismo tag.
4. **Agregá tests para cualquier módulo nuevo** — a diferencia de los repos de origen (que nunca tuvieron tests para `key_manager_adapter`/`validator_adapter`/`hybrid_processor`/`audit_worker`/`http_transporter` pese a ser infraestructura crítica), este repo sí los tiene y el estándar es mantenerlos.
5. **Nunca pinees una dependencia con `==` en `pyproject.toml`** — usá un floor (`>=`). Los consumidores ya divergen en pines exactos (p. ej. `cryptography`), y un pin exacto acá rompería la instalación en al menos uno de ellos. Ver README.
6. Las mismas reglas de seguridad no-negociables de `certificate-service/CLAUDE.md` (nunca loguear material criptográfico, nunca `print()`, nunca silenciar excepciones de red/crypto sin loguear, `secrets` no `random` para cualquier generación aleatoria con fines de seguridad) aplican acá igual.

## Al terminar una tarea

`pytest -v --cov=py_common`, `black --check src tests`, `flake8 src tests`, `bandit -r src` — los cuatro gatean CI (`.github/workflows/ci.yml`). Si agregás una dependencia nueva, evaluá si debe ser un floor en `dependencies` (si el runtime la necesita) o en `optional-dependencies.dev` (si es solo para tests/lint).
