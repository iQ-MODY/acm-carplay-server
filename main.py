import os
import time
import uuid
import base64
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding

app = FastAPI(title="ACM Auto CarPlay MFi Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# MFi Certificate & Key Management
# -----------------------------------------------------------------------------
CERT_FILE = os.environ.get("MFI_CERT_FILE", "mfi_cert.der")
KEY_FILE = os.environ.get("MFI_KEY_FILE", "mfi_key.pem")

def get_or_create_key_and_cert():
    # If custom files exist, load them
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(CERT_FILE, "rb") as f:
            cert_der = f.read()
        return private_key, cert_der

    # If scratch_key.der exists in parent or current dir, we can use it
    possible_keys = ["scratch_key.der", "../scratch_key.der"]
    for pk in possible_keys:
        if os.path.exists(pk):
            try:
                with open(pk, "rb") as f:
                    private_key = serialization.load_der_private_key(f.read(), password=None)
                    # Generate an X509 certificate for this key
                    subject = issuer = x509.Name([
                        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Apple Inc."),
                        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "MFi"),
                        x509.NameAttribute(NameOID.COMMON_NAME, "Apple MFi Authentication Coprocessor"),
                    ])
                    cert = x509.CertificateBuilder().subject_name(
                        subject
                    ).issuer_name(
                        issuer
                    ).public_key(
                        private_key.public_key()
                    ).serial_number(
                        x509.random_serial_number()
                    ).not_valid_before(
                        datetime.now(timezone.utc) - timedelta(days=365)
                    ).not_valid_after(
                        datetime.now(timezone.utc) + timedelta(days=3650)
                    ).sign(private_key, hashes.SHA256())
                    return private_key, cert.public_bytes(serialization.Encoding.DER)
            except Exception as e:
                print("Could not load scratch_key.der:", e)

    # Fallback: Generate a dedicated RSA 2048-bit key and X.509 MFi Certificate
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Apple Inc."),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "MFi"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Apple MFi Authentication Coprocessor"),
    ])
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.now(timezone.utc) - timedelta(days=365)
    ).not_valid_after(
        datetime.now(timezone.utc) + timedelta(days=3650)
    ).sign(private_key, hashes.SHA256())

    cert_der = cert.public_bytes(serialization.Encoding.DER)
    return private_key, cert_der

MFI_PRIVATE_KEY, MFI_CERT_DER = get_or_create_key_and_cert()
MFI_CERT_BASE64 = base64.b64encode(MFI_CERT_DER).decode("utf-8")

# In-memory storage for active challenges and registered devices
active_challenges = {}
registered_devices = {}

# -----------------------------------------------------------------------------
# Pydantic Request Models
# -----------------------------------------------------------------------------
class ChallengeRequest(BaseModel):
    device_id: str
    license_number: Optional[str] = "ACM-ACTIVE"
    device_public_key: Optional[str] = None
    app_package: Optional[str] = None
    app_version: Optional[str] = None

class EntitlementSyncRequest(BaseModel):
    challenge_id: str
    device_proof: Optional[str] = None

class HandshakeCertRequest(BaseModel):
    request_id: str
    device_id: str
    timestamp: int
    signature: Optional[str] = None

class HandshakeSignRequest(BaseModel):
    request_id: str
    device_id: str
    timestamp: int
    challenge: str
    signature: Optional[str] = None

# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@app.get("/")
def index():
    return {
        "service": "ACM Auto CarPlay MFi Server",
        "status": "online",
        "version": "1.0.0",
        "mode": "free-unlimited"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/v1/challenges")
def create_challenge(req: ChallengeRequest):
    cid = str(uuid.uuid4())
    nonce = str(uuid.uuid4())
    lic = req.license_number or "ACM-ACTIVE"
    # Format expected by TM Auto:
    # tm-auto-device-proof-v1\n<challenge_id>\n<nonce>\n<device_id>\n<license_number>
    signing_payload = f"tm-auto-device-proof-v1\n{cid}\n{nonce}\n{req.device_id}\n{lic}"
    
    active_challenges[cid] = {
        "device_id": req.device_id,
        "nonce": nonce,
        "signing_payload": signing_payload,
        "created_at": time.time()
    }
    registered_devices[req.device_id] = True
    
    return {
        "challenge_id": cid,
        "nonce": nonce,
        "signing_payload": signing_payload
    }

@app.post("/api/v1/entitlements/sync")
def sync_entitlements(req: EntitlementSyncRequest):
    # Free lifetime full activation for all devices!
    cid = req.challenge_id
    dev_info = active_challenges.get(cid, {})
    dev_id = dev_info.get("device_id", "ACM-DEVICE")
    registered_devices[dev_id] = True
    
    # Return active entitlement
    fake_token = base64.urlsafe_b64encode(b"ACM-ACTIVE-LIFETIME-TOKEN").decode("utf-8").rstrip("=")
    return {
        "status": "active",
        "active": True,
        "token": fake_token,
        "entitlement": {
            "tier": "full",
            "features": ["carplay", "android_auto", "wireless_carplay"],
            "license_number": "ACM-ACTIVE",
            "device_id": dev_id
        }
    }

@app.post("/api/v1/handshake/certificate")
def handshake_certificate(req: HandshakeCertRequest):
    # Protocol Major 2: RSA-based Apple MFi authentication
    # Protocol Major 3: ECDSA-based Apple MFi authentication
    return {
        "protocol_major": 2,
        "certificate": MFI_CERT_BASE64
    }

@app.post("/api/v1/handshake/sign")
def handshake_sign(req: HandshakeSignRequest):
    challenge_b64url = req.challenge
    try:
        # Challenge from Android app is base64url encoded without padding
        padding_needed = 4 - (len(challenge_b64url) % 4)
        if padding_needed and padding_needed != 4:
            challenge_b64url += "=" * padding_needed
        challenge_bytes = base64.urlsafe_b64decode(challenge_b64url)
        
        # MFi Protocol 2 signs the challenge digest with PKCS#1 v1.5
        # The challenge is either a 20-byte SHA-1 digest or a raw nonce
        if len(challenge_bytes) == 20:
            # Direct signature with PKCS#1 v1.5 and SHA1
            signature = MFI_PRIVATE_KEY.sign(
                challenge_bytes,
                padding.PKCS1v15(),
                hashes.SHA1()
            )
        else:
            # Standard signature
            signature = MFI_PRIVATE_KEY.sign(
                challenge_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
        # Android app decodes response using decodeBounded with URL_SAFE
        resp_b64url = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
        return {
            "response": resp_b64url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signing failed: {str(e)}")

@app.post("/api/v1/diagnostics")
def diagnostics(req: Request):
    return {"status": "received"}

if __name__ == "__main__":
    import uvicorn
    port_str = os.environ.get("PORT", "8080")
    try:
        port = int(port_str)
    except (ValueError, TypeError):
        port = 8080
    print(f"Starting ACM MFi Server on 0.0.0.0:{port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)

