#!/usr/bin/env python3
"""
QwenCloud Credential Store

Secure credential storage with automatic backend selection:
  1. KeyringBackend  — system keychain (requires `keyring` package, optional)
  2. EncryptedFileBackend — AES-256-GCM encrypted file (requires `cryptography`)

Design reference: ref/usage-api/safe-store-access-token.md
"""

import hashlib
import json
import logging
import os
import platform
import re
import stat
import subprocess
import sys
import uuid
from abc import ABC, abstractmethod
from base64 import b64decode, b64encode
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

_SERVICE_NAME = "qwencloud-cli"

# ══════════════════════════════════════════════════════════════════════════════
# Machine Encryption Key
# ══════════════════════════════════════════════════════════════════════════════

def _run(cmd: List[str], timeout: int = 5) -> str:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, errors="ignore",
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _win_machine_guid() -> str:
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography"
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return value
    except Exception:
        return ""


def _win_motherboard_uuid() -> str:
    out = _run(["wmic", "csproduct", "get", "UUID", "/value"])
    m = re.search(r"UUID=(.+)", out)
    return m.group(1).strip() if m else ""


def _win_cpu_id() -> str:
    out = _run(["wmic", "cpu", "get", "ProcessorId", "/value"])
    m = re.search(r"ProcessorId=(.+)", out)
    return m.group(1).strip() if m else ""


def _get_windows_sources() -> List[str]:
    return [_win_machine_guid(), _win_motherboard_uuid(), _win_cpu_id()]


def _mac_hardware_uuid() -> str:
    out = _run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"])
    m = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', out)
    return m.group(1) if m else ""


def _mac_serial_number() -> str:
    out = _run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"])
    m = re.search(r'"IOPlatformSerialNumber"\s*=\s*"([^"]+)"', out)
    return m.group(1) if m else ""


def _mac_cpu_brand() -> str:
    return _run(["sysctl", "-n", "machdep.cpu.brand_string"])


def _mac_kern_uuid() -> str:
    return _run(["sysctl", "-n", "kern.uuid"])


def _get_macos_sources() -> List[str]:
    return [_mac_hardware_uuid(), _mac_serial_number(), _mac_cpu_brand(), _mac_kern_uuid()]


def _linux_machine_id() -> str:
    for p in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
        path = Path(p)
        if path.exists():
            return path.read_text().strip()
    return ""


def _linux_dmi_field(field: str) -> str:
    path = Path(f"/sys/class/dmi/id/{field}")
    if path.exists():
        try:
            return path.read_text().strip()
        except PermissionError:
            pass
    return _run(["dmidecode", "-s", field.replace("_", "-")])


def _get_linux_sources() -> List[str]:
    return [
        _linux_machine_id(),
        _linux_dmi_field("product_uuid"),
        _linux_dmi_field("product_serial"),
        _linux_dmi_field("board_serial"),
    ]


def _is_physical_mac(mac: str) -> bool:
    """Return True if *mac* (colon-separated lowercase) is a real hardware address."""
    if mac == "00:00:00:00:00:00":
        return False
    first_byte = int(mac.split(":")[0], 16)
    if (first_byte & 0x01) != 0:   # multicast
        return False
    if (first_byte & 0x02) != 0:   # locally-administered / randomized
        return False
    return True


def _stable_mac() -> str:
    """
    Return a stable physical MAC address for use as an encryption key dimension.

    uuid.getnode() is NOT used: on macOS it returns the interface MAC which is
    often randomized (locally-administered bit set), causing the derived key to
    change across network events or reboots.

    Platform strategy:
      - macOS:   ``networksetup -listallhardwareports`` reports the factory
                 Ethernet Address even when the kernel randomizes the active one.
                 Falls back to ``ifconfig`` if networksetup is unavailable.
      - Linux:   ``ifconfig`` (or ``ip link``) with locally-administered filter.
      - Windows: ``ipconfig /all`` — Physical Address lines (dash-separated).
    """
    try:
        system = platform.system()
        if system == "Darwin":
            return _stable_mac_macos()
        if system == "Windows":
            return _stable_mac_windows()
        return _stable_mac_unix()
    except Exception:
        return ""


