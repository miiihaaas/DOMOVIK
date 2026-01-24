/**
 * Submission Handler - Complete Form Submission with Reference Number
 * Story 2.11: Reference Number Generation & Submission Processing
 *
 * Features:
 * - Collects all form data (applicant + project)
 * - Validates required fields before submission
 * - Submits to backend API (/submit/ for COA, /submit-cob/ for COB)
 * - Handles success with reference number display
 * - Handles errors with user-friendly Serbian messages
 * - Integrates with DraftManager (clears draft on success)
 * - Integrates with ConsentManager (validates consent)
 * - Integrates with FileUploadHandler (includes file metadata)
 * - CSRF token protection
 * - ARIA live regions for accessibility
 * - Loading spinner during submission
 * - Prevents double submission
 */

class SubmissionHandler {
  /**
   * Constructor - Initialize SubmissionHandler
   */
  constructor() {
    // Form element
    this.form = null;

    // Submit button
    this.submitButton = null;

    // Loading spinner
    this.spinner = null;

    // ARIA live region for announcements
    this.ariaLiveRegion = null;

    // Error container
    this.errorContainer = null;

    // Submission state
    this.isSubmitting = false;

    // API endpoint (will be set dynamically based on application type)
    this.submitUrl = null;

    // Network timeout constant (10 seconds)
    this.NETWORK_TIMEOUT_MS = 10000;
  }

  /**
   * Initialize submission handler
   * - Get DOM elements
   * - Attach form submit listener
   * - Create ARIA live region
   */
  init() {
    // Get form element (detect COA vs COB form dynamically)
    const applicationType = this.getApplicationType();
    const formId = applicationType === 'COB' ? 'cob-form' : 'coa-form-section-i';

    this.form = document.getElementById(formId);
    if (!this.form) {
      console.error(`SubmissionHandler: Form element '${formId}' not found`);
      return;
    }

    // Get submit button
    this.submitButton = document.getElementById('submit-btn');
    if (!this.submitButton) {
      console.error('SubmissionHandler: Submit button not found');
      return;
    }

    // Get spinner
    this.spinner = this.submitButton.querySelector('.submit-spinner');

    // Get error container
    this.errorContainer = document.getElementById('submission-error');

    // Create ARIA live region if not exists
    if (!this.ariaLiveRegion) {
      this.ariaLiveRegion = document.createElement('div');
      this.ariaLiveRegion.setAttribute('role', 'status');
      this.ariaLiveRegion.setAttribute('aria-live', 'assertive');
      this.ariaLiveRegion.className = 'sr-only';
      document.body.appendChild(this.ariaLiveRegion);
    }

    // Attach form submit listener
    this.form.addEventListener('submit', (e) => this.handleFormSubmit(e));

    console.log('SubmissionHandler initialized');
  }

  /**
   * Handle form submit event
   * - Prevent default form submission
   * - Validate form data
   * - Collect form data
   * - Send AJAX request to backend
   * - Handle success/error responses
   *
   * @param {Event} event - Form submit event
   */
  async handleFormSubmit(event) {
    event.preventDefault();

    // Prevent double submission
    if (this.isSubmitting) {
      console.warn('Submission already in progress');
      return;
    }

    // Clear previous errors
    this.clearError();

    // Validate form data before submission
    const validation = this.validateFormData();
    if (!validation.valid) {
      this.showError(validation.error);
      this.announceToScreenReader(validation.error);
      return;
    }

    // CRITICAL: Disable button FIRST to prevent race condition
    this.disableSubmitButton();

    // Verify button was actually disabled (DOM element exists)
    if (!this.submitButton || !this.submitButton.disabled) {
      console.error('Failed to disable submit button - DOM element missing or invalid');
      this.showError('Greška u inicijalizaciji forme. Osvežite stranicu i pokušajte ponovo.');
      return;
    }

    // Set submitting state AFTER button is confirmed disabled
    this.isSubmitting = true;

    try {
      // Collect form data
      const submissionData = this.collectFormData();

      // Send AJAX request
      const response = await this.sendSubmissionRequest(submissionData);

      if (response.success) {
        // Success: Show reference number and clear draft
        this.handleSubmissionSuccess(response);
      } else {
        // Error: Show error message
        this.handleSubmissionError(response.error || 'Greška pri slanju prijave.');
      }
    } catch (error) {
      // Network or unexpected error
      console.error('Submission exception:', error);

      // Differentiate error types for better UX
      let errorMessage = 'Došlo je do greške. Proverite internet konekciju i pokušajte ponovo.';

      if (error.name === 'AbortError') {
        // Timeout error
        errorMessage = 'Zahtev je trajao predugo. Proverite internet konekciju i pokušajte ponovo.';
      } else if (error.message && error.message.includes('NetworkError')) {
        // Network offline
        errorMessage = 'Nema internet konekcije. Proverite vezu i pokušajte ponovo.';
      } else if (error.message && error.message.includes('Failed to fetch')) {
        // Generic fetch failure (CORS, DNS, etc.)
        errorMessage = 'Ne mogu da se povežem sa serverom. Proverite internet konekciju.';
      }

      this.handleSubmissionError(errorMessage);
    } finally {
      // Reset submitting state
      this.isSubmitting = false;
      this.enableSubmitButton();
    }
  }

