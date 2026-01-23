/**
 * Real-Time Validator Module
 * Story 2.3: Real-Time Validation for Section I
 *
 * Features:
 * - Email, phone, JMBG, and matični broj validation
 * - Real-time validation with debounce (100ms)
 * - User-friendly Serbian error messages
 * - ARIA attributes for accessibility (WCAG 2.1 Level AA)
 * - Integration with entity-type-switcher and draft-manager
 *
 * Performance:
 * - All validations execute in <100ms (typically <1ms)
 * - Debounced input events (100ms delay)
 * - Immediate blur event validation
 */

// ==========================================================================
// Validation Patterns & Constants
// ==========================================================================

// Email validation (simplified RFC 5322 - close to Django EmailField)
// NOTE: This regex approximates but doesn't exactly match Django's EmailValidator
// Edge cases (consecutive dots, leading/trailing dots) may differ from server validation
const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

// Serbian phone validation (9 or 10 digits total: 06 + 7-8 more digits)
// Format: 061234567 (9 digits) or 0611234567 (10 digits)
// Accepts: 06[0-9]{7,8} (no separators in validation - normalize input first)
const PHONE_REGEX = /^06[0-9]{7,8}$/;

// Story 5.1: ID broj validation (ID + exactly 7 digits)
// Format: ID1234567 (case-insensitive)
const ID_BROJ_REGEX = /^ID\d{7}$/i;

// Story 5.1: Registracioni broj validation (alphanumeric, max 50 chars)
// Accepts: letters, numbers, dashes, underscores, spaces
const REGISTRACIONI_BROJ_REGEX = /^[a-zA-Z0-9\-_\s]{1,50}$/;

// Serbian error messages (UTF-8 encoded)
const ERROR_MESSAGES = {
  email: "Neispravan email format. Primer: marko@example.com",
  telefon: "Neispravan broj telefona. Primer: 061234567 ili 0611234567",
  jmbg: "Format mora biti IDxxxxxxx (ID + 7 cifara). Primer: ID1234567",
  maticni_broj: "Registracioni broj može sadržati slova, brojeve i crtice (maks. 50 karaktera)"
};

// ==========================================================================
// Validation Functions
// ==========================================================================

/**
 * Validate email format
 * @param {string} email - Email address to validate
 * @returns {boolean} - True if valid, false otherwise
 */
function validateEmail(email) {
  if (!email || email.trim() === '') {
    return true; // Empty is valid (required validation is server-side)
  }
  // Performance measurement (NFR5: <100ms validation)
  console.time('validateEmail');
  const isValid = EMAIL_REGEX.test(email.trim());
  console.timeEnd('validateEmail');
  return isValid;
}

/**
 * Validate Serbian phone number format
 * @param {string} phone - Phone number to validate
 * @returns {boolean} - True if valid, false otherwise
 */
function validatePhone(phone) {
  if (!phone || phone.trim() === '') {
    return true; // Empty is valid (required validation is server-side)
  }
  // Performance measurement (NFR5: <100ms validation)
  console.time('validatePhone');
  const normalized = normalizePhone(phone);
  const isValid = PHONE_REGEX.test(normalized);
  console.timeEnd('validatePhone');
  return isValid;
}

/**
 * Validate ID broj format (ID + exactly 7 digits)
 * Story 5.1: Updated from JMBG (13 digits) to ID broj (IDxxxxxxx)
 * @param {string} idBroj - ID broj to validate
 * @returns {boolean} - True if valid, false otherwise
 */
function validateJMBG(idBroj) {
  if (!idBroj || idBroj.trim() === '') {
    return true; // Empty is valid (required validation is server-side)
  }
  // Performance measurement (NFR5: <100ms validation)
  console.time('validateIDBroj');
  const isValid = ID_BROJ_REGEX.test(idBroj.trim());
  console.timeEnd('validateIDBroj');
  return isValid;
}

/**
 * Validate registracioni broj format (alphanumeric, max 50 chars)
 * Story 5.1: Updated from matični broj (8 digits) to registracioni broj
 * @param {string} regBroj - Registracioni broj to validate
 * @returns {boolean} - True if valid, false otherwise
 */
