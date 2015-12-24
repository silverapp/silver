#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    if os.path.isfile(os.path.join(os.path.dirname(__file__),
                                   'settings_local.py')):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings_local')
    else:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
