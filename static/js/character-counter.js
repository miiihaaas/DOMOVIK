/**
 * Character Counter Module - Real-Time Character Counting & Overflow Management
 * Story 2.6: COA Form Section II - Project Data with Character Management
 * Story 3.1: Made application-agnostic to support both COA and COB forms
 *
 * Features:
 * - Real-time character counting (< 100ms performance - NFR5)
 * - Character overflow highlighting (green valid / red overflow)
 * - Serbian error messages for overflow
 * - ARIA live regions for screen reader announcements
 * - Vanilla JavaScript ES6+ (no frameworks)
 * - Application-agnostic: Detects COA vs COB and uses appropriate limits
 *
 * Performance Optimization:
 * - Uses requestAnimationFrame for smooth 60fps updates
 * - Throttling if needed to maintain <100ms response
 * - Avoids DOM thrashing: batch reads, then batch writes
 */

// Character limits object per application type (Story 3.1)
const CHAR_LIMITS_COA = {
  naslov: 150,
  opis: 500,
  problem: 2000,
  cilj: 1000,
  specifični_ciljevi: 1000,
  ciljne_grupe: 1500,
  aktivnosti: 1500,
  rezultati: 1500
};

const CHAR_LIMITS_COB = {
  naslov: 150,
  kratak_opis: 500,
  problem: 1500,
  cilj: 1500,
  planirani_koraci: 1500,
  ocekivani_uticaj: 1500
};

/**
 * Get character limits based on application type (Story 3.1)
 * @returns {Object} CHAR_LIMITS object for current application
 */
function getCharLimits() {
  const appType = document.body.dataset.applicationType || 'COA';
  return appType === 'COB' ? CHAR_LIMITS_COB : CHAR_LIMITS_COA;
}

// For backward compatibility
const CHAR_LIMITS = getCharLimits();

/**
 * Initialize character counters for all Section II textareas (Task 2.3)
 * Story 3.1: Now application-agnostic, uses getCharLimits()
 * Finds all textareas, attaches input listeners for real-time updates
 */
function initializeCharacterCounters() {
  const charLimits = getCharLimits();
  Object.keys(charLimits).forEach(fieldId => {
    const textarea = document.getElementById(`id_${fieldId}`);
    if (!textarea) {
      console.warn(`Character Counter: Textarea id_${fieldId} nije pronađena`);
      return;
    }

    const maxLength = charLimits[fieldId];
    const counterElement = document.querySelector(`.character-counter[data-field="${fieldId}"]`);

    if (!counterElement) {
      console.warn(`Character Counter: Counter element za ${fieldId} nije pronađen`);
      return;
    }

    // Initialize counter display with zero state (Task 2.4)
    updateCharacterCount(fieldId, 0, maxLength);

    // Attach 'input' event for real-time updates (Task 2.6)
    // Fires on every keystroke for instant feedback
    textarea.addEventListener('input', function() {
      const currentLength = textarea.value.length;

      // Use requestAnimationFrame for smooth visual updates (Performance - Task 2.7)
      requestAnimationFrame(() => {
        updateCharacterCount(fieldId, currentLength, maxLength);
        handleCharacterOverflow(fieldId, textarea.value, maxLength);
      });
    });

    // Initialize with current value if textarea has content (e.g., from draft load)
    if (textarea.value) {
      const currentLength = textarea.value.length;
      updateCharacterCount(fieldId, currentLength, maxLength);
      handleCharacterOverflow(fieldId, textarea.value, maxLength);
    }
  });

  console.log('Character counters initialized for Section II');
}

/**
 * Update character count display (Task 2.4-2.9)
 * CODE REVIEW FIX (MEDIUM #4): Added performance measurement in development mode
 * @param {string} fieldId - Field identifier (e.g., 'naslov')
 * @param {number} currentLength - Current text length
 * @param {number} maxLength - Maximum allowed length
 */
