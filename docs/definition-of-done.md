# Definition of Done (DoD)

**Version:** 1.0
**Last Updated:** 2025-12-24
**Source:** Epic 1 Retrospective (Action Item #2)
**Applies To:** All stories in Epic 2 onwards

---

## Overview

A story is considered **DONE** when ALL criteria in this checklist are met. This ensures consistent quality, maintainability, and production-readiness across all DOMOVIK stories.

**Enforcement:**
- ✅ Code review MUST verify all DoD items before approval
- ✅ Story cannot be marked "done" in sprint-status.yaml unless DoD is met
- ✅ Exceptions require Product Owner approval and documentation in story file

---

## 1. Functional Requirements ✅

### 1.1 Acceptance Criteria Met

- [ ] **All acceptance criteria implemented**
  - Every AC in story file has corresponding implementation
  - AC validation notes added to story file
  - Edge cases considered and handled

- [ ] **User story fulfilled**
  - "As a... I want... So that..." statement satisfied
  - User value delivered (not just technical completion)

### 1.2 Manual Testing Completed

- [ ] **Happy path tested**
  - Primary user flow works end-to-end
  - Screenshots/evidence added to story file (if applicable)

- [ ] **Error paths tested**
  - Invalid input handled gracefully
  - Error messages user-friendly and actionable

- [ ] **Cross-browser compatibility tested** (if UI changes)
  - Chrome (latest)
  - Firefox (latest)
  - Safari (latest) - if macOS/iOS available
  - Edge (latest)

---

## 2. Code Quality 🔧

### 2.1 Code Standards

- [ ] **Django best practices followed**
  - Models: Proper field types, validators, Meta options
  - Views: CBVs preferred over FBVs (unless simple)
  - Templates: DRY principle, template inheritance
  - URLs: Named URL patterns, RESTful structure

- [ ] **CSS naming conventions followed**
  - BEM methodology (Block__Element--Modifier)
  - Consistent class naming across project
  - No inline styles (use CSS files)

- [ ] **Python code style**
  - PEP 8 compliant (run `flake8` if available)
  - Clear variable/function names (no single-letter names except loop counters)
  - Docstrings for complex functions

### 2.2 Security

- [ ] **No hardcoded secrets**
  - No API keys, passwords, SECRET_KEY in code
  - Environment variables used (.env file)

- [ ] **Input validation**
  - User input validated (forms, API endpoints)
  - SQL injection prevented (Django ORM used correctly)
  - XSS prevented (template auto-escaping enabled)

- [ ] **File upload security** (if applicable)
  - File extension whitelist enforced
  - File size limits enforced
  - Files stored outside web root

### 2.3 Performance

- [ ] **No obvious performance issues**
  - No N+1 queries (use `select_related`, `prefetch_related`)
  - Database indexes on frequently queried fields
  - Large datasets paginated

- [ ] **Static files optimized** (for production-ready stories)
  - Images compressed (< 200KB per image)
  - CSS/JS minified (or ready for minification)

---

## 3. UTF-8 Encoding Compliance 🌍

**NEW (Epic 1 Retrospective):** Prevent Serbian character corruption issues.

### 3.1 Template Encoding

- [ ] **All HTML templates use UTF-8**
  - `<meta charset="UTF-8">` in `<head>` (verify in base.html)
  - No corrupted Serbian characters (č, ć, š, đ, ž)
  - Verify: Open template in browser → Inspect text → No "ponete", "lanova" corruption

### 3.2 Python File Encoding

- [ ] **All .py files UTF-8 encoded**
  - Add `# -*- coding: utf-8 -*-` at top if Serbian strings in code
  - Verify: Open file in editor → Check encoding (bottom-right in VS Code)

### 3.3 Database Encoding

- [ ] **Database configured for UTF-8**
  - MySQL: `charset=utf8mb4` in settings.py (supports full Unicode)
  - Collation: `utf8mb4_unicode_ci`
  - Verify: Check `config/settings.py` DATABASES config

### 3.4 Console Output Encoding

- [ ] **Scripts handle UTF-8 output**
  - Windows: Add `encoding='utf-8'` to `print()` or file writes
  - Verify: Run script in PowerShell → No encoding errors
  - Example:
    ```python
    print("Završeno", encoding='utf-8')  # Windows compatibility
    ```

### 3.5 Static Files Encoding

- [ ] **CSV/JSON/XML files use UTF-8**
  - Save files with UTF-8 encoding (not Windows-1252)
  - BOM (Byte Order Mark) optional but avoid if possible

**Validation Checklist (Manual):**
```bash
# Check for Serbian character corruption
grep -r "ponete\|lanova\|uvamo\|Mo~ete\|Zaponi" templates/
# Should return NO results (these are corrupted forms)

# Verify UTF-8 in Python files
file -i apps/**/*.py
# Should show "charset=utf-8"
```

---

## 4. Testing 🧪

### 4.1 Unit Tests Written

- [ ] **Unit tests cover acceptance criteria**
  - Minimum 1 test per AC
  - Tests use Django TestCase or pytest
  - Test file: `apps/<app>/tests.py`

- [ ] **Test coverage > 80%** (for new code)
  - Run `coverage run manage.py test`
  - Run `coverage report` → Verify new files > 80%
  - Optional but recommended for Epic 2+

### 4.2 All Tests Passing

- [ ] **No test failures**
  - Run `python manage.py test`
  - All tests pass (green output)
  - No skipped tests without justification

- [ ] **No test regressions**
  - Previous stories' tests still pass
  - If tests break, either fix them or update test expectations

### 4.3 Edge Cases Tested

- [ ] **Error handling tested**
  - Invalid input tests
  - 404/403/500 error tests (if applicable)
  - Example: `test_invalid_route_returns_404`

- [ ] **Boundary conditions tested**
  - Empty lists, null values, max length strings
  - Example: `test_form_rejects_text_over_max_length`

---

## 5. Documentation 📚

### 5.1 Code Documentation

- [ ] **Inline comments for complex logic**
  - Not needed for obvious code
  - Required for algorithms, workarounds, non-obvious decisions
  - Example:
    ```python
    # Fix for Django 4.2 bug with select_related on reverse ForeignKey
    queryset = queryset.select_related('submission__applicant')
    ```

- [ ] **Docstrings for complex functions**
  - Not needed for simple getters/setters
  - Required for complex views, utilities, business logic
  - Format: Google-style or NumPy-style (be consistent)

### 5.2 Story Documentation

- [ ] **Story file updated**
  - Status changed to "done"
  - Dev Agent Record section completed:
    - Agent Model Used
    - Debug Log References
    - Completion Notes List
    - File List (all modified/created files)

- [ ] **README updates** (if applicable)
  - New features documented
  - Installation steps updated (if new dependencies)
  - Environment variables documented (if new .env vars)

### 5.3 Migration Documentation

- [ ] **Database migrations created** (if models changed)
  - Run `python manage.py makemigrations`
  - Migrations committed to git
  - Migration tested (apply and rollback)

---

## 6. Version Control 🔄

### 6.1 Git Hygiene

- [ ] **All changes committed**
  - No uncommitted changes (`git status` clean)
  - Meaningful commit messages
  - Commits follow pattern: "Story X.Y DONE: Brief description"

- [ ] **.gitignore verified**
  - No static files blocked (check `git status`)
  - No secrets in git (.env in .gitignore)
  - Verify: `git ls-files static/` shows all needed assets

- [ ] **requirements.txt validated**
  - Test in clean virtual environment:
    ```bash
    python -m venv test-venv
    source test-venv/bin/activate
    pip install -r requirements.txt
    python manage.py check  # Should succeed
    ```
  - No version typos (e.g., Django==5.2 doesn't exist)

### 6.2 File Organization

- [ ] **Files in correct locations**
  - Templates: `templates/<app>/`
  - Static files: `static/css/`, `static/images/`, `static/downloads/`
  - Apps: `apps/<app>/`
  - Scripts: `scripts/` (not project root)

---

## 7. Accessibility ♿

### 7.1 Semantic HTML

- [ ] **Proper HTML5 tags used**
  - `<header>`, `<nav>`, `<main>`, `<footer>`, `<section>`, `<article>`
  - Not just `<div>` for everything

- [ ] **Heading hierarchy correct**
  - One `<h1>` per page
  - Headings in order (h1 → h2 → h3, no skipping levels)

### 7.2 Keyboard Navigation

- [ ] **All interactive elements keyboard-accessible**
  - Tab key cycles through links, buttons, form fields
  - Enter/Space activates buttons
  - Focus states visible (`:focus` CSS defined)

### 7.3 Screen Reader Support

- [ ] **Alt text for images**
  - All `<img>` tags have `alt` attribute
  - Alt text descriptive (not "image" or "icon")

- [ ] **ARIA labels** (if needed)
  - Complex widgets have `aria-label` or `aria-labelledby`
  - Not required for simple forms/links

### 7.4 Color Contrast

- [ ] **Text contrast meets WCAG AA**
  - Minimum 4.5:1 contrast ratio (normal text)
  - Minimum 3:1 contrast ratio (large text)
  - Verify: https://webaim.org/resources/contrastchecker/

---

## 8. Responsive Design 📱

### 8.1 Breakpoints Tested

- [ ] **Desktop (1024px+)**
  - Layout works on large screens
  - No horizontal scrolling

- [ ] **Tablet (768px)**
  - Layout adapts (usually 1-2 columns)
  - Touch-friendly tap targets

- [ ] **Mobile (320px)**
  - Single column layout
  - Minimum 44x44px tap targets
  - Text readable without zoom

### 8.2 Touch Targets

- [ ] **All interactive elements meet minimum size**
  - Buttons, links: min 44x44px (NFR requirement)
  - Verify in CSS: `min-width: 44px; min-height: 44px;`

---

## 9. Code Review ✔️

### 9.1 Peer Review Completed

- [ ] **Code reviewed by another developer or AI reviewer**
  - All code review issues addressed
  - No unresolved comments
  - Review notes added to story file

### 9.2 Validation Review (for complex stories)

- [ ] **Story validated before implementation** (recommended for Epic 2+)
  - Validation score > 80%
  - All MUST FIX items applied
  - SHOULD FIX items considered

---

## 10. Deployment Readiness 🚀

### 10.1 Environment Variables

- [ ] **All env vars documented**
  - `.env.example` updated with new variables
  - `README.md` or `docs/setup.md` lists required env vars
  - No default values in code (use .env)

### 10.2 Static Files Ready

- [ ] **Static files collected** (if testing deployment)
  - Run `python manage.py collectstatic`
  - No errors
  - Files copied to STATIC_ROOT

### 10.3 Database Migrations Applied

- [ ] **Migrations run successfully**
  - Run `python manage.py migrate`
  - No errors
  - Database schema matches models

---

## Exception Handling

**If a DoD item cannot be met:**

1. Document exception in story file (## DoD Exceptions section)
2. Explain rationale (e.g., "Browser testing deferred to user - no BrowserStack access")
3. Get Product Owner approval
4. Create technical debt item in retrospective

**Example:**
```markdown
## DoD Exceptions

**Item:** Cross-browser testing (Safari)
**Rationale:** No macOS/iOS devices available for team
**Approved By:** Mihas (Product Owner)
**Technical Debt:** Track in Epic 4 for pre-production testing
```

---

## Epic 1 Learnings Applied

**Items added based on Epic 1 Retrospective:**

1. ✅ **UTF-8 Encoding Compliance** (Section 3) - Prevents Serbian character corruption
2. ✅ **.gitignore Validation** (Section 6.1) - Prevents static file blocking
3. ✅ **requirements.txt Validation** (Section 6.1) - Prevents version typos
4. ✅ **Story Validation** (Section 9.2) - Recommended for complex stories

---

## Checklist Quick Reference

**Copy this to each story file for tracking:**

```markdown
## Definition of Done Checklist

- [ ] 1. Functional Requirements: ACs met, manual testing complete
- [ ] 2. Code Quality: Django/CSS standards, security, performance
- [ ] 3. UTF-8 Encoding: Templates, Python, database, scripts, static files
- [ ] 4. Testing: Unit tests written, all tests passing, edge cases covered
- [ ] 5. Documentation: Code comments, story file updated, migrations documented
- [ ] 6. Version Control: Commits clean, .gitignore verified, requirements.txt validated
- [ ] 7. Accessibility: Semantic HTML, keyboard nav, alt text, color contrast
- [ ] 8. Responsive Design: Breakpoints tested, touch targets meet minimum
- [ ] 9. Code Review: Peer review complete, validation review (if complex)
- [ ] 10. Deployment Readiness: Env vars documented, static files ready, migrations applied
```

---

## References

- **Epic 1 Retrospective:** `_bmad-output/implementation-artifacts/epic-1-retrospective.md`
- **WCAG Guidelines:** https://www.w3.org/WAI/WCAG21/quickref/
- **Django Best Practices:** https://docs.djangoproject.com/en/4.2/misc/design-philosophies/

---

**Version:** 1.0
**Author:** Bob (Scrum Master)
**Approved:** Mihas (Product Owner)
**Effective Date:** 2025-12-24 (Epic 2 onwards)
