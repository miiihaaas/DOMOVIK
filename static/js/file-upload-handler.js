/**
 * File Upload Handler - Multiple Files with Preview
 * Story 2.9: File Upload UI - Multiple Files with Preview
 *
 * Features:
 * - Drag and drop file upload
 * - Click to upload (file input fallback)
 * - Client-side validation (file size, extension)
 * - Upload to backend API (/upload/)
 * - Delete files (/delete/<id>/)
 * - CSRF token protection
 * - Progress indication
 * - Error handling with Serbian messages
 * - Multiple file upload support
 */

// Global registry for uploaded files (Story 2.8 Task 12 - Draft integration)
window.uploadedFilesRegistry = window.uploadedFilesRegistry || [];

/**
 * FileUploadHandler class - Manages file uploads for a specific upload zone
 * @param {string} uploadZoneId - ID of the upload zone element
 * @param {string} fileInputId - ID of the file input element
 * @param {string} filesListId - ID of the uploaded files list container
 * @param {string} errorContainerId - ID of the error message container
 * @param {string} category - File category (BUDGET, BIOGRAPHY, SUPPORT_LETTER)
 */
class FileUploadHandler {
  constructor(uploadZoneId, fileInputId, filesListId, errorContainerId, category) {
    this.uploadZone = document.getElementById(uploadZoneId);
    this.fileInput = document.getElementById(fileInputId);
    this.filesList = document.getElementById(filesListId);
    this.errorContainer = document.getElementById(errorContainerId);
    this.category = category;

    // API endpoints (Story 2.8 backend)
    this.uploadUrl = '/upload/';
    this.deleteBaseUrl = '/delete/';

    // File validation limits
    this.maxFileSize = 10 * 1024 * 1024; // 10MB in bytes
    this.maxFileCount = 5; // Maximum 5 files per category (biografije, pisma)
    this.allowedExtensions = this.getAllowedExtensions();

    // UI timeout constants (milliseconds)
    this.ERROR_AUTO_HIDE_MS = 10000; // 10 seconds
    this.SUCCESS_AUTO_HIDE_MS = 3000; // 3 seconds
    this.UPLOAD_TIMEOUT_MS = 30000; // 30 seconds

    // Upload state
    this.isUploading = false;

    // Initialize event listeners
    this.attachEventListeners();
  }

  /**
   * Get allowed file extensions based on category
   * @returns {Array} Array of allowed extensions
   */
  getAllowedExtensions() {
    if (this.category === 'BUDGET') {
      return ['xls', 'xlsx'];
    } else if (this.category === 'BIOGRAPHY' || this.category === 'SUPPORT_LETTER' ||
               this.category === 'OPIS_INICIJATIVE' || this.category === 'PISMO_NAMERE') {
      return ['pdf', 'doc', 'docx'];
    }
    return [];
  }

  /**
   * Attach event listeners for click and drag-drop
   */
  attachEventListeners() {
    if (!this.uploadZone || !this.fileInput) {
      console.error(`FileUploadHandler: Elements not found for category ${this.category}`);
      return;
    }

    // Click to upload
    this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

    // Drag and drop events
    this.uploadZone.addEventListener('dragover', (e) => this.handleDragOver(e));
    this.uploadZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
    this.uploadZone.addEventListener('drop', (e) => this.handleDrop(e));
  }

