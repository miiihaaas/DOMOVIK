# DOMOVIK - Project Context (Biblija Projekta)

**KRITIČNA PRAVILA** - Ovo je obavezno štivo za SVE AI agente pre implementacije!

---

## 🔥 Technology Stack - EXACT VERSIONS

**APSOLUTNO KRITIČNO:**
```
Django==5.2
Python>=3.11        ← Recommended (minimum 3.9)
MySQL==8.0+
Celery==5.3.0
Redis==latest
```

**NAPOMENA:**
- ✅ Verify all dependency versions exist on PyPI before adding to requirements.txt

**ZABRANA:**
- ❌ NE koristiti PostgreSQL (projekat koristi MySQL)
- ❌ NE koristiti Cookiecutter Django (previše bloat-a)

---

## 📁 Project Structure

```
domovik/
├── manage.py
├── requirements.txt                # Django==5.2 LTS + production deps (see docs/requirements-guide.md)
├── requirements-dev.txt            # Development dependencies (testing, linting, etc.)
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

## 🌍 UTF-8 Encoding Best Practices

**KRITIČNO za srpski jezik - OBAVEZNO PRAVILO:**

**1. HTML Templates:**
- ✅ OBAVEZNO: `<meta charset="UTF-8">` u `<head>` (verify u base.html)
- ❌ ZABRANA: Korumpirana slova (č → c, ć → c, š → s, đ → d, ž → z)
- 🔍 Provera: Grep za "ponete", "lanova", "uvamo" → Mora vratiti 0 rezultata

**2. Python Files (.py):**
- ✅ UTF-8 encoding u editoru (VS Code: proveri bottom-right status bar)
- ✅ Ako ima srpski tekst u kodu: Dodaj `# -*- coding: utf-8 -*-` na vrh fajla
- 🔍 Provera: `file -i apps/**/*.py` → Treba pokazati "charset=utf-8"

**3. Database (MySQL):**
- ✅ OBAVEZNO u `config/settings.py`:
  ```python
  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.mysql',
          'OPTIONS': {
              'charset': 'utf8mb4',  # Pun Unicode support
          },
      }
  }
  ```

**4. Console Output (Windows kompatibilnost):**
- ✅ Za Python script-e sa srpskim tekstom:
  ```python
  print("Srpski tekst", encoding='utf-8')  # Windows fix
  ```
- 🔍 Provera: Pokreni script u PowerShell → Ne sme biti encoding errora

**5. Static Files (CSV, JSON, XML):**
- ✅ Sačuvaj sa UTF-8 encoding (ne Windows-1252)
- ✅ Izbegavaj BOM (Byte Order Mark) ako je moguće

**Epic 1 Lessons:**
- Story 1.1: 6 HIGH priority issues zbog korumpiranih srpskih slova
- Story 1.2: Windows console encoding greške u verify scriptu
- **Rešenje:** Dodato u Definition of Done (see docs/definition-of-done.md)

**Reference:**
- Full checklist: `docs/definition-of-done.md` (Section 3: UTF-8 Encoding Compliance)
- Code review: `docs/code-review-checklist.md` (Section 5: UTF-8 Encoding Compliance)

---

## 🚀 Deployment

**Environment:**
- Linux server
- Nginx/Apache
- Environment configs: .env files (dev/staging/prod)
- Daily database backups

---

## 📚 Reference Documents

**Core Project Documents:**
1. **PRD.md** - Funkcionalni zahtevi
2. **Architecture.md** - Tehnički design
3. **UX Design Specification.md** - Dizajn pattern-i
4. **Epics.md** - Story breakdown

**Process & Quality Documents (NEW - Epic 1 Retrospective):**
5. **docs/definition-of-done.md** - DoD checklist za sve priče (Epic 2+)
6. **docs/code-review-checklist.md** - Systematic code review process
7. **docs/requirements-guide.md** - Dependency classification (production vs dev)

**Retrospectives & Learnings:**
8. **_bmad-output/implementation-artifacts/epic-1-retrospective.md** - Epic 1 lessons learned

---

**Datum kreiranja:** 2025-12-23
**Poslednja izmena:** 2025-12-24 (Epic 1 Retrospective - Process Improvements Applied)
**Verzija:** 1.1
