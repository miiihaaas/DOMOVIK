/**
 * Team Members Dynamic Table Handler
 * Story 5.1: Form Enhancements - Ostali članovi tima
 *
 * Provides functionality for:
 * - Adding new team member rows
 * - Removing team member rows (minimum 1 row)
 * - Reindexing form fields after removal
 * - Managing delete button states
 * - Collecting team members data for submission
 */

const TeamMembersManager = (function() {
    'use strict';

    // Configuration
    const CONFIG = {
        containerId: 'team-members-container',
        rowClass: 'team-member-row',
        addButtonId: 'add-team-member',
        minRows: 1,
        maxRows: 10
    };

    // State
    let rowCount = 0;
    let initialized = false;

    /**
     * Initialize the team members manager
     */
    function init() {
        if (initialized) return;

        const container = document.getElementById(CONFIG.containerId);
        if (!container) {
            console.warn('TeamMembersManager: Container not found');
            return;
        }

        // Count initial rows
        rowCount = container.querySelectorAll('.' + CONFIG.rowClass).length;

        // If no rows exist, add one
        if (rowCount === 0) {
            addRow();
        }

        // Bind add button
        const addButton = document.getElementById(CONFIG.addButtonId);
        if (addButton) {
            addButton.addEventListener('click', function(e) {
                e.preventDefault();
                addRow();
            });
        }

        // Bind existing delete buttons
        bindDeleteButtons();

        // Update button states
        updateDeleteButtonStates();

        initialized = true;
        console.log('TeamMembersManager initialized with', rowCount, 'rows');
    }

    /**
     * Add a new team member row
     */
    function addRow() {
        if (rowCount >= CONFIG.maxRows) {
            alert('Maksimalan broj članova tima je ' + CONFIG.maxRows + '.');
            return;
        }

        const container = document.getElementById(CONFIG.containerId);
        if (!container) return;

        const newIndex = rowCount;
        const rowHtml = createRowHtml(newIndex);

        // Append to container
        container.insertAdjacentHTML('beforeend', rowHtml);

        rowCount++;

        // Bind delete button for new row
        bindDeleteButtons();
        updateDeleteButtonStates();

        console.log('Added team member row', newIndex);
    }

    /**
     * Remove a team member row
     * @param {number} index - Row index to remove
     */
    function removeRow(index) {
        const container = document.getElementById(CONFIG.containerId);
        if (!container) return;

        const rows = container.querySelectorAll('.' + CONFIG.rowClass);
        if (rows.length <= CONFIG.minRows) {
            console.warn('Cannot remove: minimum rows reached');
            return;
        }

        // Find and remove the row
        const row = container.querySelector('[data-row-index="' + index + '"]');
        if (row) {
            row.remove();
            rowCount--;

            // Reindex remaining rows
            reindexRows();
            updateDeleteButtonStates();

            console.log('Removed team member row', index);
        }
    }

    /**
     * Reindex all rows after removal
     */
    function reindexRows() {
        const container = document.getElementById(CONFIG.containerId);
        if (!container) return;

        const rows = container.querySelectorAll('.' + CONFIG.rowClass);
        rows.forEach(function(row, newIndex) {
            // Update row index data attribute
            row.setAttribute('data-row-index', newIndex);

            // Update input names and IDs
            const inputs = row.querySelectorAll('input');
            inputs.forEach(function(input) {
                const name = input.getAttribute('name');
                const id = input.getAttribute('id');

                if (name) {
                    const newName = name.replace(/\[\d+\]/, '[' + newIndex + ']');
                    input.setAttribute('name', newName);
                }

                if (id) {
                    const newId = id.replace(/_\d+_/, '_' + newIndex + '_');
                    input.setAttribute('id', newId);

                    // Update associated label
                    const label = row.querySelector('label[for="' + id + '"]');
                    if (label) {
                        label.setAttribute('for', newId);
                    }
                }
            });

            // Update delete button
            const deleteBtn = row.querySelector('.delete-team-member');
            if (deleteBtn) {
                deleteBtn.setAttribute('data-index', newIndex);
            }
        });
    }

    /**
     * Update delete button states (disable if only 1 row)
     */
    function updateDeleteButtonStates() {
        const container = document.getElementById(CONFIG.containerId);
        if (!container) return;

        const rows = container.querySelectorAll('.' + CONFIG.rowClass);
        const deleteButtons = container.querySelectorAll('.delete-team-member');

        deleteButtons.forEach(function(btn) {
            if (rows.length <= CONFIG.minRows) {
                btn.disabled = true;
                btn.classList.add('disabled');
                btn.setAttribute('title', 'Minimum 1 član tima je obavezan');
            } else {
                btn.disabled = false;
                btn.classList.remove('disabled');
                btn.setAttribute('title', 'Obriši člana tima');
            }
        });
    }

    /**
     * Bind click handlers to delete buttons
     */
    function bindDeleteButtons() {
        const container = document.getElementById(CONFIG.containerId);
        if (!container) return;

        const deleteButtons = container.querySelectorAll('.delete-team-member');
        deleteButtons.forEach(function(btn) {
            // Clone and replace to remove all existing listeners
            const newBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(newBtn, btn);

            // Add fresh listener
            newBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const index = parseInt(this.getAttribute('data-index'), 10);
                console.log('Delete button clicked for index:', index);
                removeRow(index);
            });
        });
    }

    /**
     * Create HTML for a new row
     * @param {number} index - Row index
     * @returns {string} HTML string
     */
    function createRowHtml(index) {
        return `
            <div class="team-member-row" data-row-index="${index}">
                <div class="form-group">
                    <label for="team_member_${index}_ime_prezime">Ime i prezime</label>
                    <input type="text"
                           class="form-control"
                           id="team_member_${index}_ime_prezime"
                           name="team_members[${index}][ime_prezime]"
                           maxlength="100"
                           placeholder="Ime i prezime člana">
                </div>
                <div class="form-group">
                    <label for="team_member_${index}_email">Email</label>
                    <input type="email"
                           class="form-control"
                           id="team_member_${index}_email"
                           name="team_members[${index}][email]"
                           placeholder="email@example.com">
                </div>
                <div class="form-group">
                    <label for="team_member_${index}_telefon">Telefon</label>
                    <input type="text"
                           class="form-control"
                           id="team_member_${index}_telefon"
                           name="team_members[${index}][telefon]"
                           maxlength="30"
                           placeholder="Broj telefona">
                </div>
                <div class="form-group team-member-actions">
                    <button type="button"
                            class="btn btn-outline-danger delete-team-member"
                            data-index="${index}"
                            title="Obriši člana tima">
                        Obriši
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Get all team members data for submission
     * @returns {Array} Array of team member objects
     */
    function getTeamMembersData() {
        const container = document.getElementById(CONFIG.containerId);
        if (!container) return [];

        const rows = container.querySelectorAll('.' + CONFIG.rowClass);
        const teamMembers = [];

        rows.forEach(function(row) {
            const imePrezime = row.querySelector('input[name*="ime_prezime"]');
            const email = row.querySelector('input[name*="email"]');
            const telefon = row.querySelector('input[name*="telefon"]');

            const member = {
                ime_prezime: imePrezime ? imePrezime.value.trim() : '',
                email: email ? email.value.trim() : '',
                telefon: telefon ? telefon.value.trim() : ''
            };

            // Only include if at least one field has data
            if (member.ime_prezime || member.email || member.telefon) {
                teamMembers.push(member);
            }
        });

        return teamMembers;
    }

    /**
     * Clear all team members data
     */
    function clearAll() {
        const container = document.getElementById(CONFIG.containerId);
        if (!container) return;

        // Remove all rows except one
        const rows = container.querySelectorAll('.' + CONFIG.rowClass);
        rows.forEach(function(row, index) {
            if (index > 0) {
                row.remove();
            } else {
                // Clear the first row
                const inputs = row.querySelectorAll('input');
                inputs.forEach(function(input) {
                    input.value = '';
                });
            }
        });

        rowCount = 1;
        reindexRows();
        updateDeleteButtonStates();
    }

    /**
     * Load team members from data (e.g., from draft)
     * @param {Array} members - Array of member objects
     */
    function loadFromData(members) {
        if (!Array.isArray(members) || members.length === 0) return;

        // Clear existing
        clearAll();

        const container = document.getElementById(CONFIG.containerId);
        if (!container) return;

        // Add rows for each member
        members.forEach(function(member, index) {
            if (index > 0) {
                addRow();
            }

            const row = container.querySelector('[data-row-index="' + index + '"]');
            if (row) {
                const imePrezime = row.querySelector('input[name*="ime_prezime"]');
                const email = row.querySelector('input[name*="email"]');
                const telefon = row.querySelector('input[name*="telefon"]');

                if (imePrezime) imePrezime.value = member.ime_prezime || '';
                if (email) email.value = member.email || '';
                if (telefon) telefon.value = member.telefon || '';
            }
        });
    }

    // Public API
    return {
        init: init,
        addRow: addRow,
        removeRow: removeRow,
        getTeamMembersData: getTeamMembersData,
        clearAll: clearAll,
        loadFromData: loadFromData
    };
})();

// Auto-initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    TeamMembersManager.init();
});