  /**
   * Handle dragover event - add visual feedback
   */
  handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    this.uploadZone.classList.add('drag-over');
  }

  /**
   * Handle dragleave event - remove visual feedback
   */
  handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    this.uploadZone.classList.remove('drag-over');
  }

  /**
   * Handle drop event - process dropped files
   */
  handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    this.uploadZone.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    this.handleFileSelect({ target: { files: files } });
  }

  /**
   * Handle file selection (from input or drop event)
   * @param {Event} event - File input change event or drop event
   */
  async handleFileSelect(event) {
    const files = event.target.files;

    if (!files || files.length === 0) {
      return;
    }

    // Clear previous errors
    this.clearError();

    // For BUDGET, OPIS_INICIJATIVE, and PISMO_NAMERE categories, only allow 1 file
    if ((this.category === 'BUDGET' || this.category === 'OPIS_INICIJATIVE' || this.category === 'PISMO_NAMERE') && files.length > 1) {
      this.showError('Može se upload-ovati samo jedan fajl.');
      return;
    }

    // For BIOGRAPHY and SUPPORT_LETTER, enforce max file count (5 files total)
    if (this.category === 'BIOGRAPHY' || this.category === 'SUPPORT_LETTER') {
      const currentFileCount = this.getCurrentFileCount();
      const totalAfterUpload = currentFileCount + files.length;

      if (totalAfterUpload > this.maxFileCount) {
        this.showError(`Maksimalan broj fajlova je ${this.maxFileCount}. Trenutno imate ${currentFileCount} fajl(ova). Možete upload-ovati još ${this.maxFileCount - currentFileCount}.`);
        return;
      }
    }

    // Validate and upload files sequentially
    const totalFiles = files.length;
    for (let i = 0; i < files.length; i++) {
      const file = files[i];

      // Announce upload progress for screen readers (multiple files only)
      if (totalFiles > 1) {
        this.announceProgress(`Upload-ujem fajl ${i + 1} od ${totalFiles}...`);
      }

      // Client-side validation
      const validationError = this.validateFile(file);
      if (validationError) {
        this.showError(validationError);
        continue; // Skip this file, continue with others
      }

      // Upload file to backend
      await this.uploadFile(file);
    }

    // Clear progress announcement
    if (totalFiles > 1) {
      this.announceProgress(`Završeno upload-ovanje ${totalFiles} fajl(ova).`);
    }

    // Reset file input to allow re-uploading same file
    this.fileInput.value = '';
  }

  /**
   * Get current count of uploaded files in this category
   * @returns {number} Number of files currently uploaded
   */
  getCurrentFileCount() {
    if (!this.filesList) return 0;
    return this.filesList.querySelectorAll('.file-preview-card').length;
  }

  /**
   * Validate file before upload (client-side pre-validation)
   * @param {File} file - File object
   * @returns {string|null} Error message or null if valid
   */
  validateFile(file) {
    // Check file size (10MB max)
    if (file.size > this.maxFileSize) {
      return `Fajl "${file.name}" premašuje 10MB. Maksimalna dozvoljena veličina je 10MB.`;
    }

    // Check file extension
    const fileName = file.name.toLowerCase();
    const fileExtension = fileName.split('.').pop();

    if (!this.allowedExtensions.includes(fileExtension)) {
      const allowedFormats = this.allowedExtensions.map(ext => ext.toUpperCase()).join(', ');
      return `Format fajla "${file.name}" nije podržan. Molimo koristite ${allowedFormats} fajlove.`;
    }

    return null; // File is valid
  }

  /**
   * Upload file to backend API
   * @param {File} file - File object to upload
   */
  async uploadFile(file) {
    // Prevent multiple simultaneous uploads
    if (this.isUploading) {
      this.showError('Molimo sačekajte da se prethodni upload završi.');
      return;
    }

    this.isUploading = true;
    this.showLoading();

    // Create AbortController for timeout handling
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.UPLOAD_TIMEOUT_MS);

    try {
      // Create FormData
      const formData = new FormData();
      formData.append('file', file);
      formData.append('category', this.category);

      // Get CSRF token
      const csrfToken = this.getCsrfToken();
      formData.append('csrfmiddlewaretoken', csrfToken);

      // Make API request with timeout
      const response = await fetch(this.uploadUrl, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
        // Note: Don't set Content-Type header for FormData (browser sets it automatically with boundary)
      });

      clearTimeout(timeoutId);

      const data = await response.json();

      if (response.ok && data.success) {
        // Upload successful
        this.onUploadSuccess(data);
        this.showSuccess(`Fajl "${file.name}" je uspešno upload-ovan.`);
      } else {
        // Upload failed - backend validation error
        const errorMsg = data.errors || data.error || 'Upload nije uspeo. Molimo pokušajte ponovo.';
        this.showError(errorMsg);
      }
    } catch (error) {
      clearTimeout(timeoutId);

      // Check if error is due to timeout
      if (error.name === 'AbortError') {
        console.error('Upload timeout:', error);
        this.showError(`Upload je prekinut zbog isteka vremena (${this.UPLOAD_TIMEOUT_MS / 1000}s). Molimo proverite internet konekciju i pokušajte sa manjim fajlom.`);
      } else {
        // Network error or other exception
        console.error('Upload error:', error);
        this.showError('Upload nije uspeo. Molimo proverite internet konekciju i pokušajte ponovo.');
      }
    } finally {
      this.isUploading = false;
      this.hideLoading();
    }
  }

  /**
   * Handle successful upload - add file to preview and registry
   * @param {Object} data - Response data from backend
   */
  onUploadSuccess(data) {
    const fileData = {
      file_id: data.file_id,
      filename: data.filename,
      size: data.size,
      file_type: data.file_type,
      category: this.category
    };

    // BUGFIX: For single-file categories, remove any existing file in the same category
    // before adding the new one. This prevents duplicate files when replacing uploads.
    const singleFileCategories = ['BUDGET', 'OPIS_INICIJATIVE', 'PISMO_NAMERE'];
    if (singleFileCategories.includes(this.category)) {
      window.uploadedFilesRegistry = window.uploadedFilesRegistry.filter(
        file => file.category !== this.category
      );
    }

    // Add to global registry (for draft integration)
    window.uploadedFilesRegistry.push(fileData);

    // Add file preview to UI
    if (window.FilePreview) {
      const preview = new window.FilePreview(this.filesList.id);
      preview.addFile(fileData, (fileId) => this.deleteFile(fileId));
    }

    // Trigger draft save (if draft manager exists)
    if (typeof saveDraft === 'function') {
      saveDraft();
    }
  }

  /**
   * Show custom delete confirmation dialog
   * @param {string} message - Confirmation message
   * @returns {Promise<boolean>} True if confirmed, false if cancelled
   */
  async confirmDelete(message) {
    // Use native confirm() for now (custom modal can be added in future story)
    // TODO: Replace with custom civic-tech styled modal in Story 2.12
    return confirm(message);
  }

  /**
   * Delete file from backend and remove from UI
   * @param {number} fileId - File ID from backend
   */
  async deleteFile(fileId) {
    const confirmed = await this.confirmDelete('Da li ste sigurni da želite da obrišete ovaj fajl?');
    if (!confirmed) {
      return;
    }

    try {
      // Get CSRF token
      const csrfToken = this.getCsrfToken();

      // Make DELETE request
      const response = await fetch(`${this.deleteBaseUrl}${fileId}/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Delete successful
        this.onDeleteSuccess(fileId);
        this.showSuccess('Fajl je uspešno obrisan.');
      } else {
        // Delete failed
        const errorMsg = data.error || 'Brisanje nije uspelo. Molimo pokušajte ponovo.';
        this.showError(errorMsg);
      }
    } catch (error) {
      console.error('Delete error:', error);
      this.showError('Brisanje nije uspelo. Molimo proverite internet konekciju i pokušajte ponovo.');
    }
  }

  /**
   * Handle successful file deletion
   * @param {number} fileId - File ID that was deleted
   */
  onDeleteSuccess(fileId) {
    // Remove from global registry
    window.uploadedFilesRegistry = window.uploadedFilesRegistry.filter(
      file => file.file_id !== fileId
    );

    // Remove preview card from DOM
    const card = this.filesList.querySelector(`[data-file-id="${fileId}"]`);
    if (card) {
      card.remove();
    }

    // Trigger draft save
    if (typeof saveDraft === 'function') {
      saveDraft();
    }
  }

  /**
   * Get CSRF token for Django CSRF protection
   *
   * PRIMARY: Reads from DOM meta tag (CSRF_COOKIE_HTTPONLY=True compatible)
   * FALLBACK: Reads from 'csrftoken' cookie (backwards compatibility)
   *
   * Story 4-5 Security Fix: Django's CSRF_COOKIE_HTTPONLY=True blocks JavaScript
   * access to csrftoken cookie. Templates now render token in meta tag:
   * <meta name="csrf-token" content="{{ csrf_token }}">
   *
   * Security Note: This token MUST be included in all POST requests
   * to /upload/ and /delete/<id>/ to prevent
   * Cross-Site Request Forgery (CSRF) attacks.
   *
   * @returns {string} CSRF token value or empty string if not found
   *
   * @example
   * const csrfToken = this.getCsrfToken();
   * formData.append('csrfmiddlewaretoken', csrfToken);
   */
  getCsrfToken() {
    // FIRST: Try to read from DOM meta tag (CSRF_COOKIE_HTTPONLY=True compatible)
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag && metaTag.content) {
      return metaTag.content;
    }

    // FALLBACK: Try to read from cookie (for backwards compatibility)
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }

    // FINAL: Log warning if both methods failed
    if (!cookieValue) {
      console.warn('CSRF token not found in DOM meta tag or cookie. Ensure <meta name="csrf-token"> exists in template.');
    }

    return cookieValue;
  }

  /**
   * Show loading spinner during upload
   */
  showLoading() {
    this.uploadZone.classList.add('upload-zone--loading');
    const btn = this.uploadZone.querySelector('.upload-btn');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="loading-spinner"></span> Učitava se...';
    }
  }

  /**
   * Hide loading spinner after upload
   */
  hideLoading() {
    this.uploadZone.classList.remove('upload-zone--loading');
    const btn = this.uploadZone.querySelector('.upload-btn');
    if (btn) {
      btn.disabled = false;
      // Single file categories use singular form
      const singleFileCategories = ['BUDGET', 'OPIS_INICIJATIVE', 'PISMO_NAMERE'];
      btn.textContent = singleFileCategories.includes(this.category) ? 'Odaberi fajl' : 'Odaberi fajl(ove)';
    }
  }

  /**
   * Show error message
   * @param {string} message - Error message to display
   */
  showError(message) {
    if (!this.errorContainer) return;

    this.errorContainer.innerHTML = `
      <span class="error-icon" aria-hidden="true">⚠️</span>
      <div class="error-message">
        <span class="error-text">${message}</span>
      </div>
    `;
    this.errorContainer.style.display = 'flex';

    // Auto-hide after configured timeout
    setTimeout(() => {
      this.clearError();
    }, this.ERROR_AUTO_HIDE_MS);
  }

  /**
   * Show success message (auto-hides after 3 seconds)
   * @param {string} message - Success message to display
   */
  showSuccess(message) {
    // Create temporary success message
    const successDiv = document.createElement('div');
    successDiv.className = 'upload-success';
    successDiv.innerHTML = `
      <span class="success-icon" aria-hidden="true">✓</span>
      <span class="success-text">${message}</span>
    `;

    // Insert before error container
    this.errorContainer.parentNode.insertBefore(successDiv, this.errorContainer);

    // Auto-remove after configured timeout
    setTimeout(() => {
      successDiv.remove();
    }, this.SUCCESS_AUTO_HIDE_MS);
  }

  /**
   * Clear error message
   */
  clearError() {
    if (this.errorContainer) {
      this.errorContainer.style.display = 'none';
      this.errorContainer.innerHTML = '';
    }
  }

  /**
   * Announce progress to screen readers via ARIA live region
   * @param {string} message - Progress message to announce
   */
  announceProgress(message) {
    // Find or create ARIA live region for progress announcements
    let liveRegion = document.getElementById(`${this.category.toLowerCase()}-upload-progress-live`);

    if (!liveRegion) {
      liveRegion = document.createElement('div');
      liveRegion.id = `${this.category.toLowerCase()}-upload-progress-live`;
      liveRegion.className = 'sr-only';
      liveRegion.setAttribute('aria-live', 'polite');
      liveRegion.setAttribute('aria-atomic', 'true');
      this.uploadZone.appendChild(liveRegion);
    }

    liveRegion.textContent = message;
  }
}

/**
 * Get uploaded files from global registry filtered by application type
 * Formats files for backend submission
 * @returns {Array} Array of file metadata objects
 */
function getUploadedFiles() {
  // Determine application type from body data attribute
  const applicationType = document.body.dataset.applicationType || 'COA';

  // Define valid file categories for each application type
  const cobCategories = ['OPIS_INICIJATIVE', 'PISMO_NAMERE'];
  const coaCategories = ['BUDGET', 'BIOGRAPHY', 'SUPPORT_LETTER'];

  // Filter files by current application type to prevent cross-form contamination
  const validCategories = applicationType === 'COB' ? cobCategories : coaCategories;

  return (window.uploadedFilesRegistry || [])
    .filter(file => validCategories.includes(file.category))
    .map(file => ({
      file_type: file.category,
      name: file.filename,
      size: file.size,
      file_id: file.file_id,
      original_filename: file.filename,
      stored_filename: file.filename
    }));
}

// Expose globally for submission-handler.js
window.getUploadedFiles = getUploadedFiles;

/**
 * Initialize file upload handlers on page load
 */
document.addEventListener('DOMContentLoaded', function() {
  // Initialize Budget upload handler
  const budgetHandler = new FileUploadHandler(
    'budget-upload-zone',
    'budget-file-input',
    'budget-files-list',
    'budget-upload-error',
    'BUDGET'
  );

  // Initialize Biografije upload handler
  const biografijeHandler = new FileUploadHandler(
    'biografije-upload-zone',
    'biografije-file-input',
    'biografije-files-list',
    'biografije-upload-error',
    'BIOGRAPHY'
  );

  // Initialize Pisma podrške upload handler
  const pismaHandler = new FileUploadHandler(
    'pisma-upload-zone',
    'pisma-file-input',
    'pisma-files-list',
    'pisma-upload-error',
    'SUPPORT_LETTER'
  );

  // Attach click handlers to upload buttons (Story 2.9 Code Review Fix #8)
  const budgetBtn = document.getElementById('budget-upload-btn');
  if (budgetBtn) {
    budgetBtn.addEventListener('click', () => {
      document.getElementById('budget-file-input').click();
    });
  }

  const biografijeBtn = document.getElementById('biografije-upload-btn');
  if (biografijeBtn) {
    biografijeBtn.addEventListener('click', () => {
      document.getElementById('biografije-file-input').click();
    });
  }

  const pismaBtn = document.getElementById('pisma-upload-btn');
  if (pismaBtn) {
    pismaBtn.addEventListener('click', () => {
      document.getElementById('pisma-file-input').click();
    });
  }

  // Initialize COB form upload handlers (Story 3-4)
  const opisInicijativeHandler = new FileUploadHandler(
    'opis-inicijative-upload-zone',
    'opis-inicijative-file-input',
    'opis-inicijative-files-list',
    'opis-inicijative-upload-error',
    'OPIS_INICIJATIVE'
  );

  const pismoNamereHandler = new FileUploadHandler(
    'pismo-namere-upload-zone',
    'pismo-namere-file-input',
    'pismo-namere-files-list',
    'pismo-namere-upload-error',
    'PISMO_NAMERE'
  );

  // Attach click handlers for COB upload buttons
  const opisInicijativeBtn = document.getElementById('opis-inicijative-upload-btn');
  if (opisInicijativeBtn) {
    opisInicijativeBtn.addEventListener('click', () => {
      document.getElementById('opis-inicijative-file-input').click();
    });
  }

  const pismoNamereBtn = document.getElementById('pismo-namere-upload-btn');
  if (pismoNamereBtn) {
    pismoNamereBtn.addEventListener('click', () => {
      document.getElementById('pismo-namere-file-input').click();
    });
  }

  // Expose handlers globally for debugging (development only)
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    window.budgetHandler = budgetHandler;
    window.biografijeHandler = biografijeHandler;
    window.pismaHandler = pismaHandler;
    window.opisInicijativeHandler = opisInicijativeHandler;
    window.pismoNamereHandler = pismoNamereHandler;
  }
});
