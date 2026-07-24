/**
 * Draft Manager - Auto-Save Draft Preservation System
 * Story 2.2: Basic draft save/load for entity type switching
 * Story 2.4: Auto-save every 30s, beforeunload handler, visual notifications
 * Story 2.15: Server-side draft tracking for GDPR 7-day auto-deletion
 * Story 3.1: Application-agnostic support for COA and COB forms
 *
 * Features:
 * - Auto-save every 30 seconds (debounced from last input)
 * - Immediate save on browser close/navigate (beforeunload)
 * - Visual "Sačuvano" notification with queueing
 * - 7-day retention with automatic deletion
 * - GDPR-compliant (metadata-only server tracking, form data client-side only)
 * - QuotaExceededError handling with graceful degradation
 * - Performance measurement (development mode only)
 * - Server-side draft expiration sync
 * - Application type detection (COA/COB) from data attribute
 */

// Story 3.1: Dynamic draft key based on application type
const getApplicationType = () => document.body.dataset.applicationType || 'COA';
const getDraftKey = () => `domovik_${getApplicationType().toLowerCase()}_draft`;
const DRAFT_KEY = getDraftKey();

// Global auto-save timer reference (Story 2.4 - Task 1.1)
// Explicitly on window object for access from entity-type-switcher.js (Task 4.4)
window.autoSaveTimeout = null;

// Global indicator timeout for visual feedback queueing (Story 2.4 - Task 2.7)
let indicatorTimeout;

// Guard flag to prevent duplicate event listener registration (Code Review Fix MEDIUM #6)
let autoSaveInitialized = false;

// Draft ID for server-side tracking (Story 2.15)
let draftId = null;

/**
 * Generate UUID v4 for draft tracking (Story 2.15)
 * @returns {string} UUID v4 string
 */
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Get or create draft ID from localStorage (Story 2.15)
 * Story 3.1: Updated to use dynamic draft key
 * @returns {string} Draft UUID
 */
function getOrCreateDraftId() {
  try {
    const draftJson = localStorage.getItem(getDraftKey());
    if (draftJson) {
      const draftData = JSON.parse(draftJson);
      if (draftData.draft_id) {
        return draftData.draft_id;
      }
    }
  } catch (error) {
    console.error('Failed to parse draft JSON for draft_id:', error);
  }

  // Generate new UUID
  return generateUUID();
}

/**
 * Get CSRF token from DOM meta tag or cookie (Story 2.15, Bugfix: CSRF_COOKIE_HTTPONLY=True)
 *
 * CRITICAL BUGFIX (Story 4-5 aftermath):
 * - CSRF_COOKIE_HTTPONLY was changed to True for security (prevents XSS attacks)
 * - This blocks JavaScript from reading document.cookie
 * - Solution: Read CSRF token from DOM meta tag FIRST (Django best practice)
 * - Fallback to cookie for backwards compatibility (if HTTPONLY is disabled)
 *
 * Implementation:
 * 1. Try to read from <meta name="csrf-token" content="{{ csrf_token }}"> in template
 * 2. Fallback to document.cookie if meta tag not found (backwards compatibility)
 * 3. Return null if both methods fail (will trigger CSRF 403 error)
 *
 * @returns {string|null} CSRF token or null if not found
 */
function getCSRFToken() {
  // FIRST: Try to read from DOM meta tag (CSRF_COOKIE_HTTPONLY=True compatible)
  const metaTag = document.querySelector('meta[name="csrf-token"]');
  if (metaTag && metaTag.content) {
    return metaTag.content;
  }

  // FALLBACK: Try to read from cookie (for backwards compatibility)
  const name = 'csrftoken';
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }

  // FINAL: Log warning if both methods failed
  if (!cookieValue) {
    console.warn('CSRF token not found in DOM meta tag or cookie. Ensure <meta name="csrf-token"> exists in template.');
  }

  return cookieValue;
}

/**
 * Register draft metadata on server for GDPR tracking (Story 2.15)
 * Non-blocking: Draft still saved to localStorage even if server registration fails
 */
async function registerDraftOnServer() {
  if (!draftId) {
    console.warn('No draft ID - skipping server registration');
    return;
  }

  try {
    // ISSUE 5 FIX: Add 5-second timeout to prevent blocking on slow server
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    // ISSUE 9 FIX: Read application type from data attribute instead of hardcoding
    const applicationType = document.body.dataset.applicationType || 'COA';

    const response = await fetch('/api/drafts/register/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken()
      },
      body: JSON.stringify({
        draft_id: draftId,
        application_type: applicationType
      }),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      console.warn('Draft registration failed (non-critical):', await response.text());
    } else {
      const data = await response.json();
      console.log('Draft registered on server:', data.message);
    }

  } catch (error) {
    // Non-blocking - draft still saved in localStorage
    if (error.name === 'AbortError') {
      console.warn('Server registration timeout (5s) - draft saved locally only');
    } else {
      console.warn('Server registration failed (offline or error):', error);
    }
  }
}

/**
 * Check if draft has expired server-side (Story 2.15)
 * Called on page load to sync localStorage with server
 * @returns {Promise<boolean>} True if expired, false otherwise
 */
