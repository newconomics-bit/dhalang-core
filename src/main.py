"""Main entry point for Dhalang-Core."""

import logging

from src.dhalang import Dhalang


def main() -> None:
    """Run Dhalang with sample inputs."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # Create Dhalang orchestrator
    dhalang = Dhalang()

    # Test case 1: Security scan
    print("\n" + "=" * 70)
    print("TEST 1: Cek subdomain target.com")
    print("=" * 70)
    result1 = dhalang.proses("Cek subdomain target.com")
    print(result1)

    # Test case 2: Code analysis
    print("\n" + "=" * 70)
    print("TEST 2: Analisis bug di code login")
    print("=" * 70)
    result2 = dhalang.proses("Analisis bug di code login")
    print(result2)

    # Test case 3: Chain delegation (security audit + code analysis)
    print("\n" + "=" * 70)
    print("TEST 3: Audit keamanan target.com dan cek code backend-nya")
    print("=" * 70)
    result3 = dhalang.proses("Audit keamanan target.com dan cek code backend-nya")
    print(result3)


if __name__ == "__main__":
    main()