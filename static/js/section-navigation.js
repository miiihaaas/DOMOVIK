/**
 * Section Navigation Module - Multi-Section Form Navigation with Validation
 * Story 2.6: Task 7-8 - Progress Stepper Update & Section Navigation (Section I ↔ II)
 * Story 2.7: Enhanced navigation with all 3 sections, validation, scroll, ARIA
 *
 * Features:
 * - Section visibility management (Section I ↔ II ↔ III)
 * - Progress stepper updates with enhanced visual states (active, completed, inactive)
 * - Validation before navigation (all 3 sections)
 * - Smooth scroll to top after navigation
 * - Focus management (first field or first error)
 * - Keyboard navigation support
 * - ARIA announcements for screen readers
 * - Integration with draft system (current section persistence)
 * - Validation summary for 5+ errors
 * - Performance optimizations (<100ms navigation)
 */

let currentSection = 1; // Track current active section (1, 2, or 3)

/**
 * Update progress stepper to show current section (Story 2.7 - Enhanced)
 * @param {number} sectionNumber - Section number (1, 2, or 3)
 */
function updateProgressStepper(sectionNumber) {
  // Performance measurement start
  const perfStart = performance.now();

  // Update stepper text
  const stepperText = document.querySelector('.stepper-text strong');
  if (stepperText) {
    stepperText.textContent = `Sekcija ${sectionNumber} od 3`;
  }

  // Update screen reader announcement
  const srText = document.querySelector('.stepper-text .sr-only');
  if (srText) {
    srText.textContent = `Nalazite se u sekciji ${sectionNumber} od 3`;
  }

  // Cache step elements for performance
  // CODE REVIEW FIX (MEDIUM #5 & #8): Use BEM class only
  const steps = document.querySelectorAll('.progress-stepper__step');

  steps.forEach((step, index) => {
    const stepNum = index + 1;

    // Remove all state classes first
    // CODE REVIEW FIX (MEDIUM #5): Use BEM modifiers only
    step.classList.remove('progress-stepper__step--active', 'progress-stepper__step--completed');

    if (stepNum === sectionNumber) {
      // ACTIVE STATE: Current section
      step.classList.add('progress-stepper__step--active');
      step.setAttribute('aria-current', 'step');
      step.setAttribute('aria-disabled', 'false');
    } else if (stepNum < sectionNumber) {
      // COMPLETED STATE: Previous sections
      step.classList.add('progress-stepper__step--completed');
      step.removeAttribute('aria-current');
      step.setAttribute('aria-disabled', 'false'); // Can navigate back
    } else {
      // INACTIVE STATE: Future sections
      step.removeAttribute('aria-current');
      step.setAttribute('aria-disabled', 'true'); // Cannot skip ahead
    }
  });

  // Update connector lines (tirkizna for completed sections)
  // CODE REVIEW FIX (MEDIUM #8): Use BEM class only
  const connectors = document.querySelectorAll('.progress-stepper__connector');
  connectors.forEach((connector, index) => {
    const connectorAfterStep = index + 1; // Connector after step 1 is index 0

    if (connectorAfterStep < sectionNumber) {
      connector.classList.add('progress-stepper__connector--completed');
    } else {
      connector.classList.remove('progress-stepper__connector--completed');
    }
  });

  // Performance measurement end
  const perfEnd = performance.now();
  const perfTime = perfEnd - perfStart;

  // CODE REVIEW FIX (LOW #10): Adjusted threshold to 75ms (less aggressive, NFR5 target is <100ms total)
  // Log if exceeds 75ms threshold (target is <100ms for full navigation)
  if (perfTime > 75) {
    console.warn(`updateProgressStepper took ${perfTime.toFixed(2)}ms (target: <75ms)`);
  }
}

/**
 * Show specified section and hide others (Story 2.7 - Enhanced for all 3 sections)
 * @param {number} sectionNumber - Section number to show (1, 2, or 3)
 */