async function checkDraftExpiration() {
  if (!draftId) {
    return false; // No draft ID to check
  }

  try {
    const response = await fetch(`/api/drafts/check/${draftId}/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCSRFToken()
      }
    });

    // ISSUE 10 FIX: Handle CSRF token errors by deleting stale draft
    if (response.status === 403) {
      console.warn('CSRF token invalid - deleting stale draft from localStorage');
      localStorage.removeItem(getDraftKey());
      return true; // Treat as expired
    }

    if (!response.ok) {
      console.warn('Draft expiration check failed');
      return false;
    }

    const data = await response.json();

    // BUGFIX: Only delete draft if it EXISTS on server AND is expired
    // If server doesn't have the draft (!data.exists), keep localStorage draft
    // This handles cases where registerDraftOnServer() failed (network, timeout, etc)
    if (data.exists && data.expired) {
      console.log('Draft expired on server. Deleting from localStorage.');
      localStorage.removeItem(getDraftKey());
      return true; // Expired
    }

    // If draft doesn't exist on server, log warning but keep localStorage draft
    if (!data.exists) {
      console.warn('Draft not registered on server - keeping localStorage draft for recovery');
    }

    return false; // Still valid (or not on server, but valid in localStorage)

  } catch (error) {
    console.error('Draft expiration check error:', error);
    return false; // Assume valid if server unreachable
  }
}

/**
 * Collect all form data for saving (Story 2.4 - Task 3, Story 2.7 - Task 11)
 * Story 3.1: Updated to handle both COA and COB forms dynamically
 * @returns {Object} Draft data object with application_type, timestamp, and all fields
 */
function collectFormData() {
  // Get current section from section-navigation.js if available
  let currentSectionNumber = 1;
  if (typeof currentSection !== 'undefined') {
    currentSectionNumber = currentSection;
  }

  const appType = getApplicationType();

  // Common data for both COA and COB
  const baseData = {
    draft_id: draftId,  // Story 2.15: UUID for server-side tracking
    application_type: appType,  // Story 3.1: Dynamic COA/COB detection
    timestamp: new Date().toISOString(),
    currentSection: currentSectionNumber,  // Story 2.7: Track current section for restoration
    entity_type: document.getElementById('id_entity_type')?.value || 'fizicko',
    fizicko: {
      ime: document.getElementById('id_ime')?.value || '',
      prezime: document.getElementById('id_prezime')?.value || ''
      // Z3 (2026-07-24): Broj lične karte / ID broj no longer collected.
    },
    pravno: {
      naziv_organizacije: document.getElementById('id_naziv_organizacije')?.value || '',
      // COA uses id_maticni_broj, COB uses id_registracioni_broj (Story 5.1)
      maticni_broj: document.getElementById('id_maticni_broj')?.value || '',
      registracioni_broj: document.getElementById('id_registracioni_broj')?.value || ''
    },
    // Story 5.1: Team members data (both COA and COB)
    team_members: (typeof TeamMembersManager !== 'undefined' && TeamMembersManager.getTeamMembersData)
      ? TeamMembersManager.getTeamMembersData()
      : [],
    common: {
      adresa: document.getElementById('id_adresa')?.value || '',
      email: document.getElementById('id_email')?.value || '',
      telefon: document.getElementById('id_telefon')?.value || ''
    },
    // Story 2.10 Task 7: Consent checkboxes state (GDPR-compliant - client-side only)
    consent_checkboxes: collectConsentStates(),
    // Story 2.8 Task 12: File upload metadata integration (GDPR-compliant)
    uploadedFiles: collectUploadedFileMetadata()
  };

  // Section II: Different fields for COA vs COB
  if (appType === 'COA') {
    // COA: Project Data (Story 2.6, Story 5.2: Added date fields)
    baseData.sectionII = {
      naslov: document.getElementById('id_naslov')?.value || '',
      opis: document.getElementById('id_opis')?.value || '',
      problem: document.getElementById('id_problem')?.value || '',
      cilj: document.getElementById('id_cilj')?.value || '',
      specifični_ciljevi: document.getElementById('id_specifični_ciljevi')?.value || '',
      ciljne_grupe: document.getElementById('id_ciljne_grupe')?.value || '',
      aktivnosti: document.getElementById('id_aktivnosti')?.value || '',
      rezultati: document.getElementById('id_rezultati')?.value || '',
      // Story 5.2: Project timeline dates
      datum_startovanja: document.getElementById('id_datum_startovanja')?.value || '',
      datum_zavrsetka: document.getElementById('id_datum_zavrsetka')?.value || '',
      budžet: document.getElementById('id_budžet')?.value || ''
    };
  } else if (appType === 'COB') {
    // COB: Initiative Data (Story 3.1, Story 5.3: Added naziv_tima, dates, budget)
    baseData.sectionII = {
      // Story 5.3: Team name - FIRST field
      naziv_tima: document.getElementById('id_naziv_tima')?.value || '',
      naslov: document.getElementById('id_naslov')?.value || '',
      kratak_opis: document.getElementById('id_kratak_opis')?.value || '',
      problem: document.getElementById('id_problem')?.value || '',
      cilj: document.getElementById('id_cilj')?.value || '',
      // Story 5.3: Renamed from "planirani_koraci" to "planirane_aktivnosti" in UI
      planirani_koraci: document.getElementById('id_planirani_koraci')?.value || '',
      ocekivani_uticaj: document.getElementById('id_ocekivani_uticaj')?.value || '',
      // Story 5.3: Project timeline dates
      datum_startovanja: document.getElementById('id_datum_startovanja')?.value || '',
      datum_zavrsetka: document.getElementById('id_datum_zavrsetka')?.value || '',
      // Story 5.3: Total budget in EUR
      totalni_budzet: document.getElementById('id_totalni_budzet')?.value || ''
    };
  }

  return baseData;
}

/**
 * Collect consent checkbox states for draft (Story 2.10 - Task 7.2-7.3)
 * GDPR Compliance: Client-side only, saved to localStorage
 *
 * @returns {Object} { privacy: boolean, terms: boolean, accuracy: boolean }
 */
function collectConsentStates() {
  // Check if ConsentManager exists and has getConsentStates method
  if (window.consentManager && typeof window.consentManager.getConsentStates === 'function') {
    return window.consentManager.getConsentStates();
  }

  // Fallback: Directly check checkbox states
  return {
    privacy: document.getElementById('consent-privacy')?.checked || false,
    terms: document.getElementById('consent-terms')?.checked || false,
    accuracy: document.getElementById('consent-accuracy')?.checked || false
  };
}

/**
 * Collect uploaded file metadata for draft (Story 2.8 - Task 12.2)
 * GDPR Compliance: Only stores METADATA, not actual file content
 *
 * Returns array of file metadata objects:
 * @returns {Array} [{file_id, original_filename, file_size, file_type, category}, ...]
 */
function collectUploadedFileMetadata() {
  // Check if uploadedFilesRegistry exists (defined in file-upload.js - Story 2.9)
  if (typeof window.uploadedFilesRegistry !== 'undefined' && Array.isArray(window.uploadedFilesRegistry)) {
    return window.uploadedFilesRegistry.map(file => ({
      file_id: file.file_id,
      original_filename: file.filename,
      file_size: file.size,
      file_type: file.file_type || file.filename.split('.').pop().toLowerCase(),
      category: file.category
    }));
  }

  // Fallback: No files uploaded yet
  return [];
}

/**
 * Save all form field values to localStorage
 * Story 2.2: Basic save functionality
 * Story 2.4: Added performance measurement, visual indicators, error handling
 * Story 2.15: Added server-side draft registration for GDPR tracking
 * Called by: entity-type-switcher.js, auto-save timer, beforeunload handler
 *
 * GDPR COMPLIANCE (NFR16-18):
 * - Form data stored ONLY in client-side localStorage (no server transmission)
 * - Only METADATA (draft_id, application_type) sent to server
 * - 7-day retention enforced by server-side periodic task
 * - User data remains on user's device until explicit form submission
 * - Admin panel NEVER sees draft data (only submitted applications)
 */
function saveDraft() {
  // Story 3.1: Dynamic form ID based on application type
  const formId = getApplicationType() === 'COA' ? 'coa-form-section-i' : 'cob-form';
  const form = document.getElementById(formId);
  if (!form) {
    console.warn('Draft Manager: Forma nije pronađena');
    return;
  }

  // CODE REVIEW FIX (MEDIUM #4): Check localStorage availability before every save
  if (!isLocalStorageAvailable()) {
    console.warn('localStorage nije dostupan - preskačem čuvanje');
    return;
  }

  // Performance measurement (development only - Task 1.6)
  const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  if (isDevelopment) {
    console.time('saveDraft');
  }

  const draftData = collectFormData();
  let saveError = null;

  try {
    // Show saving indicator (Task 2.2)
    showSavingIndicator();

    // Story 3.1: Use dynamic draft key
    localStorage.setItem(getDraftKey(), JSON.stringify(draftData));

    // Performance measurement end
    if (isDevelopment) {
      console.timeEnd('saveDraft');
    }

    // Story 2.15: Register draft metadata on server (non-blocking)
    registerDraftOnServer().catch(err => {
      // Silent fail - localStorage save already succeeded
      console.warn('Background server registration failed:', err);
    });

  } catch (error) {
    saveError = error;
    // QuotaExceededError specific handling (Task 5.4)
    if (error.name === 'QuotaExceededError') {
      showPersistentWarning('Auto-save je pun. Kliknite PODNESI što pre.');
      disableAutoSave();
    } else {
      console.error('Greška prilikom čuvanja draft-a:', error);
    }
  } finally {
    // CODE REVIEW FIX (MEDIUM #5): Always show correct indicator even if error occurred
    if (!saveError) {
      showSavedIndicator();
    }
  }
}

/**
 * Check if draft exists and is valid (Story 2.5 - Task 1.1)
 * REFACTORED from loadDraft() to support modal display on page load
 * @returns {Object} {exists: boolean, expired: boolean, data: object|null}
 */
function checkDraftExists() {
  try {
    // Story 3.1: Use dynamic draft key
    const draftJson = localStorage.getItem(getDraftKey());
    if (!draftJson) {
      return { exists: false, expired: false, data: null };
    }

    const draftData = JSON.parse(draftJson);

    // Check if draft is expired (>7 days old) using extracted helper
    if (isExpiredDraft(draftData)) {
      // Auto-delete expired draft (GDPR - NFR18)
      localStorage.removeItem(getDraftKey());
      console.log('Draft expired (>7 days), auto-deleted');
      return { exists: false, expired: true, data: null };
    }

    // Valid draft exists
    return { exists: true, expired: false, data: draftData };
  } catch (error) {
    // Corrupt JSON handling - cleanup and return false
    console.error('Corrupt draft data detected, cleaning up:', error);
    localStorage.removeItem(getDraftKey());
    return { exists: false, expired: false, data: null };
  }
}

/**
 * Check if draft data is expired (>7 days old) (Story 2.5 - Task 1.2)
 * EXTRACTED from loadDraft() 7-day retention logic (lines 131-140)
 * @param {Object} draftData - Draft data object with timestamp
 * @returns {boolean} True if draft is >7 days old, false otherwise
 */
function isExpiredDraft(draftData) {
  if (!draftData || !draftData.timestamp) {
    return false; // No timestamp = not expired (will be handled as invalid)
  }

  const draftAge = Date.now() - new Date(draftData.timestamp).getTime();
  const MAX_AGE = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds

  return draftAge > MAX_AGE;
}

/**
 * Load form field values from localStorage (Story 2.5 - Task 1.3)
 * REFACTORED to use checkDraftExists() instead of inline checking
 * Called after showing fields during entity type switch
 */
function loadDraft() {
  try {
    // Use extracted checkDraftExists() function (Task 1.3)
    const draftCheck = checkDraftExists();

    if (!draftCheck.exists) {
      // No valid draft found
      return;
    }

    const draftData = draftCheck.data;

    // Restore entity type
    // CODE REVIEW FIX: Restore entity_type for Draft Recovery (cold start)
    // This is safe because entity-type-switcher.js NO LONGER calls loadDraft()
    const entityTypeInput = document.getElementById('id_entity_type');
    if (entityTypeInput && draftData.entity_type) {
      entityTypeInput.value = draftData.entity_type;

      // Manually update UI without triggering click event (avoids saveDraft() loop)
      const fizickoFields = document.getElementById('fizicko-fields');
      const pravnoFields = document.getElementById('pravno-fields');

      if (draftData.entity_type === 'fizicko') {
        if (fizickoFields) {
          fizickoFields.classList.add('active');
          // Enable required attributes for fizicko fields
          fizickoFields.querySelectorAll('input, textarea').forEach(input => {
            if (input.closest('.team-members-section')) return;
            input.setAttribute('required', 'required');
          });
        }
        if (pravnoFields) {
          pravnoFields.classList.remove('active');
          // Disable required attributes for pravno fields
          pravnoFields.querySelectorAll('input, textarea').forEach(input => {
            input.removeAttribute('required');
          });
        }
      } else if (draftData.entity_type === 'pravno') {
        if (pravnoFields) {
          pravnoFields.classList.add('active');
          // Enable required attributes for pravno fields
          pravnoFields.querySelectorAll('input, textarea').forEach(input => {
            if (input.closest('.team-members-section')) return;
            input.setAttribute('required', 'required');
          });
        }
        if (fizickoFields) {
          fizickoFields.classList.remove('active');
          // Disable required attributes for fizicko fields
          fizickoFields.querySelectorAll('input, textarea').forEach(input => {
            input.removeAttribute('required');
          });
        }
      }

      // Update button states
      document.querySelectorAll('.switcher-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.entity === draftData.entity_type);
      });
    }

    // Restore fizičko lice fields
    if (draftData.fizicko) {
      restoreFieldValue('id_ime', draftData.fizicko.ime);
      restoreFieldValue('id_prezime', draftData.fizicko.prezime);
      // Z3 (2026-07-24): Broj lične karte / ID broj no longer collected/restored.
    }

    // Restore pravno lice fields
    if (draftData.pravno) {
      restoreFieldValue('id_naziv_organizacije', draftData.pravno.naziv_organizacije);
      restoreFieldValue('id_maticni_broj', draftData.pravno.maticni_broj);
      // Story 5.1: COB uses id_registracioni_broj
      restoreFieldValue('id_registracioni_broj', draftData.pravno.registracioni_broj);
    }

    // Story 5.1: Restore team members data
    if (draftData.team_members && draftData.team_members.length > 0) {
      if (typeof TeamMembersManager !== 'undefined' && TeamMembersManager.loadFromData) {
        TeamMembersManager.loadFromData(draftData.team_members);
      }
    }

    // Restore common fields
    if (draftData.common) {
      restoreFieldValue('id_adresa', draftData.common.adresa);
      restoreFieldValue('id_email', draftData.common.email);
      restoreFieldValue('id_telefon', draftData.common.telefon);
    }

    // Restore Section II fields (Story 2.6 - Task 6.3, Story 3.1 - COB support)
    if (draftData.sectionII) {
      const appType = getApplicationType();

      if (appType === 'COA') {
        // COA: Project Data
        restoreFieldValue('id_naslov', draftData.sectionII.naslov);
        restoreFieldValue('id_opis', draftData.sectionII.opis);
        restoreFieldValue('id_problem', draftData.sectionII.problem);
        restoreFieldValue('id_cilj', draftData.sectionII.cilj);
        restoreFieldValue('id_specifični_ciljevi', draftData.sectionII.specifični_ciljevi);
        restoreFieldValue('id_ciljne_grupe', draftData.sectionII.ciljne_grupe);
        restoreFieldValue('id_aktivnosti', draftData.sectionII.aktivnosti);
        restoreFieldValue('id_rezultati', draftData.sectionII.rezultati);
        // Story 5.2: Restore project timeline dates
        restoreFieldValue('id_datum_startovanja', draftData.sectionII.datum_startovanja);
        restoreFieldValue('id_datum_zavrsetka', draftData.sectionII.datum_zavrsetka);
        restoreFieldValue('id_budžet', draftData.sectionII.budžet);

        // Story 5.2: Trigger duration calculator update after restoring dates
        if (window.DurationCalculator && typeof window.DurationCalculator.update === 'function') {
          window.DurationCalculator.update();
        }
      } else if (appType === 'COB') {
        // COB: Initiative Data (Story 3.1, Story 5.3: Added naziv_tima, dates, budget)
        // Story 5.3: Team name - FIRST field
        restoreFieldValue('id_naziv_tima', draftData.sectionII.naziv_tima);
        restoreFieldValue('id_naslov', draftData.sectionII.naslov);
        restoreFieldValue('id_kratak_opis', draftData.sectionII.kratak_opis);
        restoreFieldValue('id_problem', draftData.sectionII.problem);
        restoreFieldValue('id_cilj', draftData.sectionII.cilj);
        restoreFieldValue('id_planirani_koraci', draftData.sectionII.planirani_koraci);
        restoreFieldValue('id_ocekivani_uticaj', draftData.sectionII.ocekivani_uticaj);
        // Story 5.3: Restore project timeline dates
        restoreFieldValue('id_datum_startovanja', draftData.sectionII.datum_startovanja);
        restoreFieldValue('id_datum_zavrsetka', draftData.sectionII.datum_zavrsetka);
        // Story 5.3: Restore total budget
        restoreFieldValue('id_totalni_budzet', draftData.sectionII.totalni_budzet);

        // Story 5.3: Trigger duration calculator update after restoring dates
        if (window.DurationCalculator && typeof window.DurationCalculator.update === 'function') {
          window.DurationCalculator.update();
        }
      }

      // Trigger character counter updates for Section II (Task 6.4)
      triggerCharacterCountersAfterDraftLoad();
    }

    // Restore current section (Story 2.7 - Task 11.4-11.5)
    if (draftData.currentSection && typeof showSection === 'function') {
      // Show the section user was on when they left
      showSection(draftData.currentSection);
    }

    // Story 2.8 Task 12.5-12.6: Display file metadata reminder
    if (draftData.uploadedFiles && draftData.uploadedFiles.length > 0) {
      console.log('Draft contains', draftData.uploadedFiles.length, 'uploaded file(s), displaying reminder...');
      displayFileMetadataReminder(draftData.uploadedFiles);
    } else {
      console.log('No uploaded files in draft, skipping reminder');
    }

    // Story 2.10 Task 7.5-7.7: Restore consent checkbox states
    if (draftData.consent_checkboxes) {
      loadConsentStatesFromDraft(draftData.consent_checkboxes);
    }

    // Development logging (comment out for production)
    // console.log('Draft loaded from localStorage');

    // Trigger validation for all restored fields (Story 2.3)
    triggerValidationAfterDraftLoad();
  } catch (error) {
    console.error('Failed to load draft:', error);
  }
}

/**
 * Load consent checkbox states from draft (Story 2.10 - Task 7.5-7.7)
 * Restores checkbox states and updates submit button accordingly
 *
 * @param {Object} consentStates - { privacy: boolean, terms: boolean, accuracy: boolean }
 */
function loadConsentStatesFromDraft(consentStates) {
  try {
    // Use ConsentManager if available
    if (window.consentManager && typeof window.consentManager.setConsentStates === 'function') {
      window.consentManager.setConsentStates(consentStates);
    } else {
      // Fallback: Directly set checkbox states (Story 2.10 Code Review Fix #8)
      const privacyCheckbox = document.getElementById('consent-privacy');
      const termsCheckbox = document.getElementById('consent-terms');
      const accuracyCheckbox = document.getElementById('consent-accuracy');

      if (privacyCheckbox && consentStates.privacy !== undefined) {
        privacyCheckbox.checked = consentStates.privacy;
      }
      if (termsCheckbox && consentStates.terms !== undefined) {
        termsCheckbox.checked = consentStates.terms;
      }
      if (accuracyCheckbox && consentStates.accuracy !== undefined) {
        accuracyCheckbox.checked = consentStates.accuracy;
      }
    }
  } catch (error) {
    console.error('Failed to load consent states from draft:', error);
  }
}

/**
 * Save consent checkbox states to draft (Story 2.10 - Task 7.3-7.4)
 * Called from ConsentManager when checkbox state changes
 * Triggers auto-save debounce timer
 */
function saveConsentStatesToDraft() {
  // Trigger standard draft save which includes consent states via collectConsentStates()
  saveDraft();
}

/**
 * Clear consent states from draft (Story 2.10 - Task 7.8)
 * Story 3.1: Updated to use dynamic draft key
 * Called on successful submission to cleanup
 */
function clearConsentStatesFromDraft() {
  const draft = JSON.parse(localStorage.getItem(getDraftKey()) || '{}');

  if (draft && draft.consent_checkboxes) {
    delete draft.consent_checkboxes;
    localStorage.setItem(getDraftKey(), JSON.stringify(draft));
    console.log('Consent states cleared from draft');
  }
}

/**
 * Display file metadata reminder to user (Story 2.8 - Task 12.5-12.6)
 * GDPR Compliance: Actual files NOT saved, only metadata
 *
 * Shows user which files they had uploaded before, but requires re-upload
 * @param {Array} filesMetadata - Array of file metadata objects
 */
function displayFileMetadataReminder(filesMetadata) {
  console.log('[DEBUG] displayFileMetadataReminder called with', filesMetadata.length, 'files');

  // Find the pre-existing draft reminder element in HTML
  const reminderElement = document.getElementById('file-draft-reminder');

  if (!reminderElement) {
    // Reminder element not found - skip
    console.warn('[BUG] file-draft-reminder element not found in HTML');
    return;
  }

  console.log('[DEBUG] file-draft-reminder element found, populating with metadata...');

  // Create file list HTML
  const fileListHTML = filesMetadata.map(file => {
    const categoryDisplay = {
      'BUDGET': 'Budžet',
      'BIOGRAPHY': 'Biografija',
      'SUPPORT_LETTER': 'Pismo podrške'
    }[file.category] || file.category;

    return `<li><strong>${file.original_filename}</strong> (${formatFileSize(file.file_size)}) - ${categoryDisplay}</li>`;
  }).join('');

  // Update reminder content with file metadata list
  reminderElement.innerHTML = `
    <span class="draft-reminder__icon" aria-hidden="true">⚠️</span>
    <div class="draft-reminder__content">
      <p class="draft-reminder__text"><strong>Prethodno upload-ovani fajlovi:</strong></p>
      <ul class="draft-reminder__list">
        ${fileListHTML}
      </ul>
      <p class="draft-reminder__note">Fajlovi nisu sačuvani u draft-u (GDPR zaštita). Molimo upload-ujte ponovo.</p>
    </div>
  `;

  // Show the reminder (change from display:none to display:block)
  reminderElement.style.display = 'block';

  console.log('[DEBUG] ✅ File metadata reminder displayed successfully');
  console.log('[DEBUG] Reminder HTML:', reminderElement.innerHTML.substring(0, 150) + '...');
}

/**
 * Format file size in human-readable format (Story 2.8 - Task 12.5)
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted file size (e.g., "1.5 MB", "500 KB")
 */
function formatFileSize(bytes) {
  if (bytes < 1024) {
    return bytes + ' B';
  } else if (bytes < 1024 * 1024) {
    return (bytes / 1024).toFixed(1) + ' KB';
  } else {
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }
}

/**
 * Trigger character counters for Section II after draft load (Story 2.6 - Task 6.4)
 * Story 3.1: Updated to handle both COA and COB fields
 * IMPORTANT: Only triggers for Section II textareas if they have content
 */
function triggerCharacterCountersAfterDraftLoad() {
  const appType = getApplicationType();

  let sectionIIFields;
  if (appType === 'COA') {
    // COA: Project Data fields
    sectionIIFields = ['naslov', 'opis', 'problem', 'cilj', 'specifični_ciljevi', 'ciljne_grupe', 'aktivnosti', 'rezultati'];
  } else if (appType === 'COB') {
    // COB: Initiative Data fields (Story 5.3: Added naziv_tima)
    sectionIIFields = ['naziv_tima', 'naslov', 'kratak_opis', 'problem', 'cilj', 'planirani_koraci', 'ocekivani_uticaj'];
  } else {
    sectionIIFields = [];
  }

  sectionIIFields.forEach(fieldId => {
    const field = document.getElementById(`id_${fieldId}`);
    if (field && field.value) {
      // Dispatch input event to trigger character counter update
      field.dispatchEvent(new Event('input', { bubbles: true }));
    }
  });
}

/**
 * Trigger validation for all restored fields after draft load
 * Story 2.3: Real-time validation integration
 * IMPORTANT: Only validates VISIBLE fields (Task 2.6: Don't validate hidden fields)
 */
function triggerValidationAfterDraftLoad() {
  // Z3 (2026-07-24): id_jmbg / id_id_broj removed. Registracioni broj kept for pravna lica.
  const fieldsToValidate = ['id_email', 'id_telefon', 'id_maticni_broj', 'id_registracioni_broj'];

  fieldsToValidate.forEach(fieldId => {
    const field = document.getElementById(fieldId);
    // Check if field exists, has value, AND is visible (offsetParent !== null means visible)
    if (field && field.value && field.offsetParent !== null) {
      // Dispatch blur event to trigger immediate validation
      field.dispatchEvent(new Event('blur'));
    }
  });
}

/**
 * Helper function to restore a single field value
 * @param {string} fieldId - DOM element ID
 * @param {string} value - Value to restore
 */
function restoreFieldValue(fieldId, value) {
  const field = document.getElementById(fieldId);
  if (field && value) {
    field.value = value;
  }
}

/**
 * Reset auto-save timer with debounce pattern (Story 2.4 - Task 1.2)
 * Clears existing timeout and sets new 30s timeout
 * Called on every 'input' event to implement debounce
 */
function resetAutoSaveTimer() {
  // Clear existing timeout to prevent multiple pending saves
  clearTimeout(window.autoSaveTimeout);

  // Set new 30-second timeout
  window.autoSaveTimeout = setTimeout(() => {
    saveDraft();
  }, 30000); // 30 seconds (FR20)
}

/**
 * Show saving indicator (Story 2.4 - Task 2.2)
 * Displays spinner + "Čuva se..." text
 * CODE REVIEW FIX (HIGH #3): Use classList instead of className replacement
 */
function showSavingIndicator() {
  const indicator = document.getElementById('autosave-indicator');
  if (!indicator) return;

  // Cancel previous hide timeout if exists (Task 2.7 - queueing)
  if (indicatorTimeout) {
    clearTimeout(indicatorTimeout);
  }

  // Remove all state modifiers, add visible and saving
  indicator.classList.remove('autosave-indicator--saved', 'autosave-indicator--warning');
  indicator.classList.add('autosave-indicator--visible', 'autosave-indicator--saving');
  indicator.querySelector('.autosave-indicator__text').textContent = 'Čuva se...';
  indicator.setAttribute('aria-live', 'polite');
}

/**
 * Show saved indicator (Story 2.4 - Task 2.3)
 * Displays checkmark + "Sačuvano" text, auto-hides after 2s
 * CODE REVIEW FIX (HIGH #3): Use classList instead of className replacement
 */
function showSavedIndicator() {
  const indicator = document.getElementById('autosave-indicator');
  if (!indicator) return;

  // Remove all state modifiers, add visible and saved
  indicator.classList.remove('autosave-indicator--saving', 'autosave-indicator--warning');
  indicator.classList.add('autosave-indicator--visible', 'autosave-indicator--saved');
  indicator.querySelector('.autosave-indicator__text').textContent = 'Sačuvano';
  indicator.setAttribute('aria-live', 'polite');

  // Auto-hide after 2 seconds (Task 2.3)
  indicatorTimeout = setTimeout(() => {
    indicator.classList.remove('autosave-indicator--visible');
  }, 2000);
}

/**
 * Show persistent warning message (Story 2.4 - Task 5.2, 5.4)
 * @param {string} message - Warning message to display
 * CODE REVIEW FIX (HIGH #3): Use classList instead of className replacement
 */
function showPersistentWarning(message) {
  const indicator = document.getElementById('autosave-indicator');
  if (!indicator) {
    alert(message); // Fallback if indicator doesn't exist
    return;
  }

  // Cancel any hide timeouts
  if (indicatorTimeout) {
    clearTimeout(indicatorTimeout);
  }

  // Remove all state modifiers, add visible and warning
  indicator.classList.remove('autosave-indicator--saving', 'autosave-indicator--saved');
  indicator.classList.add('autosave-indicator--visible', 'autosave-indicator--warning');
  indicator.querySelector('.autosave-indicator__text').textContent = message;
  indicator.setAttribute('aria-live', 'assertive'); // Urgent announcement
  // No timeout - warning stays visible
}

/**
 * Disable auto-save feature (Story 2.4 - Task 5.4)
 * Called when QuotaExceededError occurs
 * CODE REVIEW FIX (MEDIUM #6): Also remove beforeunload handler
 */
function disableAutoSave() {
  // Clear auto-save timeout to stop trying
  clearTimeout(window.autoSaveTimeout);

  // Remove event listeners to stop triggering auto-save
  const formInputs = document.querySelectorAll('input[type="text"], input[type="email"], textarea');
  formInputs.forEach(input => {
    input.removeEventListener('input', resetAutoSaveTimer);
  });

  // Remove beforeunload handler to stop save-on-close attempts
  window.removeEventListener('beforeunload', handleBeforeUnload);

  console.warn('Auto-save je onemogućen zbog premašene storage kvote');
}

/**
 * Test if localStorage is available (Story 2.4 - Task 5.1)
 * Handles Safari private mode and other localStorage restrictions
 * @returns {boolean} True if localStorage is available, false otherwise
 */
function isLocalStorageAvailable() {
  try {
    const testKey = '__domovik_test__';
    localStorage.setItem(testKey, 'test');
    localStorage.removeItem(testKey);
    return true;
  } catch (error) {
    // Safari private mode throws here immediately
    return false;
  }
}

/**
 * Handle browser close/navigate - save draft immediately
 * Story 2.4 - Task 1.4: beforeunload handler
 * CODE REVIEW FIX (HIGH #2): Error handling to prevent data loss
 * CODE REVIEW FIX (MEDIUM #6): Named function for removeEventListener support
 */
function handleBeforeUnload(e) {
  try {
    saveDraft(); // Immediate save before unload
  } catch (error) {
    // If save fails, log error but don't block page unload
    console.error('Greška pri čuvanju draft-a tokom zatvaranja:', error);
  }
  // Note: Modern browsers ignore custom messages in e.returnValue
}

/**
 * Create modal HTML markup (Story 2.5 - Task 2.1-2.6)
 * Returns modal HTML string with proper ARIA attributes and accessibility
 * @returns {string} Modal HTML markup
 */
function createModalHTML() {
  return `
    <div class="draft-recovery-modal" role="dialog" aria-modal="true"
         aria-labelledby="modal-heading" aria-describedby="modal-message" tabindex="-1">
      <div class="draft-recovery-modal__backdrop" data-modal-backdrop></div>
      <div class="draft-recovery-modal__content">
        <button class="draft-recovery-modal__close" aria-label="Zatvori modal" data-modal-close>
          <span aria-hidden="true">&times;</span>
        </button>
        <h2 id="modal-heading" class="draft-recovery-modal__heading">
          Pronađeni prethodno sačuvani podaci
        </h2>
        <p id="modal-message" class="draft-recovery-modal__message">
          Želite li da nastavite sa popunjavanjem ili da počnete ispočetka?
        </p>
        <div class="draft-recovery-modal__actions">
          <button class="draft-recovery-modal__btn draft-recovery-modal__btn--primary" data-action="continue">
            Nastavi
          </button>
          <button class="draft-recovery-modal__btn draft-recovery-modal__btn--secondary" data-action="start-fresh">
            Počni ispočetka
          </button>
        </div>
      </div>
    </div>
  `;
}

/**
 * Show modal with focus trap and accessibility (Story 2.5 - Task 3.1-3.7)
 * Displays the draft recovery modal and manages focus
 */
function showModal() {
  // Create and inject modal HTML
  const modalHTML = createModalHTML();
  document.body.insertAdjacentHTML('beforeend', modalHTML);

  const modal = document.querySelector('.draft-recovery-modal');
  const continueBtn = modal.querySelector('[data-action="continue"]');
  const startFreshBtn = modal.querySelector('[data-action="start-fresh"]');
  const closeBtn = modal.querySelector('[data-modal-close]');
  const backdrop = modal.querySelector('[data-modal-backdrop]');

  // Save previous focus for restoration (Task 3.4)
  const previousFocus = document.activeElement;

  // Disable form interaction while modal is open (Task 10.5)
  // Story 3.1: Dynamic form ID based on application type
  const formId = getApplicationType() === 'COA' ? 'coa-form-section-i' : 'cob-form';
  const form = document.getElementById(formId);
  if (form) {
    form.style.pointerEvents = 'none';
    form.style.opacity = '0.5';
    form.style.cursor = 'not-allowed';
  }

  // Prevent body scroll (Task 3.7)
  document.body.style.overflow = 'hidden';

  // Show modal with fade-in animation (Task 3.2)
  requestAnimationFrame(() => {
    modal.classList.add('draft-recovery-modal--visible');
  });

  // Focus on "Nastavi" button after animation (Task 3.5)
  setTimeout(() => {
    continueBtn.focus();
  }, 250);

  // Focus trap implementation (Task 3.3)
  const focusableElements = modal.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];

  function handleKeyDown(e) {
    // Escape key closes modal without clearing draft (Task 3.6, 3.9)
    if (e.key === 'Escape') {
      closeModal(modal, previousFocus, false);
      return;
    }

    // Tab key focus trap (Task 3.3, 3.8)
    if (e.key === 'Tab') {
      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    }
  }

  modal.addEventListener('keydown', handleKeyDown);

  // Event listeners for actions (Task 4, 5, 6)
  continueBtn.addEventListener('click', () => handleContinue(modal, previousFocus));
  startFreshBtn.addEventListener('click', () => handleStartFresh(modal, previousFocus));
  closeBtn.addEventListener('click', () => closeModal(modal, previousFocus, false));
  backdrop.addEventListener('click', () => closeModal(modal, previousFocus, false));
}

/**
 * Handle "Nastavi" button click (Story 2.5 - Task 4.1-4.6)
 * Loads draft and triggers validation
 */
function handleContinue(modal, previousFocus) {
  // Call existing loadDraft() from Story 2.2 (Task 4.2)
  loadDraft();

  // Call triggerValidationAfterDraftLoad() from Story 2.3 (Task 4.3)
  triggerValidationAfterDraftLoad();

  // Close modal (Task 4.4)
  closeModal(modal, previousFocus, false);

  // Initialize auto-save system after modal closes (Task 8.5)
  initializeAutoSave();

  // Focus first form field after modal closes (Task 4.6)
  // Story 3.1: Dynamic form ID
  setTimeout(() => {
    const formId = getApplicationType() === 'COA' ? 'coa-form-section-i' : 'cob-form';
    const firstInput = document.querySelector(`#${formId} input[type="text"]`);
    if (firstInput) {
      firstInput.focus();
    }
  }, 300);
}

