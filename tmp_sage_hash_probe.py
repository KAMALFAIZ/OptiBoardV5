import hashlib, uuid

def sage_hash(guid_str: str, password: str) -> str:
    raw = uuid.UUID(guid_str).bytes_le
    return hashlib.sha256(raw + password.encode("utf-8")).hexdigest().upper()

# Verification on known pair
assert sage_hash("92461CF1-020E-4532-8CB9-71FAFB3E5CF9", "M@bosggr2019") == \
    "31529A2D1AD7AA106973079BE32E429503A68B928CDC86245FAD86EBDF44140A"
print("self-check OK")

# Target: Administrateur
ADMIN_GUID = "77384016-921F-472F-B56D-1D563B7DDF3C"
NEW_PWD = "M@BOSGGR2025"
h = sage_hash(ADMIN_GUID, NEW_PWD)
print(f"New PROT_Hash for <Administrateur> = 0x{h}")
