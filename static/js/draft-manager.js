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

// Guard flag to prevent duplicate event listener registration (Code Review Fix MEDIUM #6)
let autoSaveInitialized = false;

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
 * Check if draft exists and is valid (Story 2.5 - Task 1.1)
 * REFACTORED from loadDraft() to support modal display on page load
 * @returns {Object} {exists: boolean, expired: boolean, data: object|null}
 */
function checkDraftExists() {
  try {
    const draftJson = localStorage.getItem(DRAFT_KEY);
    if (!draftJson) {
      return { exists: false, expired: false, data: null };
    }

    const draftData = JSON.parse(draftJson);

    // Check if draft is expired (>7 days old) using extracted helper
    if (isExpiredDraft(draftData)) {
      // Auto-delete expired draft (GDPR - NFR18)
      localStorage.removeItem(DRAFT_KEY);
      console.log('Draft expired (>7 days), auto-deleted');
      return { exists: false, expired: true, data: null };
    }

    // Valid draft exists
    return { exists: true, expired: false, data: draftData };
  } catch (error) {
    // Corrupt JSON handling - cleanup and return false
    console.error('Corrupt draft data detected, cleaning up:', error);
    localStorage.removeItem(DRAFT_KEY);
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
  const form = document.getElementById('coa-form-section-i');
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
  setTimeout(() => {
    const firstInput = document.querySelector('#coa-form-section-i input[type="text"]');
    if (firstInput) {
      firstInput.focus();
    }
  }, 300);
}

/**
 * Handle "Počni ispočetka" button click (Story 2.5 - Task 5.1-5.7)
 * Clears draft and resets form
 */
function handleStartFresh(modal, previousFocus) {
  // Delete draft from localStorage (Task 5.2)
  localStorage.removeItem(DRAFT_KEY);

  // Reset form (Task 5.3)
  const form = document.getElementById('coa-form-section-i');
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
  ['id_email', 'id_telefon', 'id_jmbg', 'id_maticni_broj'].forEach(fieldId => {
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
  setTimeout(() => {
    const firstInput = document.querySelector('#coa-form-section-i input[type="text"]');
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
    const form = document.getElementById('coa-form-section-i');
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
        const fallbackInput = document.querySelector('#coa-form-section-i input[type="text"]');
        if (fallbackInput) {
          fallbackInput.focus();
        }
      }
    } else if (previousFocus) {
      // Element was removed from DOM, use fallback
      const fallbackInput = document.querySelector('#coa-form-section-i input[type="text"]');
      if (fallbackInput) {
        fallbackInput.focus();
      }
    }
  }, 200);
}

/**
 * Show localStorage unavailable warning (Story 2.5 - Task 9.2-9.4)
 * Displays persistent warning at top of form when localStorage is unavailable
 */
function showLocalStorageWarning() {
  const form = document.getElementById('coa-form-section-i');
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
 */
document.addEventListener('DOMContentLoaded', function() {
  // STEP 1: Check if localStorage is available FIRST (Task 10.2)
  if (!isLocalStorageAvailable()) {
    showLocalStorageWarning(); // Show warning banner (Task 9.2)
    console.warn('localStorage nije dostupan - draft recovery modal onemogućen');
    return; // Stop initialization - form still works but no draft functionality
  }

  // STEP 2: Check if draft exists (Task 10.3)
  const draftCheck = checkDraftExists();

  // STEP 3: If draft exists AND valid, show modal (Task 10.4)
  if (draftCheck.exists) {
    showModal(); // Modal will handle draft loading or clearing
    // Note: Auto-save timer will be initialized after modal is closed
  } else {
    // STEP 4: No draft - proceed with normal flow (Task 10.7)
    // Load draft anyway (will do nothing if no draft exists)
    loadDraft();

    // Initialize auto-save system
    initializeAutoSave();
  }

  // Note: If modal is shown, auto-save will be initialized after modal action
  // This is handled in handleContinue() and handleStartFresh()
});