function updateCharacterCount(fieldId, currentLength, maxLength) {
  // Performance measurement (development mode only - CODE REVIEW FIX MEDIUM #4)
  const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  const startTime = isDevelopment ? performance.now() : 0;

  const counterElement = document.querySelector(`.character-counter[data-field="${fieldId}"]`);
  if (!counterElement) return;

  // Display format: "currentLength/maxLength" (Task 2.5)
  // Compact format (no spaces, no "karaktera" label) - DECISION from Dev Notes
  const displayText = `${currentLength}/${maxLength}`;

  counterElement.textContent = displayText;

  // Update color and style (Task 2.8)
  if (currentLength > maxLength) {
    // Overflow state - RED
    counterElement.style.color = '#DC2626'; // Red (Tailwind red-600)
    counterElement.style.fontWeight = 'bold';
    counterElement.classList.add('character-counter--error');
  } else {
    // Valid state - GRAY
    counterElement.style.color = '#6B7280'; // Neutral gray (Tailwind gray-500)
    counterElement.style.fontWeight = 'normal';
    counterElement.classList.remove('character-counter--error');
  }

  // Update ARIA live region for screen readers (Task 2.9)
  counterElement.setAttribute('aria-live', 'polite');

  // Performance check (development mode only - CODE REVIEW FIX MEDIUM #4)
  if (isDevelopment) {
    const duration = performance.now() - startTime;
    if (duration > 100) {
      console.warn(`⚠️ Character counter slow for ${fieldId}: ${duration.toFixed(2)}ms (requirement: <100ms)`);
    }
  }
}

/**
 * Handle character overflow highlighting (Task 3.1-3.11)
 * Displays green valid / red overflow text preview BELOW textarea
 * @param {string} fieldId - Field identifier
 * @param {string} text - Current textarea value
 * @param {number} maxLength - Maximum allowed length
 */
function handleCharacterOverflow(fieldId, text, maxLength) {
  const previewElement = document.querySelector(`.character-overflow-preview[data-field="${fieldId}"]`);
  const errorElement = document.querySelector(`.character-error-message[data-field="${fieldId}"]`);

  if (!previewElement) return;

  // Task 3.2: Check if text exceeds limit
  if (text.length > maxLength) {
    // Task 3.3-3.4: Split text into valid and overflow portions
    const validText = text.substring(0, maxLength);
    const overflowText = text.substring(maxLength);

    // Task 3.5: Create preview HTML with green/red highlighting
    // SECURITY: Use textContent to prevent XSS, then wrap with spans
    const validSpan = document.createElement('span');
    validSpan.className = 'text-valid';
    validSpan.textContent = validText;

    const overflowSpan = document.createElement('span');
    overflowSpan.className = 'text-overflow';
    overflowSpan.textContent = overflowText;

    // Task 3.6: Inject preview BELOW textarea
    previewElement.innerHTML = '';
    previewElement.appendChild(validSpan);
    previewElement.appendChild(overflowSpan);
    previewElement.style.display = 'block';

    // Task 4: Show overflow error message
    const excessCount = text.length - maxLength;
    showOverflowError(fieldId, excessCount);
  } else {
    // Task 3.10: Clear preview when user fixes overflow
    previewElement.innerHTML = '';
    previewElement.style.display = 'none';

    // Clear error message (Task 4.7)
    clearOverflowError(fieldId);
  }
}

/**
 * Show overflow error message (Task 4.1-4.8)
 * Displays Serbian error message with excess character count
 * @param {string} fieldId - Field identifier
 * @param {number} excessCount - Number of excess characters
 */
function showOverflowError(fieldId, excessCount) {
  const errorElement = document.querySelector(`.character-error-message[data-field="${fieldId}"]`);
  if (!errorElement) return;

  // Task 4.3: Generate Serbian error message
  const message = `Tekst je predugačak za ${excessCount} karaktera. Molimo skratite crveni deo.`;

  // Task 4.4: Display error message
  errorElement.textContent = message;

  // Task 4.6: Add ARIA attribute for screen readers
  errorElement.setAttribute('role', 'alert');

  // Show error message
  errorElement.style.display = 'block';
}

/**
 * Clear overflow error message (Task 4.7, 4.9)
 * @param {string} fieldId - Field identifier
 */
function clearOverflowError(fieldId) {
  const errorElement = document.querySelector(`.character-error-message[data-field="${fieldId}"]`);
  if (!errorElement) return;

  errorElement.textContent = '';
  errorElement.style.display = 'none';
}

/**
 * Budget Field Validation & Formatting (Task 5)
 * Serbian format: 1.000.000,00 (dot for thousands, comma for decimals)
 */

/**
 * Validate budget field - positive numbers only (Task 5.1-5.6)
 * @returns {boolean} True if valid, false otherwise
 */
