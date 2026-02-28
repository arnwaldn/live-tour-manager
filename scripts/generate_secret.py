#!/usr/bin/env python3
"""
Generate a secure SECRET_KEY for production deployment.

Usage:
    python scripts/generate_secret.py

The generated key is suitable for use in:
- Railway environment variables
- Docker Compose .env files
- Any production environment
"""
import secrets


def generate_secret_key(length: int = 32) -> str:
    """Generate a cryptographically secure secret key.

    Args:
        length: Number of bytes (will produce hex string of 2x length)

    Returns:
        Hex-encoded secret key string
    """
    return secrets.token_hex(length)


if __name__ == "__main__":
    key = generate_secret_key()
    print("\n" + "=" * 60)
    print("SECRET KEY GENERATOR - GigRoute")
    print("=" * 60)
    print(f"\nSECRET_KEY={key}")
    print("\n" + "-" * 60)
    print("Instructions:")
    print("1. Copiez cette cle dans vos variables d'environnement")
    print("2. Sur Railway: Dashboard > Variables > Add Variable")
    print("3. NE PARTAGEZ JAMAIS cette cle!")
    print("=" * 60 + "\n")
