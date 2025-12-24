# DOMOVIK - Project Context (Biblija Projekta)

**KRITIČNA PRAVILA** - Ovo je obavezno štivo za SVE AI agente pre implementacije!

---

## 🔥 Technology Stack - EXACT VERSIONS

**APSOLUTNO KRITIČNO:**
```
Django==5.2         ← NOT 4.2! Django 5.2 LTS je korektna verzija
Python>=3.11        ← Recommended (minimum 3.9)
MySQL==8.0+
Celery==5.3.0
Redis==latest
```

**ZABRANA:**
- ❌ NE koristiti Django 4.2 (stara verzija)
- ❌ NE koristiti PostgreSQL (projekat koristi MySQL)
- ❌ NE koristiti Cookiecutter Django (previše bloat-a)

---

## 📁 Project Structure

```
domovik/
├── manage.py
├── requirements.txt                # Django==5.2 obavezno!
├── config/                         # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── celery.py
├── apps/                           # Django applications
│   ├── core/                       # Shared utilities
│   ├── submissions/                # COA/COB form handling
│   ├── landing/                    # Landing page
│   └── notifications/              # Email handling
├── static/                         # Static files (CSS, JS, images)
│   ├── css/
│   ├── js/
│   ├── images/
│   └── downloads/                  # Excel templates
├── templates/                      # Django templates
└── media/                          # User uploads
```

---

## 🎨 Design System - Civic Tech Identity

**Paleta Boja:**
```css
--primary-teal: #0EA5E9;        /* Primarna tirkizna */
--accent-coral: #FF7A59;        /* Koraljna CTA */
--neutral-warm-gray: #F5F5F0;
--text-primary: #2C3E50;
```

**ZABRANA:**
- ❌ NE koristiti hladnu korporativnu plavu
- ❌ NE koristiti generic Bootstrap default colors

---

## 🔒 GDPR Compliance - KRITIČNO!

**localStorage Draft Sistem:**
- ✅ Podaci se čuvaju SAMO u browser localStorage (client-side)
- ✅ Server dobija podatke SAMO na "PODNESI" klik
- ✅ 7-day retention, automatsko brisanje
- ❌ ZABRANA: Draft podaci na serveru pre submit-a

---

## 📝 Coding Standards

**Python (PEP 8):**
- 4 spaces indentation
- Snake_case za functions i variables
- PascalCase za classes

**JavaScript:**
- Vanilla JS (NO frameworks - React, Vue, Angular)
- ES6+ syntax
- Consistent naming conventions

**CSS (BEM Methodology):**
```css
.landing__hero                  /* Block */
.landing__hero-title            /* Element */
.landing__banner--coa           /* Modifier */
```

---

## 🚀 Deployment

**Environment:**
- Linux server
- Nginx/Apache
- Environment configs: .env files (dev/staging/prod)
- Daily database backups

---

## 📚 Reference Documents

1. **PRD.md** - Funkcionalni zahtevi
2. **Architecture.md** - Tehnički design
3. **UX Design Specification.md** - Dizajn pattern-i
4. **Epics.md** - Story breakdown

---

**Datum kreiranja:** 2025-12-23
**Poslednja izmena:** 2025-12-24
**Verzija:** 1.0
