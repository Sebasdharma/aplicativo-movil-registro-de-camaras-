import argparse
import ipaddress
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def write_private_key(path, key):
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_or_create_ca(output_dir):
    ca_key_path = output_dir / "local-ca.key"
    ca_cert_path = output_dir / "local-ca.crt"
    if ca_key_path.exists() != ca_cert_path.exists():
        raise RuntimeError(
            "El certificado local está incompleto; conserva ambos archivos "
            "de la CA o retíralos juntos antes de generarlos de nuevo."
        )
    if ca_key_path.exists():
        ca_key = serialization.load_pem_private_key(
            ca_key_path.read_bytes(),
            password=None,
        )
        ca_cert = x509.load_pem_x509_certificate(ca_cert_path.read_bytes())
        return ca_key, ca_cert

    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    name = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AsisTech local"),
        x509.NameAttribute(NameOID.COMMON_NAME, "AsisTech local camera CA"),
    ])
    now = datetime.now(timezone.utc)
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=None,
                decipher_only=None,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )
    write_private_key(ca_key_path, ca_key)
    ca_cert_path.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    return ca_key, ca_cert


def create_server_certificate(ip_address, output_dir):
    ca_key, ca_cert = load_or_create_ca(output_dir)
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AsisTech local"),
        x509.NameAttribute(NameOID.COMMON_NAME, str(ip_address)),
    ])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=397))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.IPAddress(ip_address),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                x509.DNSName("localhost"),
            ]),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    write_private_key(output_dir / "server.key", server_key)
    (output_dir / "server.crt").write_bytes(
        certificate.public_bytes(serialization.Encoding.PEM)
    )


def main():
    parser = argparse.ArgumentParser(
        description="Genera un certificado HTTPS local para la cámara web AsisTech."
    )
    parser.add_argument("ip_address", help="IPv4 actual del equipo que ejecuta el backend")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "certs",
    )
    args = parser.parse_args()
    ip_address = ipaddress.ip_address(args.ip_address)
    if not isinstance(ip_address, ipaddress.IPv4Address):
        parser.error("Usa una dirección IPv4 para la red Wi-Fi local.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    create_server_certificate(ip_address, args.output_dir)
    print(f"Certificado del servidor: {args.output_dir / 'server.crt'}")
    print(f"Clave privada del servidor: {args.output_dir / 'server.key'}")
    print(f"Certificado para instalar en Android: {args.output_dir / 'local-ca.crt'}")
    print("No copies ni compartas local-ca.key ni server.key.")


if __name__ == "__main__":
    main()
