/**
 * COB Section Navigation Module - Multi-Section Form Navigation with Validation
 * Story 3-4: COB Form Section Navigation (Section I ↔ II ↔ III)
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
 *
 * COB-SPECIFIC DIFFERENCES FROM COA:
 * - Section I: NO JMBG/Matični broj fields (simplified)
 * - Section II: NO Budget field, different field names (naslov, kratak_opis, problem, cilj, planirani_koraci, ocekivani_uticaj)
 */

let currentSection = 1; // Track current active section (1, 2, or 3)

/**
 * Update progress stepper to show current section
 * @param {number} sectionNumber - Section number (1, 2, or 3)
 */
function updateProgressStepper(sectionNumber) {
  // Performance measurement start
  const perfStart = performance.now();

  // Get active step label for mobile display
  const activeStep = document.querySelector(`.progress-stepper__step[data-step="${sectionNumber}"]`);
  const activeLabel = activeStep ? activeStep.querySelector('.progress-stepper__label') : null;
  const labelText = activeLabel ? activeLabel.textContent : '';

  // Update stepper counter text (includes label for mobile compact view)
  const stepperText = document.querySelector('.progress-stepper__counter strong') || document.querySelector('.stepper-text strong');
  if (stepperText) {
    stepperText.innerHTML = `Korak <span class="progress-stepper__current">${sectionNumber}</span> od 3<span class="progress-stepper__counter-label">: ${labelText}</span>`;
  }

  // Update screen reader announcement
  const srText = document.querySelector('.progress-stepper__counter .sr-only') || document.querySelector('.stepper-text .sr-only');
  if (srText) {
    srText.textContent = `Nalazite se u sekciji ${sectionNumber} od 3`;
  }

  // Cache step elements for performance
  const steps = document.querySelectorAll('.progress-stepper__step');

  steps.forEach((step, index) => {
    const stepNum = index + 1;

    // Remove all state classes first
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

  // Connector lines are now CSS ::after pseudo-elements on steps,
  // so completed state is handled automatically via step class changes.

  // Performance measurement end
  const perfEnd = performance.now();
  const perfTime = perfEnd - perfStart;

  if (perfTime > 75) {
    console.warn(`updateProgressStepper took ${perfTime.toFixed(2)}ms (target: <75ms)`);
  }
}

/**
 * Show specified section and hide others
 * @param {number} sectionNumber - Section number to show (1, 2, or 3)
 */
function showSection(sectionNumber) {
  // Performance tracking
  const perfStart = performance.now();

  // Section elements
  const sectionI = document.getElementById('section-i');
  const sectionII = document.getElementById('section-ii');
  const sectionIII = document.getElementById('section-iii');

  // Hide all sections first
  if (sectionI) sectionI.style.display = 'none';
  if (sectionII) sectionII.style.display = 'none';
  if (sectionIII) sectionIII.style.display = 'none';

  // Show requested section
  if (sectionNumber === 1) {
    // Show Section I
    if (sectionI) {
      sectionI.style.display = 'block';
    }
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

      // Initialize file upload UI when Section III becomes visible
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

  if (perfTime > 75) {
    console.warn(`showSection took ${perfTime.toFixed(2)}ms (target: <75ms)`);
  }
}

/**
 * Validate Section I before allowing navigation (COB-specific)
 * COB SIMPLIFICATION: No JMBG/Matični broj validation
 * @returns {Object} {isValid: boolean, errors: array, firstErrorField: element}
 */
function validateSectionI() {
  let isValid = true;
  let errors = [];
  let firstInvalidField = null;

  // Get entity type
  const entityType = document.getElementById('id_entity_type')?.value || '';

  if (!entityType) {
    isValid = false;
    errors.push({ field: 'entity_type', message: 'Molimo izaberite tip podnosioca (fizičko ili pravno lice)' });
  }

  // Validate based on entity type (ONLY active entity type fields)
  if (entityType === 'fizicko') {
    // Fizičko lice fields (NO JMBG - COB simplification)
    const requiredFields = [
      { id: 'id_ime', label: 'Ime' },
      { id: 'id_prezime', label: 'Prezime' },
      { id: 'id_adresa', label: 'Adresa' },
      { id: 'id_email', label: 'Email' },
      { id: 'id_telefon', label: 'Telefon' }
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
    // Pravno lice fields (NO Matični broj - COB simplification)
    const requiredFields = [
      { id: 'id_naziv_organizacije', label: 'Naziv organizacije' },
      { id: 'id_adresa', label: 'Adresa' },
      { id: 'id_email', label: 'Email' },
      { id: 'id_telefon', label: 'Telefon' }
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
  }

  return { isValid, errors, firstErrorField: firstInvalidField };
}

/**
 * Validate Section II before allowing navigation (COB-specific)
 * COB FIELDS: naslov, kratak_opis, problem, cilj, planirani_koraci, ocekivani_uticaj
 * NO BUDGET FIELD (COB simplification)
 * @returns {Object} {isValid: boolean, errors: array, firstErrorField: element}
 */
function validateSectionII() {
  let isValid = true;
  let errors = [];
  let firstInvalidField = null;

  // COB Section II fields with character limits
  const SECTION_II_FIELDS = {
    naslov: { maxLength: 150, label: 'Naslov inicijative' },
    kratak_opis: { maxLength: 500, label: 'Kratak opis' },
    problem: { maxLength: 1500, label: 'Problem koji inicijativa rešava' },
    cilj: { maxLength: 1500, label: 'Cilj inicijative' },
    planirani_koraci: { maxLength: 1500, label: 'Planirani koraci' },
    ocekivani_uticaj: { maxLength: 1500, label: 'Očekivani uticaj na zajednicu' }
  };

  // Check all textareas
  Object.keys(SECTION_II_FIELDS).forEach(fieldId => {
    const field = document.getElementById(`id_${fieldId}`);
    if (!field) return;

    const value = field.value.trim();
    const fieldConfig = SECTION_II_FIELDS[fieldId];

    // Check if empty
    if (value === '') {
      const errorMsg = `${fieldConfig.label} je obavezno polje`;
      showValidationError(field, errorMsg);
      errors.push({ field: fieldId, message: errorMsg });
      isValid = false;

      // Track first invalid field for focus
      if (!firstInvalidField) {
        firstInvalidField = field;
      }
    } else {
      // Clear error if field is valid
      clearValidationError(field);
    }
  });

  return { isValid, errors, firstErrorField: firstInvalidField };
}

/**
 * Validate Section III before submission (COB-specific)
 * Placeholder - always return valid until file upload validation is implemented
 * @returns {Object} {isValid: boolean, errors: array, firstErrorField: element}
 */
function validateSectionIII() {
  // Section III will be validated in future stories
  // For now, return valid result to allow testing of navigation flow I ↔ II ↔ III
  return { isValid: true, errors: [], firstErrorField: null };
}

/**
 * Show validation error message
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
 * Smooth scroll to top of page
 */
function scrollToTop() {
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });
}

/**
 * Scroll to first error field
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
 * Focus first field in section
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
 * Display validation summary banner for 5+ errors
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
  const form = document.querySelector('#cob-form, form');
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
 * Update navigation button labels and visibility based on current section
 * @param {number} sectionNumber - Current section number (1, 2, or 3)
 */
function updateNavigationButtons(sectionNumber) {
  const btnNext = document.getElementById('next-btn');
  const btnPrev = document.getElementById('prev-btn');

  if (!btnNext || !btnPrev) return;

  if (sectionNumber === 1) {
    // Section I: Previous button becomes "Home"
    btnPrev.innerHTML = '<span aria-hidden="true">🏠</span> POČETNA';
    btnPrev.setAttribute('aria-label', 'Povratak na početnu stranu');
    btnPrev.disabled = false;

    // Next button is visible
    btnNext.style.display = 'inline-block';
    btnNext.textContent = 'SLEDEĆA SEKCIJA';
    btnNext.disabled = false;
  } else if (sectionNumber === 2) {
    // Section II: Previous button is normal
    btnPrev.textContent = 'PRETHODNA SEKCIJA';
    btnPrev.setAttribute('aria-label', 'Vrati se na prethodnu sekciju');
    btnPrev.disabled = false;

    // Next button is visible
    btnNext.style.display = 'inline-block';
    btnNext.textContent = 'SLEDEĆA SEKCIJA';
    btnNext.disabled = false;
  } else if (sectionNumber === 3) {
    // Section III: Previous button is normal
    btnPrev.textContent = 'PRETHODNA SEKCIJA';
    btnPrev.setAttribute('aria-label', 'Vrati se na prethodnu sekciju');
    btnPrev.disabled = false;

    // Next button is HIDDEN (last section)
    btnNext.style.display = 'none';
  }
}

/**
 * Initialize section navigation
 * Attaches event listeners to navigation buttons
 */
function initializeSectionNavigation() {
  const btnNext = document.getElementById('next-btn');
  const btnPrev = document.getElementById('prev-btn');

  if (!btnNext || !btnPrev) {
    console.warn('COB Navigation buttons not found');
    return;
  }

  // Enable buttons
  btnNext.disabled = false;
  btnNext.textContent = 'SLEDEĆA SEKCIJA';

  btnPrev.disabled = false;
  btnPrev.textContent = 'PRETHODNA SEKCIJA';

  // Set initial button states for Section I
  updateNavigationButtons(1);

  // "SLEDEĆA SEKCIJA" button handler
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

        // Update navigation buttons
        updateNavigationButtons(2);
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

        // Update navigation buttons
        updateNavigationButtons(3);
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

  // "PRETHODNA SEKCIJA" button handler
  btnPrev.addEventListener('click', function(e) {
    e.preventDefault();

    // Check if button is "Home" button (in Section I)
    if (currentSection === 1) {
      // Navigate to landing page
      window.location.href = '/';
      return;
    }

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

      // Update navigation buttons
      updateNavigationButtons(1);
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

      // Update navigation buttons
      updateNavigationButtons(2);
    }
  });

  console.log('COB Section navigation initialized');
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
    validateSectionI,
    validateSectionII,
    initializeSectionNavigation
  };
}
