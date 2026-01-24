/**
 * Duration Calculator for Project Dates
 * Story 5.2: Automatic calculation of project duration from start/end dates
 *
 * Features:
 * - Real-time duration calculation
 * - Validation of date range (end >= start)
 * - Serbian month pluralization (mesec/meseca/meseci)
 * - Minimum 1 month duration
 */

(function() {
    'use strict';

    // DOM Elements
    const startDateInput = document.getElementById('id_datum_startovanja');
    const endDateInput = document.getElementById('id_datum_zavrsetka');
    const durationDisplay = document.getElementById('trajanje_projekta');
    const endDateError = document.getElementById('id_datum_zavrsetka_error');

    // Exit if elements don't exist (not on COA form)
    if (!startDateInput || !endDateInput || !durationDisplay) {
        return;
    }

    /**
     * Calculate duration in months between two dates.
     * Rounds up if there are extra days.
     *
     * @param {Date} startDate - Start date
     * @param {Date} endDate - End date
     * @returns {number} - Duration in months (minimum 1)
     */
    function calculateMonths(startDate, endDate) {
        if (!startDate || !endDate) {
            return 0;
        }

        // Calculate difference in months
        let months = (endDate.getFullYear() - startDate.getFullYear()) * 12;
        months += endDate.getMonth() - startDate.getMonth();

        // Round up if there are extra days
        const dayDiff = endDate.getDate() - startDate.getDate();
        if (dayDiff > 0) {
            months += 1;
        }

        // Minimum 1 month (if same day or very short period)
        return Math.max(months, 1);
    }

    /**
     * Format duration with proper Serbian pluralization.
     *
     * Rules:
     * - 1 mesec (singular)
     * - 2-4 meseca (paucal)
     * - 5-20 meseci (plural)
     * - 21 mesec, 22-24 meseca, 25-30 meseci, etc.
     *
     * @param {number} months - Number of months
     * @returns {string} - Formatted string (e.g., "6 meseci")
     */
    function formatDuration(months) {
        if (months === 0) {
            return '-';
        }

        const lastDigit = months % 10;
        const lastTwoDigits = months % 100;

        // Exception for 11-19 (always "meseci")
        if (lastTwoDigits >= 11 && lastTwoDigits <= 19) {
            return months + ' meseci';
        }

        // Standard rules
        if (lastDigit === 1) {
            return months + ' mesec';
        } else if (lastDigit >= 2 && lastDigit <= 4) {
            return months + ' meseca';
        } else {
            return months + ' meseci';
        }
    }

    /**
     * Validate date range and update UI.
     * Shows error if end date is before start date.
     *
     * @returns {boolean} - True if valid, false otherwise
     */
    function validateDateRange() {
        const startValue = startDateInput.value;
        const endValue = endDateInput.value;

        // Clear error if either field is empty
        if (!startValue || !endValue) {
            hideError();
            return true;
        }

        const startDate = new Date(startValue);
        const endDate = new Date(endValue);

        if (endDate < startDate) {
            showError('Datum završetka ne može biti pre datuma startovanja.');
            return false;
        }

        hideError();
        return true;
    }

    /**
     * Show validation error for end date.
     *
     * @param {string} message - Error message to display
     */
    function showError(message) {
        if (endDateError) {
            endDateError.textContent = message;
            endDateError.style.display = 'block';
        }
        endDateInput.setAttribute('aria-invalid', 'true');
        endDateInput.classList.add('is-invalid');
    }

    /**
     * Hide validation error for end date.
     */
    function hideError() {
        if (endDateError) {
            endDateError.textContent = '';
            endDateError.style.display = 'none';
        }
        endDateInput.setAttribute('aria-invalid', 'false');
        endDateInput.classList.remove('is-invalid');
    }

    /**
     * Update duration display based on current date values.
     */
    function updateDuration() {
        const startValue = startDateInput.value;
        const endValue = endDateInput.value;

        // Show "-" if either date is empty
        if (!startValue || !endValue) {
            durationDisplay.textContent = '-';
            durationDisplay.classList.remove('duration-valid', 'duration-error');
            return;
        }

        // Validate date range
        if (!validateDateRange()) {
            durationDisplay.textContent = '-';
            durationDisplay.classList.remove('duration-valid');
            durationDisplay.classList.add('duration-error');
            return;
        }

        // Calculate and display duration
        const startDate = new Date(startValue);
        const endDate = new Date(endValue);
        const months = calculateMonths(startDate, endDate);
        const formattedDuration = formatDuration(months);

        durationDisplay.textContent = formattedDuration;
        durationDisplay.classList.add('duration-valid');
        durationDisplay.classList.remove('duration-error');
    }

    /**
     * Initialize event listeners.
     */
    function init() {
        // Listen for changes on both date inputs
        startDateInput.addEventListener('change', updateDuration);
        endDateInput.addEventListener('change', updateDuration);

        // Also listen for input events for real-time feedback
        startDateInput.addEventListener('input', updateDuration);
        endDateInput.addEventListener('input', updateDuration);

        // Initial calculation if values are pre-filled (e.g., from draft)
        if (startDateInput.value || endDateInput.value) {
            updateDuration();
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose for draft manager integration
    window.DurationCalculator = {
        update: updateDuration,
        validate: validateDateRange
    };

})();