function validateBudgetField() {
  const budgetField = document.getElementById('id_budžet');
  if (!budgetField) return true;

  const value = budgetField.value.trim();

  // Check if empty (Task 5.2 - required field)
  if (value === '') {
    showFieldError(budgetField, 'Budžet je obavezan');
    return false;
  }

  // Remove thousand separators for validation (Task 5.10 - accept both formatted and unformatted)
  // Serbian format: 1.000.000,00 → 1000000.00
  const rawValue = value.replace(/\./g, '').replace(',', '.');

  // Check if numeric (Task 5.5)
  if (isNaN(rawValue)) {
    showFieldError(budgetField, 'Molimo unesite validan broj');
    return false;
  }

  // Check if negative (Task 5.4)
  if (parseFloat(rawValue) < 0) {
    showFieldError(budgetField, 'Budžet mora biti pozitivan broj');
    return false;
  }

  // Valid - clear error (Task 5.6)
  clearFieldError(budgetField);
  return true;
}

/**
 * Format budget field with thousand separators (Task 5.8, 5.14)
 * NOTE: Disabled for type="number" fields as browsers don't accept locale-formatted values
 * The browser handles number display natively for type="number" inputs
 */
function formatBudgetField() {
  const budgetField = document.getElementById('id_budžet');
  if (!budgetField) return;

  // Skip formatting for type="number" fields - browser handles this natively
  // Serbian locale formatting (1.000,00) is incompatible with type="number" which expects dots for decimals
  if (budgetField.type === 'number') {
    return;
  }

  const rawValue = budgetField.value.replace(/\./g, '').replace(',', '.');

  if (!isNaN(rawValue) && rawValue !== '') {
    // Serbian locale: sr-RS (Task 5.8)
    const formatted = new Intl.NumberFormat('sr-RS', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(parseFloat(rawValue));

    budgetField.value = formatted;
  }
}

/**
 * Remove formatting on focus for easy editing (Task 5.9, 5.15)
 * NOTE: Disabled for type="number" fields
 */
function unformatBudgetField() {
  const budgetField = document.getElementById('id_budžet');
  if (!budgetField) return;

  // Skip for type="number" fields - they don't have locale formatting
  if (budgetField.type === 'number') {
    return;
  }

  // Remove thousand separators (dots) and replace decimal comma with dot
  const rawValue = budgetField.value.replace(/\./g, '').replace(',', '.');

  if (!isNaN(rawValue)) {
    budgetField.value = rawValue;
  }
}

/**
 * Show field error message
 * @param {HTMLElement} field - Input field element
 * @param {string} message - Error message to display
 */
function showFieldError(field, message) {
  const errorElement = document.getElementById(`${field.id}_error`);
  if (!errorElement) return;

  errorElement.textContent = message;
  errorElement.style.display = 'block';
  errorElement.setAttribute('aria-live', 'polite');

  field.setAttribute('aria-invalid', 'true');
  field.classList.add('error');
}

/**
 * Clear field error message
 * @param {HTMLElement} field - Input field element
 */
function clearFieldError(field) {
  const errorElement = document.getElementById(`${field.id}_error`);
  if (!errorElement) return;

  errorElement.textContent = '';
  errorElement.style.display = 'none';

  field.setAttribute('aria-invalid', 'false');
  field.classList.remove('error');
}

/**
 * Initialize budget field validation and formatting (Task 5.7-5.15)
 */
function initializeBudgetField() {
  const budgetField = document.getElementById('id_budžet');
  if (!budgetField) return;

  // Attach blur listener for formatting (Task 5.8)
  budgetField.addEventListener('blur', function() {
    if (validateBudgetField()) {
      formatBudgetField();
    }
  });

  // Attach focus listener to remove formatting (Task 5.9)
  budgetField.addEventListener('focus', unformatBudgetField);

  // Attach input listener for real-time validation
  budgetField.addEventListener('input', validateBudgetField);

  console.log('Budget field validation initialized');
}

/**
 * Initialize character counter system on page load
 * Called by DOMContentLoaded event or after draft load
 */
document.addEventListener('DOMContentLoaded', function() {
  // Only initialize if Section II exists on the page
  const sectionII = document.getElementById('section-ii');
  if (sectionII) {
    initializeCharacterCounters();
    initializeBudgetField();
  }
});

// Export functions for testing and draft-manager integration
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    CHAR_LIMITS_COA,
    CHAR_LIMITS_COB,
    getCharLimits,
    initializeCharacterCounters,
    updateCharacterCount,
    handleCharacterOverflow,
    showOverflowError,
    clearOverflowError
  };
}