/**
 * Handle "Počni ispočetka" button click (Story 2.5 - Task 5.1-5.7)
 * Story 3.1: Updated to use dynamic draft key and form ID
 * Clears draft and resets form
 */
function handleStartFresh(modal, previousFocus) {
  // Delete draft from localStorage (Task 5.2)
  // Story 3.1: Use dynamic draft key
  localStorage.removeItem(getDraftKey());

  // Reset form (Task 5.3)
  // Story 3.1: Dynamic form ID
  const formId = getApplicationType() === 'COA' ? 'coa-form-section-i' : 'cob-form';
  const form = document.getElementById(formId);
  if (form) {
    form.reset();
  }

  // Reset entity_type to default fizicko (Task 5.4)
  const fizickoRadio = document.querySelector('input[name="entity_type"][value="fizicko"]');
  if (fizickoRadio) {
    fizickoRadio.checked = true;
  }

  // Clear all validation errors manually (Task 5.5)
  // CRITICAL: clearAllValidations() DOES NOT EXIST - manually clear each field
  // Z3 (2026-07-24): id_jmbg removed.
  ['id_email', 'id_telefon', 'id_maticni_broj'].forEach(fieldId => {
    const field = document.getElementById(fieldId);
    if (field && typeof clearValidationError === 'function') {
      clearValidationError(field);
    }
  });

  // Close modal (Task 5.6)
  closeModal(modal, previousFocus, true);

  // Initialize auto-save system for fresh start (Task 8.6)
  initializeAutoSave();

  // Focus first form field (Task 5.7)
  // Story 3.1: Dynamic form ID
  setTimeout(() => {
    const formId = getApplicationType() === 'COA' ? 'coa-form-section-i' : 'cob-form';
    const firstInput = document.querySelector(`#${formId} input[type="text"]`);
    if (firstInput) {
      firstInput.focus();
    }
  }, 300);
}

