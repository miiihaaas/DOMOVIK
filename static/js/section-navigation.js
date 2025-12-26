/**
 * Section Navigation Module - Multi-Section Form Navigation with Validation
 * Story 2.6: Task 7-8 - Progress Stepper Update & Section Navigation
 *
 * Features:
 * - Section visibility management (Section I ↔ Section II)
 * - Progress stepper updates ("Sekcija 1 od 3", "Sekcija 2 od 3")
 * - Section II validation before allowing navigation
 * - Integration with character-counter.js for validation
 *
 * NOTE: Full multi-section navigation will be completed in Story 2.7
 * This implementation handles Section I → Section II transition only
 */

let currentSection = 1; // Track current active section

/**
 * Update progress stepper to show current section (Task 7)
 * @param {number} sectionNumber - Section number (1, 2, or 3)
 */
function updateProgressStepper(sectionNumber) {
  // Update stepper text
  const stepperText = document.querySelector('.stepper-text strong');
  if (stepperText) {
    stepperText.textContent = `Sekcija ${sectionNumber} od 3`;
  }

  // Update stepper visual indicators
  const steps = document.querySelectorAll('.stepper-step');
  steps.forEach((step, index) => {
    const stepNum = index + 1;
    if (stepNum === sectionNumber) {
      step.classList.add('active');
    } else if (stepNum < sectionNumber) {
      step.classList.add('completed');
      step.classList.remove('active');
    } else {
      step.classList.remove('active', 'completed');
    }
  });
}

/**
 * Show specified section and hide others (Task 8.10)
 * CODE REVIEW FIX (MEDIUM #3): Simplified to avoid conflicts with entity-type-switcher.js
 * @param {number} sectionNumber - Section number to show
 */
function showSection(sectionNumber) {
  // Hide all sections
  document.querySelectorAll('[id^="section-"]').forEach(section => {
    section.style.display = 'none';
  });

  // Section I is embedded in form, not a separate div - hide entity-type-switcher container
  const entitySwitcher = document.querySelector('.entity-type-switcher');
  const sectionII = document.getElementById('section-ii');

  if (sectionNumber === 1) {
    // Show Section I (entity switcher + fields visible)
    if (entitySwitcher) entitySwitcher.style.display = 'block';
    // entity-type-switcher.js will handle which entity fields to show
    if (sectionII) sectionII.style.display = 'none';
  } else if (sectionNumber === 2) {
    // Show Section II, hide Section I switcher
    if (entitySwitcher) entitySwitcher.style.display = 'none';
    if (sectionII) sectionII.style.display = 'block';

    // CODE REVIEW FIX (MEDIUM #2): Initialize character counters when Section II becomes visible
    if (typeof initializeCharacterCounters === 'function') {
      initializeCharacterCounters();
    }
  }

  // Update current section tracker
  currentSection = sectionNumber;

  // Update progress stepper
  updateProgressStepper(sectionNumber);
}

/**
 * Validate Section II before allowing navigation (Task 8.3-8.8)
 * @returns {boolean} True if all Section II fields are valid
 */
