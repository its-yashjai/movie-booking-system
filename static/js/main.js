/**
 * Global JavaScript for BookMyshowClone
 * Contains common utility functions for Toasts and Cookies.
 */

// --- Toast and Cookie Helper Functions ---

/**
 * Displays a temporary notification (optional - disabled by default)
 * @param {string} message - The message to display
 * @param {string} type - Bootstrap color type (success, danger, info, warning)
 * @param {boolean} show - Set to true to show the toast (default: false to disable)
 */
function showToast(message, type = 'info', show = false) {
    // Toast notifications disabled by default - pass show=true to enable
    if (!show) return;
    
    // Remove existing toasts to prevent stacking too many
    document.querySelectorAll('.toast-container-custom').forEach(t => t.remove());

    const toastContainer = document.createElement('div');
    toastContainer.className = `toast-container-custom position-fixed bottom-0 end-0 p-3`;
    toastContainer.style.zIndex = '9999';
    
    toastContainer.innerHTML = `
        <div class="toast align-items-center text-white bg-${type} border-0 show" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-info-circle'} me-2"></i> ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    document.body.appendChild(toastContainer);
    
    // Auto remove after 4 seconds
    setTimeout(() => {
        if (toastContainer && toastContainer.parentNode) {
            toastContainer.parentNode.removeChild(toastContainer);
        }
    }, 4000);
}

/**
 * Helper to retrieve CSRF token from cookies
 * @param {string} name - The name of the cookie to retrieve
 */
function getCookie(name) {
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
    return cookieValue;
}

/**
 * Like or dislike a review via AJAX (FEATURE DISABLED)
 * @param {string} reviewId - The ID of the review
 * @param {boolean} isLike - True for like, False for dislike
 * @param {HTMLElement} button - The button element clicked
 */
/*
async function likeReview(reviewId, isLike, button) {
    const csrftoken = getCookie('csrftoken');
    
    try {
        const response = await fetch(`/review/${reviewId}/like/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ is_like: isLike })
        });
        
        if (!response.ok) {
            console.error('Review like error: HTTP', response.status);
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Find the review card container
            const reviewCard = button.closest('.review-card') || button.closest('.card');
            if (!reviewCard) return;
            
            // Update counts
            const likeBtn = reviewCard.querySelector('.review-like-btn');
            const dislikeBtn = reviewCard.querySelector('.review-dislike-btn');
            
            if (likeBtn && data.likes !== undefined) {
                const likeCount = likeBtn.querySelector('.likes-count');
                if (likeCount) likeCount.textContent = data.likes;
                
                // Update visual state for like button
                if (isLike) {
                    likeBtn.classList.remove('btn-outline-secondary');
                    likeBtn.classList.add('btn-primary');
                    const icon = likeBtn.querySelector('i');
                    if (icon) {
                        icon.classList.remove('far');
                        icon.classList.add('fas');
                    }
                } else if (data.action === 'removed') {
                    // Only revert if user clicked dislike and it was a like
                    likeBtn.classList.add('btn-outline-secondary');
                    likeBtn.classList.remove('btn-primary');
                    const icon = likeBtn.querySelector('i');
                    if (icon) {
                        icon.classList.add('far');
                        icon.classList.remove('fas');
                    }
                }
            }
            
            if (dislikeBtn && data.dislikes !== undefined) {
                const dislikeCount = dislikeBtn.querySelector('.dislikes-count');
                if (dislikeCount) dislikeCount.textContent = data.dislikes;
                
                // Update visual state for dislike button
                if (!isLike) {
                    dislikeBtn.classList.remove('btn-outline-secondary');
                    dislikeBtn.classList.add('btn-danger');
                    const icon = dislikeBtn.querySelector('i');
                    if (icon) {
                        icon.classList.remove('far');
                        icon.classList.add('fas');
                    }
                } else if (data.action === 'removed') {
                    // Only revert if user clicked like and it was a dislike
                    dislikeBtn.classList.add('btn-outline-secondary');
                    dislikeBtn.classList.remove('btn-danger');
                    const icon = dislikeBtn.querySelector('i');
                    if (icon) {
                        icon.classList.add('far');
                        icon.classList.remove('fas');
                    }
                }
            }
        }
    } catch (error) {
        console.error('Review like error:', error);
    }
}
*/
