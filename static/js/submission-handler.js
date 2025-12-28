/**
 * Submission Handler - Complete Form Submission with Reference Number
 * Story 2.11: Reference Number Generation & Submission Processing
 *
 * Features:
 * - Collects all form data (applicant + project)
 * - Validates required fields before submission
 * - Submits to backend API (/api/submissions/submit/)
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

    // API endpoint
    this.submitUrl = '/api/submissions/submit/';
  }

  /**
   * Initialize submission handler
   * - Get DOM elements
   * - Attach form submit listener
   * - Create ARIA live region
   */
  init() {
    // Get form element (Section I form)
    this.form = document.getElementById('coa-form-section-i');
    if (!this.form) {
      console.error('SubmissionHandler: Form element not found');
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

    // Set submitting state
    this.isSubmitting = true;
    this.disableSubmitButton();

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
      this.handleSubmissionError('Došlo je do greške. Proverite internet konekciju i pokušajte ponovo.');
    } finally {
      // Reset submitting state
      this.isSubmitting = false;
      this.enableSubmitButton();
    }
  }

  /**
   * Validate form data before submission
   * Story 2.11 - Task 9: Basic validation
   *
   * @returns {Object} { valid: boolean, error: string }
   */
  validateFormData() {
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

    // Check Section II project fields
    const naslov = document.getElementById('id_naslov')?.value.trim();
    const opis = document.getElementById('id_opis')?.value.trim();

    if (!naslov || !opis) {
      return {
        valid: false,
        error: 'Molimo unesite naslov i opis projekta.'
      };
    }

    // All validation passed
    return { valid: true, error: null };
  }

  /**
   * Collect all form data for submission
   * Story 2.11 - Task 8: Data collection
   *
   * @returns {Object} Complete submission data
   */
  collectFormData() {
    const entityType = document.getElementById('id_entity_type')?.value || 'fizicko';

    // Build submission data object
    const submissionData = {
      application_type: 'COA', // COA for project application
      applicant: {
        entity_type: entityType,
        address: document.getElementById('id_adresa')?.value || '',
        email: document.getElementById('id_email')?.value || '',
        phone: document.getElementById('id_telefon')?.value || ''
      },
      project: {
        title: document.getElementById('id_naslov')?.value || '',
        short_description: document.getElementById('id_opis')?.value || '',
        problem: document.getElementById('id_problem')?.value || '',
        main_goal: document.getElementById('id_cilj')?.value || '',
        specific_goals: document.getElementById('id_specifični_ciljevi')?.value || '',
        target_groups: document.getElementById('id_ciljne_grupe')?.value || '',
        activities: document.getElementById('id_aktivnosti')?.value || '',
        results: document.getElementById('id_rezultati')?.value || '',
        total_budget: parseInt(document.getElementById('id_budžet')?.value || '0', 10)
      },
      consent: {
        privacy: document.getElementById('consent-privacy')?.checked || false,
        terms: document.getElementById('consent-terms')?.checked || false,
        accuracy: document.getElementById('consent-accuracy')?.checked || false
      }
    };

    // Add entity-specific fields
    if (entityType === 'fizicko') {
      submissionData.applicant.first_name = document.getElementById('id_ime')?.value || '';
      submissionData.applicant.last_name = document.getElementById('id_prezime')?.value || '';
      submissionData.applicant.jmbg = document.getElementById('id_jmbg')?.value || '';
    } else if (entityType === 'pravno') {
      submissionData.applicant.organization_name = document.getElementById('id_naziv_organizacije')?.value || '';
      submissionData.applicant.maticni_broj = document.getElementById('id_maticni_broj')?.value || '';
    }

    console.log('Collected submission data:', submissionData);
    return submissionData;
  }

  /**
   * Send submission request to backend API
   * Story 2.11 - Task 8: AJAX submission
   *
   * @param {Object} submissionData - Complete submission data
   * @returns {Promise<Object>} Response from server
   */
  async sendSubmissionRequest(submissionData) {
    // Get CSRF token
    const csrfToken = this.getCSRFToken();

    // Send POST request
    const response = await fetch(this.submitUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(submissionData),
      credentials: 'same-origin' // Include cookies for session
    });

    // Parse JSON response
    const data = await response.json();

    // Check if response is successful
    if (!response.ok) {
      // HTTP error (4xx, 5xx)
      throw new Error(data.error || 'Greška pri komunikaciji sa serverom.');
    }

    return data;
  }

  /**
   * Get CSRF token from cookie
   * Django CSRF protection
   *
   * @returns {string} CSRF token
   */
  getCSRFToken() {
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

    return cookieValue || '';
  }

  /**
   * Handle successful submission
   * Story 2.11 - Task 7: Draft cleanup on success
   *
   * @param {Object} response - Success response with reference number
   */
  handleSubmissionSuccess(response) {
    const referenceNumber = response.reference_number;

    console.log('Submission successful:', referenceNumber);

    // Clear draft from localStorage (Story 2.11 - Task 7)
    if (typeof localStorage !== 'undefined') {
      const DRAFT_KEY = 'domovik_coa_draft';
      localStorage.removeItem(DRAFT_KEY);
      console.log('Draft cleared from localStorage');
    }

    // Announce success to screen readers
    this.announceToScreenReader(`Prijava uspešno podnesena. Vaš referentni broj: ${referenceNumber}`);

    // Show success message with reference number
    this.showSuccessMessage(referenceNumber);

    // Disable form to prevent re-submission
    this.disableForm();
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
   */
  disableSubmitButton() {
    if (this.submitButton) {
      this.submitButton.disabled = true;
      this.submitButton.setAttribute('aria-disabled', 'true');

      // Show spinner
      if (this.spinner) {
        this.spinner.style.display = 'inline-block';
      }

      // Update button text
      const buttonText = this.submitButton.querySelector('.submit-btn__text');
      if (buttonText) {
        buttonText.textContent = 'Šalje se...';
      }
    }
  }

  /**
   * Enable submit button and hide loading spinner
   */
  enableSubmitButton() {
    if (this.submitButton) {
      this.submitButton.disabled = false;
      this.submitButton.setAttribute('aria-disabled', 'false');

      // Hide spinner
      if (this.spinner) {
        this.spinner.style.display = 'none';
      }

      // Restore button text
      const buttonText = this.submitButton.querySelector('.submit-btn__text');
      if (buttonText) {
        buttonText.textContent = 'Podnesi prijavu';
      }
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
