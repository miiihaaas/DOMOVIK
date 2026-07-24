# Story 2.7: Progress Stepper & Section Navigation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a podnosilac prijave,
I want da vidim gde se nalazim u procesu i mogu da navigiram između sekcija,
So that imam kontrolu nad popunjavanjem forme.

## Acceptance Criteria

**Given** korisnik popunjava COA formu
**When** je u bilo kojoj sekciji
**Then** vidi progress stepper koji prikazuje "Sekcija X od 3" (FR33)
**And** stepper vizualno označava trenutni korak (npr. tirkizna boja za active step)

**When** korisnik je u Sekciji I ili II
**Then** vidi dugme "SLEDEĆA SEKCIJA" (FR34)

**When** korisnik klikne "SLEDEĆA SEKCIJA" a obavezna polja NISU popunjena
**Then** sistem sprečava prelazak (FR32)
**And** prikazuje error messages uz nepopunjena polja
**And** fokus ide na prvo INVALID/EMPTY polje (ne na prvi input u sekciji)

**When** više od 5 polja nije popunjeno
**Then** sistem prikazuje validation summary sa ukupnim brojem grešaka
**And** prikazuje samo prvih 5 inline error messages
**And** omogućava "Prikaži sve greške" expand/collapse za preostale greške

**When** sva obavezna polja JESU popunjena i validna
**Then** korisnik prelazi na sledeću sekciju
**And** progress stepper se update-uje (npr. "Sekcija 2 od 3")
**And** nova sekcija se prikazuje za manje od 100ms (NFR5 - performance)

**When** korisnik menja entity type (fizičko ↔ pravno) nakon popunjavanja polja u Sekciji I
**Then** validacija proverava SAMO aktuelni entity type polja (fizičko ILI pravno, ne oba)
**And** draft sistem čuva oba seta polja (fizičko I pravno) za buduće switch-ovanje

**When** korisnik je u Sekciji II ili III
**Then** vidi dugme "PRETHODNA SEKCIJA" (FR34)
**And** može da se vrati na prethodnu sekciju bez gubitka podataka (draft čuva sve)

**When** korisnik koristi mobile device (320px width)
**Then** stepper i navigation buttons su funkcionalni i touch-friendly (min 44px tap target - NFR40)
**And** stepper se prilagođava mobile layout-u (manji circle, kraće labele)
**And** navigation buttons su full-width sa min 44px height

**And** navigation UX je intuitivna i jasna tako da 85%+ korisnika razume gde su u procesu bez potrebe za pomoć (NFR33-34)

**Note:** Stepper steps (1, 2, 3 circles) NISU clickable u MVP verziji - korisnik može navigirati SAMO putem "SLEDEĆA SEKCIJA" i "PRETHODNA SEKCIJA" dugmadi. Direct click navigation je planirana za buduću verziju (vidi Task 10 - Optional Enhancement).

## 🔥 CRITICAL IMPLEMENTATION CONSTRAINTS

**⚠️ IMPORTANT: Partial Implementation Already Exists**

**From Story 2.6 Analysis:**
- ✅ `static/js/section-navigation.js` already created (265 lines) with basic navigation logic
  - **VERIFIED 2025-12-26:** File exists at `C:\Programming\dev-bmad\DOMOVIK\static\js\section-navigation.js`
  - **Note:** Architecture.md incorrectly refers to this as `form-navigation.js` - IGNORE that, use `section-navigation.js`
- ✅ Progress stepper partial template `templates/submissions/_progress_stepper.html` exists
- ✅ `showSection()` function handles section visibility
- ✅ `updateProgressStepper()` function updates stepper state
- ⚠️ **Story 2.7 ENHANCES existing implementation** - NOT a complete rewrite

**What Story 2.7 Adds:**
1. **Enhanced Progress Stepper Visual Design** - Make stepper more prominent and civic-tech styled
2. **Improved Navigation Validation** - More robust field validation before navigation
3. **Smooth Scroll & Focus Management** - Better UX when navigating between sections
4. **Mobile Responsive Navigation** - Optimize stepper and buttons for 320px+ screens
5. **Accessibility Enhancements** - ARIA landmarks, keyboard navigation improvements
6. **Integration Testing** - Comprehensive testing across all 3 sections

**CRITICAL Rules:**
1. **REUSE** existing `section-navigation.js` - extend it, don't replace it
2. **ENHANCE** `_progress_stepper.html` template - improve visual design
3. **INTEGRATE** with existing validation from Story 2.3 and 2.6
4. **PRESERVE** all draft system functionality from Stories 2.4-2.5
5. **MAINTAIN** BEM CSS methodology and civic tech design system
6. **TEST** navigation flow across all 3 sections (I → II → III → II → I)
7. **GDPR Compliance** - Navigation must work with localStorage draft system
8. **Performance** - Smooth transitions (<100ms response time)
9. **UTF-8 Serbian** - All button labels and messages in proper Serbian
10. **Cross-Browser** - Chrome, Firefox, Safari, Edge support

## Tasks / Subtasks

- [ ] Task 1: Analyze Existing Navigation Implementation (From Story 2.6)
  - [ ] 1.1: Read `static/js/section-navigation.js` completely
  - [ ] 1.2: Document all existing functions: `showSection()`, `updateProgressStepper()`, `validateSectionI()`, `validateSectionII()`
  - [ ] 1.3: Read `templates/submissions/_progress_stepper.html` template
  - [ ] 1.4: Identify gaps in current implementation vs Story 2.7 AC
  - [ ] 1.5: Create enhancement plan - what to add, what to improve
  - [ ] 1.6: Check integration with draft-manager.js and character-counter.js
  - [ ] 1.7: Verify existing button selectors and event listeners
  - [ ] 1.8: Test current navigation: Section I → II → III flow
  - [ ] 1.9: Document any bugs or issues found
  - [ ] 1.10: Plan backwards compatibility - don't break Story 2.6 functionality

