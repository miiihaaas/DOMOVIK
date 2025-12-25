/**
 * Entity Type Switcher Logic
 * Story 2.2: COA Form Section I - Dynamic Fizičko/Pravno lice field switching
 *
 * Features:
 * - Toggle between fizičko and pravno lice forms
 * - Show/hide appropriate field groups
 * - Update hidden entity_type input value
 * - Integration with draft system (Story 2.4)
 */

document.addEventListener('DOMContentLoaded', function() {
  const switcherButtons = document.querySelectorAll('.switcher-btn');
  const entityTypeInput = document.getElementById('id_entity_type');
  const fizickoFields = document.getElementById('fizicko-fields');
  const pravnoFields = document.getElementById('pravno-fields');

  // Validate required DOM elements exist
  if (!entityTypeInput || !fizickoFields || !pravnoFields) {
    console.error('Entity switcher: Required DOM elements not found');
    return;
  }

  switcherButtons.forEach(button => {
    button.addEventListener('click', function() {
      const entityType = this.dataset.entity;

      // Save current form data to draft BEFORE switching (Story 2.4 integration point)
      if (typeof saveDraft === 'function') {
        saveDraft();
      }

      // Update active button state
      switcherButtons.forEach(btn => btn.classList.remove('active'));
      this.classList.add('active');

      // Update hidden input value
      entityTypeInput.value = entityType;

      // Show/hide appropriate field groups
      if (entityType === 'fizicko') {
        fizickoFields.classList.add('active');
        pravnoFields.classList.remove('active');

        // Enable/disable required attributes for proper validation
        toggleRequiredFields(fizickoFields, true);
        toggleRequiredFields(pravnoFields, false);

      } else if (entityType === 'pravno') {
        pravnoFields.classList.add('active');
        fizickoFields.classList.remove('active');

        toggleRequiredFields(pravnoFields, true);
        toggleRequiredFields(fizickoFields, false);
      }

      // Restore previously saved data for the newly active entity type (Story 2.4 integration)
      if (typeof loadDraft === 'function') {
        loadDraft();
      }
    });
  });

  /**
   * Toggle required attribute on form fields
   * @param {HTMLElement} container - Parent element containing form fields
   * @param {boolean} isRequired - Whether fields should be required
   */
  function toggleRequiredFields(container, isRequired) {
    const inputs = container.querySelectorAll('input, textarea');
    inputs.forEach(input => {
      if (isRequired) {
        input.setAttribute('required', 'required');
      } else {
        input.removeAttribute('required');
      }
    });
  }
});