/**
 * Close modal with animation (Story 2.5 - Task 6, integrated with Task 4-5)
 * @param {HTMLElement} modal - Modal element
 * @param {HTMLElement} previousFocus - Previously focused element
 * @param {boolean} clearDraft - Whether draft was cleared (not used, but kept for signature consistency)
 */
function closeModal(modal, previousFocus, clearDraft) {
  // Remove visible class for fade-out animation
  modal.classList.remove('draft-recovery-modal--visible');

  // Wait for animation to complete (200ms)
  setTimeout(() => {
    // Remove modal from DOM
    modal.remove();

    // Restore body scroll
    document.body.style.overflow = '';

    // Re-enable form interaction (Task 10.6)
    // Story 3.1: Dynamic form ID
    const formId = getApplicationType() === 'COA' ? 'coa-form-section-i' : 'cob-form';
    const form = document.getElementById(formId);
    if (form) {
      form.style.pointerEvents = '';
      form.style.opacity = '';
      form.style.cursor = '';
    }

    // Restore focus (Task 3.10)
    // CODE REVIEW FIX (LOW #8): Added fallback if element was removed from DOM
    if (previousFocus && document.body.contains(previousFocus)) {
      try {
        previousFocus.focus();
      } catch (e) {
        // Fallback: focus first form input if restoration fails
        const fallbackInput = document.querySelector(`#${formId} input[type="text"]`);
        if (fallbackInput) {
          fallbackInput.focus();
        }
      }
    } else if (previousFocus) {
      // Element was removed from DOM, use fallback
      const fallbackInput = document.querySelector(`#${formId} input[type="text"]`);
      if (fallbackInput) {
        fallbackInput.focus();
      }
    }
  }, 200);
}

