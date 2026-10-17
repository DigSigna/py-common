"""Shared Python infrastructure for DigSigna's Python microservices.

Extracted from certificate-service (and verified byte-for-byte identical in
signing-service at the time of extraction): JWT/JWKS auth, hybrid audit
logging, idempotency, and the structured logger/request-context plumbing
they depend on. See each submodule's docstring for the equivalent Go
reference in hsm-service where one exists.
"""

__version__ = "0.1.0"
