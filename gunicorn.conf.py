"""
Gunicorn settings, loaded automatically from the working directory
(/app).

The start command in backend.entrypoint.sh must stay unchanged, so the
server is tuned here instead:

- Threaded workers: with the default single sync worker, one idle
  browser connection (e.g. a preconnect) blocks every other request
  until the worker times out.
- A longer timeout, because video uploads through the admin can take
  longer than the 30 s default.
"""

worker_class = 'gthread'
workers = 2
threads = 4

timeout = 300
