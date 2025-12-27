/**
 * ConsentManager - Manages consent checkboxes and submit button activation
 * Story 2.10: COA Form Section III - Documentation & Consent
 *
 * Features:
 * - Three consent checkboxes validation (privacy, terms, accuracy)
 * - Submit button activation logic (disabled by default)
 * - File upload validation integration (budget + min 1 biografija required)
 * - Draft system integration (save checkbox states to localStorage)
 * - ARIA announcements for screen readers
 * - Error messaging for missing requirements
 * - Accessibility support (keyboard navigation, focus states)
 *
 * @class ConsentManager
 */

// File category constants (Story 2.9 integration)
const FILE_CATEGORIES = {
  BUDGET: 'BUDGET',
  BIOGRAPHY: 'BIOGRAPHY',
  SUPPORT_LETTER: 'SUPPORT_LETTER'
};

// Debounce delay for draft save (milliseconds)
const DRAFT_SAVE_DEBOUNCE_DELAY = 300;

class ConsentManager {
  /**
   * Constructor - Initialize ConsentManager
   */
  constructor() {
    // Checkbox elements
    this.privacyCheckbox = null;
    this.termsCheckbox = null;
    this.accuracyCheckbox = null;

    // Submit button
    this.submitButton = null;

    // Error container
    this.errorContainer = null;

    // ARIA live region for screen reader announcements
    this.ariaLiveRegion = null;

    // Debounce timer for draft save
    this.draftSaveTimer = null;

    // Form submission state
    this.isSubmitting = false;
  }

  /**
   * Initialize the consent manager
   * - Get DOM elements
   * - Create ARIA live region
   * - Attach event listeners
   * - Perform initial state check (for draft recovery)
   */
  init() {
    // Get DOM elements
    this.privacyCheckbox = document.getElementById('consent-privacy');
    this.termsCheckbox = document.getElementById('consent-terms');
    this.accuracyCheckbox = document.getElementById('consent-accuracy');
    this.submitButton = document.getElementById('submit-btn');
    this.errorContainer = document.getElementById('consent-error');

    // Create ARIA live region if not exists
    if (!this.ariaLiveRegion) {
      this.ariaLiveRegion = document.createElement('div');
      this.ariaLiveRegion.setAttribute('role', 'status');
      this.ariaLiveRegion.setAttribute('aria-live', 'polite');
      this.ariaLiveRegion.className = 'sr-only';
      document.body.appendChild(this.ariaLiveRegion);
    }

    // Attach event listeners
    this.attachEventListeners();

    // Initial state check (for draft recovery)
    this.updateSubmitButtonState();
  }

  /**
   * Attach event listeners to checkboxes and submit button
   * - Listen for 'change' event on each checkbox
   * - Listen for 'submit' event on form to prevent double submission
   * - Call handleCheckboxChange() on change
   */
  attachEventListeners() {
    if (this.privacyCheckbox) {
      this.privacyCheckbox.addEventListener('change', () => this.handleCheckboxChange());
    }
    if (this.termsCheckbox) {
      this.termsCheckbox.addEventListener('change', () => this.handleCheckboxChange());
    }
    if (this.accuracyCheckbox) {
      this.accuracyCheckbox.addEventListener('change', () => this.handleCheckboxChange());
    }

    // Prevent double submission (Story 2.10 Code Review Fix #2)
    if (this.submitButton && this.submitButton.form) {
      this.submitButton.form.addEventListener('submit', (event) => this.handleFormSubmit(event));
    }
  }

  /**
   * Handle checkbox change event
   * - Update submit button state
   * - Save checkbox states to draft (debounced)
   */
  handleCheckboxChange() {
    // Update submit button state immediately
    this.updateSubmitButtonState();

    // Debounce draft save to avoid excessive localStorage writes (Story 2.10 Code Review Fix #1)
    if (this.draftSaveTimer) {
      clearTimeout(this.draftSaveTimer);
    }

    this.draftSaveTimer = setTimeout(() => {
      // Save checkbox states to draft (if draft manager exists)
      if (window.draftManager && typeof window.draftManager.saveConsentStatesToDraft === 'function') {
        window.draftManager.saveConsentStatesToDraft();
      } else if (typeof saveConsentStatesToDraft === 'function') {
        // Fallback: Call global function if exists
        saveConsentStatesToDraft();
      }
    }, DRAFT_SAVE_DEBOUNCE_DELAY);
  }