function showSection(sectionNumber) {
  // Performance tracking
  const perfStart = performance.now();

  // Section elements
  const entitySwitcher = document.querySelector('.entity-type-switcher');
  const sectionII = document.getElementById('section-ii');
  const sectionIII = document.getElementById('section-iii');

  // Hide all sections first
  if (entitySwitcher) entitySwitcher.style.display = 'none';
  if (sectionII) sectionII.style.display = 'none';
  if (sectionIII) sectionIII.style.display = 'none';

  // Show requested section
  if (sectionNumber === 1) {
    // Show Section I (entity switcher + fields visible)
    if (entitySwitcher) {
      entitySwitcher.style.display = 'block';
    }
    // entity-type-switcher.js will handle which entity fields to show
  } else if (sectionNumber === 2) {
    // Show Section II
    if (sectionII) {
      sectionII.style.display = 'block';

      // Initialize character counters when Section II becomes visible
      if (typeof initializeCharacterCounters === 'function') {
        initializeCharacterCounters();
      }
    }
  } else if (sectionNumber === 3) {
    // Show Section III
    if (sectionIII) {
      sectionIII.style.display = 'block';

      // Initialize file upload UI when Section III becomes visible (Story 2.9)
      if (typeof initializeFileUploads === 'function') {
        initializeFileUploads();
      }
    }
  }

  // Update current section tracker
  currentSection = sectionNumber;

  // Update progress stepper
  updateProgressStepper(sectionNumber);

  // Performance tracking end
  const perfEnd = performance.now();
  const perfTime = perfEnd - perfStart;

  // CODE REVIEW FIX (LOW #10): Adjusted threshold to 75ms
  // Log if exceeds 75ms (full navigation target is <100ms)
  if (perfTime > 75) {
    console.warn(`showSection took ${perfTime.toFixed(2)}ms (target: <75ms)`);
  }
}

/**
 * Validate Section II before allowing navigation (Task 8.3-8.8)
 * CODE REVIEW FIX (HIGH #3): Return object format matching validateSectionI()
 * @returns {Object} {isValid: boolean, errors: array, firstErrorField: element}
 */
function validateSectionII() {
  let isValid = true;
  let errors = [];
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

  // Field labels for error messages
  const FIELD_LABELS = {
    naslov: 'Naslov projekta',
    opis: 'Kratak opis projekta',
    problem: 'Problem koji projekat rešava',
    cilj: 'Cilj projekta',
    specifični_ciljevi: 'Specifični ciljevi',
    ciljne_grupe: 'Ciljne grupe',
    aktivnosti: 'Aktivnosti projekta',
    rezultati: 'Očekivani rezultati'
  };

  // Check all textareas (Task 8.4)
  Object.keys(SECTION_II_FIELDS).forEach(fieldId => {
    const field = document.getElementById(`id_${fieldId}`);
    if (!field) return;

    const value = field.value.trim();

    // Check if empty (Task 8.6)
    if (value === '') {
      const errorMsg = `${FIELD_LABELS[fieldId]} je obavezno polje`;
      showValidationError(field, errorMsg);
      errors.push({ field: fieldId, message: errorMsg });
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
  const budgetField = document.getElementById('id_budžet'); // HTML template uses diacritic (ž)
  if (budgetField) {
    const value = budgetField.value.trim();

    if (value === '') {
      const errorMsg = 'Budžet je obavezan';
      showValidationError(budgetField, errorMsg);
      errors.push({ field: 'budzet', message: errorMsg });
      isValid = false;
      if (!firstInvalidField) {
        firstInvalidField = budgetField;
      }
    } else {
      // Validate positive number
      const rawValue = value.replace(/\./g, '').replace(',', '.');
      if (isNaN(rawValue) || parseFloat(rawValue) < 0) {
        const errorMsg = 'Budžet mora biti pozitivan broj';
        showValidationError(budgetField, errorMsg);
        errors.push({ field: 'budzet', message: errorMsg });
        isValid = false;
        if (!firstInvalidField) {
          firstInvalidField = budgetField;
        }
      } else {
        clearValidationError(budgetField);
      }
    }
  }

  return { isValid, errors, firstErrorField: firstInvalidField };
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
 * Validate Section I before allowing navigation (Story 2.7 - Task 5)
 * @returns {Object} {isValid: boolean, errors: array, firstErrorField: element}
 */
function validateSectionI() {
  let isValid = true;
  let errors = [];
  let firstInvalidField = null;

  // Get entity type
  const entityType = document.getElementById('id_entity_type')?.value || '';

  // DEBUG: Log entity type for troubleshooting
  console.log('[validateSectionI] Entity type:', entityType);

  if (!entityType) {
    isValid = false;
    errors.push({ field: 'entity_type', message: 'Molimo izaberite tip podnosioca (fizičko ili pravno lice)' });
  }

  // Validate based on entity type (ONLY active entity type fields)
  if (entityType === 'fizicko') {
    // Fizičko lice fields
    const requiredFields = [
      { id: 'id_ime', label: 'Ime' },
      { id: 'id_prezime', label: 'Prezime' },
      { id: 'id_adresa', label: 'Adresa' },
      { id: 'id_email', label: 'Email' },
      { id: 'id_telefon', label: 'Telefon' },
      { id: 'id_jmbg', label: 'JMBG' }
    ];

    requiredFields.forEach(fieldDef => {
      const field = document.getElementById(fieldDef.id);
      if (!field || field.value.trim() === '') {
        showValidationError(field, `${fieldDef.label} je obavezno polje`);
        errors.push({ field: fieldDef.id, message: `${fieldDef.label} je obavezno` });
        isValid = false;

        if (!firstInvalidField) {
          firstInvalidField = field;
        }
      } else {
        clearValidationError(field);
      }
    });
  } else if (entityType === 'pravno') {
    // Pravno lice fields
    const requiredFields = [
      { id: 'id_naziv_organizacije', label: 'Naziv organizacije' },
      { id: 'id_adresa', label: 'Adresa' },
      { id: 'id_email', label: 'Email' },
      { id: 'id_telefon', label: 'Telefon' },
      { id: 'id_maticni_broj', label: 'Matični broj' }
    ];

    // DEBUG: Log pravno validation
    console.log('[validateSectionI] Validating PRAVNO lice fields...');

    requiredFields.forEach(fieldDef => {
      const field = document.getElementById(fieldDef.id);
      const fieldValue = field ? field.value.trim() : null;

      // DEBUG: Log each field check
      console.log(`[validateSectionI] Field ${fieldDef.id}: exists=${!!field}, value="${fieldValue}"`);

      if (!field || field.value.trim() === '') {
        showValidationError(field, `${fieldDef.label} je obavezno polje`);
        errors.push({ field: fieldDef.id, message: `${fieldDef.label} je obavezno` });
        isValid = false;

        if (!firstInvalidField) {
          firstInvalidField = field;
        }
      } else {
        clearValidationError(field);
      }
    });

    // DEBUG: Log validation result
    console.log('[validateSectionI] PRAVNO validation result:', { isValid, errorCount: errors.length });
  }

  return { isValid, errors, firstErrorField: firstInvalidField };
}

/**
 * Validate Section III before submission (Story 2.7 - Task 5.6-5.9)
 * CODE REVIEW FIX (MEDIUM #4): Placeholder - always return valid until Story 2.10
 * @returns {Object} {isValid: boolean, errors: array, firstErrorField: element}
 */
function validateSectionIII() {
  // Section III will be implemented in Story 2.10 (file uploads, consent checkboxes)
  // For now, return valid result to allow testing of navigation flow I ↔ II ↔ III
  // IMPORTANT: This will be replaced with real validation in Story 2.10
  return { isValid: true, errors: [], firstErrorField: null };
}

/**
 * Smooth scroll to top of page (Story 2.7 - Task 6.1)
 */
function scrollToTop() {
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });
}

/**
 * Scroll to first error field (Story 2.7 - Task 6.3)
 * @param {HTMLElement} errorField - First invalid field element
 */
function scrollToFirstError(errorField) {
  if (errorField) {
    errorField.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    });

    // Focus after scroll animation completes
    setTimeout(() => {
      errorField.focus();
    }, 300);
  }
}

