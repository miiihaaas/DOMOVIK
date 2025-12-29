# DOMOVIK - Platform za Podršku Građanskim Inicijativama

DOMOVIK je web platforma za prijem i obradu prijava za građanske projekte (COA) i inicijative (COB).

## Tehnologije

- **Django 5.2** - Web framework
- **MySQL 8.0+** - Production database
- **Python 3.11+** - Programming language
- **Celery** - Background tasks (email, draft cleanup)
- **Redis** - Task broker and cache

## Pokretanje Projekta

### 1. Konfiguracija

Kopiraj `.env.example` u `.env` i podesi potrebne parametre:

```bash
cp .env.example .env
```

Ključne konfiguracije u `.env`:
- `SECRET_KEY` - Django secret key (generiši novi za production)
- `DEBUG` - `True` za development, `False` za production
- `DB_*` - MySQL konekcija (korisnik, lozinka, host, port)
- `EMAIL_*` - SMTP konfiguracija za slanje email-ova
- `ADMIN_EMAIL` - Email adresa admin korisnika (prima notifikacije)
- `CELERY_BROKER_URL` - Redis URL za Celery task broker

### 2. Instalacija Zavisnosti

```bash
pip install -r requirements.txt
```

### 3. Migracije

```bash
python manage.py migrate
```

### 4. Admin Panel Setup

#### Kreiranje Superuser Naloga

Za pristup admin panelu (`/admin/`), potreban je superuser nalog:

```bash
python manage.py createsuperuser
```

Interaktivni prompt će tražiti:
- **Username** - Korisničko ime (npr. `admin`)
- **Email** - Email adresa (npr. `admin@domovik.org`)
- **Password** - Lozinka (minimum 8 karaktera, kombinacija slova i brojeva)

**Password Requirements (NFR22):**
- Minimum 8 karaktera
- Kombinacija slova i brojeva (ne sme biti samo brojevi)
- Ne sme biti česta lozinka (Django proverava top 20,000 common passwords)
- Ne sme biti slična username-u ili email-u

**Primeri:**
- ❌ `12345678` - Samo brojevi (neispravno)
- ❌ `password` - Česta lozinka (neispravno)
- ❌ `Admin1` - Prekratko (neispravno)
- ✅ `Admin123!` - Validna lozinka

#### Pristup Admin Panelu

1. Pokreni Django development server:
   ```bash
   python manage.py runserver
   ```

2. Otvori browser i idi na: http://localhost:8000/admin/

3. Unesi superuser credentials i klikni "Log in"

4. Nakon uspešnog logovanja, videćeš DOMOVIK Admin Panel sa:
   - **Applications** - Sve podnesene prijave (COA i COB)
   - **Applicants** - Podnosioci prijava
   - **Project Data** - Detaljni podaci o projektima (COA)
   - **Initiative Data** - Detaljni podaci o inicijativama (COB)
   - **File Metadata** - Uploadovani dokumenti

#### Admin Panel Karakteristike

**Pretraga i Filtriranje:**
- Pretraga po referentnom broju (npr. `COA-2025-001`)
- Pretraga po email adresi podnosioca
- Pretraga po imenu/organizaciji podnosioca
- Filter po tipu prijave (COA ili COB)
- Filter po statusu (Submitted, Under Review, Approved, Rejected)
- Filter po datumu podnošenja

**Bezbednost:**
- Session timeout: 30 minuta neaktivnosti (NFR21)
- Session se automatski produžava pri svakoj aktivnosti
- Session se gasi nakon zatvaranja browsera
- HTTPS obavezno u production okruženju
- Admin ne može dodavati/brisati prijave (data integrity)

**GDPR Compliance:**
- Admin vidi SAMO podnesene prijave (status = `submitted` ili kasnije)
- Draft podaci se čuvaju ISKLJUČIVO u browser localStorage (client-side)
- Server NIKADA ne dobija draft podatke pre finalnog submit-a

### 5. Pokretanje Celery Worker-a (za Email-ove i Background Tasks)

U zasebnom terminalu:

```bash
celery -A config worker -l INFO
```

Za scheduled tasks (draft cleanup):

```bash
celery -A config beat -l INFO
```

## Struktura Projekta

```
domovik/
├── apps/
│   ├── landing/          # Landing page
│   ├── submissions/      # COA/COB forme i submission logic
│   └── core/             # Shared utilities
├── config/               # Django settings, URLs, Celery config
├── static/               # CSS, JS, images, downloads
├── templates/            # Django templates
├── media/                # User uploads (budgets, biographies, letters)
├── logs/                 # Application logs
├── manage.py             # Django management command
├── requirements.txt      # Python dependencies
└── .env                  # Environment configuration (not in git)
```

## Dodatne Admin Komande

### Dodavanje Novih Admin Korisnika

```bash
python manage.py createsuperuser
```

**NAPOMENA:** Za production, koristite jake lozinke (npr. generisane sa password manager-om).

### Resetovanje Lozinke Admin Korisnika

```bash
python manage.py changepassword <username>
```

### Izmena Admin URL-a (Security Hardening - Opciono)

U `.env` fajlu, dodaj:

```
ADMIN_URL=my-secret-admin-url/
```

Tada će admin panel biti dostupan na: `http://localhost:8000/my-secret-admin-url/`

**Napomena:** Ovo je "security through obscurity" i nije zamena za jake lozinke i HTTPS.

## Testing

Pokreni test suite:

```bash
python manage.py test
```

Pokreni samo admin authentication tests:

```bash
python manage.py test apps.submissions.tests.test_admin_auth
python manage.py test apps.submissions.tests.test_admin_integration
```

## Production Deployment

**Pre deployment-a:**

1. Postavi `DEBUG=False` u `.env`
2. Generiši novi `SECRET_KEY` (nikada ne koristi development key u production)
3. Konfiguriši MySQL database (ne SQLite)
4. Postavi HTTPS (TLS 1.2+) - obavezno za production (NFR8)
5. Konfiguriši SMTP server za email notifikacije
6. Postavi `ALLOWED_HOSTS` na production domain
7. Konfiguriši Redis za Celery
8. Pokreni Celery worker i beat kao systemd services

**HTTPS Enforcement:**
Kada je `DEBUG=False`, Django automatski postavlja:
- `SECURE_SSL_REDIRECT=True` - Redirektuje HTTP na HTTPS
- `SESSION_COOKIE_SECURE=True` - Session cookies samo preko HTTPS
- `CSRF_COOKIE_SECURE=True` - CSRF cookies samo preko HTTPS

## Licenca

© 2025 DOMOVIK. Sva prava zadržana.

---

**Verzija:** 1.0
**Datum:** 2025-12-29
**Story:** 4.1 - Admin Authentication & Authorization