  /**
   * Validate form data before submission
   * Story 2.11 - Task 9: Basic validation
   * FIX #5 & #15: Application-type aware validation
   *
   * @returns {Object} { valid: boolean, error: string }
   */
  validateFormData() {
    const applicationType = this.getApplicationType();

    // Check if consent checkboxes are all checked (via ConsentManager)
    if (window.consentManager && typeof window.consentManager.areAllCheckboxesChecked === 'function') {
      if (!window.consentManager.areAllCheckboxesChecked()) {
        return {
          valid: false,
          error: 'Molimo potvrdite sve saglasnosti pre slanja prijave.'
        };
      }
    }

    // Check if required files are uploaded (via ConsentManager file validation)
    if (window.consentManager && typeof window.consentManager.validateRequiredFiles === 'function') {
      const fileValidation = window.consentManager.validateRequiredFiles();
      if (!fileValidation.valid) {
        return {
          valid: false,
          error: `Molimo upload-ujte sve obavezne dokumente: ${fileValidation.missing.join(', ')}`
        };
      }
    }

    // Check entity type
    const entityType = document.getElementById('id_entity_type')?.value;
    if (!entityType) {
      return {
        valid: false,
        error: 'Tip podnosioca nije izabran.'
      };
    }

    // Basic field validation for visible fields
    if (entityType === 'fizicko') {
      const ime = document.getElementById('id_ime')?.value.trim();
      const prezime = document.getElementById('id_prezime')?.value.trim();
      if (!ime || !prezime) {
        return {
          valid: false,
          error: 'Molimo unesite ime i prezime.'
        };
      }
    } else if (entityType === 'pravno') {
      const naziv = document.getElementById('id_naziv_organizacije')?.value.trim();
      if (!naziv) {
        return {
          valid: false,
          error: 'Molimo unesite naziv organizacije.'
        };
      }
    }

    // Check common fields
    const adresa = document.getElementById('id_adresa')?.value.trim();
    const email = document.getElementById('id_email')?.value.trim();
    const telefon = document.getElementById('id_telefon')?.value.trim();

    if (!adresa || !email || !telefon) {
      return {
        valid: false,
        error: 'Molimo popunite sva obavezna polja (adresa, email, telefon).'
      };
    }

    // FIX #15: Application-type aware Section II validation
    if (applicationType === 'COB') {
      // COB: Initiative fields (WITH id_ prefix, same as COA)
      const naslov = document.getElementById('id_naslov')?.value.trim();
      const kratak_opis = document.getElementById('id_kratak_opis')?.value.trim();

      if (!naslov || !kratak_opis) {
        return {
          valid: false,
          error: 'Molimo unesite naslov i kratak opis inicijative.'
        };
      }
    } else {
      // COA: Project fields (WITH id_ prefix)
      const naslov = document.getElementById('id_naslov')?.value.trim();
      const opis = document.getElementById('id_opis')?.value.trim();

      if (!naslov || !opis) {
        return {
          valid: false,
          error: 'Molimo unesite naslov i opis projekta.'
        };
      }
    }

    // All validation passed
    return { valid: true, error: null };
  }

