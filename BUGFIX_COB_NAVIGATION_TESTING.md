# COB Form Navigation Bugfix - Testing Documentation

## Bug Report
**Issue:** "Sledeća sekcija" button doesn't work on COB form at http://127.0.0.1:8000/inicijativa/

**Root Cause:**
- COB form was reusing `section-navigation.js` from Epic 2 (COA form)
- COA validates fields that DON'T EXIST in COB:
  - Section I: `id_jmbg` (JMBG field - removed in COB)
  - Section I: `id_maticni_broj` (Matični broj - removed in COB)
  - Section II: `id_budžet` (Budget field - removed in COB)
- COA Section II field names are different from COB
- COA used `.entity-type-switcher` as Section I container, COB uses `#section-i`

## Fix Applied
**Created:** `static/js/cob-section-navigation.js` (591 lines)
- COB-specific validation for Section I (NO JMBG/Matični broj)
- COB-specific validation for Section II (NO Budget, different field names)
- Updated DOM selectors to match COB form structure

**Modified:** `templates/submissions/cob_form.html`
- Changed line 314: `section-navigation.js` → `cob-section-navigation.js`

## Git Commit
```
commit 8541081
Author: [Developer]
Date: [Today]

Bugfix: COB form section navigation - "Sledeća sekcija" button now works
```

## Testing Checklist

### Pre-Test Setup
- [ ] Django dev server running: `python manage.py runserver 127.0.0.1:8000`
- [ ] Navigate to: http://127.0.0.1:8000/inicijativa/
- [ ] Open browser DevTools Console (F12)

### Test 1: Initial State
- [ ] Section I is visible
- [ ] Section II is hidden
- [ ] Section III is hidden
- [ ] Progress stepper shows "Sekcija 1 od 3"
- [ ] "SLEDEĆA SEKCIJA" button is enabled
- [ ] "PRETHODNA SEKCIJA" button is enabled

### Test 2: Navigation Validation (Empty Form)
- [ ] Click "SLEDEĆA SEKCIJA" without filling any fields
- [ ] Validation errors appear for required fields
- [ ] Section I remains visible (navigation blocked)
- [ ] Console shows no JavaScript errors

### Test 3: Section I → Section II Navigation (Fizičko lice)
Fill Section I fields:
- [ ] Tip podnosioca: Fizičko lice (default)
- [ ] Ime: "Marko"
- [ ] Prezime: "Marković"
- [ ] Adresa: "Ulica Kralja Petra 1, Beograd"
- [ ] Email: "marko.markovic@example.com"
- [ ] Telefon: "0601234567"

Click "SLEDEĆA SEKCIJA":
- [ ] Section I disappears
- [ ] Section II appears
- [ ] Progress stepper shows "Sekcija 2 od 3"
- [ ] Stepper Step 1 has "completed" state
- [ ] Stepper Step 2 has "active" state
- [ ] Console shows no errors

### Test 4: Section I → Section II Navigation (Pravno lice)
- [ ] Click "PRETHODNA SEKCIJA" to return to Section I
- [ ] Switch to "Pravno lice"
- [ ] Fill required fields:
  - Naziv organizacije: "Test Organizacija DOO"
  - Adresa: "Ulica Kneza Miloša 10, Beograd"
  - Email: "info@testorg.rs"
  - Telefon: "0112345678"
- [ ] Click "SLEDEĆA SEKCIJA"
- [ ] Section II appears (navigation successful)

### Test 5: Section II → Section III Navigation
Fill Section II fields:
- [ ] Naslov inicijative: "Test inicijativa"
- [ ] Kratak opis: "Kratak opis inicijative za testiranje navigacije"
- [ ] Problem: "Problem koji inicijativa rešava - test tekst"
- [ ] Cilj: "Cilj inicijative - test tekst"
- [ ] Planirani koraci: "Planirani koraci za realizaciju - test tekst"
- [ ] Očekivani uticaj: "Očekivani uticaj na zajednicu - test tekst"

Click "SLEDEĆA SEKCIJA":
- [ ] Section II disappears
- [ ] Section III appears
- [ ] Progress stepper shows "Sekcija 3 od 3"
- [ ] Stepper Steps 1-2 have "completed" state
- [ ] Stepper Step 3 has "active" state

### Test 6: Backward Navigation (Section III → II → I)
From Section III:
- [ ] Click "PRETHODNA SEKCIJA"
- [ ] Section II appears
- [ ] Progress stepper shows "Sekcija 2 od 3"