function validateMaticniBroj(regBroj) {
  if (!regBroj || regBroj.trim() === '') {
    return true; // Empty is valid (required validation is server-side)
  }
  // Performance measurement (NFR5: <100ms validation)
  console.time('validateRegistracioniBroj');
  const isValid = REGISTRACIONI_BROJ_REGEX.test(regBroj.trim());
  console.timeEnd('validateRegistracioniBroj');
  return isValid;
}

// ==========================================================================
// Helper Functions
// ==========================================================================

/**
 * Normalize phone number by removing separators
 * @param {string} phone - Phone number with possible separators
 * @returns {string} - Normalized phone number (digits only)
 */
function normalizePhone(phone) {
  return phone.replace(/[-\s\/]/g, '');  // Remove -, spaces, /
}

/**
 * Debounce function - delays execution until after delay period
 * @param {Function} func - Function to debounce
 * @param {number} delay - Delay in milliseconds (default 100ms)
 * @returns {Function} - Debounced function
 */
function debounce(func, delay = 100) {
  let timeoutId;
  return function(...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(this, args), delay);
  };
}

/**
 * Show validation error for a field
 * @param {HTMLElement} field - Input field element
 * @param {string} errorMessage - Error message to display
 */
function showValidationError(field, errorMessage) {
  if (!field) return;

  const fieldId = field.id;
  const errorContainerId = `${fieldId}_error`;
  const errorContainer = document.getElementById(errorContainerId);

  if (!errorContainer) {
    console.warn(`Validation error container not found: ${errorContainerId}`);
    return;
  }

  // Show error message
  errorContainer.textContent = errorMessage;
  errorContainer.style.display = 'block';

  // Update ARIA attributes
  field.setAttribute('aria-invalid', 'true');

  // Add error styling to form group
  const formGroup = field.closest('.form-group');
  if (formGroup) {
    formGroup.classList.add('error');
    formGroup.classList.remove('valid');
  }
}

/**
 * Clear validation error for a field
 * @param {HTMLElement} field - Input field element
 */
function clearValidationError(field) {
  if (!field) return;

  const fieldId = field.id;
  const errorContainerId = `${fieldId}_error`;
  const errorContainer = document.getElementById(errorContainerId);

  if (!errorContainer) {
    return;
  }

  // Hide error message
  errorContainer.textContent = '';
  errorContainer.style.display = 'none';

  // Update ARIA attributes
  field.setAttribute('aria-invalid', 'false');

  // Remove error styling from form group
  const formGroup = field.closest('.form-group');
  if (formGroup) {
    formGroup.classList.remove('error');
    formGroup.classList.add('valid');
  }
}

// ==========================================================================
// Field-Specific Validation Handlers
// ==========================================================================

/**
 * Validate email field
 * @param {Event} event - Input or blur event
 */
function handleEmailValidation(event) {
  const field = event.target;
  const value = field.value;

  if (validateEmail(value)) {
    clearValidationError(field);
  } else {
    showValidationError(field, ERROR_MESSAGES.email);
  }
}

/**
 * Validate phone field
 * @param {Event} event - Input or blur event
 */
function handlePhoneValidation(event) {
  const field = event.target;
  const value = field.value;

  if (validatePhone(value)) {
    clearValidationError(field);
  } else {
    showValidationError(field, ERROR_MESSAGES.telefon);
  }
}

/**
 * Validate JMBG field
 * @param {Event} event - Input or blur event
 */
function handleJMBGValidation(event) {
  const field = event.target;
  const value = field.value;

  if (validateJMBG(value)) {
    clearValidationError(field);
  } else {
    showValidationError(field, ERROR_MESSAGES.jmbg);
  }
}

/**
 * Validate matični broj field
 * @param {Event} event - Input or blur event
 */
function handleMaticniBrojValidation(event) {
  const field = event.target;
  const value = field.value;

  if (validateMaticniBroj(value)) {
    clearValidationError(field);
  } else {
    showValidationError(field, ERROR_MESSAGES.maticni_broj);
  }
}

// ==========================================================================
// Clear All Validation Errors (Integration with Entity Switcher)
// ==========================================================================

/**
 * Clear all validation errors from the form
 * Called before entity type switch to reset validation state
 * Story 5.1: Added id_id_broj and id_registracioni_broj for COB form
 */
