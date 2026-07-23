"""
H4CK3R Wordlist Generator
=========================
Launches the hacker-themed GUI by default.
The CLI mode is still available via ``python -m wordlist_generator.cli``.
"""

from wordlist_generator.app import launch


def main() -> None:
    """Launch the H4CK3R Wordlist Generator Desktop GUI."""
    launch()


if __name__ == "__main__":
    main()

