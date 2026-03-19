/**
 * File Preview Component - Display uploaded files with icons and delete button
 * Story 2.9: File Upload UI - Multiple Files with Preview
 *
 * Features:
 * - Display file preview cards with icon, name, size
 * - File type icons (PDF red, DOC blue, Excel green)
 * - Delete button with callback
 * - File size formatting (bytes to KB/MB)
 * - Long filename truncation
 * - Fade-in animation
 */

/**
 * FilePreview class - Manages file preview display
 * @param {string} containerId - ID of the container element for file previews
 */
class FilePreview {
  constructor(containerId) {
    this.container = document.getElementById(containerId);

    if (!this.container) {
      console.error(`FilePreview: Container not found: ${containerId}`);
    }
  }

  /**
   * Add file preview card to the container
   * @param {Object} fileData - File data object {file_id, filename, size, file_type}
   * @param {Function} deleteCallback - Callback function to call when delete button is clicked
   */
  addFile(fileData, deleteCallback) {
    if (!this.container) return;

    // Create preview card element
    const card = document.createElement('div');
    card.className = 'file-preview-card';
    card.setAttribute('data-file-id', fileData.file_id);

    // Get file icon HTML
    const iconHTML = this.getFileIcon(fileData.file_type);

    // Format file size
    const formattedSize = this.formatFileSize(fileData.size);

    // Truncate long filenames (keep extension visible)
    const displayName = this.truncateFilename(fileData.filename, 40);

    // Build card HTML
    card.innerHTML = `
      ${iconHTML}
      <div class="file-info">
        <span class="file-name" title="${fileData.filename}">${displayName}</span>
        <span class="file-size">${formattedSize}</span>
      </div>
      <button type="button" class="file-delete-btn" aria-label="Obriši ${fileData.filename}" data-file-id="${fileData.file_id}">
        <span class="delete-icon" aria-hidden="true">&times;</span>
      </button>
    `;

    // Attach delete button click handler
    const deleteBtn = card.querySelector('.file-delete-btn');
    deleteBtn.addEventListener('click', (e) => {
      e.preventDefault();
      deleteCallback(fileData.file_id);
    });

    // Add card to container
    this.container.appendChild(card);
  }

  /**
   * Remove file preview card from the container
   * @param {number} fileId - File ID to remove
   */
  removeFile(fileId) {
    if (!this.container) return;

    const card = this.container.querySelector(`[data-file-id="${fileId}"]`);
    if (card) {
      card.remove();
    }
  }

  /**
   * Get file icon HTML based on file type
   * @param {string} fileType - File extension (pdf, doc, docx, xls, xlsx)
   * @returns {string} HTML string for file icon
   */
  getFileIcon(fileType) {
    const type = fileType.toLowerCase();
    let iconClass = 'file-icon';
    let iconContent = '';

    if (type === 'pdf') {
      iconClass += ' file-icon--pdf';
      iconContent = this.getPdfIconSVG();
    } else if (type === 'doc' || type === 'docx') {
      iconClass += ' file-icon--doc';
      iconContent = this.getDocIconSVG();
    } else if (type === 'xls' || type === 'xlsx') {
      iconClass += ' file-icon--xls';
      iconContent = this.getExcelIconSVG();
    } else {
      // Generic file icon
      iconClass += ' file-icon--generic';
      iconContent = '📄';
    }

    return `<div class="${iconClass}">${iconContent}</div>`;
  }

  /**
   * Get PDF icon SVG (inline SVG)
   * @returns {string} SVG markup
   */
  getPdfIconSVG() {
    return `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2Z" fill="currentColor"/>
        <path d="M14 2V8H20" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    `;
  }

  /**
   * Get DOC icon SVG (inline SVG)
   * @returns {string} SVG markup
   */
  getDocIconSVG() {
    return `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2Z" fill="currentColor"/>
        <path d="M14 2V8H20" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M8 12H16M8 16H16" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
      </svg>
    `;
  }

  /**
   * Get Excel icon SVG (inline SVG)
   * @returns {string} SVG markup
   */
  getExcelIconSVG() {
    return `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2Z" fill="currentColor"/>
        <path d="M14 2V8H20" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M8 12H16M8 16H12" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
      </svg>
    `;
  }

  /**
   * Format file size from bytes to human-readable format
   * @param {number} bytes - File size in bytes
   * @returns {string} Formatted file size (e.g., "1.5 MB", "500 KB", "1 KB")
   */
  formatFileSize(bytes) {
    if (bytes === 0) return '0 B';

    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];

    if (bytes < k) {
      return bytes + ' B';
    }

    const i = Math.floor(Math.log(bytes) / Math.log(k));
    const size = (bytes / Math.pow(k, i)).toFixed(1);

    // Remove trailing .0 for whole numbers (1.0 KB -> 1 KB)
    const cleanSize = size.endsWith('.0') ? size.slice(0, -2) : size;

    return cleanSize + ' ' + sizes[i];
  }

  /**
   * Truncate long filename while keeping extension visible
   * @param {string} filename - Original filename
   * @param {number} maxLength - Maximum length before truncation
   * @returns {string} Truncated filename with ellipsis
   */
  truncateFilename(filename, maxLength) {
    if (filename.length <= maxLength) {
      return filename;
    }

    // Split filename and extension
    const lastDotIndex = filename.lastIndexOf('.');
    const name = filename.substring(0, lastDotIndex);
    const extension = filename.substring(lastDotIndex);

    // Calculate how many characters we can show from the name
    const extensionLength = extension.length;
    const availableLength = maxLength - extensionLength - 3; // -3 for "..."

    if (availableLength <= 0) {
      // Filename is too long even with just extension
      return '...' + extension;
    }

    // Truncate name and add ellipsis
    const truncatedName = name.substring(0, availableLength);
    return truncatedName + '...' + extension;
  }

  /**
   * Clear all file previews from the container
   */
  clearAll() {
    if (this.container) {
      this.container.innerHTML = '';
    }
  }

  /**
   * Get count of files in the container
   * @returns {number} Number of files
   */
  getFileCount() {
    if (!this.container) return 0;
    return this.container.querySelectorAll('.file-preview-card').length;
  }
}

// Expose FilePreview class globally
window.FilePreview = FilePreview;
