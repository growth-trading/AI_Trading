"""
Entry point cho Waitress WSGI server (production on Windows).
Chạy: python serve.py
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aitrading.settings')

from waitress import serve
from aitrading.wsgi import application

HOST   = os.environ.get('WAITRESS_HOST',    '127.0.0.1')
PORT   = int(os.environ.get('WAITRESS_PORT',    '8000'))
THREADS = int(os.environ.get('WAITRESS_THREADS', '8'))

if __name__ == '__main__':
    print(f'Starting Waitress on {HOST}:{PORT} with {THREADS} threads...')
    serve(application, host=HOST, port=PORT, threads=THREADS)