def _stable_mac_macos() -> str:
    """macOS: prefer networksetup for factory MACs, fall back to ifconfig."""
    out = _run(["networksetup", "-listallhardwareports"])
    if out:
        macs = []
        for m in re.finditer(
            r"Ethernet\s+Address:\s+([0-9a-f]{2}(?::[0-9a-f]{2}){5})", out, re.I,
        ):
            mac = m.group(1).lower()
            if _is_physical_mac(mac):
                macs.append(mac)
        if macs:
            return min(macs)
    return _stable_mac_unix()


def _stable_mac_unix() -> str:
    """Linux / generic Unix: parse ``ifconfig`` ether lines."""
    out = _run(["ifconfig"])
    macs = []
    for m in re.finditer(r"ether\s+([0-9a-f]{2}(?::[0-9a-f]{2}){5})", out, re.I):
        mac = m.group(1).lower()
        if _is_physical_mac(mac):
            macs.append(mac)
    return min(macs) if macs else ""


def _stable_mac_windows() -> str:
    """Windows: parse ``ipconfig /all`` Physical Address lines."""
    out = _run(["ipconfig", "/all"])
    macs = []
    for m in re.finditer(
        r"Physical\s+Address[\s.]*:\s+([0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){5})", out,
    ):
        mac = m.group(1).replace("-", ":").lower()
        if _is_physical_mac(mac):
            macs.append(mac)
    return min(macs) if macs else ""


def get_machine_key() -> bytes:
    """
    Collect multi-dimensional hardware info and derive a 32-byte SHA-256
    encryption key. Partial source failures are tolerated.
    """
    system = platform.system()
    if system == "Windows":
        sources = _get_windows_sources()
    elif system == "Darwin":
        sources = _get_macos_sources()
    elif system == "Linux":
        sources = _get_linux_sources()
    else:
        sources = []

    sources.append(_stable_mac())
    sources.append(platform.machine())

    combined = "|".join(s for s in sources if s).encode("utf-8")
    if not combined:
        raise RuntimeError(
            "Cannot collect any hardware information for encryption key derivation. "
            "Check system permissions or platform support."
        )
    return hashlib.sha256(combined).digest()


# ══════════════════════════════════════════════════════════════════════════════
# HostID Fallback (when hardware key derivation is unavailable)
# ══════════════════════════════════════════════════════════════════════════════

def _host_id_candidates() -> List[Path]:
    candidates = [Path.home() / ".qwencloud" / "host_id"]
    if os.name != "nt":
        candidates.append(Path("/etc/qwencloud-host-id"))
    else:
        appdata = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        candidates.append(Path(appdata) / "qwencloud" / "host_id")
    return candidates


def _get_or_create_host_id() -> str:
    candidates = _host_id_candidates()
    for path in candidates:
        try:
            content = path.read_text(encoding="utf-8").strip()
            if len(content) >= 32:
                return content
        except OSError:
            continue

    new_id = str(uuid.uuid4())
    for path in candidates:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new_id, encoding="utf-8")
            if os.name != "nt":
                os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            log.info("HostID written to: %s", path)
            return new_id
        except OSError as e:
            log.debug("Failed to write HostID to %s: %s", path, e)
    raise RuntimeError(
        f"Cannot write HostID to any path: {[str(p) for p in candidates]}"
    )


def _get_machine_key_or_fallback() -> bytes:
    """Try hardware-based encryption key first, fall back to HostID."""
    try:
        return get_machine_key()
    except RuntimeError:
        log.debug("Hardware key derivation unavailable, falling back to HostID")
    host_id = _get_or_create_host_id()
    return hashlib.sha256(host_id.encode("utf-8")).digest()


# ══════════════════════════════════════════════════════════════════════════════
# AES-256-GCM Cipher (for EncryptedFileBackend)
# ══════════════════════════════════════════════════════════════════════════════

_FORMAT_VERSION = 1
_PBKDF2_ITERATIONS = 260_000
_KEY_LEN = 32
_NONCE_LEN = 12
_SALT_LEN = 32


