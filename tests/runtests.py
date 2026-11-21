#!/usr/bin/env python
"""Запуск регрессионных тестов wagtail-desktop-publisher с гарантией
wheel-импорта: падает, если пакет импортирован из исходников.

    python runtests.py
"""
import os
import sys

import django

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:] = [p for p in sys.path
               if os.path.abspath(p or ".") != _repo_root]
sys.path.append(_repo_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
django.setup()

import wagtail_desktop_publisher  # noqa: E402

_pkg = wagtail_desktop_publisher.__file__.replace(os.sep, "/")
if "site-packages" not in _pkg:
    sys.exit(f"ОШИБКА: импортирован НЕ wheel: {_pkg}")
print("проверяемый пакет (wheel):", _pkg)

import django.conf  # noqa: E402
from django.test.utils import get_runner  # noqa: E402

runner = get_runner(django.conf.settings)(interactive=False, verbosity=1)
failures = runner.run_tests(["tests"])
sys.exit(bool(failures))
