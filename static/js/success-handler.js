/**
 * Success Screen Handler
 * Story 2.13: Success Screen with Reference Number
 *
 * Features:
 * - Confetti animation on page load
 * - Copy reference number to clipboard
 * - Resend email functionality
 * - Accessibility announcements
 */

document.addEventListener('DOMContentLoaded', function() {
    // Trigger confetti animation on page load
    const confettiContainer = document.getElementById('confetti-container');
    if (confettiContainer) {
        triggerConfetti(confettiContainer);
    }

    // Copy reference number to clipboard
    const copyBtn = document.getElementById('copy-btn');
    const referenceNumberElement = document.getElementById('reference-number');
    const notificationRegion = document.getElementById('notification-region');

    if (copyBtn && referenceNumberElement) {
        const referenceNumber = referenceNumberElement.textContent;

        copyBtn.addEventListener('click', function() {
            // BROWSER COMPATIBILITY FIX: Check if Clipboard API is supported
            // Safari < 13.1, Firefox < 63 don't support navigator.clipboard
            if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
                navigator.clipboard.writeText(referenceNumber).then(function() {
                    // Visual feedback
                    copyBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg> Kopirano!';
                    copyBtn.classList.add('copied');
                    // ACCESSIBILITY FIX: Update aria-label for screen readers
                    copyBtn.setAttribute('aria-label', 'Referentni broj kopiran');

                    // Screen reader announcement
                    if (notificationRegion) {
                        notificationRegion.textContent = `Referentni broj ${referenceNumber} je kopiran u clipboard.`;
                    }

                    // Reset button after 2 seconds
                    setTimeout(function() {
                        copyBtn.innerHTML = `
                            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                                <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z"/>
                                <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z"/>
                            </svg>
                            Kopiraj
                        `;
                        copyBtn.classList.remove('copied');
                        // ACCESSIBILITY FIX: Restore original aria-label
                        copyBtn.setAttribute('aria-label', 'Kopiraj referentni broj');
                    }, 2000);
                }).catch(function(err) {
                    console.error('Failed to copy reference number:', err);
                    if (notificationRegion) {
                        notificationRegion.textContent = 'Greška pri kopiranju. Molimo kopirajte ručno.';
                    }
                });
            } else {
                // FALLBACK: Use older execCommand approach for unsupported browsers
                console.warn('Clipboard API not supported - using fallback');
                try {
                    const textarea = document.createElement('textarea');
                    textarea.value = referenceNumber;
                    textarea.style.position = 'fixed';
                    textarea.style.opacity = '0';
                    document.body.appendChild(textarea);
                    textarea.select();
                    const successful = document.execCommand('copy');
                    document.body.removeChild(textarea);

                    if (successful) {
                        copyBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg> Kopirano!';
                        copyBtn.classList.add('copied');
                        copyBtn.setAttribute('aria-label', 'Referentni broj kopiran');

                        if (notificationRegion) {
                            notificationRegion.textContent = `Referentni broj ${referenceNumber} je kopiran.`;
                        }

                        setTimeout(function() {
                            copyBtn.innerHTML = `
                                <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                                    <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z"/>
                                    <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z"/>
                                </svg>
                                Kopiraj
                            `;
                            copyBtn.classList.remove('copied');
                            copyBtn.setAttribute('aria-label', 'Kopiraj referentni broj');
                        }, 2000);
                    } else {
                        throw new Error('execCommand failed');
                    }
                } catch (fallbackErr) {
                    console.error('Fallback copy failed:', fallbackErr);
                    if (notificationRegion) {
                        notificationRegion.textContent = 'Kopiranje nije podržano u ovom pretraživaču. Molimo kopirajte ručno.';
                    }
                }
            }
        });
    }

    // Resend email button
    const resendBtn = document.getElementById('resend-email-btn');

    if (resendBtn && referenceNumberElement) {
        const referenceNumber = referenceNumberElement.textContent;

        resendBtn.addEventListener('click', function() {
            // Disable button during request
            resendBtn.disabled = true;
            resendBtn.classList.add('loading');

            // Get CSRF token
            const csrfToken = getCSRFToken();

            // Send resend request
            fetch(`/api/submissions/resend-email/${referenceNumber}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Success feedback
                    resendBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg> Email poslat!';
                    resendBtn.classList.remove('loading');
                    resendBtn.classList.add('success');

                    // Screen reader announcement
                    if (notificationRegion) {
                        notificationRegion.textContent = data.message;
                    }

                    // Reset button after 3 seconds
                    setTimeout(function() {
                        resendBtn.innerHTML = `
                            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                                <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z"/>
                                <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z"/>
                            </svg>
                            Pošalji email ponovo
                        `;
                        resendBtn.classList.remove('success');
                        resendBtn.disabled = false;
                    }, 3000);
                } else {
                    throw new Error(data.message || 'Email sending failed');
                }
            })
            .catch(error => {
                console.error('Email resend error:', error);

                // Error feedback
                resendBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg> Greška';
                resendBtn.classList.remove('loading');
                resendBtn.classList.add('error');

                // Screen reader announcement
                if (notificationRegion) {
                    notificationRegion.textContent = 'Greška pri slanju emaila. Pokušajte ponovo.';
                }

                // Reset button after 3 seconds
                setTimeout(function() {
                    resendBtn.innerHTML = `
                        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z"/>
                            <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z"/>
                        </svg>
                        Pošalji email ponovo
                    `;
                    resendBtn.classList.remove('error');
                    resendBtn.disabled = false;
                }, 3000);
            });
        });
    }
});

/**
 * Trigger confetti animation
 * Lightweight CSS/JS confetti animation
 *
 * PERFORMANCE FIX: Track created elements and clean up immediately on page unload
 * to prevent memory leaks if user navigates away before animation completes
 */
function triggerConfetti(container) {
    const colors = ['#0EA5E9', '#FF7A59', '#10B981', '#F59E0B', '#8B5CF6'];
    const confettiCount = 50;
    const animationDuration = 3000; // 3 seconds

    // PERFORMANCE FIX: Track confetti elements for cleanup
    const confettiElements = [];

    for (let i = 0; i < confettiCount; i++) {
        const element = createConfettiPiece(container, colors, animationDuration);
        confettiElements.push(element);
    }

    // PERFORMANCE FIX: Cleanup function to remove all confetti
    const cleanup = () => {
        confettiElements.forEach(el => {
            if (el && el.parentNode) {
                el.remove();
            }
        });
        container.innerHTML = '';
    };

    // Clean up after animation completes
    setTimeout(cleanup, animationDuration + 500);

    // MEMORY LEAK FIX: Add beforeunload listener to cleanup if user navigates away
    const beforeUnloadHandler = () => {
        cleanup();
        window.removeEventListener('beforeunload', beforeUnloadHandler);
    };
    window.addEventListener('beforeunload', beforeUnloadHandler);
}

/**
 * Create single confetti piece
 * PERFORMANCE FIX: Return element reference for cleanup tracking
 */
function createConfettiPiece(container, colors, duration) {
    const confetti = document.createElement('div');
    const color = colors[Math.floor(Math.random() * colors.length)];
    const size = Math.random() * 10 + 5; // 5-15px
    const startX = Math.random() * 100; // 0-100%
    const endX = startX + (Math.random() * 40 - 20); // ±20% movement
    const rotation = Math.random() * 360;
    const animationDelay = Math.random() * 500; // 0-500ms delay

    confetti.style.cssText = `
        position: absolute;
        width: ${size}px;
        height: ${size}px;
        background: ${color};
        top: -20px;
        left: ${startX}%;
        opacity: 1;
        transform: rotate(${rotation}deg);
        pointer-events: none;
    `;

    container.appendChild(confetti);

    // Animate confetti falling
    const animation = confetti.animate([
        {
            top: '-20px',
            left: `${startX}%`,
            opacity: 1,
            transform: `rotate(${rotation}deg)`
        },
        {
            top: '100%',
            left: `${endX}%`,
            opacity: 0,
            transform: `rotate(${rotation + 720}deg)` // 2 full rotations
        }
    ], {
        duration: duration,
        delay: animationDelay,
        easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        fill: 'forwards'
    });

    // Remove element after animation
    animation.onfinish = () => {
        if (confetti && confetti.parentNode) {
            confetti.remove();
        }
    };

    // PERFORMANCE FIX: Return element for cleanup tracking
    return confetti;
}

/**
 * Get CSRF token from cookie
 */
function getCSRFToken() {
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

    return cookieValue || '';
}
