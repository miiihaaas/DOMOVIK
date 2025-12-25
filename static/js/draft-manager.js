/**
 * Draft Manager - Basic Draft Preservation
 * Story 2.2: Basic draft save/load for entity type switching
 * Story 2.4: Will add advanced features (auto-save 30s, recovery modal, 7-day retention)
 *
 * Scope (Story 2.2):
 * - Basic saveDraft() and loadDraft() functions
 * - Save all form fields to localStorage
 * - Restore form fields from localStorage
 * - Called by entity-type-switcher.js when switching fizičko/pravno
 *
 * Future (Story 2.4):
 * - Auto-save every 30 seconds
 * - Draft recovery modal on page load
 * - 7-day retention with automatic deletion
 * - Visual "Sačuvano" notification
 */

const DRAFT_KEY = 'domovik_coa_draft';

/**
 * Save all form field values to localStorage
 * Called before hiding fields during entity type switch
 */
function saveDraft() {
  const form = document.getElementById('coa-form-section-i');
  if (!form) {
    console.warn('Draft Manager: Form not found');
    return;
  }

  const draftData = {
    entity_type: document.getElementById('id_entity_type')?.value || 'fizicko',
    fizicko: {
      ime: document.getElementById('id_ime')?.value || '',
      prezime: document.getElementById('id_prezime')?.value || '',
      jmbg: document.getElementById('id_jmbg')?.value || ''
    },
    pravno: {
      naziv_organizacije: document.getElementById('id_naziv_organizacije')?.value || '',
      maticni_broj: document.getElementById('id_maticni_broj')?.value || ''
    },
    common: {
      adresa: document.getElementById('id_adresa')?.value || '',
      email: document.getElementById('id_email')?.value || '',
      telefon: document.getElementById('id_telefon')?.value || ''
    },
    timestamp: new Date().toISOString()
  };

  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draftData));
    console.log('Draft saved to localStorage');
    // Story 2.4 will add visual "Sačuvano" notification here
  } catch (error) {
    console.error('Failed to save draft:', error);
  }
}

/**
 * Load form field values from localStorage
 * Called after showing fields during entity type switch
 */
function loadDraft() {
  try {
    const draftJson = localStorage.getItem(DRAFT_KEY);
    if (!draftJson) {
      console.log('No draft found in localStorage');
      return;
    }

    const draftData = JSON.parse(draftJson);

    // Check if draft is fresh (< 7 days old)
    if (draftData.timestamp) {
      const draftAge = Date.now() - new Date(draftData.timestamp).getTime();
      const MAX_AGE = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds

      if (draftAge > MAX_AGE) {
        console.log('Draft too old (>7 days), removing from localStorage');
        localStorage.removeItem(DRAFT_KEY);
        return;
      }
    }

    // Restore entity type
    const entityTypeInput = document.getElementById('id_entity_type');
    if (entityTypeInput && draftData.entity_type) {
      entityTypeInput.value = draftData.entity_type;
    }

    // Restore fizičko lice fields
    if (draftData.fizicko) {
      restoreFieldValue('id_ime', draftData.fizicko.ime);
      restoreFieldValue('id_prezime', draftData.fizicko.prezime);
      restoreFieldValue('id_jmbg', draftData.fizicko.jmbg);
    }

    // Restore pravno lice fields
    if (draftData.pravno) {
      restoreFieldValue('id_naziv_organizacije', draftData.pravno.naziv_organizacije);
      restoreFieldValue('id_maticni_broj', draftData.pravno.maticni_broj);
    }

    // Restore common fields
    if (draftData.common) {
      restoreFieldValue('id_adresa', draftData.common.adresa);
      restoreFieldValue('id_email', draftData.common.email);
      restoreFieldValue('id_telefon', draftData.common.telefon);
    }

    console.log('Draft loaded from localStorage');
  } catch (error) {
    console.error('Failed to load draft:', error);
  }
}

/**
 * Helper function to restore a single field value
 * @param {string} fieldId - DOM element ID
 * @param {string} value - Value to restore
 */
function restoreFieldValue(fieldId, value) {
  const field = document.getElementById(fieldId);
  if (field && value) {
    field.value = value;
  }
}

/**
 * Initialize draft system on page load
 * Story 2.4 will add draft recovery modal here
 */
document.addEventListener('DOMContentLoaded', function() {
  // Story 2.2: Just load draft silently
  // Story 2.4: Show recovery modal if draft exists and is recent
  loadDraft();
});
