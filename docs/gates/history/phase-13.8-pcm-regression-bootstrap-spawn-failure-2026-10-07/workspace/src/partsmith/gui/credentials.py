"""Provider credentials stored only in the host OS credential store."""

import sys


class CredentialError(Exception):
    """A safe, non-secret credential-store failure."""


class CredentialStore:
    """Use a specific native backend, never plaintext fallbacks."""

    def __init__(self, provider="OpenAI", backend=None):
        self.provider = provider
        self.service = f"PartSmith/AI/{provider}"
        self.backend = backend

    def _backend(self):
        if self.backend is None:
            try:
                if sys.platform == "win32":
                    from keyring.backends.Windows import WinVaultKeyring

                    self.backend = WinVaultKeyring()
                elif sys.platform == "darwin":
                    from keyring.backends.macOS import Keyring

                    self.backend = Keyring()
                else:
                    from keyring.backends.SecretService import Keyring

                    self.backend = Keyring()
                if self.backend.priority <= 0:
                    raise CredentialError()
            except Exception:
                raise CredentialError(
                    "Secure credential storage is unavailable."
                ) from None
        return self.backend

    def read_for_processing(self):
        """Read internally for authentication/redaction; never bind to UI."""
        try:
            return self._backend().get_password(self.service, "api-key")
        except Exception:
            raise CredentialError(
                "Could not read the secure credential store."
            ) from None

    def configured(self):
        return bool(self.read_for_processing())

    def save(self, key):
        if not key.strip():
            raise CredentialError("Enter a nonblank API key.")
        try:
            self._backend().set_password(self.service, "api-key", key)
        except Exception:
            raise CredentialError(
                "Could not save the API key in secure credential storage."
            ) from None
