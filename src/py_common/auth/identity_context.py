from dataclasses import dataclass, field
from typing import Optional, List

from py_common.errors import (
    InvalidOwnerTypeError,
    OwnerIdRequiredError,
    TenantRequiredError,
)
from .owner_type import OwnerType


@dataclass
class IdentityContext:
    tenant_id: str
    owner_type: OwnerType
    owner_id: str
    user_id: str
    cert_level: int
    max_cert_level: int
    can_certify: bool
    certification_path: str
    # Flat list of permission codes (e.g. "admin", "hsm:key:generate") — the
    # real JWT claim identification-service issues (signer.js/
    # build-access-token-claims.js) encodes `permissions` as a JSON array,
    # exactly as go-common's identity.Context.Permissions []string already
    # documents it. Previously typed Dict[str, Any] with a .get()-based
    # has_permission(), which crashed with AttributeError against any real
    # token (KD-015, platform-docs/security/known-deviations.md).
    permissions: List[str] = field(default_factory=list)

    # Campos opcionales (punteros en Go)
    organization_id: Optional[str] = None
    parent_key_id: Optional[str] = None

    def validate(self) -> None:
        """Valida que los campos obligatorios sean correctos."""
        if not self.tenant_id:
            raise TenantRequiredError("Tenant ID es requerido")

        if not self.owner_id:
            raise OwnerIdRequiredError("Owner ID es requerido")

        if not isinstance(self.owner_type, OwnerType):
            raise InvalidOwnerTypeError(
                "OwnerType debe ser un miembro del Enum OwnerType"
            )

    def can_certify_level(self, level: int) -> bool:
        """Determina si puede certificar un nivel específico."""
        return self.can_certify and self.max_cert_level >= level

    def has_permission(self, name: str) -> bool:
        """Chequea membership en la lista plana de codes de permiso —
        equivalente exacto a go-common's identity.Context.HasPermission
        (slices.Contains). Único punto de verdad: tanto el dependency de
        ruta (require_admin) como las reglas de autorización dentro de un
        caso de uso (p. ej. CreateCAUseCase) llaman acá, nunca duplican esta
        lógica."""
        return name in self.permissions
