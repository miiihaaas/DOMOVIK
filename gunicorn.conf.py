import multiprocessing

bind = "unix:/var/www/domovik/gunicorn.sock"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 2
timeout = 120
keepalive = 5

# Logging
accesslog = "/var/www/domovik/logs/gunicorn-access.log"
errorlog = "/var/www/domovik/logs/gunicorn-error.log"
loglevel = "info"

# Process naming
proc_name = "domovik"
