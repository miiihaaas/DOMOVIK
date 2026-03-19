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

  // Initialize required fields based on current entity type (fix for hidden required fields)
  const initialEntityType = entityTypeInput.value || 'fizicko';
  if (initialEntityType === 'fizicko') {
    toggleRequiredFields(fizickoFields, true);
    toggleRequiredFields(pravnoFields, false);
  } else {
    toggleRequiredFields(pravnoFields, true);
    toggleRequiredFields(fizickoFields, false);
  }

  switcherButtons.forEach(button => {
    button.addEventListener('click', function() {
      const entityType = this.dataset.entity;

      // Race condition prevention (Story 2.4 - Task 4.4)
      // Clear pending auto-save timeout before manual save during entity switch
      if (window.autoSaveTimeout) {
        clearTimeout(window.autoSaveTimeout);
      }

      // Save current form data to draft BEFORE switching (Story 2.4 integration point)
      if (typeof saveDraft === 'function') {
        saveDraft();
      }

      // Clear ALL validation errors BEFORE entity type switch (Story 2.3)
      if (window.RealTimeValidator && typeof window.RealTimeValidator.clearAllValidationErrors === 'function') {
        window.RealTimeValidator.clearAllValidationErrors();
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

      // CODE REVIEW FIX: REMOVED loadDraft() call - causes race condition
      // loadDraft() restore-uje entity_type nazad na staru vrednost iz draft-a
      // Entity switcher već čisti/pokazuje prava polja, ne treba loadDraft()
      // Draft će biti restore-ovan samo na cold start (Draft Recovery Modal)

      // REMOVED: Restore previously saved data for the newly active entity type
      // if (typeof loadDraft === 'function') {
      //   loadDraft();
      // }

      // Re-validate visible fields AFTER entity switch completes (Story 2.3)
      if (window.RealTimeValidator && typeof window.RealTimeValidator.revalidateVisibleFields === 'function') {
        window.RealTimeValidator.revalidateVisibleFields();
      }
    });
  });
});