/**
 * Show localStorage unavailable warning (Story 2.5 - Task 9.2-9.4)
 * Story 3.1: Updated to use dynamic form ID
 * Displays persistent warning at top of form when localStorage is unavailable
 */
function showLocalStorageWarning() {
  // Story 3.1: Dynamic form ID
  const formId = getApplicationType() === 'COA' ? 'coa-form-section-i' : 'cob-form';
  const form = document.getElementById(formId);
  if (!form) return;

  const warningHTML = `
    <div class="localstorage-warning" role="alert">
      <span class="localstorage-warning__icon" aria-hidden="true">⚠️</span>
      <span class="localstorage-warning__text">
        Auto-save nije dostupan. Molimo ne zatvarajte browser dok ne završite.
      </span>
    </div>
  `;

  // Insert warning at the top of the form
  form.insertAdjacentHTML('afterbegin', warningHTML);
}

/**
 * Initialize auto-save system (Story 2.5 - Task 8.5, 8.6)
 * Helper function to avoid code duplication in modal handlers and DOMContentLoaded
 * CODE REVIEW FIX (MEDIUM #6): Added guard flag to prevent duplicate event listeners
 */
function initializeAutoSave() {
  // Prevent duplicate initialization
  if (autoSaveInitialized) {
    return;
  }

  // Attach auto-save timer to form inputs
  const formInputs = document.querySelectorAll('input[type="text"], input[type="email"], textarea');
  formInputs.forEach(input => {
    input.addEventListener('input', resetAutoSaveTimer);
  });

  // Add beforeunload handler to save on browser close/navigate
  window.addEventListener('beforeunload', handleBeforeUnload);

  // Mark as initialized
  autoSaveInitialized = true;
}

