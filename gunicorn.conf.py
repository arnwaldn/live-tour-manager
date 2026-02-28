# =============================================================================
# GigRoute - Gunicorn Production Configuration
# =============================================================================
import os
import multiprocessing

# Bind
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"

# Workers: 2 * CPU + 1 (minimum 2, capped at 4 for small instances)
workers = min(multiprocessing.cpu_count() * 2 + 1, 4)
threads = 2

# Preload app to save memory (shared code across workers)
preload_app = True

# Timeouts
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'

# Worker lifecycle
max_requests = 1000
max_requests_jitter = 50

# Security: limit request sizes
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# Tmp upload dir (for file uploads)
tmp_upload_dir = None

# Server mechanics
worker_class = "gthread"
forwarded_allow_ips = "*"
proxy_protocol = False
