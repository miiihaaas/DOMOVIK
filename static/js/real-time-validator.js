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

// JMBG validation (exactly 13 digits)
const JMBG_REGEX = /^[0-9]{13}$/;

// Matični broj validation (exactly 8 digits for Serbia)
// NOTE: Server-side model allows up to 20 characters (CharField max_length=20)
// Client-side enforces 8 digits as business rule preference
const MATICNI_REGEX = /^[0-9]{8}$/;

// Serbian error messages (UTF-8 encoded)
const ERROR_MESSAGES = {
  email: "Neispravan email format. Primer: marko@example.com",
  telefon: "Neispravan broj telefona. Primer: 061234567 ili 0611234567",
  jmbg: "JMBG mora imati tačno 13 cifara",
  maticni_broj: "Matični broj mora imati tačno 8 cifara"
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
 * Validate JMBG format (exactly 13 digits)
 * @param {string} jmbg - JMBG to validate
 * @returns {boolean} - True if valid, false otherwise
 */
function validateJMBG(jmbg) {
  if (!jmbg || jmbg.trim() === '') {
    return true; // Empty is valid (required validation is server-side)
  }
  // Performance measurement (NFR5: <100ms validation)
  console.time('validateJMBG');
  const isValid = JMBG_REGEX.test(jmbg.trim());
  console.timeEnd('validateJMBG');
  return isValid;
}

/**
 * Validate matični broj format (exactly 8 digits)
 * @param {string} maticniBroj - Matični broj to validate
 * @returns {boolean} - True if valid, false otherwise
 */
function validateMaticniBroj(maticniBroj) {
  if (!maticniBroj || maticniBroj.trim() === '') {
    return true; // Empty is valid (required validation is server-side)
  }
  // Performance measurement (NFR5: <100ms validation)
  console.time('validateMaticniBroj');
  const isValid = MATICNI_REGEX.test(maticniBroj.trim());
  console.timeEnd('validateMaticniBroj');
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
 */
function clearAllValidationErrors() {
  const fields = ['id_email', 'id_telefon', 'id_jmbg', 'id_maticni_broj'];

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
    const jmbgField = document.getElementById('id_jmbg');
    if (jmbgField && jmbgField.value) {
      handleJMBGValidation({ target: jmbgField });
    }
  } else if (entityType === 'pravno') {
    const maticniBrojField = document.getElementById('id_maticni_broj');
    if (maticniBrojField && maticniBrojField.value) {
      handleMaticniBrojValidation({ target: maticniBrojField });
    }
  }
}

// ==========================================================================
// Initialization & Event Listeners
// ==========================================================================

document.addEventListener('DOMContentLoaded', function() {
  // Get form field elements
  const emailField = document.getElementById('id_email');
  const telefonField = document.getElementById('id_telefon');
  const jmbgField = document.getElementById('id_jmbg');
  const maticniBrojField = document.getElementById('id_maticni_broj');

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

  // Attach event listeners to JMBG field
  if (jmbgField) {
    jmbgField.addEventListener('input', debounce(handleJMBGValidation, 100));
    jmbgField.addEventListener('blur', handleJMBGValidation);
  }

  // Attach event listeners to matični broj field
  if (maticniBrojField) {
    maticniBrojField.addEventListener('input', debounce(handleMaticniBrojValidation, 100));
    maticniBrojField.addEventListener('blur', handleMaticniBrojValidation);
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
