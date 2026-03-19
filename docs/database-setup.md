# Database Setup Guide

## MySQL Database Configuration for DOMOVIK

This guide covers MySQL 8.0+ database setup for the DOMOVIK project.

**Critical:** Database must use `utf8mb4` charset for Serbian language support (č, ć, š, đ, ž).

---

## Option 1: Local MySQL Installation

### Windows

1. **Download MySQL 8.0+:**
   - Visit: https://dev.mysql.com/downloads/mysql/
   - Download MySQL Installer for Windows
   - Run installer and select "Developer Default"

2. **Configure MySQL Service:**
   ```cmd
   # Verify MySQL service is running
   sc query MySQL80

   # Start MySQL if not running
   net start MySQL80
   ```

3. **Create Database and User:**
   ```sql
   # Connect to MySQL as root
   mysql -u root -p

   # Create database with utf8mb4 charset
   CREATE DATABASE domovik_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

   # Create user
   CREATE USER 'domovik_user'@'localhost' IDENTIFIED BY 'your-strong-password';

   # Grant privileges
   GRANT ALL PRIVILEGES ON domovik_dev.* TO 'domovik_user'@'localhost';

   # Reload privileges
   FLUSH PRIVILEGES;
   ```

### Linux (Ubuntu/Debian)

1. **Install MySQL:**
   ```bash
   sudo apt update
   sudo apt install mysql-server
   sudo systemctl start mysql
   sudo systemctl enable mysql
   ```

2. **Secure Installation:**
   ```bash
   sudo mysql_secure_installation
   ```

3. **Create Database and User:**
   ```bash
   # Connect as root
   sudo mysql -u root -p

   # Run same SQL as Windows section above
   ```

### macOS

1. **Install MySQL via Homebrew:**
   ```bash
   brew install mysql@8.0
   brew services start mysql@8.0
   ```

2. **Create Database and User:**
   - Same SQL as Windows section

---

## Option 2: Docker MySQL (Recommended for Development)

### Docker Compose Setup

1. **Create `docker-compose.yml` in project root:**

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: domovik_mysql
    environment:
      MYSQL_DATABASE: domovik_dev
      MYSQL_USER: domovik_user
      MYSQL_PASSWORD: domovik_pass
      MYSQL_ROOT_PASSWORD: root_pass
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

volumes:
  mysql_data:
```

2. **Start MySQL Container:**
   ```bash
   docker-compose up -d
   ```

3. **Verify Container Running:**
   ```bash
   docker ps
   docker logs domovik_mysql
   ```

4. **Connect to MySQL:**
   ```bash
   docker exec -it domovik_mysql mysql -u domovik_user -p
   ```

---

## Django Configuration

### 1. Install MySQL Driver

```bash
pip install mysqlclient==2.2.7
```

**Windows Note:** If `mysqlclient` fails to install, install Visual C++ Build Tools first.

### 2. Create `.env` File

Copy `.env.example` to `.env` and configure:

```env
# Database Configuration
DB_ENGINE=django.db.backends.mysql
DB_NAME=domovik_dev
DB_USER=domovik_user
DB_PASSWORD=your-strong-password  # Change this!
DB_HOST=localhost
DB_PORT=3306
```

**Docker users:** Use `DB_HOST=localhost` (port mapping exposes container on localhost:3306)

### 3. Verify Django Database Connection

```bash
python manage.py check --database default
```

**Expected output:**
```
System check identified no issues (0 silenced).
```

### 4. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Troubleshooting

### Error: "Can't connect to MySQL server"

**Cause:** MySQL not running or wrong host/port

**Solution:**
```bash
# Verify MySQL is running
sc query MySQL80  # Windows
sudo systemctl status mysql  # Linux
brew services list  # macOS

# Check .env file has correct DB_HOST and DB_PORT
```

### Error: "Access denied for user"

**Cause:** Wrong username/password

**Solution:**
- Verify `.env` DB_USER and DB_PASSWORD match MySQL user credentials
- Test connection manually: `mysql -u domovik_user -p`

### Error: "Unknown database 'domovik_dev'"

**Cause:** Database not created

**Solution:**
```sql
CREATE DATABASE domovik_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Error: "No module named 'MySQLdb'"

**Cause:** mysqlclient not installed

**Solution:**
```bash
pip install mysqlclient==2.2.7
```

### Windows: mysqlclient Installation Fails

**Solution:**
1. Install Visual C++ Build Tools: https://visualstudio.microsoft.com/downloads/
2. Retry: `pip install mysqlclient==2.2.7`

---

## Verify UTF-8 Charset

**Critical for Serbian language support!**

```bash
# Connect to MySQL
mysql -u domovik_user -p

# Check database charset
SHOW CREATE DATABASE domovik_dev;

# Should show: CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
```

**If charset is NOT utf8mb4:**

```sql
ALTER DATABASE domovik_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Fix existing tables
ALTER TABLE submissions_application CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE submissions_applicant CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

## Testing

Run test suite to verify database configuration:

```bash
python manage.py test apps.submissions
```

**Expected:** All tests pass (some may skip if not using MySQL in test mode)

---

## Production Notes

### Security Checklist

- ✅ Use strong password for MySQL user (minimum 16 characters)
- ✅ Never commit `.env` file to git
- ✅ Restrict MySQL user privileges to only `domovik_dev` database
- ✅ Configure MySQL to only accept connections from application server
- ✅ Enable MySQL slow query log for performance monitoring
- ✅ Set up daily database backups

### Performance Optimization

```sql
-- Add indexes on frequently queried fields (already in migrations)
-- Monitor slow queries:
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;  -- Log queries > 2 seconds
```

---

## References

- Django MySQL Notes: https://docs.djangoproject.com/en/5.2/ref/databases/#mysql-notes
- MySQL 8.0 Documentation: https://dev.mysql.com/doc/refman/8.0/en/
- UTF-8 Best Practices: project-context.md (lines 114-148)

---

**Document Version:** 1.0
**Last Updated:** 2025-12-25 (Story 2.1 Code Review)
**Maintained By:** DOMOVIK Development Team