def _derive_key(machine_key: bytes, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_LEN,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return kdf.derive(machine_key)


def _encrypt_dict(data: Dict[str, Any], machine_key: bytes) -> dict:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt = os.urandom(_SALT_LEN)
    nonce = os.urandom(_NONCE_LEN)
    key = _derive_key(machine_key, salt)
    plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, associated_data=None)
    return {
        "version": _FORMAT_VERSION,
        "salt": b64encode(salt).decode(),
        "nonce": b64encode(nonce).decode(),
        "ciphertext": b64encode(ciphertext).decode(),
    }


def _decrypt_dict(envelope: dict, machine_key: bytes) -> Dict[str, Any]:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    version = envelope.get("version")
    if version != _FORMAT_VERSION:
        raise ValueError(f"Unsupported credential file version: {version}")
    salt = b64decode(envelope["salt"])
    nonce = b64decode(envelope["nonce"])
    ciphertext = b64decode(envelope["ciphertext"])
    key = _derive_key(machine_key, salt)
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, associated_data=None)
    except Exception as e:
        raise ValueError(
            "Decryption failed: machine encryption key mismatch or file corrupted"
        ) from e
    return json.loads(plaintext.decode("utf-8"))


# ══════════════════════════════════════════════════════════════════════════════
# Backend Abstraction
# ══════════════════════════════════════════════════════════════════════════════

class BaseBackend(ABC):
    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def get(self, service: str, key: str) -> Optional[str]: ...

    @abstractmethod
    def set(self, service: str, key: str, value: str) -> None: ...

    @abstractmethod
    def delete(self, service: str, key: str) -> None: ...


_KEYRING_PROBE_KEY = "__qwencloud_probe__"
_KEYRING_PROBE_VAL = "ok"


def _system_has_keyring_support() -> bool:
    """
    Heuristic: return True if the current platform is likely to have a working
    system keychain without needing any extra daemons.

      - macOS  : always True (Keychain is part of the OS)
      - Windows: always True (DPAPI / Credential Manager)
      - Linux  : True only when a Secret Service bus name is registered
                 (i.e. gnome-keyring / kwallet is running)
    """
    system = platform.system()
    if system in ("Darwin", "Windows"):
        return True
    if system == "Linux":
        # Check if org.freedesktop.secrets is present on the session D-Bus
        try:
            out = _run(
                ["dbus-send", "--session", "--print-reply",
                 "--dest=org.freedesktop.DBus",
                 "/org/freedesktop/DBus",
                 "org.freedesktop.DBus.ListNames"],
                timeout=3,
            )
            return "org.freedesktop.secrets" in out
        except Exception:
            return False
    return False


def _try_install_keyring() -> bool:
    """
    Attempt to install the ``keyring`` package into the current Python
    environment via pip.  Returns True on success, False on failure.

    The install is silent (stdout/stderr suppressed) to avoid polluting
    the skill output.  A one-line progress message is printed to stderr.
    """
    print(
        "[credential-store] keyring package not found — attempting: "
        "pip install keyring ...",
        file=sys.stderr,
    )
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "keyring"],
            capture_output=True,
            timeout=60,
        )
        if result.returncode == 0:
            print("[credential-store] keyring installed successfully.", file=sys.stderr)
            return True
        stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
        print(
            f"[credential-store] pip install keyring failed (rc={result.returncode}): "
            f"{stderr_text[:200]}",
            file=sys.stderr,
        )
        return False
    except Exception as e:
        print(f"[credential-store] pip install keyring error: {e}", file=sys.stderr)
        return False


def _import_keyring():
    """
    Import and return the ``keyring`` module, auto-installing it when:
      1. The system platform has a native keychain (macOS, Windows, or Linux
         with Secret Service), AND
      2. The package is not yet installed.

    Returns the module on success, None if unavailable.
    """
    # Fast path: already importable
    try:
        import keyring as _kr
        return _kr
    except ImportError:
        pass

    # Only auto-install when the platform has a real keychain
    if not _system_has_keyring_support():
        log.debug("keyring skipped: platform has no system keychain")
        return None

    if not _try_install_keyring():
        return None

    # Invalidate import caches so the freshly installed package is visible
    import importlib
    importlib.invalidate_caches()
    try:
        import keyring as _kr
        return _kr
    except ImportError as e:
        log.debug("keyring still not importable after install: %s", e)
        return None