function validateSectionII() {
  let isValid = true;
  let firstInvalidField = null;

  // Character limits from character-counter.js
  const SECTION_II_FIELDS = {
    naslov: 150,
    opis: 500,
    problem: 2000,
    cilj: 1000,
    specifični_ciljevi: 1000,
    ciljne_grupe: 1500,
    aktivnosti: 1500,
    rezultati: 1500
  };

  // Check all textareas (Task 8.4)
  Object.keys(SECTION_II_FIELDS).forEach(fieldId => {
    const field = document.getElementById(`id_${fieldId}`);
    if (!field) return;

    const value = field.value.trim();

    // Check if empty (Task 8.6)
    if (value === '') {
      showValidationError(field, 'Ovo polje je obavezno');
      isValid = false;

      // Track first invalid field for focus (Task 8.8)
      if (!firstInvalidField) {
        firstInvalidField = field;
      }
    } else {
      // Clear error if field is valid
      clearValidationError(field);
    }
  });

  // Check budget field (Task 8.5)
  const budgetField = document.getElementById('id_budžet');
  if (budgetField) {
    const value = budgetField.value.trim();

    if (value === '') {
      showValidationError(budgetField, 'Budžet je obavezan');
      isValid = false;
      if (!firstInvalidField) {
        firstInvalidField = budgetField;
      }
    } else {
      // Validate positive number
      const rawValue = value.replace(/\./g, '').replace(',', '.');
      if (isNaN(rawValue) || parseFloat(rawValue) < 0) {
        showValidationError(budgetField, 'Budžet mora biti pozitivan broj');
        isValid = false;
        if (!firstInvalidField) {
          firstInvalidField = budgetField;
        }
      } else {
        clearValidationError(budgetField);
      }
    }
  }

  // Focus first invalid field (Task 8.8)
  if (!isValid && firstInvalidField) {
    firstInvalidField.focus();
    firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  return isValid;
}

/**
 * Show validation error message (Task 8.7)
 * @param {HTMLElement} field - Input/textarea element
 * @param {string} message - Error message
 */
function showValidationError(field, message) {
  // Try to find existing error element
  let errorElement = document.getElementById(`${field.id}_error`);

  // If not exists, create one
  if (!errorElement) {
    errorElement = document.createElement('div');
    errorElement.id = `${field.id}_error`;
    errorElement.className = 'validation-error';
    errorElement.setAttribute('aria-live', 'polite');
    field.parentElement.appendChild(errorElement);
  }

  errorElement.textContent = message;
  errorElement.style.display = 'block';

  field.setAttribute('aria-invalid', 'true');
  field.classList.add('error');
}

/**
 * Clear validation error message
 * @param {HTMLElement} field - Input/textarea element
 */
function clearValidationError(field) {
  const errorElement = document.getElementById(`${field.id}_error`);
  if (errorElement) {
    errorElement.textContent = '';
    errorElement.style.display = 'none';
  }

  field.setAttribute('aria-invalid', 'false');
  field.classList.remove('error');
}

/**
 * Initialize section navigation (Task 8.1-8.13)
 * Attaches event listeners to navigation buttons
 * CODE REVIEW FIX (HIGH #2): Use specific selectors to avoid conflicts with other buttons
 */
function initializeSectionNavigation() {
  const btnNext = document.querySelector('.form-navigation .btn-primary'); // SLEDEĆA SEKCIJA
  const btnPrev = document.querySelector('.form-navigation .btn-secondary'); // PRETHODNA SEKCIJA

  if (!btnNext || !btnPrev) {
    console.warn('Navigation buttons not found');
    return;
  }

  // Enable buttons (Task 8.1-8.2)
  btnNext.disabled = false;
  btnNext.textContent = 'SLEDEĆA SEKCIJA';

  btnPrev.disabled = false;
  btnPrev.textContent = 'PRETHODNA SEKCIJA';

  // "SLEDEĆA SEKCIJA" button handler (Task 8.6-8.12)
  btnNext.addEventListener('click', function(e) {
    e.preventDefault();

    if (currentSection === 1) {
      // Navigate from Section I to Section II
      showSection(2);
    } else if (currentSection === 2) {
      // Validate Section II before proceeding (Task 8.6)
      if (validateSectionII()) {
        // Validation passed - would navigate to Section III (Story 2.7)
        alert('Section II validation passed! Section III navigation will be implemented in Story 2.7.');
      }
      // If validation failed, errors are shown and focus is on first invalid field
    }
  });

  // "PRETHODNA SEKCIJA" button handler (Task 8.9, 8.13)
  btnPrev.addEventListener('click', function(e) {
    e.preventDefault();

    if (currentSection === 2) {
      // Return to Section I without validation
      showSection(1);
    } else if (currentSection === 1) {
      // Already at first section, do nothing or show message
      console.log('Already at first section');
    }
  });

  console.log('Section navigation initialized');
}

/**
 * Initialize on page load
 */
document.addEventListener('DOMContentLoaded', function() {
  // Initialize section navigation
  initializeSectionNavigation();

  // Start with Section I visible (default)
  updateProgressStepper(1);
});

// Export for testing and external use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    updateProgressStepper,
    showSection,
    validateSectionII,
    initializeSectionNavigation
  };
}
