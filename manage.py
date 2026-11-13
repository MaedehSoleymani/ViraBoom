#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
<<<<<<< HEAD
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
=======
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'viraboom.settings')
>>>>>>> a3390943c75568a903668ee7d6076997ba2ef9df
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
<<<<<<< HEAD
            "Django نصب نیست. ابتدا محیط مجازی را فعال و requirements.txt را نصب کنید."
=======
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
>>>>>>> a3390943c75568a903668ee7d6076997ba2ef9df
        ) from exc
    execute_from_command_line(sys.argv)


<<<<<<< HEAD
if __name__ == "__main__":
=======
if __name__ == '__main__':
>>>>>>> a3390943c75568a903668ee7d6076997ba2ef9df
    main()