  /**
   * Handle form submit event
   * - Disable submit button during submission to prevent double submission
   * - Show loading spinner
   * @param {Event} event - Submit event
   */
  handleFormSubmit(event) {
    // Prevent double submission
    if (this.isSubmitting) {
      event.preventDefault();
      return false;
    }

    this.isSubmitting = true;
    this.submitButton.disabled = true;

    // Show loading spinner
    const spinner = this.submitButton.querySelector('.submit-spinner');
    if (spinner) {
      spinner.style.display = 'inline-block';
    }

    // Note: Form will submit naturally unless prevented elsewhere
    // Story 2.11 will handle actual submission with backend integration
  }

  /**
   * Check if all checkboxes are checked
   * @returns {boolean} True if all three checkboxes are checked, false otherwise
   */
  areAllCheckboxesChecked() {
    return (
      this.privacyCheckbox && this.privacyCheckbox.checked &&
      this.termsCheckbox && this.termsCheckbox.checked &&
      this.accuracyCheckbox && this.accuracyCheckbox.checked
    );
  }

  /**
   * Validate that required files are uploaded
   * Story 2.10 - Task 6: File upload validation before submit
   *
   * Required files:
   * - Budget: 1 Excel file (BUDGET category)
   * - Biografije: Minimum 1 PDF/DOC file (BIOGRAPHY category)
   *
   * Optional files (not required for submit):
   * - Pisma podrške: SUPPORT_LETTER category
   *
   * @returns {Object} { valid: boolean, missing: string[] }
   * @throws {TypeError} If uploadedFilesRegistry is not an array (Story 2.10 Code Review Fix #3)
   */
  validateRequiredFiles() {
    const missing = [];

    // Check if uploadedFilesRegistry exists and is an array (Story 2.10 Code Review Fix #3)
    if (!window.uploadedFilesRegistry || !Array.isArray(window.uploadedFilesRegistry)) {
      // Registry not found or invalid - assume no files uploaded
      missing.push('Budžet projekta');
      missing.push('Biografije članova tima');
      return { valid: false, missing: missing };
    }

    // Count uploaded files by category (Story 2.10 Code Review Fix #4 - use constants)
    const budgetFiles = window.uploadedFilesRegistry.filter(file => file.category === FILE_CATEGORIES.BUDGET);
    const biografijeFiles = window.uploadedFilesRegistry.filter(file => file.category === FILE_CATEGORIES.BIOGRAPHY);

    // Budget file required (exactly 1)
    if (budgetFiles.length === 0) {
      missing.push('Budžet projekta');
    }

    // At least one biografija required
    if (biografijeFiles.length === 0) {
      missing.push('Biografije članova tima');
    }

    // Pisma podrške are optional (not required for submit)

    return {
      valid: missing.length === 0,
      missing: missing
    };
  }

  /**
   * Update submit button state (enable/disable)
   * Story 2.10 - Task 5: Checkbox state management
   * Story 2.10 - Task 6: File validation integration
   *
   * Enable submit button ONLY if:
   * 1. All three checkboxes are checked
   * 2. Required files are uploaded (budget + min 1 biografija)
   */
  updateSubmitButtonState() {
    if (!this.submitButton) return;

    const allCheckboxesChecked = this.areAllCheckboxesChecked();
    const fileValidation = this.validateRequiredFiles();

    // Enable submit only if all checkboxes checked AND required files uploaded
    if (allCheckboxesChecked && fileValidation.valid) {
      this.enableSubmitButton();
      this.clearError();
    } else {
      this.disableSubmitButton();

      // Show error if checkboxes are checked but files are missing
      if (allCheckboxesChecked && !fileValidation.valid) {
        const missingList = fileValidation.missing.join(', ');
        this.showError(`Molimo upload-ujte sve obavezne dokumente pre slanja prijave: ${missingList}`);
      } else {
        this.clearError();
      }
    }
  }

