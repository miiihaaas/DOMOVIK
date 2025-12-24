# Code Review Checklist

**Version:** 1.0
**Last Updated:** 2025-12-24
**Source:** Epic 1 Retrospective (Action Item #4)
**Reviewer:** Use this checklist for ALL story code reviews

---

## Overview

This checklist ensures systematic and thorough code review for every DOMOVIK story. Follow this checklist in order, checking off items as you validate them.

**Review Philosophy:**
- 🔍 **Adversarial mindset** - Actively look for problems, don't assume code is correct
- 🎯 **Production-ready standard** - Code should be deployable, not just "working on my machine"
- 📚 **Learning opportunity** - Use reviews to teach and share knowledge

**Review Modes:**
1. **Standard Review:** All items in this checklist
2. **Quick Review:** Sections 1-4 only (for trivial changes)
3. **Adversarial Review:** All items + extra scrutiny (for complex stories)

---

## 1. Pre-Review Checklist ✅

**Before starting review, verify:**

- [ ] **Story status is "ready-for-review"**
  - Check sprint-status.yaml or story file
  - Developer has marked all tasks [x] complete

- [ ] **All tests passing**
  - Run `python manage.py test`
  - Verify 0 failures in output
  - Check for skipped tests (ask why if found)

- [ ] **Code committed to git**
  - No uncommitted changes (`git status` clean)
  - Commit message follows pattern: "Story X.Y DONE: Description"

---

## 2. Functional Correctness 🎯

### 2.1 Acceptance Criteria Validation

- [ ] **All ACs implemented**
  - Read story file → Check each AC
  - For each AC, find corresponding code implementation
  - Verify AC is actually met (not just claimed)

- [ ] **Manual testing performed**
  - Run application (`python manage.py runserver`)
  - Navigate to changed pages
  - Execute user flow from story
  - Verify no obvious bugs

### 2.2 Edge Cases Handled

- [ ] **Error handling present**
  - Invalid input rejected with user-friendly messages
  - 404/403/500 errors handled gracefully
  - No uncaught exceptions in views

- [ ] **Boundary conditions considered**
  - Empty lists, null values, max length strings tested
  - Check: What happens if database is empty?
  - Check: What happens if user enters 10,000 characters?

---

## 3. Code Quality 🔧

### 3.1 Django Best Practices

- [ ] **Models follow conventions**
  - Field types appropriate (CharField vs TextField, etc.)
  - `__str__` methods defined
  - Meta class ordering, verbose_name defined
  - No database queries in `__init__` or property methods

- [ ] **Views follow conventions**
  - CBVs (Class-Based Views) used unless simple function view needed
  - No business logic in templates
  - Context data properly structured
  - No hardcoded URLs (use `reverse()` or `{% url %}`)

- [ ] **Templates follow conventions**
  - DRY: Template inheritance used (`{% extends %}`)
  - No inline styles (CSS in static files)
  - Proper template tag loading (`{% load static %}`)
  - HTML properly indented and formatted

### 3.2 CSS/JavaScript Quality

- [ ] **CSS naming conventions**
  - BEM methodology (Block__Element--Modifier)
  - Consistent naming with existing project
  - No `!important` overuse (justified if used)

- [ ] **CSS structure**
  - No duplicate styles
  - Media queries properly structured (desktop-first or mobile-first, be consistent)
  - Colors use CSS variables (not hardcoded hex values)

### 3.3 Python Code Style

- [ ] **PEP 8 compliance**
  - Run `flake8` if available
  - Line length < 120 chars (or project standard)
  - Proper spacing, indentation

- [ ] **Readable code**
  - Variable names descriptive (not `x`, `data`, `temp`)
  - Functions do one thing
  - No overly complex nested logic (max 3 levels deep)

---

## 4. Security Review 🔒

### 4.1 Secret Management

- [ ] **No hardcoded secrets**
  - Search for: `SECRET_KEY`, `API_KEY`, `PASSWORD` in code
  - All secrets in `.env` file
  - `.env` in `.gitignore` (not committed)

- [ ] **Environment variables used correctly**
  - `config('SECRET_KEY')` pattern (python-decouple)
  - Default values safe (DEBUG=False in production)

### 4.2 Input Validation

- [ ] **User input validated**
  - Forms use Django Form/ModelForm validation
  - API endpoints validate request data
  - No raw SQL (use Django ORM)

- [ ] **XSS prevention**
  - Template auto-escaping enabled (default in Django)
  - No `mark_safe()` unless justified
  - User input not directly rendered in JavaScript

### 4.3 File Upload Security (if applicable)

- [ ] **File extension whitelist enforced**
  - Only allowed extensions accepted (`.xlsx`, `.pdf`, `.doc`, `.jpg`, etc.)
  - Check MIME type, not just extension

- [ ] **File size limits enforced**
  - Max file size defined (e.g., 10MB for DOMOVIK)
  - Enforced in form validation

- [ ] **Files stored securely**
  - Files stored outside web root (MEDIA_ROOT)
  - Filenames sanitized (no `../` path traversal)

---

## 5. UTF-8 Encoding Compliance 🌍

**NEW (Epic 1 Retrospective):** Prevent Serbian character corruption.

### 5.1 Template Encoding

- [ ] **No corrupted Serbian characters**
  - Search templates for: `ponete`, `lanova`, `uvamo`, `Mo~ete`, `Zaponi`
  - Should find ZERO results (these are corrupted forms)
  - Correct forms: `počnete`, `članova`, `čuvamo`, `Možete`, `Započni`

- [ ] **UTF-8 meta tag present**
  - Check `templates/base.html` has: `<meta charset="UTF-8">`

### 5.2 Python File Encoding

- [ ] **Python files UTF-8 encoded**
  - If Serbian strings in code, check for: `# -*- coding: utf-8 -*-`
  - Verify in editor: File → Encoding → UTF-8

### 5.3 Console Output (Windows Compatibility)

- [ ] **Scripts handle UTF-8 output**
  - If script prints Serbian text, check for:
    ```python
    print("Текст", encoding='utf-8')  # Windows fix
    ```
  - Run script in PowerShell → Verify no encoding errors

### 5.4 Database Encoding

- [ ] **MySQL configured for UTF-8**
  - Check `config/settings.py` DATABASES config:
    ```python
    'OPTIONS': {
        'charset': 'utf8mb4',
    }
    ```

---

## 6. Testing Coverage 🧪

### 6.1 Unit Tests Quality

- [ ] **Tests actually test something**
  - No placeholder tests (e.g., `assertTrue(True)`)
  - Tests verify AC, not just code execution

- [ ] **Tests use proper assertions**
  - `assertEqual`, `assertContains`, not just `assertTrue`
  - Error messages in assertions (e.g., `assertEqual(x, y, "User count mismatch")`)

- [ ] **Tests are independent**
  - Each test can run alone (`python manage.py test apps.landing.tests.TestFoo.test_bar`)
  - No test order dependencies

### 6.2 Test Coverage

- [ ] **All ACs have tests**
  - Minimum 1 test per AC
  - Complex ACs have multiple tests

- [ ] **Error paths tested**
  - Not just happy path
  - Tests for 404, validation errors, edge cases

- [ ] **No regressions**
  - All previous tests still pass
  - If tests updated, reason documented in commit

---

## 7. .gitignore Validation 🚫

**CRITICAL (Epic 1 Retrospective):** Prevent static files from being blocked.

### 7.1 Static Files Not Blocked

- [ ] **Check git status for static files**
  - Run: `git status`
  - Verify: All intended static files listed (CSS, images, downloads)
  - Verify: No assets missing due to overly broad .gitignore rules

- [ ] **.gitignore rules specific, not broad**
  - ❌ BAD: `downloads/` (blocks entire directory)
  - ✅ GOOD: `*.pyc`, `__pycache__/`, `.env`

- [ ] **Test with actual files**
  - Create test file in static/ directory
  - Run `git status` → Should appear if needed
  - Delete test file

**Epic 1 Example - Story 1.1:**
- `.gitignore` had `downloads/` rule
- Blocked `static/downloads/budzet-projekta-sablon.xlsx` from git
- File existed locally but NOT in git → production would have 404

**Prevention:**
```bash
# After reviewing code, verify static assets tracked:
git ls-files static/
# Should show ALL needed assets (CSS, images, downloads)
```

---

## 8. requirements.txt Validation 📦

**CRITICAL (Epic 1 Retrospective):** Prevent dependency errors.

### 8.1 Dependency Versions Valid

- [ ] **All versions exist**
  - Check each dependency version on PyPI
  - Example: `Django==5.2` ❌ (doesn't exist)
  - Example: `Django==4.2` ✅ (LTS version)

- [ ] **Versions explicitly pinned**
  - No bare package names (e.g., `Django` ❌)
  - All have `==X.Y` or `~=X.Y.Z` (e.g., `Django==4.2` ✅)

### 8.2 Dependency Classification Correct

- [ ] **Production vs Dev dependencies separated**
  - Check: Is `pytest` in `requirements.txt`? ❌ (should be in requirements-dev.txt)
  - Check: Is `Django` in `requirements.txt`? ✅ (production dependency)
  - Reference: `docs/requirements-guide.md`

- [ ] **New dependencies justified**
  - Ask: Why is this package needed?
  - Ask: Is there a Django built-in alternative?
  - Prefer smaller, maintained packages

### 8.3 Clean Environment Test

- [ ] **requirements.txt installs in clean venv**
  - Create clean virtual environment:
    ```bash
    python -m venv test-review-venv
    source test-review-venv/bin/activate  # Windows: test-review-venv\Scripts\activate
    pip install -r requirements.txt
    python manage.py check
    ```
  - Should succeed with no errors
  - Delete test-review-venv after verification

**Epic 1 Example - Story 1.1:**
- `requirements.txt` had `Django==5.2` (typo)
- Django 5.2 doesn't exist
- `pip install -r requirements.txt` would FAIL
- Caught in second code review

---

## 9. Documentation Review 📚

### 9.1 Inline Documentation

- [ ] **Complex code has comments**
  - Algorithms, workarounds, non-obvious decisions explained
  - No obvious comments (e.g., `# Increment counter` for `i += 1`)

- [ ] **Docstrings for complex functions**
  - Views with business logic have docstrings
  - Utility functions documented

### 9.2 Story File Updated

- [ ] **Status marked "done"**
  - Story file header: `Status: done`
  - sprint-status.yaml updated (if applicable)

- [ ] **Dev Agent Record completed**
  - Agent Model Used
  - Completion Notes List
  - File List (all modified/created files)

- [ ] **Code review notes added** (if issues found)
  - Section: `## Review Follow-ups`
  - List of issues found
  - List of issues fixed

### 9.3 README / Setup Docs Updated

- [ ] **New features documented** (if user-facing)
  - README.md updated with feature description

- [ ] **New dependencies documented**
  - Installation instructions updated
  - Environment variables added to .env.example

---

## 10. Responsive Design & Accessibility ♿

### 10.1 Responsive Design

- [ ] **Breakpoints tested** (if UI changes)
  - Desktop (1024px+): Layout works
  - Tablet (768px): Layout adapts
  - Mobile (320px): Single column, readable

- [ ] **Touch targets meet minimum**
  - Interactive elements min 44x44px
  - Verify in CSS: `min-width: 44px; min-height: 44px;`

### 10.2 Accessibility

- [ ] **Semantic HTML used**
  - `<header>`, `<nav>`, `<main>`, `<footer>` (not just `<div>`)
  - Heading hierarchy correct (h1 → h2 → h3)

- [ ] **Alt text for images**
  - All `<img>` tags have `alt` attribute
  - Alt text descriptive

- [ ] **Keyboard navigation works**
  - Tab cycles through interactive elements
  - Focus states visible (`:focus` CSS)

- [ ] **Color contrast sufficient**
  - Text contrast > 4.5:1 (WCAG AA)
  - Verify: https://webaim.org/resources/contrastchecker/

---

## 11. Performance & Optimization ⚡

### 11.1 Database Queries

- [ ] **No N+1 queries**
  - Check views for loops over QuerySets
  - Use `select_related()` for ForeignKey
  - Use `prefetch_related()` for ManyToMany

- [ ] **Pagination used for large datasets**
  - Lists with > 50 items should paginate
  - Use Django Paginator

### 11.2 Static Files

- [ ] **Images optimized** (if new images added)
  - File size < 200KB per image
  - WebP format preferred (with PNG fallback)

- [ ] **CSS/JS not duplicated**
  - No repeated selectors or rules
  - DRY principle applied

---

## 12. Deployment Readiness 🚀

### 12.1 Environment Variables

- [ ] **.env.example updated**
  - All new env vars added to .env.example
  - Example values provided (not real secrets)

- [ ] **No default secrets in code**
  - DEBUG defaults to False (not True)
  - SECRET_KEY has no default in settings.py

### 12.2 Migrations

- [ ] **Migrations created** (if models changed)
  - Run `python manage.py makemigrations`
  - Migrations committed to git
  - Migration tested (apply with `migrate`, rollback to verify)

- [ ] **Migration has no data loss**
  - No `RemoveField` without data migration
  - No `AlterField` that truncates data

---

## 13. Final Checks ✔️

### 13.1 Definition of Done

- [ ] **All DoD items met**
  - Reference: `docs/definition-of-done.md`
  - Verify checklist in story file completed

### 13.2 No Obvious Issues

- [ ] **Code "smells" addressed**
  - No dead code (commented-out blocks)
  - No TODO comments (create story or remove)
  - No console.log / print debugging statements

### 13.3 Review Summary

- [ ] **Review notes added to story file**
  - Section: `## Review Follow-ups`
  - List of issues found + fixed
  - No unresolved issues

---

## Adversarial Review Mode 🔥

**For complex or high-risk stories, add these extra checks:**

### Extra Security Checks

- [ ] **OWASP Top 10 considerations**
  - Injection vulnerabilities
  - Broken authentication
  - Sensitive data exposure
  - XML External Entities (XXE)
  - Broken access control

### Extra Performance Checks

- [ ] **Load testing** (if applicable)
  - How does it perform with 1000 users?
  - How does it perform with 10,000 database records?

### Extra Reliability Checks

- [ ] **Error recovery**
  - What happens if database is down?
  - What happens if external API fails?

---

## Review Workflow

**Step-by-step process:**

1. **Pre-Review** (Section 1)
   - Verify tests pass, code committed

2. **Functional Review** (Sections 2)
   - Verify ACs met, manual testing

3. **Code Quality** (Sections 3-5)
   - Django standards, security, UTF-8 encoding

4. **Testing & Documentation** (Sections 6, 9)
   - Unit tests, story file updated

5. **Critical Validations** (Sections 7-8)
   - .gitignore, requirements.txt (NEW from Epic 1)

6. **UI/UX** (Section 10)
   - Responsive design, accessibility

7. **Performance & Deployment** (Sections 11-12)
   - Queries, migrations

8. **Final Checks** (Section 13)
   - DoD, no obvious issues

9. **Approve or Request Changes**
   - If all items checked: Approve ✅
   - If issues found: Request changes, add to story file

---

## Issue Severity Classification

**When reporting issues:**

- **CRITICAL:** Security vulnerability, data loss risk, app crashes
  - Example: Hardcoded SECRET_KEY, SQL injection vulnerability
  - **Action:** MUST FIX before merge

- **HIGH:** Breaks functionality, doesn't meet AC, obvious bugs
  - Example: Form doesn't submit, 404 on valid route
  - **Action:** MUST FIX before merge

- **MEDIUM:** Code quality, maintainability, minor bugs
  - Example: No input validation, N+1 queries, missing docstrings
  - **Action:** SHOULD FIX (or justify why not)

- **LOW:** Style, optimization, nice-to-have
  - Example: Variable naming, CSS organization
  - **Action:** Optional (fix if time allows)

---

## Epic 1 Learnings Applied

**New checklist items from Epic 1 Retrospective:**

1. ✅ **UTF-8 Encoding Compliance** (Section 5) - Prevents Serbian character corruption
2. ✅ **.gitignore Validation** (Section 7) - Prevents static file blocking
3. ✅ **requirements.txt Validation** (Section 8) - Prevents version typos and dependency errors
4. ✅ **Clean Environment Test** (Section 8.3) - Validates requirements.txt actually works

---

## References

- **Definition of Done:** `docs/definition-of-done.md`
- **Requirements Guide:** `docs/requirements-guide.md`
- **Epic 1 Retrospective:** `_bmad-output/implementation-artifacts/epic-1-retrospective.md`
- **Django Coding Style:** https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/
- **OWASP Top 10:** https://owasp.org/www-project-top-ten/

---

**Version:** 1.0
**Author:** Bob (Scrum Master)
**Approved:** Mihas (Product Owner)
**Effective Date:** 2025-12-24 (Epic 2 onwards)