From Section II:
- [ ] Click "PRETHODNA SEKCIJA"
- [ ] Section I appears
- [ ] Progress stepper shows "Sekcija 1 od 3"

### Test 7: Validation Error Messages (Section II)
Navigate to Section II:
- [ ] Clear all Section II fields
- [ ] Click "SLEDEĆA SEKCIJA"
- [ ] Validation errors appear for each required field:
  - "Naslov inicijative je obavezno polje"
  - "Kratak opis je obavezno polje"
  - "Problem koji inicijativa rešava je obavezno polje"
  - "Cilj inicijative je obavezno polje"
  - "Planirani koraci je obavezno polje"
  - "Očekivani uticaj na zajednicu je obavezno polje"
- [ ] Navigation is blocked (Section II remains visible)

### Test 8: Focus Management
- [ ] Navigate from Section I → Section II
- [ ] First field in Section II receives focus (id_naslov)
- [ ] Navigate back Section II → Section I
- [ ] First field in Section I receives focus (id_ime or id_naziv_organizacije)

### Test 9: Scroll Behavior
- [ ] Navigate forward and backward
- [ ] Page scrolls to top smoothly on each navigation
- [ ] No jumping or janky scroll behavior

### Test 10: Browser Console
Check browser console for:
- [ ] No JavaScript errors
- [ ] Console log: "COB Section navigation initialized"
- [ ] Optional performance warnings (if navigation >100ms)

## Expected Results
✅ All tests should PASS
✅ Navigation works smoothly between all 3 sections
✅ Validation blocks navigation when required fields are empty
✅ Backward navigation works without validation
✅ Progress stepper updates correctly
✅ No JavaScript errors in console

## Field Comparison: COA vs COB

### Section I Differences
| Field | COA | COB |
|-------|-----|-----|
| JMBG (Fizičko) | ✅ Required | ❌ Removed |
| Matični broj (Pravno) | ✅ Required | ❌ Removed |

### Section II Differences
| Field | COA | COB |
|-------|-----|-----|
| Naslov projekta | ✅ (id_naslov) | ✅ (id_naslov) |
| Kratak opis | ✅ (id_opis) | ✅ (id_kratak_opis) |
| Problem | ✅ (id_problem) | ✅ (id_problem) |
| Cilj | ✅ (id_cilj) | ✅ (id_cilj) |
| Specifični ciljevi | ✅ (id_specifični_ciljevi) | ❌ Removed |
| Ciljne grupe | ✅ (id_ciljne_grupe) | ❌ Removed |
| Aktivnosti | ✅ (id_aktivnosti) | ✅ (id_planirani_koraci) |
| Rezultati | ✅ (id_rezultati) | ✅ (id_ocekivani_uticaj) |
| **Budget** | **✅ (id_budžet)** | **❌ Removed** |

## Files Modified
1. **NEW:** `static/js/cob-section-navigation.js`
   - 591 lines
   - COB-specific validation logic
   - Validates correct field names for COB form

2. **MODIFIED:** `templates/submissions/cob_form.html`
   - Line 314: Changed script reference to `cob-section-navigation.js`

## Verification Commands
```bash
# Check if COB form loads
curl -s http://127.0.0.1:8000/inicijativa/ -o /dev/null -w "%{http_code}\n"
# Expected: 200

# Check if navigation script loads
curl -s http://127.0.0.1:8000/static/js/cob-section-navigation.js -o /dev/null -w "%{http_code}\n"
# Expected: 200

# Check git commit
git log -1 --oneline
# Expected: 8541081 Bugfix: COB form section navigation - "Sledeća sekcija" button now works
```

## Notes
- Navigation works ONLY with valid data in required fields
- Backward navigation (PRETHODNA SEKCIJA) does NOT require validation
- Draft auto-save triggers on navigation (if enabled)
- Character counters initialize when Section II becomes visible
- File upload UI initializes when Section III becomes visible

## Regression Testing
Verify COA form still works:
- [ ] Navigate to: http://127.0.0.1:8000/aplikacija/
- [ ] Test COA navigation (should still use `section-navigation.js`)
- [ ] Verify COA validation includes JMBG, Matični broj, and Budget
- [ ] No impact on COA form functionality

## Success Criteria
✅ COB form section navigation fully functional
✅ All manual tests pass
✅ No JavaScript console errors
✅ COA form navigation unaffected (regression test)
✅ Git commit created with detailed description
✅ Documentation updated

---
**Test Date:** [To be filled by tester]
**Tester:** [To be filled by tester]
**Status:** PENDING / PASS / FAIL
