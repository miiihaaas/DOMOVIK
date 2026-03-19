# Python Dependency Management Guide

**Version:** 1.0
**Last Updated:** 2025-12-24
**Source:** Epic 1 Retrospective (Action Item #3)

---

## Overview

This guide establishes clear criteria for classifying Python dependencies in DOMOVIK project. Proper dependency classification ensures:

- ✅ Minimal production deployment size
- ✅ Faster production installs
- ✅ Clear separation of dev vs production concerns
- ✅ Easier dependency auditing

---

## Dependency Classification

### Production Dependencies (`requirements.txt`)

**Definition:** Packages required for the application to RUN in production environment.

**Criteria - Include if:**
- ✅ Imported in application code (`apps/`, `config/`)
- ✅ Required by Django to serve requests
- ✅ Needed for database connections
- ✅ Used in production workflows (email sending, file processing, etc.)

**Examples:**
```txt
# requirements.txt
Django==5.2              # Core framework
python-decouple==3.8     # Environment variable management
mysqlclient==2.2.0       # MySQL database driver (production DB)
Pillow==10.0.0           # Image processing for file uploads
celery==5.3.0            # Background task processing
```

**Anti-Examples (DON'T put in production):**
- ❌ Testing libraries (pytest, coverage)
- ❌ Code quality tools (black, flake8, mypy)
- ❌ Development utilities (ipython, django-debug-toolbar)
- ❌ Build/deployment tools (fabric, ansible)
- ❌ Data manipulation scripts (openpyxl, pandas) - unless used in production code

---

### Development Dependencies (`requirements-dev.txt`)

**Definition:** Packages required ONLY for development, testing, or deployment workflows.

**Criteria - Include if:**
- ✅ Used in tests (`apps/*/tests.py`)
- ✅ Code quality/linting tools
- ✅ Development utilities
- ✅ Build/deployment automation
- ✅ Data migration/verification scripts (one-time use)

**Examples:**
```txt
# requirements-dev.txt
pytest==7.4.0                  # Testing framework
pytest-django==4.5.2           # Django integration for pytest
coverage==7.3.0                # Test coverage reporting
black==23.7.0                  # Code formatter
flake8==6.1.0                  # Linter
mypy==1.5.0                    # Type checker
django-debug-toolbar==4.2.0    # Development debugging
ipython==8.14.0                # Interactive Python shell
openpyxl==3.1.2                # Excel file manipulation (for scripts only)
factory-boy==3.3.0             # Test fixture generation
faker==19.3.0                  # Fake data generation for tests
```

**Story 1.2 Example - openpyxl:**
- **Usage:** `scripts/verify_excel_template.py` (verification script)
- **Decision:** `requirements-dev.txt` ✅
- **Rationale:** Script runs only during development/testing, NOT in production

---

## Installation Workflows

### Development Environment Setup

```bash
# Install production dependencies first
pip install -r requirements.txt

# Then install dev dependencies
pip install -r requirements-dev.txt
```

**Result:** Full development environment with testing, linting, debugging tools.

---

### Production Deployment

```bash
# Install ONLY production dependencies
pip install -r requirements.txt
```

**Result:** Minimal production environment, faster installs, smaller Docker images.

---

### CI/CD Pipeline

```bash
# CI/CD should install BOTH for testing
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests with dev dependencies available
pytest apps/
```

**Result:** Tests run with all necessary tools, production code validated.

---

## Decision Tree

**When adding a new package, ask:**

```
┌─────────────────────────────────────┐
│ Is package imported in apps/ or     │
│ config/ (production code)?          │
└─────────┬───────────────────────────┘
          │
    ┌─────┴─────┐
    │    YES    │
    └─────┬─────┘
          │
          v
    requirements.txt ✅ (PRODUCTION)


    ┌─────┴─────┐
    │    NO     │
    └─────┬─────┘
          │
          v
┌─────────────────────────────────────┐
│ Is package used in tests.py or      │
│ scripts/ or dev tools?              │
└─────────┬───────────────────────────┘
          │
    ┌─────┴─────┐
    │    YES    │
    └─────┬─────┘
          │
          v
    requirements-dev.txt ✅ (DEVELOPMENT)


    ┌─────┴─────┐
    │    NO     │
    └─────┬─────┘
          │
          v
    ⚠️ QUESTION: Why is this package needed?
```

---

## Common Pitfalls

### ❌ **Pitfall #1: Putting Test Libraries in Production**

**Wrong:**
```txt
# requirements.txt
pytest==7.4.0  # ❌ NOT NEEDED in production
```

**Right:**
```txt
# requirements-dev.txt
pytest==7.4.0  # ✅ Only needed for testing
```

**Impact:** Larger production Docker images, unnecessary dependencies.

---

### ❌ **Pitfall #2: Putting Script Dependencies in Production**

**Wrong:**
```txt
# requirements.txt
openpyxl==3.1.2  # ❌ Only used in scripts/verify_excel_template.py
```

**Right:**
```txt
# requirements-dev.txt
openpyxl==3.1.2  # ✅ Script runs only during development
```

**Impact:** Unnecessary production dependency, bloated installs.

**Exception:** If openpyxl is used in production code (e.g., `apps/submissions/views.py` generates Excel reports for users), then it belongs in `requirements.txt`.

---

### ❌ **Pitfall #3: Forgetting to Pin Versions**

**Wrong:**
```txt
Django  # ❌ No version specified
```

**Right:**
```txt
Django==5.2  # ✅ Explicit version
```

**Impact:** Unpredictable installs, potential breakage from version changes.

---

### ❌ **Pitfall #4: Not Testing requirements.txt in Clean Environment**

**Problem:** Adding dependency to `requirements-dev.txt` but code imports it in production files.

**Prevention:**
```bash
# Create clean virtual environment
python -m venv test-venv
source test-venv/bin/activate  # Windows: test-venv\Scripts\activate

# Install ONLY production dependencies
pip install -r requirements.txt

# Try to run production code
python manage.py check

# If it fails, missing dependency belongs in requirements.txt!
```

**Epic 1 Example - Story 1.1:**
- Django 5.2 LTS version confirmed and installed successfully
- Clean venv testing procedure validated
- **Lesson:** Always test requirements.txt in clean venv during code review

---

## Version Pinning Strategy

### Exact Versions (Recommended for Stability)

```txt
Django==5.2              # Exact version - most stable
python-decouple==3.8     # No surprises
```

**Pros:**
- ✅ Predictable builds
- ✅ No surprise breakage

**Cons:**
- ❌ Manual updates needed for security patches

---

### Compatible Release Versions (For Flexibility)

```txt
Django~=4.2.0            # Allows 4.2.x (patch updates only)
pytest~=7.4.0            # Allows 7.4.x
```

**Pros:**
- ✅ Automatic security patches
- ✅ Predictable minor updates

**Cons:**
- ❌ Rare chance of patch version breakage

---

### Range Versions (NOT Recommended)

```txt
Django>=4.2,<5.0         # ❌ Too flexible
```

**Pros:**
- None for production

**Cons:**
- ❌ Unpredictable installs
- ❌ CI/CD can pass but production breaks

---

## Validation Checklist

**Before committing requirements changes:**

- [ ] All packages have explicit versions (no bare package names)
- [ ] Production dependencies in `requirements.txt`
- [ ] Dev dependencies in `requirements-dev.txt`
- [ ] Tested `pip install -r requirements.txt` in clean venv
- [ ] Tested `python manage.py check` with only production deps
- [ ] All versions verified to exist on PyPI (check project-context.md for correct versions)
- [ ] Added comments explaining unusual dependencies

**Example commented dependency:**
```txt
# requirements-dev.txt
openpyxl==3.1.2  # Used in scripts/verify_excel_template.py (dev-only)
```

---

## Future Considerations

### Poetry / Pipenv (Not Used in DOMOVIK)

**Current:** `requirements.txt` + `requirements-dev.txt` (pip-based)

**Alternative:** Poetry or Pipenv for dependency management

**Decision:** Stick with pip for simplicity (Django ecosystem standard)

**Rationale:**
- pip is universal and well-understood
- No additional tooling required
- Compatible with all deployment platforms

**Revisit:** If dependency conflicts become common in Epic 2+, consider Poetry.

---

## References

- **Epic 1 Retrospective:** `_bmad-output/implementation-artifacts/epic-1-retrospective.md`
- **Story 1.2:** openpyxl dependency classification issue
- **Python Packaging Guide:** https://packaging.python.org/tutorials/installing-packages/

---

**Guide Version:** 1.0
**Author:** Bob (Scrum Master)
**Approved:** Mihas (Product Owner)
**Effective Date:** 2025-12-24 (Epic 2 onwards)