/**
 * Focus first field in section (Story 2.7 - Task 6.2)
 * @param {number} sectionNumber - Section number (1, 2, or 3)
 */
function focusFirstField(sectionNumber) {
  let firstField = null;

  if (sectionNumber === 1) {
    // Section I: First visible entity field (depends on fizičko/pravno)
    const entityType = document.getElementById('id_entity_type')?.value || 'fizicko';
    if (entityType === 'fizicko') {
      firstField = document.getElementById('id_ime');
    } else {
      firstField = document.getElementById('id_naziv_organizacije');
    }
  } else if (sectionNumber === 2) {
    // Section II: First textarea (naslov)
    firstField = document.getElementById('id_naslov');
  } else if (sectionNumber === 3) {
    // Section III: First file upload or consent checkbox
    firstField = document.querySelector('#section-iii input, #section-iii textarea');
  }

  if (firstField) {
    firstField.focus();
  }
}

/**
 * Display validation summary banner for 5+ errors (Story 2.7 - Task 12.2-12.4)
 * @param {Array} errors - Array of error objects
 */
function displayValidationSummary(errors) {
  const errorCount = errors.length;
  if (errorCount === 0) return;

  // Remove existing summary if present
  const existingSummary = document.querySelector('.validation-summary');
  if (existingSummary) {
    existingSummary.remove();
  }

  // Create summary banner
  const summaryHTML = `
    <div class="validation-summary" role="alert" aria-live="assertive">
      <div class="validation-summary__header">
        <strong>⚠️ Molimo popunite sva obavezna polja</strong>
        <p>Ukupno grešaka: ${errorCount}</p>
      </div>
      ${errorCount > 5 ? `
        <button type="button" class="validation-summary__toggle" id="toggle-errors" aria-expanded="false">
          Prikaži sve greške
        </button>
        <div class="validation-summary__errors" id="all-errors" style="display: none;">
          <ul>
            ${errors.map(err => `<li>${err.message}</li>`).join('')}
          </ul>
        </div>
      ` : `
        <div class="validation-summary__errors">
          <ul>
            ${errors.map(err => `<li>${err.message}</li>`).join('')}
          </ul>
        </div>
      `}
    </div>
  `;

  // Insert at top of form
  const form = document.querySelector('#coa-form-section-i, form');
  if (form) {
    form.insertAdjacentHTML('afterbegin', summaryHTML);

    // Add toggle handler for 5+ errors
    if (errorCount > 5) {
      const toggleBtn = document.getElementById('toggle-errors');
      const errorsList = document.getElementById('all-errors');

      if (toggleBtn && errorsList) {
        toggleBtn.addEventListener('click', () => {
          const isExpanded = toggleBtn.getAttribute('aria-expanded') === 'true';
          toggleBtn.setAttribute('aria-expanded', !isExpanded);
          errorsList.style.display = isExpanded ? 'none' : 'block';
          toggleBtn.textContent = isExpanded ? 'Prikaži sve greške' : 'Sakrij greške';
        });
      }
    }

    // Scroll to summary
    const summary = document.querySelector('.validation-summary');
    if (summary) {
      summary.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
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

  // "SLEDEĆA SEKCIJA" button handler (Story 2.7 - Enhanced)
  btnNext.addEventListener('click', function(e) {
    e.preventDefault();

    // Performance tracking start
    const navStart = performance.now();

    let validationResult = null;

    if (currentSection === 1) {
      // Validate Section I before proceeding
      validationResult = validateSectionI();

      if (validationResult.isValid) {
        // Validation passed - navigate to Section II
        // Save draft before navigation (Task 11)
        if (typeof saveDraft === 'function') {
          saveDraft();
        }

        showSection(2);

        // Smooth scroll to top (Task 6)
        scrollToTop();

        // Focus first field after delay
        setTimeout(() => {
          focusFirstField(2);
        }, 200);
      } else {
        // Validation failed - show errors
        displayValidationSummary(validationResult.errors);

        // Scroll to first error field
        if (validationResult.firstErrorField) {
          scrollToFirstError(validationResult.firstErrorField);
        }
      }
    } else if (currentSection === 2) {
      // Validate Section II before proceeding
      // CODE REVIEW FIX (HIGH #2): Use new object return format and displayValidationSummary()
      const validationResult = validateSectionII();

      if (validationResult.isValid) {
        // Validation passed - navigate to Section III
        // Save draft before navigation
        if (typeof saveDraft === 'function') {
          saveDraft();
        }

        showSection(3);

        // Smooth scroll to top
        scrollToTop();

        // Focus first field after delay
        setTimeout(() => {
          focusFirstField(3);
        }, 200);
      } else {
        // Validation failed - show errors
        displayValidationSummary(validationResult.errors);

        // Scroll to first error field
        if (validationResult.firstErrorField) {
          scrollToFirstError(validationResult.firstErrorField);
        }
      }
    } else if (currentSection === 3) {
      // Already at last section - this button should be hidden or disabled
      console.log('Already at last section - use PODNESI button');
    }

    // Performance tracking end
    const navEnd = performance.now();
    const navTime = navEnd - navStart;

    // Log if exceeds 100ms threshold (NFR5)
    if (navTime > 100) {
      console.warn(`Navigation took ${navTime.toFixed(2)}ms (target: <100ms)`);
    }
  });

  // "PRETHODNA SEKCIJA" button handler (Story 2.7 - Enhanced)
  btnPrev.addEventListener('click', function(e) {
    e.preventDefault();

    // No validation required for backward navigation
    if (currentSection === 2) {
      // Return to Section I
      // Save draft before navigation
      if (typeof saveDraft === 'function') {
        saveDraft();
      }

      showSection(1);

      // Smooth scroll to top
      scrollToTop();

      // Focus first field after delay
      setTimeout(() => {
        focusFirstField(1);
      }, 200);
    } else if (currentSection === 3) {
      // Return to Section II
      // Save draft before navigation
      if (typeof saveDraft === 'function') {
        saveDraft();
      }

      showSection(2);

      // Smooth scroll to top
      scrollToTop();

      // Focus first field after delay
      setTimeout(() => {
        focusFirstField(2);
      }, 200);
    } else if (currentSection === 1) {
      // Already at first section, do nothing
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
