#!/bin/bash
# Domovik deployment script - run with sudo
set -e

echo "=== Deploying Domovik ==="

# Add mihailo to www-data group
usermod -aG www-data mihailo

# Copy systemd services
cp /var/www/domovik/systemd/domovik-gunicorn.service /etc/systemd/system/
cp /var/www/domovik/systemd/domovik-celery-worker.service /etc/systemd/system/
cp /var/www/domovik/systemd/domovik-celery-beat.service /etc/systemd/system/

# Copy Nginx config
cp /var/www/domovik/nginx/domovik.conf /etc/nginx/sites-available/domovik
ln -sf /etc/nginx/sites-available/domovik /etc/nginx/sites-enabled/domovik
rm -f /etc/nginx/sites-enabled/default

# Set permissions
chown -R mihailo:www-data /var/www/domovik
chmod -R 755 /var/www/domovik
chmod 640 /var/www/domovik/.env

# Test Nginx config
nginx -t

# Reload systemd
systemctl daemon-reload

# Enable and start services
systemctl enable domovik-gunicorn
systemctl enable domovik-celery-worker
systemctl enable domovik-celery-beat

systemctl restart domovik-gunicorn
systemctl restart domovik-celery-worker
systemctl restart domovik-celery-beat
systemctl restart nginx

echo "=== Checking service status ==="
systemctl status domovik-gunicorn --no-pager
systemctl status domovik-celery-worker --no-pager
systemctl status domovik-celery-beat --no-pager
systemctl status nginx --no-pager

echo "=== Deployment complete ==="
echo "Test: curl http://91.107.234.61/"