class KeyringBackend(BaseBackend):
    name = "keyring"

    def is_available(self) -> bool:
        """
        Ensure the keyring package is present (auto-installing if needed),
        then perform an actual round-trip write + read + delete probe.

        Name-only checks are insufficient: macOS Keychain reports a valid
        backend name even in headless/CLI environments where actual operations
        silently fail or block on GUI dialogs.
        """
        _kr = _import_keyring()
        if _kr is None:
            return False

        try:
            import keyring.errors

            backend = _kr.get_keyring()
            backend_name = type(backend).__name__
            _NO_OP = ("FailKeyring", "NullKeyring", "PlaintextKeyring")
            if any(n in backend_name for n in _NO_OP):
                log.debug("keyring backend %s is unusable", backend_name)
                return False

            # Real round-trip probe: write → read → delete
            _kr.set_password(_SERVICE_NAME, _KEYRING_PROBE_KEY, _KEYRING_PROBE_VAL)
            val = _kr.get_password(_SERVICE_NAME, _KEYRING_PROBE_KEY)
            try:
                _kr.delete_password(_SERVICE_NAME, _KEYRING_PROBE_KEY)
            except keyring.errors.PasswordDeleteError:
                pass

            if val != _KEYRING_PROBE_VAL:
                log.debug("keyring round-trip probe failed (got %r)", val)
                return False

            log.debug("keyring backend ready: %s", backend_name)
            return True

        except Exception as e:
            log.debug("keyring unavailable: %s", e)
            return False

    def get(self, service: str, key: str) -> Optional[str]:
        import keyring
        return keyring.get_password(service, key)

    def set(self, service: str, key: str, value: str) -> None:
        import keyring
        keyring.set_password(service, key, value)

    def delete(self, service: str, key: str) -> None:
        import keyring
        import keyring.errors
        try:
            keyring.delete_password(service, key)
        except keyring.errors.PasswordDeleteError:
            pass