  /**
   * Get application type from body data attribute
   * BUGFIX: Dynamic detection for COA vs COB
   * @returns {string} 'COA' or 'COB'
   */
  getApplicationType() {
    return document.body.dataset.applicationType || 'COA';
  }

  /**
   * Get submit URL based on application type
   * Story 3.5: COB submission endpoint
   * BUGFIX: Correct URLs without /api/submissions/ prefix (routes are at root)
   * @returns {string} Submit endpoint URL
   */
  getSubmitUrl() {
    const appType = this.getApplicationType();
    if (appType === 'COB') {
      return '/submit-cob/';
    } else {
      return '/submit/';  // COA default (was /api/submissions/submit/)
    }
  }

  /**
   * Collect all form data for submission
   * Story 2.11 - Task 8: Data collection
   * Story 3.5: COB initiative data collection
   * BUGFIX: Application-type aware data collection (COA vs COB)
   *
   * @returns {Object} Complete submission data
   */
  collectFormData() {
    const entityType = document.getElementById('id_entity_type')?.value || 'fizicko';
    const applicationType = this.getApplicationType();

    // Build submission data object
    const submissionData = {
      application_type: applicationType, // BUGFIX: Dynamic COA/COB detection
      applicant: {
        entity_type: entityType,
        address: document.getElementById('id_adresa')?.value || '',
        email: document.getElementById('id_email')?.value || '',
        phone: document.getElementById('id_telefon')?.value || ''
      },
      consent: {}
    };

    // Add entity-specific fields
    if (entityType === 'fizicko') {
      submissionData.applicant.first_name = document.getElementById('id_ime')?.value || '';
      submissionData.applicant.last_name = document.getElementById('id_prezime')?.value || '';

      // JMBG only for COA (Story 3.5: COB has NO JMBG)
      if (applicationType === 'COA') {
        submissionData.applicant.jmbg = document.getElementById('id_jmbg')?.value || '';
      }
    } else if (entityType === 'pravno') {
      submissionData.applicant.organization_name = document.getElementById('id_naziv_organizacije')?.value || '';

      // Matični broj only for COA (Story 3.5: COB has NO matični)
      if (applicationType === 'COA') {
        submissionData.applicant.maticni_broj = document.getElementById('id_maticni_broj')?.value || '';
      }
    }

    // Add application-specific data (COA vs COB)
    if (applicationType === 'COB') {
      // COB: Initiative data (NO budget, WITH id_ prefix same as COA)
      submissionData.initiative = {
        naslov: document.getElementById('id_naslov')?.value || '',
        kratak_opis: document.getElementById('id_kratak_opis')?.value || '',
        problem: document.getElementById('id_problem')?.value || '',
        cilj_inicijative: document.getElementById('id_cilj')?.value || '',
        planirani_koraci: document.getElementById('id_planirani_koraci')?.value || '',
        ocekivani_uticaj: document.getElementById('id_ocekivani_uticaj')?.value || ''
      };

      // COB consent (3 checkboxes, same as COA)
      submissionData.consent.privacy = document.getElementById('consent-privacy')?.checked || false;
      submissionData.consent.terms = document.getElementById('consent-terms')?.checked || false;
      submissionData.consent.accuracy = document.getElementById('consent-accuracy')?.checked || false;

      // BUGFIX #2: Get files from global getUploadedFiles() function
      if (typeof window.getUploadedFiles === 'function') {
        // Use uploaded files from Story 2.8 FileUploadHandler (global registry)
        submissionData.files = window.getUploadedFiles();
      } else {
        // Fallback: Collect file metadata from input elements
        submissionData.files = this.collectFileMetadata();
      }
    } else {
      // COA: Project data (WITH budget)
      // Story 5.2: Added datum_startovanja and datum_zavrsetka
      submissionData.project = {
        title: document.getElementById('id_naslov')?.value || '',
        short_description: document.getElementById('id_opis')?.value || '',
        problem: document.getElementById('id_problem')?.value || '',
        main_goal: document.getElementById('id_cilj')?.value || '',
        specific_goals: document.getElementById('id_specifični_ciljevi')?.value || '',
        target_groups: document.getElementById('id_ciljne_grupe')?.value || '',
        activities: document.getElementById('id_aktivnosti')?.value || '',
        results: document.getElementById('id_rezultati')?.value || '',
        // Story 5.2: Project timeline dates
        datum_startovanja: document.getElementById('id_datum_startovanja')?.value || null,
        datum_zavrsetka: document.getElementById('id_datum_zavrsetka')?.value || null,
        total_budget: parseInt(document.getElementById('id_budžet')?.value || '0', 10)
      };

      // COA consent (3 checkboxes)
      submissionData.consent.privacy = document.getElementById('consent-privacy')?.checked || false;
      submissionData.consent.terms = document.getElementById('consent-terms')?.checked || false;
      submissionData.consent.accuracy = document.getElementById('consent-accuracy')?.checked || false;

      // BUGFIX #2: COA also needs files from global registry
      if (typeof window.getUploadedFiles === 'function') {
        submissionData.files = window.getUploadedFiles();
      }
    }

    // FIX #17: Remove console.log in production (information disclosure)
    // console.log('Collected submission data:', submissionData);
    return submissionData;
  }