function clearAllValidationErrors() {
  const fields = ['id_email', 'id_telefon', 'id_jmbg', 'id_maticni_broj', 'id_id_broj', 'id_registracioni_broj'];

  fields.forEach(fieldId => {
    const field = document.getElementById(fieldId);
    if (field) {
      clearValidationError(field);
    }
  });
}

/**
 * Re-validate visible fields after entity type switch
 * Only validates fields that are currently visible
 * Story 5.1: Added support for COB fields (id_id_broj, id_registracioni_broj)
 */
function revalidateVisibleFields() {
  // Common fields (always visible)
  const emailField = document.getElementById('id_email');
  const telefonField = document.getElementById('id_telefon');

  if (emailField && emailField.value) {
    handleEmailValidation({ target: emailField });
  }

  if (telefonField && telefonField.value) {
    handlePhoneValidation({ target: telefonField });
  }

  // Entity-specific fields (only validate if visible)
  const entityType = document.getElementById('id_entity_type')?.value || 'fizicko';

  if (entityType === 'fizicko') {
    // COA uses id_jmbg, COB uses id_id_broj
    const jmbgField = document.getElementById('id_jmbg');
    const idBrojField = document.getElementById('id_id_broj');
    if (jmbgField && jmbgField.value) {
      handleJMBGValidation({ target: jmbgField });
    }
    if (idBrojField && idBrojField.value) {
      handleJMBGValidation({ target: idBrojField });
    }
  } else if (entityType === 'pravno') {
    // COA uses id_maticni_broj, COB uses id_registracioni_broj
    const maticniBrojField = document.getElementById('id_maticni_broj');
    const regBrojField = document.getElementById('id_registracioni_broj');
    if (maticniBrojField && maticniBrojField.value) {
      handleMaticniBrojValidation({ target: maticniBrojField });
    }
    if (regBrojField && regBrojField.value) {
      handleMaticniBrojValidation({ target: regBrojField });
    }
  }
}

// ==========================================================================
// Initialization & Event Listeners
// ==========================================================================

document.addEventListener('DOMContentLoaded', function() {
  // Get form field elements - COA form
  const emailField = document.getElementById('id_email');
  const telefonField = document.getElementById('id_telefon');
  const jmbgField = document.getElementById('id_jmbg');
  const maticniBrojField = document.getElementById('id_maticni_broj');

  // Story 5.1: Get COB form fields
  const idBrojField = document.getElementById('id_id_broj');
  const regBrojField = document.getElementById('id_registracioni_broj');

  // Attach event listeners to email field
  if (emailField) {
    emailField.addEventListener('input', debounce(handleEmailValidation, 100));
    emailField.addEventListener('blur', handleEmailValidation);
  }

  // Attach event listeners to telefon field
  if (telefonField) {
    telefonField.addEventListener('input', debounce(handlePhoneValidation, 100));
    telefonField.addEventListener('blur', handlePhoneValidation);
  }

  // Attach event listeners to ID broj field (COA: id_jmbg)
  if (jmbgField) {
    jmbgField.addEventListener('input', debounce(handleJMBGValidation, 100));
    jmbgField.addEventListener('blur', handleJMBGValidation);
  }

  // Story 5.1: Attach event listeners to ID broj field (COB: id_id_broj)
  if (idBrojField) {
    idBrojField.addEventListener('input', debounce(handleJMBGValidation, 100));
    idBrojField.addEventListener('blur', handleJMBGValidation);
  }

  // Attach event listeners to registracioni broj field (COA: id_maticni_broj)
  if (maticniBrojField) {
    maticniBrojField.addEventListener('input', debounce(handleMaticniBrojValidation, 100));
    maticniBrojField.addEventListener('blur', handleMaticniBrojValidation);
  }

  // Story 5.1: Attach event listeners to registracioni broj field (COB: id_registracioni_broj)
  if (regBrojField) {
    regBrojField.addEventListener('input', debounce(handleMaticniBrojValidation, 100));
    regBrojField.addEventListener('blur', handleMaticniBrojValidation);
  }

  // Development logging (comment out for production)
  // console.log('Real-time validation initialized');
});

// ==========================================================================
// Global API for Integration
// ==========================================================================

// Export functions for use by entity-type-switcher.js and draft-manager.js
window.RealTimeValidator = {
  clearAllValidationErrors,
  revalidateVisibleFields
};