class EncryptedFileBackend(BaseBackend):
    """
    AES-256-GCM encrypted JSON file backend.
    Key is derived from the machine encryption key via PBKDF2.
    """
    name = "encrypted_file"

    _QWENCLOUD_DIR = Path.home() / ".qwencloud"

    def __init__(self, credentials_dir: Optional[str] = None, filename: Optional[str] = None):
        if credentials_dir:
            self._dir = Path(credentials_dir)
        else:
            env_dir = os.environ.get("QWENCLOUD_CREDENTIALS_DIR")
            if env_dir:
                self._dir = Path(env_dir)
            else:
                self._dir = self._QWENCLOUD_DIR
        self._filename = filename
        self._machine_key: Optional[bytes] = None

    def _get_machine_key(self) -> bytes:
        if self._machine_key is None:
            self._machine_key = _get_machine_key_or_fallback()
        return self._machine_key

    def _file_path(self, service: str) -> Path:
        if self._filename:
            return self._dir / self._filename
        safe_name = re.sub(r"[^\w\-.]", "_", service)
        return self._dir / f"{safe_name}.enc.json"

    def is_available(self) -> bool:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
            return True
        except ImportError:
            return False

    def _load_store(self, service: str) -> Dict[str, str]:
        fp = self._file_path(service)
        if not fp.exists():
            return {}
        try:
            with open(fp, "r", encoding="utf-8") as f:
                envelope = json.load(f)
            return _decrypt_dict(envelope, self._get_machine_key())
        except (ValueError, json.JSONDecodeError, KeyError) as e:
            log.warning("Failed to decrypt credential file %s: %s", fp, e)
            return {}

    def _save_store(self, service: str, data: Dict[str, str]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        fp = self._file_path(service)
        envelope = _encrypt_dict(data, self._get_machine_key())
        tmp_path = str(fp) + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(envelope, f)
        os.replace(tmp_path, str(fp))
        if os.name != "nt":
            os.chmod(fp, stat.S_IRUSR | stat.S_IWUSR)

    def get(self, service: str, key: str) -> Optional[str]:
        store = self._load_store(service)
        return store.get(key)

    def set(self, service: str, key: str, value: str) -> None:
        store = self._load_store(service)
        store[key] = value
        self._save_store(service, store)

    def delete(self, service: str, key: str) -> None:
        store = self._load_store(service)
        if key in store:
            del store[key]
            if store:
                self._save_store(service, store)
            else:
                fp = self._file_path(service)
                if fp.exists():
                    fp.unlink()


# ══════════════════════════════════════════════════════════════════════════════
# SecureStore — Unified Facade
# ══════════════════════════════════════════════════════════════════════════════

class SecureStore:
    """
    Unified credential store with automatic backend selection.
    Priority: keyring (system keychain) > encrypted file.
    """

    def __init__(self, credentials_dir: Optional[str] = None):
        self._backend: Optional[BaseBackend] = None
        self._credentials_dir = credentials_dir

    def _select_backend(self) -> BaseBackend:
        if self._backend is not None:
            return self._backend

        kr = KeyringBackend()
        if kr.is_available():
            self._backend = kr
            log.debug("Using keyring backend")
            return kr

        ef = EncryptedFileBackend(self._credentials_dir)
        if ef.is_available():
            self._backend = ef
            log.debug("Using encrypted file backend")
            return ef

        raise RuntimeError(
            "No credential storage backend available. "
            "Install cryptography (pip install cryptography) or keyring (pip install keyring)."
        )

    def get(self, key: str) -> Optional[str]:
        try:
            return self._select_backend().get(_SERVICE_NAME, key)
        except Exception as e:
            log.warning("SecureStore.get failed for key=%s: %s", key, e)
            return None

    def set(self, key: str, value: str) -> None:
        try:
            self._select_backend().set(_SERVICE_NAME, key, value)
        except Exception as e:
            log.warning(
                "SecureStore.set failed for key=%s: %s — token will not be cached, "
                "re-authentication will be required on the next run.",
                key, e,
            )

    def delete(self, key: str) -> None:
        try:
            self._select_backend().delete(_SERVICE_NAME, key)
        except Exception as e:
            log.debug("SecureStore.delete failed for key=%s: %s", key, e)


# Module-level singleton
_store: Optional[SecureStore] = None


def get_store() -> SecureStore:
    global _store
    if _store is None:
        _store = SecureStore()
    return _store


def diagnose() -> dict:
    """
    Return diagnostic information about the active credential store backend.
    Useful for debugging why tokens are not being cached across runs.

    Example:
        from credential_store import diagnose
        import json; print(json.dumps(diagnose(), indent=2))
    """
    info: dict = {}
    store = get_store()
    try:
        backend = store._select_backend()
        info["backend"] = backend.name
        if isinstance(backend, EncryptedFileBackend):
            info["credentials_dir"] = str(backend._dir)
            info["credentials_file"] = str(backend._file_path(_SERVICE_NAME))
            info["file_exists"] = backend._file_path(_SERVICE_NAME).exists()
        info["has_token"] = store.get("access_token") is not None
    except Exception as e:
        info["error"] = str(e)
    return info


# ══════════════════════════════════════════════════════════════════════════════
# CliCredentialStore — Device Flow Credential Management
# ══════════════════════════════════════════════════════════════════════════════

_CLI_CREDENTIALS_FILE = Path.home() / ".qwencloud" / "credentials"
_CLI_CREDENTIALS_ENC_KEY = "cli_credentials"  # key used in EncryptedFileBackend
_CLI_KEYRING_KEY = "cli_credentials"


def _cli_plaintext_mode() -> bool:
    """Return False — plaintext file storage is no longer configurable via environment variable."""
    return False


class CliCredentialStore:
    """
    Credential store for Device Flow (CLI mode) tokens.

    Priority:
      1. System keyring  (auto-detected; falls back if unavailable)
      2. AES-256-GCM encrypted file  (~/.qwencloud/credentials, machine encryption key)
      3. Plaintext file  (~/.qwencloud/credentials) — always read for one-time
         migration of existing credentials.
    """

    def __init__(self) -> None:
        # Store encrypted credentials as ~/.qwencloud/credentials (same name/dir
        # as the plaintext file); encryption is detected at load time by envelope format.
        self._enc = EncryptedFileBackend(str(Path.home() / ".qwencloud"), filename="credentials")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> Optional[dict]:
        creds = self._load_from_keyring()
        if creds:
            return creds

        creds = self._load_from_enc()
        if creds:
            return creds

        # One-time migration: promote existing plaintext file to encrypted store
        creds = self._load_from_plaintext_file()
        if creds:
            self.save(creds)
            _CLI_CREDENTIALS_FILE.unlink(missing_ok=True)
            log.info("CliCredentialStore: migrated plaintext credentials to encrypted store")
            return creds

        return None

    def save(self, creds: dict) -> None:
        if _cli_plaintext_mode():
            self._save_to_plaintext_file(creds)
            return

        if self._save_to_keyring(creds):
            self._clear_enc()
            return

        log.warning(
            "OS keyring is unavailable or write failed — "
            "falling back to encrypted file storage"
        )
        self._save_to_enc(creds)

    def clear(self) -> None:
        self._clear_keyring()
        self._clear_enc()
        try:
            _CLI_CREDENTIALS_FILE.unlink(missing_ok=True)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Keyring helpers
    # ------------------------------------------------------------------

    def _load_from_keyring(self) -> Optional[dict]:
        _kr = _import_keyring()
        if _kr is None:
            return None
        try:
            raw = _kr.get_password(_SERVICE_NAME, _CLI_KEYRING_KEY)
            if raw:
                return json.loads(raw)
        except Exception as e:
            log.debug("CliCredentialStore: keyring load failed: %s", e)
        return None

    def _save_to_keyring(self, creds: dict) -> bool:
        """Return True if credentials were persisted to OS keyring."""
        _kr = _import_keyring()
        if _kr is None:
            return False
        try:
            _kr.set_password(_SERVICE_NAME, _CLI_KEYRING_KEY, json.dumps(creds))
            return True
        except Exception as e:
            log.debug("CliCredentialStore: keyring save failed: %s", e)
            return False

    def _clear_keyring(self) -> None:
        _kr = _import_keyring()
        if _kr is None:
            return
        try:
            _kr.delete_password(_SERVICE_NAME, _CLI_KEYRING_KEY)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Encrypted file helpers
    # ------------------------------------------------------------------

    def _load_from_enc(self) -> Optional[dict]:
        try:
            raw = self._enc.get(_SERVICE_NAME, _CLI_CREDENTIALS_ENC_KEY)
            if raw:
                return json.loads(raw)
        except Exception as e:
            log.debug("CliCredentialStore: enc load failed: %s", e)
        return None

    def _save_to_enc(self, creds: dict) -> None:
        try:
            self._enc.set(_SERVICE_NAME, _CLI_CREDENTIALS_ENC_KEY, json.dumps(creds))
        except Exception as e:
            log.warning("CliCredentialStore: enc save failed: %s", e)

    def _clear_enc(self) -> None:
        try:
            self._enc.delete(_SERVICE_NAME, _CLI_CREDENTIALS_ENC_KEY)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Plaintext file helpers  (migration source)
    # ------------------------------------------------------------------

    def _load_from_plaintext_file(self) -> Optional[dict]:
        if not _CLI_CREDENTIALS_FILE.is_file():
            return None
        try:
            with open(_CLI_CREDENTIALS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("access_token"):
                return data
        except (json.JSONDecodeError, OSError) as e:
            log.debug("CliCredentialStore: plaintext file load failed: %s", e)
        return None

    def _save_to_plaintext_file(self, creds: dict) -> None:
        try:
            _CLI_CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = str(_CLI_CREDENTIALS_FILE) + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(creds, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, str(_CLI_CREDENTIALS_FILE))
            if os.name != "nt":
                os.chmod(_CLI_CREDENTIALS_FILE, stat.S_IRUSR | stat.S_IWUSR)
        except OSError as e:
            log.warning("CliCredentialStore: plaintext file save failed: %s", e)


# Module-level singleton
_cli_store: Optional[CliCredentialStore] = None


def get_cli_store() -> CliCredentialStore:
    global _cli_store
    if _cli_store is None:
        _cli_store = CliCredentialStore()
    return _cli_store