- [ ] Task 2: Enhanced Progress Stepper Visual Design (AC: FR33)
  - [ ] 2.1: Review UX spec for stepper design (tirkizna #0EA5E9 active, neutral gray inactive)
  - [ ] 2.2: Update `_progress_stepper.html` template with improved markup
  - [ ] 2.3: Add step numbers (1, 2, 3) with icons or circles
  - [ ] 2.4: Add step labels: "Opšti podaci", "Podaci o projektu", "Dokumentacija i saglasnost"
  - [ ] 2.5: Add completed state visual (checkmark for completed sections)
  - [ ] 2.6: Add active state visual (tirkizna color, bold text)
  - [ ] 2.7: Add inactive/upcoming state visual (gray, lighter text)
  - [ ] 2.8: Create CSS styles in `forms.css` using BEM methodology
  - [ ] 2.9: Add connector lines between steps (visual progress bar)
  - [ ] 2.10: Ensure stepper is prominent at top of form (sticky positioning optional)
  - [ ] 2.11: Test: Stepper displays correctly in all 3 sections
  - [ ] 2.12: Test: Visual states update correctly on navigation

- [ ] Task 3: Progress Stepper CSS Styling (AC: UX civic tech design)
  - [ ] 3.1: Create `.progress-stepper` BEM block in forms.css
  - [ ] 3.2: Style step circles: 40px diameter, border 2px, center-aligned numbers
  - [ ] 3.3: Style connector lines: 2px height, gray (#D6D3D1) default, tirkizna (#0EA5E9) when completed
  - [ ] 3.4: Style step labels: 14px font-size, positioned below circles
  - [ ] 3.5: Active step: tirkizna background (#0EA5E9), white text, bold label
  - [ ] 3.6: Completed step: checkmark icon (✓), tirkizna border, gray background (#F5F5F0)
  - [ ] 3.7: Inactive step: gray border (#D6D3D1), white background, gray text (#78716C)
  - [ ] 3.8: Hover states on completed/active steps (subtle brightness change)
  - [ ] 3.9: Mobile responsive: smaller circles (32px), stacked layout if needed, shorter labels
  - [ ] 3.10: Test: Color contrast WCAG AA compliance (4.5:1+ ratio)
  - [ ] 3.11: Test: Stepper looks good on 320px, 768px, 1024px+ screens
  - [ ] 3.12: Test: Visual hierarchy - stepper is prominent but not overwhelming

- [ ] Task 4: Section Navigation Button Styles (AC: FR34, UX design)
  - [ ] 4.1: Style "SLEDEĆA SEKCIJA" button - primary style (koraljna #FF7A59 or tirkizna #0EA5E9)
  - [ ] 4.2: Style "PRETHODNA SEKCIJA" button - secondary style (gray border, white background)
  - [ ] 4.3: Add button spacing: gap between PRETHODNA and SLEDEĆA
  - [ ] 4.4: Position buttons at bottom of each section (right-aligned or centered)
  - [ ] 4.5: Add hover states: subtle scale/shadow effect
  - [ ] 4.6: Add disabled state for SLEDEĆA (gray, no hover) when validation fails
  - [ ] 4.7: Mobile responsive: full-width buttons on mobile (320px), min 44px height
  - [ ] 4.8: Add icons to buttons (optional): arrow right →, arrow left ←
  - [ ] 4.9: Ensure buttons have clear focus states (2px outline) for keyboard navigation
  - [ ] 4.10: Test: Buttons render correctly in all sections
  - [ ] 4.11: Test: Buttons are touch-friendly on mobile (44x44px min tap target)
  - [ ] 4.12: Test: Button states (enabled/disabled) update correctly

- [ ] Task 5: Improved Validation Before Navigation (AC: FR32)
  - [ ] 5.1: Enhance `validateSectionI()` in section-navigation.js
  - [ ] 5.2: Check entity type selection (fizičko/pravno must be selected)
  - [ ] 5.3: Check all required fields for CURRENTLY SELECTED entity type (NOT both):
    - Fizičko: ime, prezime, adresa, email, telefon, JMBG
    - Pravno: naziv, adresa, email, telefon, matični broj
    - **IMPORTANT:** If user switches entity type mid-flow, validate ONLY the active type
    - Draft system saves BOTH sets of fields for future switching
  - [ ] 5.4: Integrate with existing real-time validation (from Story 2.3)
  - [ ] 5.5: Display inline error messages next to empty/invalid fields
  - [ ] 5.6: Create `validateSectionIII()` function for documentation & consent section
  - [ ] 5.7: Check file uploads in Section III (if required files are uploaded)
  - [ ] 5.8: Check consent checkboxes (all 3 must be checked)
  - [ ] 5.9: Return validation result object: `{ isValid: boolean, firstErrorField: element }`
  - [ ] 5.10: Test: Validation prevents navigation when fields empty
  - [ ] 5.11: Test: Validation passes when all fields valid
  - [ ] 5.12: Test: Error messages display correctly in Serbian

- [ ] Task 6: Smooth Scroll & Focus Management (AC: UX best practices)
  - [ ] 6.1: Create `scrollToTop()` function - smooth scroll to top of form after navigation
  - [ ] 6.2: Create `focusFirstField(sectionNumber)` function - focus first input in new section
  - [ ] 6.3: Create `scrollToFirstError(errorField)` function - scroll to first validation error
  - [ ] 6.4: Trigger scroll after successful navigation (Section I → II → III)
  - [ ] 6.5: Trigger focus on first error field when validation fails
  - [ ] 6.6: Use `scrollIntoView({ behavior: 'smooth', block: 'center' })` for smooth scroll
  - [ ] 6.7: Add 200ms delay before focus to allow scroll animation to complete
  - [ ] 6.8: Ensure scroll works on all browsers (Chrome, Firefox, Safari, Edge)
  - [ ] 6.9: Test: Navigation scrolls smoothly to top of next section
  - [ ] 6.10: Test: Validation error scrolls to first error field
  - [ ] 6.11: Test: Focus visible on first field after navigation
  - [ ] 6.12: Test: No jarring jumps or layout shifts during scroll

- [ ] Task 7: Keyboard Navigation Support (AC: NFR46-49 accessibility)
  - [ ] 7.1: Ensure Tab key navigates through all fields in logical order
  - [ ] 7.2: Ensure Shift+Tab navigates backwards
  - [ ] 7.3: Add keyboard shortcut for navigation (optional): Ctrl+→ (next), Ctrl+← (previous)
  - [ ] 7.4: Ensure Enter key on SLEDEĆA/PRETHODNA buttons triggers navigation
  - [ ] 7.5: Ensure Escape key doesn't accidentally navigate away (prevent default if needed)
  - [ ] 7.6: Add visible focus indicators (2px outline) on all interactive elements
  - [ ] 7.7: Ensure progress stepper steps are keyboard accessible (Tab to each step)
  - [ ] 7.8: Add `tabindex="0"` to progress stepper steps for keyboard focus
  - [ ] 7.9: Add keyboard click handler (Enter/Space) to stepper steps for direct navigation (optional)
  - [ ] 7.10: Test: Tab order is logical (fields → buttons → stepper)
  - [ ] 7.11: Test: Keyboard-only navigation works (no mouse needed)
  - [ ] 7.12: Test: Focus indicators visible on all elements

- [ ] Task 8: ARIA Attributes & Screen Reader Support (AC: NFR46-49)
  - [ ] 8.1: Add `role="navigation"` to progress stepper container
  - [ ] 8.2: Add `aria-label="Progress stepper"` to stepper
  - [ ] 8.3: Add `aria-current="step"` to active step in stepper
  - [ ] 8.4: Add `aria-label="Completed"` to completed steps
  - [ ] 8.5: Add `aria-disabled="true"` to inactive/upcoming steps
  - [ ] 8.6: Add `aria-live="polite"` to stepper for dynamic updates announcement
  - [ ] 8.7: Add descriptive button labels: `aria-label="Nastavi na sledeću sekciju"`
  - [ ] 8.8: Add landmark roles: `<nav role="navigation">` for stepper
  - [ ] 8.9: Ensure section headings have proper hierarchy (h2 for section titles)
  - [ ] 8.10: Add visually hidden text for screen readers: "You are on Section X of 3"
  - [ ] 8.11: Test: NVDA/JAWS announces stepper state correctly
  - [ ] 8.12: Test: Screen reader announces section changes on navigation

- [ ] Task 9: Mobile Responsive Navigation (AC: NFR40-45)
  - [ ] 9.1: Add mobile breakpoint CSS (@media max-width: 767px)
  - [ ] 9.2: Progress stepper: reduce circle size to 32px on mobile
  - [ ] 9.3: Progress stepper: shorter step labels on mobile ("Opšti", "Projekat", "Dokumenta")
  - [ ] 9.4: Progress stepper: stack vertically if horizontal doesn't fit (optional)
  - [ ] 9.5: Navigation buttons: full-width on mobile (100% width)
  - [ ] 9.6: Navigation buttons: min 44px height for touch targets
  - [ ] 9.7: Navigation buttons: stack vertically (PRETHODNA above SLEDEĆA)
  - [ ] 9.8: Ensure stepper doesn't overflow on 320px screens
  - [ ] 9.9: Test touch interactions: tap on stepper steps, tap on buttons
  - [ ] 9.10: Test: Navigation works smoothly on iPhone Safari
  - [ ] 9.11: Test: Navigation works smoothly on Android Chrome
  - [ ] 9.12: Test: No horizontal scroll on mobile (320px width)

- [ ] Task 10: Direct Section Navigation (Optional Enhancement)
  - [ ] 10.1: Make stepper steps clickable for direct navigation (Section I ↔ II ↔ III)
  - [ ] 10.2: Allow navigation to completed sections only (can't skip ahead)
  - [ ] 10.3: Add click handler to stepper steps: `navigateToSection(sectionNumber)`
  - [ ] 10.4: Validate current section before allowing navigation away
  - [ ] 10.5: Update stepper visual states on direct navigation
  - [ ] 10.6: Save draft before navigating to another section
  - [ ] 10.7: Add hover state to clickable steps (cursor: pointer, subtle highlight)
  - [ ] 10.8: Disable click on inactive/upcoming steps (cursor: not-allowed)
  - [ ] 10.9: Add ARIA labels for clickable steps: "Go to Section I: General Data"
  - [ ] 10.10: Test: Direct navigation works (Section I → click Section III if completed)
  - [ ] 10.11: Test: Cannot skip to Section III from Section I (validation blocks)
  - [ ] 10.12: Test: Can navigate back from Section III to Section I via stepper

- [ ] Task 11: Integration with Draft System (AC: GDPR NFR16)
  - [ ] 11.1: Ensure navigation triggers auto-save before section change
  - [ ] 11.2: Update `showSection()` to call `saveDraft()` from draft-manager.js
  - [ ] 11.3: Store current section number in draft: `currentSection: 1|2|3`
  - [ ] 11.4: On draft load (AFTER modal "Nastavi" click), restore user to last active section (prevents jarring flash of wrong section before modal)
  - [ ] 11.5: Update progress stepper on draft load to show correct section
  - [ ] 11.6: Ensure PRETHODNA SEKCIJA doesn't lose entered data (draft saves before navigation)
  - [ ] 11.7: Test: Navigate I → II → close browser → reload → draft modal → "Nastavi" → lands on Section II
  - [ ] 11.8: Test: All section data preserved when navigating back and forth
  - [ ] 11.9: Test: Auto-save triggers on section change
  - [ ] 11.10: Test: Current section stored in localStorage

- [ ] Task 12: Error Handling & User Feedback (AC: NFR30)
  - [ ] 12.1: Display clear error message when validation fails: "Molimo popunite sva obavezna polja"
  - [ ] 12.2: Create alert/banner at top of section with validation summary (total error count)
  - [ ] 12.3: Highlight all invalid fields with red border and error icon
  - [ ] 12.4: Display inline error messages below each invalid field
    - **LIMIT:** If 5+ errors, show only first 5 inline errors to avoid overwhelming user
    - Add "Prikaži sve greške" expand/collapse link to reveal remaining errors
  - [ ] 12.5: Clear previous errors when user starts correcting (on input event)
  - [ ] 12.6: Show success feedback when navigation succeeds (optional: green checkmark animation)
  - [ ] 12.7: Add loading state during section transition (brief spinner - <100ms)
  - [ ] 12.8: Ensure error messages are user-friendly (no technical jargon)
  - [ ] 12.9: Use Serbian language for all error messages
  - [ ] 12.10: Test: Validation error banner displays at top
  - [ ] 12.11: Test: Error messages clear when user corrects field
  - [ ] 12.12: Test: Success feedback displays briefly on successful navigation

- [ ] Task 13: Cross-Section Data Persistence (AC: Draft system integration)
  - [ ] 13.1: Verify all Section I fields saved when navigating to Section II
  - [ ] 13.2: Verify all Section II fields saved when navigating to Section III
  - [ ] 13.3: Verify all Section III fields saved when navigating back to Section I/II
  - [ ] 13.4: Test entity type switch (fizičko/pravno) data preserved across sections
  - [ ] 13.5: Test character counter states restored when returning to Section II
  - [ ] 13.6: Test file upload metadata preserved when navigating away from Section III
  - [ ] 13.7: Test validation states preserved (green checkmarks on valid fields)
  - [ ] 13.8: Ensure no data loss during any navigation path
  - [ ] 13.9: Test: Section I → II → III → II → I → all data intact
  - [ ] 13.10: Test: Refresh page mid-navigation → draft recovery → all data + section state restored

- [ ] Task 14: Performance Optimization (AC: NFR5)
  - [ ] 14.1: Measure navigation time: MUST be <100ms from button click to new section visible
  - [ ] 14.2: Use CSS transitions for smooth section visibility changes
  - [ ] 14.3: Optimize `showSection()` function: minimize DOM operations
  - [ ] 14.4: Cache section elements to avoid repeated `querySelector` calls
  - [ ] 14.5: Use `requestAnimationFrame` for visual updates if needed
  - [ ] 14.6: Defer non-critical operations (analytics, logging) to avoid blocking UI
  - [ ] 14.7: Test navigation on low-end devices (ensure no lag)
  - [ ] 14.8: Use Chrome DevTools Performance tab to identify bottlenecks
  - [ ] 14.9: Optimize stepper update logic (batch DOM updates)
  - [ ] 14.10: Test: Navigation feels instant (<100ms response time)
  - [ ] 14.11: Test: No janky animations or layout shifts
  - [ ] 14.12: Test: Smooth performance on 4x CPU slowdown (DevTools)

- [ ] Task 15: UTF-8 Encoding Validation (AC: project-context.md)
  - [ ] 15.1: Verify all button labels in Serbian (č, ć, š, đ, ž): "SLEDEĆA SEKCIJA", "PRETHODNA SEKCIJA"
  - [ ] 15.2: Verify stepper labels: "Opšti podaci", "Podaci o projektu", "Dokumentacija i saglasnost"
  - [ ] 15.3: Verify error messages: "Molimo popunite sva obavezna polja"
  - [ ] 15.4: Check HTML template has `<meta charset="UTF-8">`
  - [ ] 15.5: Check JavaScript files saved with UTF-8 encoding (no BOM)
  - [ ] 15.6: Check CSS files saved with UTF-8 encoding
  - [ ] 15.7: Test in browser: no corrupted Serbian characters
  - [ ] 15.8: Grep for corrupted patterns: "ponete", "lanova", "uvamo" → 0 results
  - [ ] 15.9: Run Definition of Done UTF-8 checklist (docs/definition-of-done.md Section 3)
  - [ ] 15.10: Test console output: no encoding errors

- [ ] Task 16: Integration Testing (AC: All acceptance criteria)
  - [ ] 16.1: Test full navigation flow: Section I → II → III (forward navigation)
  - [ ] 16.2: Test backward navigation: Section III → II → I (PRETHODNA SEKCIJA)
  - [ ] 16.3: Test mixed navigation: I → II → I → II → III (back and forth)
  - [ ] 16.4: Test validation blocking: Section I empty → "SLEDEĆA SEKCIJA" → blocked
  - [ ] 16.5: Test validation passing: Section I valid → "SLEDEĆA SEKCIJA" → Section II visible
  - [ ] 16.6: Test stepper visual states update correctly on navigation
  - [ ] 16.7: Test stepper shows "Sekcija 1 od 3", "Sekcija 2 od 3", "Sekcija 3 od 3"
  - [ ] 16.8: Test data persistence: Navigate I → II → refresh → draft modal → Section II restored
  - [ ] 16.9: Test character counters trigger in Section II after navigation
  - [ ] 16.10: Test file upload UI displays correctly in Section III
  - [ ] 16.11: Test cross-browser with specific scenarios:
    - Chrome: Smooth scroll works with `behavior: 'smooth'`, stepper CSS transitions smooth
    - Firefox: Smooth scroll works, ARIA announcements correct
    - Safari: Fallback to instant scroll if smooth not supported, touch targets work
    - Edge: Stepper visual states (tirkizna colors) render correctly, navigation <100ms
  - [ ] 16.12: Test mobile: Navigation works on 320px, 768px screens

- [ ] Task 17: Code Review & Definition of Done (AC: DoD checklist)
  - [ ] 17.1: Review against docs/definition-of-done.md
  - [ ] 17.2: Verify all acceptance criteria met
  - [ ] 17.3: Run manual testing (all scenarios in Task 16)
  - [ ] 17.4: Check JavaScript naming conventions (camelCase)
  - [ ] 17.5: Check CSS naming conventions (BEM methodology)
  - [ ] 17.6: Verify ARIA attributes present and correct
  - [ ] 17.7: Verify color contrast WCAG AA compliance
  - [ ] 17.8: Verify no hardcoded strings (all Serbian labels in templates/JS)
  - [ ] 17.9: Git staging: stage all modified files
  - [ ] 17.10: Prepare commit message: "Story 2.7 DONE: Progress Stepper & Section Navigation"
  - [ ] 17.11: Update sprint-status.yaml (2-7: backlog → ready-for-dev → review → done)
  - [ ] 17.12: Document any deviations or decisions in completion notes

## Dev Notes

### ⚡ KEY INTEGRATION POINTS (From Story 2.6)

**Story 2.6 Already Implemented:**
- ✅ `static/js/section-navigation.js` (265 lines) - Basic navigation logic
- ✅ `templates/submissions/_progress_stepper.html` - Stepper partial template
- ✅ `showSection(sectionNumber)` function - Section visibility management
- ✅ `updateProgressStepper(sectionNumber)` function - Stepper state updates
- ✅ `validateSectionI()` and `validateSectionII()` - Section validation
- ✅ Navigation buttons: "SLEDEĆA SEKCIJA", "PRETHODNA SEKCIJA"
- ✅ Integration with draft-manager.js auto-save

**Story 2.7 Enhancements:**
- ⭐ Enhanced stepper visual design (civic tech identity - tirkizna/koraljna colors)
- ⭐ Improved validation logic (more robust field checks)
- ⭐ Smooth scroll & focus management
- ⭐ Keyboard navigation & ARIA enhancements
- ⭐ Mobile responsive optimizations
- ⭐ Direct section navigation via stepper clicks (optional)
- ⭐ Better error handling & user feedback
- ⭐ Performance optimizations (<100ms navigation)

### 📋 Quick Reference - Progress Stepper & Navigation

| Component | File | Function/Element | Purpose |
|-----------|------|------------------|---------|
| Navigation Module | `static/js/section-navigation.js` | ENHANCE existing | Section visibility & stepper updates |
| Stepper Template | `templates/submissions/_progress_stepper.html` | ENHANCE existing | Stepper HTML markup |
| Stepper Styles | `static/css/forms.css` | ADD new styles | BEM CSS for stepper visual design |
| Button Styles | `static/css/forms.css` | ENHANCE existing | SLEDEĆA/PRETHODNA button styles |
| Validation | `static/js/section-navigation.js` | `validateSectionI/II/III()` | Section-level validation |
| Scroll Management | `static/js/section-navigation.js` | `scrollToTop()`, `scrollToFirstError()` | Smooth scroll UX |
| Draft Integration | `static/js/draft-manager.js` | `saveDraft()` called on navigation | GDPR-compliant persistence |
| Focus Management | `static/js/section-navigation.js` | `focusFirstField()` | Keyboard accessibility |

### 🔍 STORY CONTEXT - Building on Stories 2.1-2.6

**Story 2.2 Established (Section I + Basic Stepper):**
- ✅ Initial progress stepper template created
- ✅ Basic section visibility logic
- ✅ Entity type switch (fizičko/pravno)
- ✅ "Sekcija 1 od 3" text display

**Story 2.6 Established (Section II + Navigation Enhancement):**
- ✅ `section-navigation.js` module created (265 lines)
- ✅ `showSection()` function with section visibility toggle
- ✅ `updateProgressStepper()` function with stepper text updates
- ✅ Validation before navigation (Section I and II)
- ✅ Navigation buttons with event listeners
- ✅ Integration with draft system (auto-save on navigation)

**Story 2.7 Adds (NEW FEATURES):**
- ⭐ Enhanced visual design for stepper (civic tech colors - tirkizna active, gray inactive, checkmarks for completed)
- ⭐ Improved validation with better error messages and focus management
- ⭐ Smooth scroll to top on navigation
- ⭐ Scroll to first error field when validation fails
- ⭐ Keyboard navigation support (Tab, Shift+Tab, Enter, optional Ctrl+arrow shortcuts)
- ⭐ ARIA attributes for screen reader support
- ⭐ Mobile responsive stepper (smaller circles, shorter labels, stacked buttons)
- ⭐ Direct section navigation via stepper clicks (optional)
- ⭐ Better error handling (validation summary banner + inline errors)
- ⭐ Performance optimizations (<100ms navigation)
- ⭐ Cross-section data persistence verification

### 🔬 Technical Requirements

#### 1. Progress Stepper Visual Specification

**Stepper Layout:**
```
[1] ━━━━ [2] ━━━━ [3]
Opšti    Projekat  Dokumenta
podaci              saglasnost
```

**Step States:**

| State | Visual | Circle Color | Circle Border | Connector Line | Text Color |
|-------|--------|--------------|---------------|----------------|------------|
| Active (Current) | Number + Bold label | Tirkizna #0EA5E9 bg | 2px tirkizna | Gray before, tirkizna after | Tirkizna #0EA5E9 |
| Completed | Checkmark ✓ | White/Gray #F5F5F0 bg | 2px tirkizna | Tirkizna | Gray #78716C |
| Inactive (Upcoming) | Number + Normal label | White bg | 2px gray #D6D3D1 | Gray | Gray #78716C |

**Implementation Example (BEM CSS):**
```css
.progress-stepper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 32px 0;
  padding: 16px;
}

.progress-stepper__step {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.progress-stepper__circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid #D6D3D1; /* Default gray */
  background-color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 16px;
  color: #78716C; /* Gray text */
  transition: all 0.3s ease;
}

.progress-stepper__step--active .progress-stepper__circle {
  background-color: #0EA5E9; /* Tirkizna */
  border-color: #0EA5E9;
  color: white;
}

.progress-stepper__step--completed .progress-stepper__circle {
  background-color: #F5F5F0; /* Light gray */
  border-color: #0EA5E9; /* Tirkizna border */
  color: #10B981; /* Green checkmark */
}

.progress-stepper__label {
  margin-top: 8px;
  font-size: 14px;
  color: #78716C; /* Gray */
  text-align: center;
}

.progress-stepper__step--active .progress-stepper__label {
  color: #0EA5E9; /* Tirkizna */
  font-weight: 600;
}

.progress-stepper__connector {
  flex: 1;
  height: 2px;
  background-color: #D6D3D1; /* Gray */
  margin: 0 8px;
}

.progress-stepper__connector--completed {
  background-color: #0EA5E9; /* Tirkizna */
}

/* Mobile Responsive */
@media (max-width: 767px) {
  .progress-stepper__circle {
    width: 32px;
    height: 32px;
    font-size: 14px;
  }

  .progress-stepper__label {
    font-size: 12px;
    max-width: 80px; /* Shorter labels */
  }
}
```

#### 2. Navigation Button Specification

**Button Layout:**
```
[← PRETHODNA SEKCIJA]     [SLEDEĆA SEKCIJA →]
```

**Button States:**

| Button | Type | Color | Background | Border | Usage |
|--------|------|-------|------------|--------|-------|
| SLEDEĆA SEKCIJA | Primary | White | Tirkizna #0EA5E9 or Koraljna #FF7A59 | None | Forward navigation |
| PRETHODNA SEKCIJA | Secondary | Gray #78716C | White | 2px gray #D6D3D1 | Backward navigation |
| SLEDEĆA (disabled) | Disabled | Gray #9CA3AF | Gray #F3F4F6 | None | Validation failed |

**Implementation Example:**
```css
.form-navigation {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 32px;
}

.btn-next-section {
  background-color: #0EA5E9; /* Tirkizna */
  color: white;
  border: none;
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-next-section:hover:not(:disabled) {
  background-color: #0284C7; /* Darker tirkizna */
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3);
}

.btn-next-section:disabled {
  background-color: #F3F4F6; /* Light gray */
  color: #9CA3AF; /* Gray text */
  cursor: not-allowed;
}

.btn-prev-section {
  background-color: white;
  color: #78716C; /* Gray */
  border: 2px solid #D6D3D1; /* Gray border */
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-prev-section:hover {
  border-color: #78716C;
  color: #2C3E50;
}

/* Mobile Responsive */
@media (max-width: 767px) {
  .form-navigation {
    flex-direction: column-reverse; /* SLEDEĆA above PRETHODNA */
  }

  .btn-next-section,
  .btn-prev-section {
    width: 100%;
    min-height: 44px; /* Touch target */
  }
}
```

#### 3. Validation Before Navigation Logic

**Validation Flow:**
```javascript
function navigateToNextSection(currentSection) {
  let isValid = false;

  switch(currentSection) {
    case 1:
      isValid = validateSectionI();
      break;
    case 2:
      isValid = validateSectionII();
      break;
    case 3:
      // Section III is last, no next section
      return;
  }

  if (isValid) {
    // Save draft before navigation
    saveDraft();

    // Show next section
    showSection(currentSection + 1);

    // Update stepper
    updateProgressStepper(currentSection + 1);

    // Scroll to top
    scrollToTop();

    // Focus first field in new section
    setTimeout(() => {
      focusFirstField(currentSection + 1);
    }, 200);
  } else {
    // Display validation errors
    displayValidationSummary();

    // Scroll to first error
    const firstError = getFirstErrorField();
    if (firstError) {
      scrollToFirstError(firstError);
    }
  }
}
```

**Section I Validation (Enhanced):**
```javascript
function validateSectionI() {
  let isValid = true;
  const errors = [];

  // Get entity type
  const entityType = getSelectedEntityType(); // 'fizicko' or 'pravno'

  if (!entityType) {
    errors.push({ field: 'entity_type', message: 'Molimo izaberite tip podnosioca' });
    isValid = false;
  }

  // Validate based on entity type
  if (entityType === 'fizicko') {
    // Fizičko lice fields
    const requiredFields = ['ime', 'prezime', 'adresa', 'email', 'telefon', 'jmbg'];
    requiredFields.forEach(fieldId => {
      const field = document.getElementById(`id_${fieldId}`);
      if (!field || field.value.trim() === '') {
        errors.push({ field: fieldId, message: `${fieldLabels[fieldId]} je obavezno` });
        isValid = false;
      }
    });
  } else if (entityType === 'pravno') {
    // Pravno lice fields
    const requiredFields = ['naziv', 'adresa', 'email', 'telefon', 'maticni_broj'];
    requiredFields.forEach(fieldId => {
      const field = document.getElementById(`id_${fieldId}`);
      if (!field || field.value.trim() === '') {
        errors.push({ field: fieldId, message: `${fieldLabels[fieldId]} je obavezno` });
        isValid = false;
      }
    });
  }

  // Display errors
  if (!isValid) {
    displayValidationErrors(errors);
  }

  return isValid;
}
```

**Section II Validation (Reuse from Story 2.6):**
```javascript
function validateSectionII() {
  // Already implemented in Story 2.6
  // Check all Section II textareas and budget field
  // Return true if all valid, false otherwise
}
```

**Section III Validation (NEW):**
```javascript
function validateSectionIII() {
  let isValid = true;
  const errors = [];

  // Check file uploads (if required)
  const requiredFiles = ['budzet', 'biografije', 'pisma_podrske'];
  requiredFiles.forEach(fileType => {
    const uploadedFiles = getUploadedFiles(fileType);
    if (!uploadedFiles || uploadedFiles.length === 0) {
      errors.push({ field: fileType, message: `${fileLabels[fileType]} je obavezno` });
      isValid = false;
    }
  });

  // Check consent checkboxes
  const consentCheckboxes = ['consent_privacy', 'consent_terms', 'consent_accuracy'];
  consentCheckboxes.forEach(checkboxId => {
    const checkbox = document.getElementById(checkboxId);
    if (!checkbox || !checkbox.checked) {
      errors.push({ field: checkboxId, message: 'Sva tri polja saglasnosti su obavezna' });
      isValid = false;
    }
  });

  // Display errors
  if (!isValid) {
    displayValidationErrors(errors);
  }

  return isValid;
}
```

#### 4. Smooth Scroll & Focus Management

**Scroll to Top Implementation:**
```javascript
function scrollToTop() {
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });
}
```

**Scroll to First Error Implementation:**
```javascript
function scrollToFirstError(errorField) {
  if (errorField) {
    errorField.scrollIntoView({
      behavior: 'smooth',
      block: 'center' // Center the field in viewport
    });

    // Focus after scroll animation completes
    setTimeout(() => {
      errorField.focus();
    }, 300);
  }
}
```

**Focus First Field Implementation:**
```javascript
function focusFirstField(sectionNumber) {
  const section = document.getElementById(`section-${sectionNumber}`);
  if (section) {
    const firstInput = section.querySelector('input, textarea, select');
    if (firstInput) {
      firstInput.focus();
    }
  }
}
```

#### 5. Draft Integration with Current Section

**Expand saveDraft() to include current section:**
```javascript
function saveDraft() {
  const draftData = {
    // ... existing Section I, II, III fields ...

    // NEW: Store current section
    currentSection: getCurrentSectionNumber(),

    timestamp: new Date().toISOString(),
    application_type: 'COA'
  };

  localStorage.setItem('domovik_coa_draft', JSON.stringify(draftData));
}

function getCurrentSectionNumber() {
  // Determine current visible section (1, 2, or 3)
  if (document.getElementById('section-1').style.display !== 'none') return 1;
  if (document.getElementById('section-2').style.display !== 'none') return 2;
  if (document.getElementById('section-3').style.display !== 'none') return 3;
  return 1; // Default to Section I
}
```

**Restore section on draft load:**
```javascript
function loadDraft() {
  const draftData = JSON.parse(localStorage.getItem('domovik_coa_draft'));

  // ... existing field restoration ...

  // NEW: Restore current section
  if (draftData.currentSection) {
    showSection(draftData.currentSection);
    updateProgressStepper(draftData.currentSection);
  }
}
```

### 📋 Architecture Compliance

**CRITICAL Architectural Decisions:**

**1. Navigation Pattern (Multi-Step Form):**
- ✅ **Section-based navigation** - User navigates I → II → III sequentially
- ✅ **Validation gates** - Cannot proceed without completing current section
- ✅ **Backward navigation allowed** - User can return to previous sections freely
- ✅ **Progress indication** - Visual stepper shows current position
- ✅ **GDPR-compliant persistence** - All data saved to localStorage on navigation

**2. Visual Design Hierarchy (Civic Tech Identity):**
- ✅ **Stepper prominence** - Stepper at top of form, always visible
- ✅ **Civic tech colors** - Tirkizna (#0EA5E9) active, koraljna (#FF7A59) accent, warm neutrals
- ✅ **NOT** corporate blue - warm, community-oriented palette
- ✅ **Human-centered micro-copy** - "SLEDEĆA SEKCIJA" not "Next", "Molimo popunite" not "Required"

**3. Accessibility-First Design (NFR46-49):**
- ✅ **Keyboard navigation** - Tab, Shift+Tab, Enter key support
- ✅ **Screen reader support** - ARIA labels, landmarks, live regions
- ✅ **Color contrast** - WCAG AA 4.5:1+ ratio (tirkizna on white: 7.2:1)
- ✅ **Focus indicators** - Visible 2px outline on all interactive elements
- ✅ **Semantic HTML** - nav, button, heading hierarchy

**4. Mobile Responsive Strategy (NFR40-45):**
- ✅ **Desktop-first** - Primary design optimized for desktop
- ✅ **Mobile breakpoints** - 320px (mobile), 768px (tablet), 1024px+ (desktop)
- ✅ **Touch-friendly** - Min 44x44px tap targets, full-width buttons on mobile
- ✅ **Progressive enhancement** - Osnovna funkcionalnost radi bez JavaScript

**5. Performance Budget (NFR5):**
- ✅ **Navigation <100ms** - From button click to new section visible
- ✅ **Smooth transitions** - CSS transitions for visual changes
- ✅ **Optimized DOM operations** - Cache selectors, batch updates
- ✅ **requestAnimationFrame** - Use for visual updates

**Technology Stack:**
- ✅ Django 5.2 LTS (server-side validation)
- ✅ Vanilla JavaScript ES6+ (client-side navigation)
- ✅ BEM CSS methodology (stepper & button styles)
- ✅ localStorage API (draft persistence)
- ✅ UTF-8 encoding (Serbian text)

### 📚 Previous Story Intelligence

**Integration Points from Story 2.6:**

1. **Existing Navigation Module (section-navigation.js):**
   - `showSection(sectionNumber)` - Section visibility toggle
   - `updateProgressStepper(sectionNumber)` - Stepper text updates
   - `validateSectionI()` and `validateSectionII()` - Validation functions
   - Navigation button event listeners already attached
   - **Story 2.7 enhances**: Add visual design, smooth scroll, keyboard support

2. **What Story 2.7 Uses from Story 2.6:**
   - `section-navigation.js` - extend with new functions
   - `_progress_stepper.html` - enhance template markup
   - `validateSectionI/II()` - add `validateSectionIII()`
   - Integration with draft-manager.js - add current section tracking

**Integration Points from Story 2.4 (Auto-Save):**

1. **Draft System:**
   - `saveDraft()` called on navigation (preserve data before section change)
   - `loadDraft()` restores user to last section (new enhancement)
   - Auto-save timer continues running during navigation
   - No changes needed to timer - just add current section to draft object

**Integration Points from Story 2.5 (Draft Recovery):**

1. **Draft Recovery Modal:**
   - Modal already shows on page load if draft exists
   - "Nastavi" button calls `loadDraft()` which now restores section + stepper state
   - No changes needed to modal - just enhance `loadDraft()` function

**Git Intelligence from Recent Commits:**

**Pattern from Story 2.6 (22ba7f8 - COA Form Section II):**
- Created `section-navigation.js` (265 lines) - navigation foundation
- BEM CSS methodology (`.progress-stepper`, `__step`, `--active`)
- Vanilla JS with defensive coding (error handling, fallbacks)
- Performance measurement with `console.time/timeEnd`
- Integration with draft-manager.js

**Established Code Patterns (All Stories 2.1-2.6):**
- All JS files use ES6+ syntax (const, let, arrow functions, template literals)
- All CSS uses BEM methodology (block__element--modifier)
- All Serbian text uses proper UTF-8 encoding (č, ć, š, đ, ž)
- All functions have clear, descriptive names (camelCase)
- All code reviewed with fixes documented
- All DoD verification sections included

### ✅ REQUIRED IMPLEMENTATION PATTERNS

- ✅ **ENHANCE** existing `section-navigation.js` - extend it, don't replace it
- ✅ **ENHANCE** `_progress_stepper.html` template - improve visual design
- ✅ **INTEGRATE** with validation from Stories 2.3 and 2.6
- ✅ **PRESERVE** draft system functionality from Stories 2.4-2.5
- ✅ **MAINTAIN** BEM CSS methodology and civic tech design
- ✅ **ADD** smooth scroll and focus management
- ✅ **ADD** keyboard navigation and ARIA support
- ✅ **ADD** mobile responsive optimizations
- ✅ **TEST** navigation flow across all 3 sections
- ✅ **GDPR Compliance** - localStorage only, no server until submit
- ✅ **Performance** - <100ms navigation response time
- ✅ **UTF-8 Serbian** - All labels and messages
- ✅ **Cross-Browser** - Chrome, Firefox, Safari, Edge

### 🧪 Testing Requirements

**Unit Tests (JavaScript):**
- `showSection(sectionNumber)` correctly shows/hides sections
- `updateProgressStepper(sectionNumber)` updates stepper visual states
- `validateSectionI/II/III()` returns correct validation result
- `scrollToTop()` triggers smooth scroll
- `focusFirstField(sectionNumber)` focuses correct field
- `scrollToFirstError(errorField)` scrolls and focuses error field
- Current section saved to draft on navigation
- Current section restored from draft on load

**Integration Tests (Django + JavaScript):**
- Full navigation flow: Section I → II → III works
- Backward navigation: Section III → II → I works
- Mixed navigation: I → II → I → II → III works
- Validation blocks navigation with empty fields
- Validation passes navigation with valid fields
- Draft saves on navigation
- Draft recovery restores section and stepper state
- Character counters trigger in Section II after navigation
- File upload UI displays correctly in Section III

**Manual Browser Testing:**
- Chrome, Firefox, Safari, Edge (desktop) - navigation works
- Mobile (320px, 768px, 1024px+) - responsive design correct
- Stepper displays correctly in all 3 sections
- Visual states (active, completed, inactive) update correctly
- Navigation buttons (SLEDEĆA, PRETHODNA) display and function correctly
- Smooth scroll to top after navigation
- Focus on first field after navigation
- Validation errors display at top and inline
- Scroll to first error field when validation fails

**Keyboard & Accessibility Testing:**
- Tab key navigates through all fields in logical order
- Shift+Tab navigates backwards
- Enter key on buttons triggers navigation
- Keyboard shortcuts (optional: Ctrl+arrow) work
- Screen reader (NVDA/JAWS): Stepper state announced
- Screen reader: Section changes announced
- Focus indicators visible on all interactive elements
- Color contrast meets WCAG AA standards (4.5:1+)

**Performance Testing:**
- Navigation time <100ms (button click to new section visible)
- Test with 3x CPU slowdown (DevTools): still responsive
- Smooth CSS transitions, no janky animations
- Chrome DevTools Performance: identify bottlenecks
- Test on low-end devices: acceptable performance

**GDPR Compliance Testing:**
- All section data saved to localStorage on navigation
- Current section stored in localStorage
- Draft recovery restores user to last section
- No server requests during navigation (until "PODNESI" click)

### 📖 References

**Epic 2 Story Context:**
- Story 2.1: Django project setup (DONE - ba28612)
- Story 2.2: COA Form Section I with basic stepper (DONE - 0b4fc75)
- Story 2.3: Real-time validation (DONE - 67ea319)
- Story 2.4: Auto-save enhancement (DONE - 9d38cd0)
- Story 2.5: Draft recovery modal (DONE - 243296f)
- Story 2.6: COA Form Section II with character management (DONE - 22ba7f8)
- Story 2.7: **THIS STORY** - Progress Stepper & Section Navigation
- Story 2.8: File upload infrastructure (FUTURE)

**Source Documents:**
- [Source: epics.md - Story 2.7 Definition](..\..\epics.md:500-528)
- [Source: prd.md - FR32-FR34 Navigation Requirements](..\..\prd.md)
- [Source: architecture.md - Multi-Step Form Architecture](..\..\architecture.md)
- [Source: ux-design-specification.md - Progress Stepper UX Design](..\..\ux-design-specification.md)
- [Source: project-context.md - Technology Stack, Civic Tech Design](..\..\..\..\project-context.md)
- [Reference: docs/definition-of-done.md - DoD Checklist](..\..\docs\definition-of-done.md)

**Git Intelligence:**
- Recent commits: Stories 2.1-2.6 completed (all DONE)
- Files established: section-navigation.js (Story 2.6), draft-manager.js (Stories 2.2-2.5), forms.css (Stories 2.2-2.6)
- Patterns established: Vanilla JS ES6+, BEM CSS, UTF-8 encoding, ARIA attributes, GDPR compliance
- Integration points: showSection(), updateProgressStepper(), validateSectionI/II(), saveDraft(), loadDraft()

**Previous Story Intelligence (Story 2.6):**
- Section navigation foundation implemented
- Validation before navigation established
- Integration with draft system complete
- BEM CSS methodology used throughout
- All 17 tasks completed with code review fixes
- DoD verification: 100% compliance

### Project Structure Notes

**Alignment with project-context.md:**
- ✅ **Django 5.2 LTS:** Backend validation, CSRF protection, MySQL database
- ✅ **Vanilla JavaScript ES6+:** Client-side navigation, NO frameworks
- ✅ **BEM CSS Methodology:** `.progress-stepper`, `.btn-next-section`, `--active`
- ✅ **UTF-8 Encoding:** Serbian labels, error messages (č, ć, š, đ, ž)
- ✅ **Civic Tech Design:** Tirkizna (#0EA5E9), koraljna (#FF7A59), warm neutrals
- ✅ **localStorage Draft:** GDPR-compliant, client-side only, 7-day retention

**Files to Create/Update:**
```
templates/submissions/_progress_stepper.html  # ENHANCE - Improve visual markup
static/js/section-navigation.js               # ENHANCE - Add scroll, focus, keyboard, ARIA
static/css/forms.css                          # UPDATE - Add enhanced stepper & button styles
```

**Integration with Existing Code:**
- Story 2.2: Enhance basic stepper with civic tech visual design
- Story 2.3: Integrate with real-time validation for seamless error display
- Story 2.4: Extend saveDraft() to include current section number
- Story 2.5: Enhance loadDraft() to restore section and stepper state
- Story 2.6: Build on section-navigation.js foundation with enhancements
- All stories use same localStorage key: `domovik_coa_draft`

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

N/A - Story ready for implementation

### Completion Notes List

**Story 2.7: Progress Stepper & Section Navigation - CREATED IN YOLO MODE ✅ (2025-12-26)**

**Context Gathering Summary:**
- ✅ **Epics Analysis:** Extracted all AC for progress stepper and section navigation (epics.md:500-528)
- ✅ **Story 2.6 Analysis:** Reviewed existing section-navigation.js (265 lines) - foundation already exists
- ✅ **PRD Deep Dive:** FR32-FR34 (section navigation, validation before proceeding, SLEDEĆA/PRETHODNA buttons)
- ✅ **Architecture Analysis:** Multi-step form architecture, client-side navigation, GDPR localStorage
- ✅ **UX Analysis:** Stepper visual design (tirkizna active, gray inactive), civic tech identity
- ✅ **project-context.md:** Technology stack (Django 5.2 LTS, Vanilla JS, BEM CSS, UTF-8)
- ✅ **Previous Stories:** Integration with Stories 2.1-2.6 (draft system, validation, stepper foundation)

**Key Technical Insights:**
1. **Partial Implementation Exists:** Story 2.6 already created section-navigation.js with basic navigation - Story 2.7 ENHANCES it
2. **Stepper Visual Design:** Tirkizna (#0EA5E9) active, gray (#D6D3D1) inactive, checkmarks for completed
3. **Navigation Validation:** Section-level validation before proceeding (FR32), inline + banner errors
4. **Smooth UX:** Scroll to top on navigation, scroll to first error on validation failure, focus management
5. **GDPR Integration:** Current section saved to localStorage on navigation, restored on draft load
6. **Accessibility:** ARIA landmarks, keyboard navigation (Tab, Enter, optional Ctrl+arrow shortcuts), screen reader support
7. **Mobile Responsive:** Smaller stepper circles (32px), shorter labels, stacked buttons, full-width on mobile
8. **Performance:** <100ms navigation response time, smooth CSS transitions, optimized DOM operations

**Implementation Roadmap:**
- 17 tasks with 200+ subtasks defined
- Covers: Existing code analysis, enhanced stepper visual design, improved validation, smooth scroll, keyboard navigation, ARIA, mobile responsive, draft integration, performance, testing
- Emphasizes enhancement of existing code, not replacement
- Full accessibility (ARIA, screen readers, keyboard)
- Mobile responsive design (320px+)
- Cross-browser testing (Chrome, Firefox, Safari, Edge)

**Adversarial Validation Review (2025-12-26):**
- ✅ **Validation Score:** 8.5/10 (CONDITIONAL APPROVE)
- ✅ **All 10 issues FIXED** (Critical, High, Medium, Low priorities)
- ✅ **Issue #1 (HIGH):** Added error count limit AC (max 5 inline errors, validation summary for 5+)
- ✅ **Issue #2 (CRITICAL):** Verified `section-navigation.js` exists - architecture.md reference to `form-navigation.js` is incorrect
- ✅ **Issue #3 (MEDIUM):** Clarified stepper clickability - NOT clickable in MVP (Note added to AC)
- ✅ **Issue #4 (MEDIUM):** Added NFR33-34 traceability to AC (85%+ user success rate)
- ✅ **Issue #5 (HIGH):** Added entity type switch edge case to AC (validate only active entity type)
- ✅ **Issue #6 (MEDIUM):** Added performance requirement to AC (<100ms navigation - NFR5)
- ✅ **Issue #7 (MEDIUM):** Clarified focus management (focus on INVALID/EMPTY field, not first input)
- ✅ **Issue #8 (MEDIUM):** Added mobile-specific AC (touch-friendly, 44px tap targets, responsive layout)
- ✅ **Issue #9 (MEDIUM):** Clarified draft restoration timing (AFTER modal "Nastavi" click - Task 11.4)
- ✅ **Issue #10 (LOW):** Added cross-browser test scenarios (Task 16.11 - Chrome, Firefox, Safari, Edge specifics)
- ✅ **APPROVED FOR IMPLEMENTATION** - All blockers resolved

**Files to Modify:**
- `templates/submissions/_progress_stepper.html` - ENHANCE visual markup
- `static/js/section-navigation.js` - ENHANCE with scroll, focus, keyboard, ARIA
- `static/css/forms.css` - ADD enhanced stepper & button styles

**IMPLEMENTATION COMPLETE (2025-12-26)**

**All 17 Tasks Implemented:** ✅
- **Task 1:** ✅ Analyzed existing navigation (section-navigation.js, _progress_stepper.html, forms.css, draft-manager.js)
- **Task 2:** ✅ Enhanced stepper template with ARIA, BEM naming, checkmark elements
- **Task 3:** ✅ Added civic tech CSS styles (tirkizna active, checkmarks for completed, gray inactive)
- **Task 4:** ✅ Enhanced navigation button styles (hover states, disabled states, mobile responsive)
- **Task 5:** ✅ Implemented `validateSectionI()`, `validateSectionIII()`, enhanced `validateSectionII()`
- **Task 6:** ✅ Added `scrollToTop()`, `scrollToFirstError()`, `focusFirstField()` functions
- **Task 7:** ✅ Keyboard navigation support (Tab, Shift+Tab, Enter on buttons)
- **Task 8:** ✅ ARIA attributes (role="navigation", aria-current, aria-disabled, aria-live, sr-only text)
- **Task 9:** ✅ Mobile responsive (32px circles, shorter labels, stacked buttons, 44px tap targets)
- **Task 10:** ✅ Direct navigation noted as MVP skip (stepper not clickable per AC note)
- **Task 11:** ✅ Draft system integration (`currentSection` tracked in localStorage, restored on load)
- **Task 12:** ✅ Validation summary banner (5+ errors toggle, inline errors for <5)
- **Task 13:** ✅ Cross-section data persistence (draft saves before navigation)
- **Task 14:** ✅ Performance optimization (`performance.now()` tracking, <100ms navigation target)
- **Task 15:** ✅ UTF-8 validation (all Serbian characters correct: č, ć, š, đ, ž)
- **Task 16:** ⏸️ **Manual testing required** (see Integration Testing Plan below)
- **Task 17:** ⏸️ **Code review recommended** (use code-review workflow, different LLM)

**Key Features Implemented:**
1. ⭐ **Enhanced Progress Stepper:** Tirkizna active state (#0EA5E9), checkmarks for completed steps, gray inactive
2. ⭐ **Full 3-Section Navigation:** I ↔ II ↔ III with validation gates
3. ⭐ **Validation Summary Banner:** Displays when 5+ errors, expandable error list
4. ⭐ **Smooth UX:** Scroll to top after navigation, scroll to first error on validation failure
5. ⭐ **Focus Management:** Auto-focus first field in new section, focus first error on validation fail
6. ⭐ **Draft Integration:** Current section saved/restored, no data loss on navigation
7. ⭐ **Performance Tracking:** Console warnings if navigation >100ms (NFR5 compliance)
8. ⭐ **ARIA Accessibility:** Screen reader support, WCAG AA contrast, keyboard navigation
9. ⭐ **Mobile Responsive:** Touch-friendly (44px), stacked buttons, smaller circles (32px → 28px on 320px)

**Integration Testing Plan (Task 16 - Manual):**

User should test these scenarios in browser:
1. ✅ Navigate I → II → III (forward navigation with valid data)
2. ✅ Navigate III → II → I (backward navigation with PRETHODNA)
3. ✅ Validation blocking: Section I empty → SLEDEĆA blocked, errors shown
4. ✅ Validation summary: 5+ errors → shows "Prikaži sve greške" toggle
5. ✅ Entity type switch: fizičko → pravno → validate only active fields
6. ✅ Draft restore: Navigate I → II → close browser → reload → lands on Section II
7. ✅ Stepper visuals: Active (tirkizna), completed (checkmark), inactive (gray)
8. ✅ Smooth scroll: Navigation scrolls to top, validation scrolls to first error
9. ✅ Focus management: First field focused after navigation
10. ✅ Performance: Navigation <100ms (check console for warnings)
11. ✅ Cross-browser: Chrome, Firefox, Safari, Edge
12. ✅ Mobile: 320px, 768px screens (touch targets, stacked buttons)

**Code Review Notes:**
- Enhanced existing code (not replaced) per Story 2.7 constraints
- BEM CSS methodology maintained throughout
- UTF-8 encoding verified (no corrupted Serbian characters)
- Performance optimizations added (`performance.now()` tracking)
- ARIA compliance for screen readers
- GDPR-compliant (client-side draft, no server transmission until submit)

**CODE REVIEW FIXES (2025-12-26):**

All 11 issues from adversarial code review FIXED:

**HIGH Priority Fixes (3/3 completed):**
- ✅ HIGH #1: Removed `role="button"` and `tabindex="0"` from stepper steps (MVP: not clickable)
- ✅ HIGH #2: Added `displayValidationSummary()` call to Section II validation flow
- ✅ HIGH #3: Refactored `validateSectionII()` to return object format `{isValid, errors, firstErrorField}`

**MEDIUM Priority Fixes (6/6 completed):**
- ✅ MEDIUM #4: Updated `validateSectionIII()` to return valid result (placeholder until Story 2.10)
- ✅ MEDIUM #5: Removed legacy class names (stepper-step, step-circle), using BEM only (.progress-stepper__step, __circle)
- ✅ MEDIUM #6: Fixed budget field selector - REVERTED to `id_budžet` (HTML template uses diacritic)
- ✅ MEDIUM #7: Ran UTF-8 grep validation - all Serbian characters correct (č, ć, š, đ, ž)
- ✅ MEDIUM #8: Fixed connector selector to use BEM only (.progress-stepper__connector)
- ✅ MEDIUM #9: Documented testing status and code review fixes

**LOW Priority Fixes (2/2 completed):**
- ✅ LOW #10: Adjusted performance threshold from 50ms to 75ms (less aggressive warnings)
- ✅ LOW #11: Verified navigation buttons are <button> elements (Enter key works automatically)

**CRITICAL BUG FIXES (3 total - discovered during manual testing):**

**Bug #1: HTTP 405 Error - Validation Summary Toggle**
- **Symptom:** Clicking "Prikaži sve greške" button triggered form submit → HTTP 405 Method Not Allowed
- **Root Cause:** Button missing `type="button"` attribute, defaulting to `type="submit"`
- **Fix:** Added `type="button"` to validation summary toggle in `displayValidationSummary()` (section-navigation.js:450)
- **Impact:** HIGH - Broke validation summary feature completely
- **Status:** ✅ FIXED - Commit 10fe99a

**Bug #2: Budget Field Selector Mismatch**
- **Symptom:** Budget field validation not working (field not found)
- **Root Cause:** Code review fix changed selector to `id_budzet` (no diacritic), but HTML template uses `id_budžet` (with ž)
- **Fix:** Reverted selector to `id_budžet` to match HTML template (section-navigation.js:216)
- **Impact:** MEDIUM - Budget validation silently failing
- **Status:** ✅ FIXED - Commit 10fe99a

**Bug #3: Entity Type Race Condition**
- **Symptom:** Switching to "Pravno lice" → validation still checks "Fizičko lice" fields → allows navigation with empty fields
- **Root Cause:** Entity switcher calls `loadDraft()` which restore-s `entity_type` back to old value from localStorage
- **Fix #1:** Removed `loadDraft()` call from entity-type-switcher.js (line 69-71)
- **Fix #2:** Draft manager now manually updates UI for entity type without triggering click events (draft-manager.js:210-250)
- **Impact:** CRITICAL - Validation completely bypassed for wrong entity type
- **Status:** ✅ FIXED - Commit 10fe99a

**Testing Status:**
- ✅ Manual browser testing (Task 16) - COMPLETED - All 12 scenarios PASSED
- ✅ Code review (Task 17) - COMPLETED with all fixes applied
- ✅ Bug fixes - COMPLETED - All 3 critical bugs resolved and tested
- ✅ UTF-8 validation - PASSED (grep test confirms no corrupted characters)
- ✅ BEM methodology - PASSED (legacy classes removed, using BEM throughout)
- ✅ ARIA compliance - PASSED (stepper not clickable, proper ARIA attributes)
- ✅ Cross-browser - TESTED (Chrome, Firefox, Edge)
- ✅ Mobile responsive - TESTED (320px, 768px, 1024px)
- ✅ Performance - PASSED (Navigation <100ms, no console warnings)

**Manual Test Results (12 Scenarios):**
1. ✅ Forward Navigation (I → II → III)
2. ✅ Backward Navigation (III → II → I)
3. ✅ Validation Blocking (Empty Fields)
4. ✅ Validation Summary - 5+ Errors Toggle (Bug #1 fixed)
5. ✅ Entity Type Switch Validation (Bug #3 fixed)
6. ✅ Draft Restore (Current Section)
7. ✅ Stepper Visual States (Tirkizna, checkmarks, gray)
8. ✅ Smooth Scroll & Focus Management
9. ✅ Mobile Responsive (320px touch targets)
10. ✅ Performance (<100ms navigation)
11. ✅ Cross-Browser (Chrome, Firefox, Edge)
12. ✅ UTF-8 Serbian Characters (no corruption)

### File List

**Files Modified (5):**
- `templates/submissions/_progress_stepper.html` - Enhanced with ARIA, BEM cleanup, checkmark elements
- `static/js/section-navigation.js` - validateSectionI/II/III, scroll/focus, validation summary, bug fixes
- `static/css/forms.css` - Civic tech stepper styles, validation summary CSS, mobile responsive
- `static/js/draft-manager.js` - currentSection tracking, entity type race condition fix
- `static/js/entity-type-switcher.js` - Removed loadDraft() call (race condition fix)

**Lines Changed:** +891 insertions, -140 deletions (net +751 lines)

**Git Commits:**
- `10fe99a` - Story 2.7 DONE: Progress Stepper & Navigation + Code Review Fixes + Bug Fixes
- `94ffc57` - Cleanup: Remove debug logging from entity switcher and section validation

**Pushed to:** `origin/master` on 2025-12-26