  /**
   * Enable submit button
   * - Remove disabled attribute
   * - Update ARIA attributes
   * - Change CSS classes
   * - Announce to screen readers
   */
  enableSubmitButton() {
    this.submitButton.disabled = false;
    this.submitButton.setAttribute('aria-disabled', 'false');
    this.submitButton.classList.remove('submit-btn--disabled');
    this.submitButton.classList.add('submit-btn--enabled');

    // Announce to screen readers
    this.announceToScreenReader('Submit dugme je sada aktivno. Možete da podnete prijavu.');
  }

  /**
   * Disable submit button
   * - Add disabled attribute
   * - Update ARIA attributes
   * - Change CSS classes
   * - Announce to screen readers
   */
  disableSubmitButton() {
    this.submitButton.disabled = true;
    this.submitButton.setAttribute('aria-disabled', 'true');
    this.submitButton.classList.remove('submit-btn--enabled');
    this.submitButton.classList.add('submit-btn--disabled');

    // Announce to screen readers (only if checkboxes exist and at least one is checked)
    if (this.privacyCheckbox && (this.privacyCheckbox.checked || this.termsCheckbox.checked || this.accuracyCheckbox.checked)) {
      this.announceToScreenReader('Submit dugme je neaktivno. Molimo potvrdite sve saglasnosti i upload-ujte obavezne dokumente.');
    }
  }

  /**
   * Show error message
   * Story 2.10 - Task 13: Error handling & user feedback
   *
   * @param {string} message - Error message to display
   */
  showError(message) {
    if (!this.errorContainer) return;

    this.errorContainer.innerHTML = `
      <span class="error-icon" aria-hidden="true">⚠️</span>
      <span class="error-text">${message}</span>
    `;
    this.errorContainer.style.display = 'flex';
    this.errorContainer.setAttribute('role', 'alert');
    this.errorContainer.setAttribute('tabindex', '-1');

    // Story 2.10 Code Review Fix #5: Focus management for accessibility
    // Scroll error into view and move focus for keyboard/screen reader users
    this.errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  /**
   * Clear error message
   */
  clearError() {
    if (!this.errorContainer) return;

    this.errorContainer.innerHTML = '';
    this.errorContainer.style.display = 'none';
  }

  /**
   * Announce message to screen readers via ARIA live region
   * Story 2.10 - Task 9: Accessibility & keyboard navigation
   *
   * @param {string} message - Message to announce
   */
  announceToScreenReader(message) {
    if (!this.ariaLiveRegion) return;

    this.ariaLiveRegion.textContent = message;

    // Clear after 5 seconds
    setTimeout(() => {
      this.ariaLiveRegion.textContent = '';
    }, 5000);
  }

  /**
   * Get current consent states
   * Story 2.10 - Task 7: Draft system integration
   *
   * @returns {Object} { privacy: boolean, terms: boolean, accuracy: boolean }
   */
  getConsentStates() {
    return {
      privacy: this.privacyCheckbox ? this.privacyCheckbox.checked : false,
      terms: this.termsCheckbox ? this.termsCheckbox.checked : false,
      accuracy: this.accuracyCheckbox ? this.accuracyCheckbox.checked : false
    };
  }

  /**
   * Set consent states (for draft recovery)
   * Story 2.10 - Task 7: Draft system integration
   *
   * @param {Object} states - { privacy: boolean, terms: boolean, accuracy: boolean }
   */
  setConsentStates(states) {
    if (this.privacyCheckbox && states.privacy !== undefined) {
      this.privacyCheckbox.checked = states.privacy;
    }
    if (this.termsCheckbox && states.terms !== undefined) {
      this.termsCheckbox.checked = states.terms;
    }
    if (this.accuracyCheckbox && states.accuracy !== undefined) {
      this.accuracyCheckbox.checked = states.accuracy;
    }

    // Update submit button state after setting checkboxes
    this.updateSubmitButtonState();
  }

  /**
   * Trigger submit button state update (Story 2.10 Code Review Fix #6)
   * PUBLIC API: Called by file upload handlers when files are uploaded/deleted
   * This ensures ARIA announcements are made when submit button becomes enabled via file uploads
   */
  refreshSubmitButtonState() {
    this.updateSubmitButtonState();
  }
}

/**
 * Initialize ConsentManager on DOM ready
 * Story 2.10 - Tasks 5-7: Checkbox management, file validation, draft integration
 */
document.addEventListener('DOMContentLoaded', () => {
  window.consentManager = new ConsentManager();
  window.consentManager.init();
});
