#!/usr/bin/env python3
"""Şifre hash'leme aracı - .env dosyası için bcrypt hash üretir."""

import sys

import bcrypt


def main() -> None:
    if len(sys.argv) != 2:
        print("Kullanım: python scripts/hash_password.py <şifre>")
        sys.exit(1)

    password = sys.argv[1].encode("utf-8")
    hashed = bcrypt.hashpw(password, bcrypt.gensalt()).decode("utf-8")
    print(f"\nADMIN_PASSWORD_HASH={hashed}")
    print("\nBu değeri .env dosyanıza ekleyin.")


if __name__ == "__main__":
    main()
