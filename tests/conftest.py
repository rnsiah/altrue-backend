"""
Minimal pytest configuration for Altrue backend.
Uses existing Django settings with test overrides.
"""
import pytest
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
