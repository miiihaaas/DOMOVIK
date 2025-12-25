/**
 * Draft Manager - Auto-Save Draft Preservation System
 * Story 2.2: Basic draft save/load for entity type switching
 * Story 2.4: Auto-save every 30s, beforeunload handler, visual notifications
 *
 * Features:
 * - Auto-save every 30 seconds (debounced from last input)
 * - Immediate save on browser close/navigate (beforeunload)
 * - Visual "Sačuvano" notification with queueing
 * - 7-day retention with automatic deletion
 * - GDPR-compliant (client-side only, no server transmission)
 * - QuotaExceededError handling with graceful degradation
 * - Performance measurement (development mode only)
 */

const DRAFT_KEY = 'domovik_coa_draft';

// Global auto-save timer reference (Story 2.4 - Task 1.1)
// Explicitly on window object for access from entity-type-switcher.js (Task 4.4)
window.autoSaveTimeout = null;

// Global indicator timeout for visual feedback queueing (Story 2.4 - Task 2.7)
let indicatorTimeout;

/**
 * Collect all form data for saving (Story 2.4 - Task 3)
 * @returns {Object} Draft data object with application_type, timestamp, and all fields
 */
function collectFormData() {
  return {
    application_type: 'COA',  // Distinguishes COA vs COB drafts (multi-form system - Epic 3+)
    timestamp: new Date().toISOString(),
    entity_type: document.getElementById('id_entity_type')?.value || 'fizicko',
    fizicko: {
      ime: document.getElementById('id_ime')?.value || '',
      prezime: document.getElementById('id_prezime')?.value || '',
      jmbg: document.getElementById('id_jmbg')?.value || ''
    },
    pravno: {
      naziv_organizacije: document.getElementById('id_naziv_organizacije')?.value || '',
      maticni_broj: document.getElementById('id_maticni_broj')?.value || ''
    },
    common: {
      adresa: document.getElementById('id_adresa')?.value || '',
      email: document.getElementById('id_email')?.value || '',
      telefon: document.getElementById('id_telefon')?.value || ''
    },
    consent: {},  // Structure for future checkboxes (Story X.X)
    files_metadata: []  // Placeholder for FR24 (file uploads in later stories)
  };
}

/**
 * Save all form field values to localStorage
 * Story 2.2: Basic save functionality
 * Story 2.4: Added performance measurement, visual indicators, error handling
 * Called by: entity-type-switcher.js, auto-save timer, beforeunload handler
 *
 * GDPR COMPLIANCE (NFR16-18):
 * - Data stored ONLY in client-side localStorage (no server transmission)
 * - Zero network requests during auto-save operation
 * - 7-day retention enforced by loadDraft() check (lines 104-114)
 * - User data remains on user's device until explicit form submission
 * - Admin panel NEVER sees draft data (only submitted applications)
 */
function saveDraft() {
  const form = document.getElementById('coa-form-section-i');
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

    localStorage.setItem(DRAFT_KEY, JSON.stringify(draftData));

    // Performance measurement end
    if (isDevelopment) {
      console.timeEnd('saveDraft');
    }
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
 * Load form field values from localStorage
 * Called after showing fields during entity type switch
 */
function loadDraft() {
  try {
    const draftJson = localStorage.getItem(DRAFT_KEY);
    if (!draftJson) {
      // Development logging (comment out for production)
      // console.log('No draft found in localStorage');
      return;
    }

    const draftData = JSON.parse(draftJson);

    // Check if draft is fresh (< 7 days old)
    if (draftData.timestamp) {
      const draftAge = Date.now() - new Date(draftData.timestamp).getTime();
      const MAX_AGE = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds

      if (draftAge > MAX_AGE) {
        // Development logging (comment out for production)
        // console.log('Draft too old (>7 days), removing from localStorage');
        localStorage.removeItem(DRAFT_KEY);
        return;
      }
    }

    // Restore entity type
    const entityTypeInput = document.getElementById('id_entity_type');
    if (entityTypeInput && draftData.entity_type) {
      entityTypeInput.value = draftData.entity_type;
    }

    // Restore fizičko lice fields
    if (draftData.fizicko) {
      restoreFieldValue('id_ime', draftData.fizicko.ime);
      restoreFieldValue('id_prezime', draftData.fizicko.prezime);
      restoreFieldValue('id_jmbg', draftData.fizicko.jmbg);
    }

    // Restore pravno lice fields
    if (draftData.pravno) {
      restoreFieldValue('id_naziv_organizacije', draftData.pravno.naziv_organizacije);
      restoreFieldValue('id_maticni_broj', draftData.pravno.maticni_broj);
    }

    // Restore common fields
    if (draftData.common) {
      restoreFieldValue('id_adresa', draftData.common.adresa);
      restoreFieldValue('id_email', draftData.common.email);
      restoreFieldValue('id_telefon', draftData.common.telefon);
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
 * Trigger validation for all restored fields after draft load
 * Story 2.3: Real-time validation integration
 * IMPORTANT: Only validates VISIBLE fields (Task 2.6: Don't validate hidden fields)
 */
function triggerValidationAfterDraftLoad() {
  const fieldsToValidate = ['id_email', 'id_telefon', 'id_jmbg', 'id_maticni_broj'];

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
 * Initialize draft system on page load
 * Story 2.4: Auto-save timer, beforeunload handler, localStorage availability check
 */
document.addEventListener('DOMContentLoaded', function() {
  // Check if localStorage is available (Task 5.1)
  if (!isLocalStorageAvailable()) {
    showPersistentWarning('Auto-save nije dostupan. Molimo ne zatvarajte browser.');
    console.warn('localStorage nije dostupan - auto-save je onemogućen');
    return; // Stop initialization
  }

  // Load existing draft (Story 2.2)
  loadDraft();

  // Attach auto-save timer to form inputs (Task 1.3)
  const formInputs = document.querySelectorAll('input[type="text"], input[type="email"], textarea');
  formInputs.forEach(input => {
    input.addEventListener('input', resetAutoSaveTimer);
  });

  // Add beforeunload handler to save on browser close/navigate (Task 1.4)
  window.addEventListener('beforeunload', handleBeforeUnload);
});