  /**
   * Collect file metadata for COB submissions
   * Story 3.5: COB file metadata collection
   * @returns {Array} File metadata array
   */
  collectFileMetadata() {
    const files = [];

    // Get file upload elements (COB has 2 files)
    const opisFile = document.getElementById('opis_inicijative_file');
    const pismoFile = document.getElementById('pismo_namere_file');

    if (opisFile && opisFile.files.length > 0) {
      files.push({
        file_type: 'OPIS_INICIJATIVE',
        name: opisFile.files[0].name,
        size: opisFile.files[0].size
      });
    }

    if (pismoFile && pismoFile.files.length > 0) {
      files.push({
        file_type: 'PISMO_NAMERE',
        name: pismoFile.files[0].name,
        size: pismoFile.files[0].size
      });
    }

    return files;
  }

  /**
   * Send submission request to backend API
   * Story 2.11 - Task 8: AJAX submission
   * Story 2.12 - Task 4: Network timeout protection (10 seconds)
   * Story 3.5: Dynamic URL based on application type
   *
   * @param {Object} submissionData - Complete submission data
   * @returns {Promise<Object>} Response from server
   */
  async sendSubmissionRequest(submissionData) {
    // Get dynamic submit URL based on application type
    const submitUrl = this.getSubmitUrl();

    // Get CSRF token
    const csrfToken = this.getCSRFToken();

    // SECURITY: Validate CSRF token exists
    if (!csrfToken) {
      console.error('CSRF token missing - cannot submit form');
      throw new Error('Bezbednosna greška: CSRF token nedostaje. Osvežite stranicu i pokušajte ponovo.');
    }

    // Create AbortController for network timeout (Story 2.12 - Task 4)
    // Browser compatibility: Chrome 66+, Firefox 57+, Safari 12.1+, Edge 79+
    let controller = null;
    let timeoutId = null;

    // Check if AbortController is supported (graceful degradation)
    if (typeof AbortController !== 'undefined') {
      try {
        controller = new AbortController();
        timeoutId = setTimeout(() => controller.abort(), this.NETWORK_TIMEOUT_MS);
      } catch (e) {
        console.warn('AbortController failed to initialize:', e);
        // Continue without timeout protection (better than blocking submission)
      }
    } else {
      console.warn('AbortController not supported - timeout protection disabled');
    }

    try {
      // Send POST request
      const fetchOptions = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(submissionData),
        credentials: 'same-origin' // Include cookies for session
      };

      // Add abort signal only if controller was successfully created
      if (controller) {
        fetchOptions.signal = controller.signal;
      }

      const response = await fetch(submitUrl, fetchOptions);

      // Clear timeout on successful fetch
      if (timeoutId) {
        clearTimeout(timeoutId);
      }

      // Parse JSON response
      const data = await response.json();

      // Check if response is successful
      if (!response.ok) {
        // HTTP error (4xx, 5xx)
        throw new Error(data.error || 'Greška pri komunikaciji sa serverom.');
      }

      return data;
    } catch (error) {
      // Clear timeout on error
      if (timeoutId) {
        clearTimeout(timeoutId);
      }

      // Check if error is due to timeout (AbortError)
      if (error.name === 'AbortError') {
        throw new Error('Zahtev je trajao predugo. Proverite internet konekciju i pokušajte ponovo.');
      }

      // Re-throw other errors
      throw error;
    }
  }

  /**
   * Get CSRF token from DOM meta tag or cookie
   * Django CSRF protection
   *
   * Story 4-5: Updated to read from DOM meta tag (primary) due to CSRF_COOKIE_HTTPONLY=True
   * Falls back to cookie for backwards compatibility
   *
   * @returns {string} CSRF token or empty string if not found
   */
  getCSRFToken() {
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

    return cookieValue || '';
  }

  /**
   * Handle successful submission
   * Story 2.11 - Task 7: Draft cleanup on success
   * Story 2.13 - Redirect to success screen
   * Story 3.5: COB draft cleanup
   *
   * @param {Object} response - Success response with reference number
   */
  handleSubmissionSuccess(response) {
    const referenceNumber = response.reference_number;
    const applicationType = this.getApplicationType();  // FIX: Removed duplicate declaration

    // FIX #17: Remove console.log in production
    // console.log('Submission successful:', referenceNumber);

    // Clear draft from localStorage (Story 2.11 - Task 7, Story 3.5)
    if (typeof localStorage !== 'undefined') {
      try {
        // Dynamic draft key based on application type
        const DRAFT_KEY = applicationType === 'COB' ? 'domovik_cob_draft' : 'domovik_coa_draft';
        localStorage.removeItem(DRAFT_KEY);
        // FIX #17: Remove console.log
        // console.log(`Draft cleared from localStorage (${applicationType})`);
      } catch (e) {
        // localStorage.removeItem() can throw if storage is locked or quota exceeded
        console.warn('Failed to clear draft from localStorage:', e);
        // Non-critical error - continue with success flow
      }
    }

    // Announce success to screen readers
    this.announceToScreenReader(`Prijava uspešno podnesena. Vaš referentni broj: ${referenceNumber}`);

    if (!referenceNumber) {
      console.error('Reference number missing from response');
      this.handleSubmissionError('Greška: Referentni broj nije primljen.');
      return;
    }

    // BUGFIX: Correct success URL path (routes are at root, not under /api/submissions/)
    // URL pattern from urls.py: success/<application_type>/<reference_number>/
    const successUrl = `/success/${applicationType}/${referenceNumber}/`;

    // FIX #17: Remove console.log in production
    // console.log(`Redirecting to success screen: ${successUrl}`);
    window.location.href = successUrl;
  }

  /**
   * Handle submission error
   * Story 2.11 - Task 9: Error handling
   *
   * @param {string} errorMessage - Error message from server
   */
  handleSubmissionError(errorMessage) {
    console.error('Submission error:', errorMessage);

    // Show error message
    this.showError(errorMessage);

    // Announce error to screen readers
    this.announceToScreenReader(`Greška: ${errorMessage}`);

    // ACCESSIBILITY: Move focus to error message for screen readers
    if (this.errorContainer) {
      // Set tabindex to make container focusable
      this.errorContainer.setAttribute('tabindex', '-1');
      // Focus the error container
      setTimeout(() => {
        this.errorContainer.focus();
      }, 100); // Small delay to ensure error is rendered
    }

    // Keep draft intact on error (do NOT clear localStorage)
    console.log('Draft preserved due to submission error');
  }

  /**
   * Show success message with reference number
   * Story 2.11 - Task 8: Success display
   *
   * @param {string} referenceNumber - Generated reference number
   */
  showSuccessMessage(referenceNumber) {
    // Create success message container
    const successHTML = `
      <div class="submission-success" role="alert" aria-live="assertive">
        <div class="submission-success__icon">✅</div>
        <h2 class="submission-success__title">Prijava uspešno podnesena!</h2>
        <p class="submission-success__message">
          Vaša prijava je uspešno primljena i obrađena.
        </p>
        <div class="submission-success__reference">
          <strong>Referentni broj:</strong>
          <span class="reference-number">${referenceNumber}</span>
        </div>
        <p class="submission-success__instructions">
          Molimo sačuvajte ovaj broj za buduću komunikaciju.
          Potvrda će biti poslata na email adresu koju ste naveli.
        </p>
      </div>
    `;

    // Hide form and show success message
    if (this.form) {
      this.form.style.display = 'none';
    }

    // Insert success message after form
    if (this.form && this.form.parentElement) {
      this.form.parentElement.insertAdjacentHTML('beforeend', successHTML);

      // Scroll to success message
      const successElement = document.querySelector('.submission-success');
      if (successElement) {
        successElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  }

  /**
   * Show error message
   * Story 2.11 - Task 9: Error display
   *
   * @param {string} errorMessage - Error message to display
   */
  showError(errorMessage) {
    if (!this.errorContainer) {
      // Fallback: Create error container if not exists
      this.errorContainer = document.createElement('div');
      this.errorContainer.id = 'submission-error';
      this.errorContainer.className = 'form-error';
      this.errorContainer.setAttribute('role', 'alert');

      // Insert at top of form
      if (this.form) {
        this.form.insertAdjacentElement('afterbegin', this.errorContainer);
      }
    }

    this.errorContainer.innerHTML = `
      <span class="error-icon" aria-hidden="true">⚠️</span>
      <span class="error-text">${errorMessage}</span>
    `;
    this.errorContainer.style.display = 'flex';

    // Scroll error into view
    this.errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  /**
   * Clear error message
   */
  clearError() {
    if (this.errorContainer) {
      this.errorContainer.innerHTML = '';
      this.errorContainer.style.display = 'none';
    }
  }

  /**
   * Disable submit button and show loading spinner
   * Story 2.12 - Enhanced with accessibility and error handling
   */
  disableSubmitButton() {
    if (!this.submitButton) {
      console.error('Cannot disable submit button - element not found');
      return;
    }

    // Disable button (prevents clicks)
    this.submitButton.disabled = true;
    this.submitButton.setAttribute('aria-disabled', 'true');

    // Show spinner
    if (this.spinner) {
      this.spinner.style.display = 'inline-block';
      // ACCESSIBILITY: Add aria-label to spinner for screen readers
      this.spinner.setAttribute('aria-label', 'Učitavanje u toku');
    }

    // Update button text
    const buttonText = this.submitButton.querySelector('.submit-btn__text');
    if (buttonText) {
      buttonText.textContent = 'Šalje se prijava, molimo sačekajte...';
    }

    // ACCESSIBILITY: Announce state change to screen readers
    this.announceToScreenReader('Prijava se šalje, molimo sačekajte...');
  }

  /**
   * Enable submit button and hide loading spinner
   * Story 2.12 - Enhanced with DOM validation and error recovery
   */
  enableSubmitButton() {
    // EDGE CASE: Re-query button if it was removed from DOM during submission
    if (!this.submitButton || !document.body.contains(this.submitButton)) {
      console.warn('Submit button was removed from DOM - re-querying');
      this.submitButton = document.getElementById('submit-btn');
      this.spinner = this.submitButton ? this.submitButton.querySelector('.submit-spinner') : null;
    }

    if (!this.submitButton) {
      console.error('Cannot enable submit button - element not found in DOM');
      return;
    }

    // Re-enable button
    this.submitButton.disabled = false;
    this.submitButton.setAttribute('aria-disabled', 'false');

    // Hide spinner
    if (this.spinner) {
      this.spinner.style.display = 'none';
      // Remove aria-label
      this.spinner.removeAttribute('aria-label');
    }

    // Restore button text
    const buttonText = this.submitButton.querySelector('.submit-btn__text');
    if (buttonText) {
      buttonText.textContent = 'PODNESI PRIJAVU';
    }
  }

  /**
   * Disable entire form to prevent changes after submission
   */
  disableForm() {
    if (this.form) {
      const inputs = this.form.querySelectorAll('input, textarea, select, button');
      inputs.forEach(input => {
        input.disabled = true;
      });
    }
  }

  /**
   * Announce message to screen readers via ARIA live region
   * Story 2.11 - Task 9: Accessibility
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
}

/**
 * Initialize SubmissionHandler on DOM ready
 * Story 2.11 - Tasks 8: Frontend submission handler
 */
document.addEventListener('DOMContentLoaded', () => {
  window.submissionHandler = new SubmissionHandler();
  window.submissionHandler.init();
});
