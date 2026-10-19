"""
Gunicorn settings, loaded automatically from the working directory (/app).

The start command in backend.entrypoint.sh must stay unchanged, so the
server is tuned here instead.
"""

# With the default single sync worker, one idle browser connection (e.g. a
# preconnect) blocks every other request until the worker times out.
# Threaded workers keep serving requests while such connections stay open.
worker_class = 'gthread'
workers = 2
threads = 4

# Video uploads through the admin can take longer than the 30 s default.
timeout = 300