/**
 * Initialize draft system on page load (Story 2.5 - Task 10)
 * Story 2.4: Auto-save timer, beforeunload handler, localStorage availability check
 * Story 2.5: Draft recovery modal integration
 * Story 2.15: Server-side draft expiration check
 */
document.addEventListener('DOMContentLoaded', async function() {
  // STEP 1: Check if localStorage is available FIRST (Task 10.2)
  if (!isLocalStorageAvailable()) {
    showLocalStorageWarning(); // Show warning banner (Task 9.2)
    console.warn('localStorage nije dostupan - draft recovery modal onemogućen');
    return; // Stop initialization - form still works but no draft functionality
  }

  // STEP 2: Initialize draft ID (Story 2.15)
  draftId = getOrCreateDraftId();
  console.log('Draft ID initialized:', draftId);

  // STEP 3: Check if draft expired on server (Story 2.15)
  const expired = await checkDraftExpiration();
  if (expired) {
    console.log('Draft expired - starting fresh');
    draftId = generateUUID(); // Generate new ID for fresh start
    initializeAutoSave();
    return;
  }

  // STEP 4: Check if draft exists (Task 10.3)
  const draftCheck = checkDraftExists();

  // STEP 5: If draft exists AND valid, show modal (Task 10.4)
  if (draftCheck.exists) {
    showModal(); // Modal will handle draft loading or clearing
    // Note: Auto-save timer will be initialized after modal is closed
  } else {
    // STEP 6: No draft - proceed with normal flow (Task 10.7)
    // Load draft anyway (will do nothing if no draft exists)
    loadDraft();

    // Initialize auto-save system
    initializeAutoSave();
  }

  // Note: If modal is shown, auto-save will be initialized after modal action
  // This is handled in handleContinue() and handleStartFresh()
});
