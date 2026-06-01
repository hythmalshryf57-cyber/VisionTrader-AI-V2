// theme.js - Cyberpunk Cosmic Ocean Theme Engine

document.addEventListener('DOMContentLoaded', () => {
    // 1. Generate Stars
    const createStars = () => {
        const starsContainer = document.createElement('div');
        starsContainer.className = 'stars-container';
        starsContainer.style.position = 'fixed';
        starsContainer.style.top = '0';
        starsContainer.style.left = '0';
        starsContainer.style.width = '100%';
        starsContainer.style.height = '100%';
        starsContainer.style.zIndex = '-2';
        starsContainer.style.pointerEvents = 'none';
        
        for (let i = 0; i < 150; i++) {
            const star = document.createElement('div');
            star.className = 'cosmic-star';
            const size = Math.random() * 2 + 1;
            star.style.width = size + 'px';
            star.style.height = size + 'px';
            star.style.left = Math.random() * 100 + 'vw';
            star.style.top = Math.random() * 100 + 'vh';
            star.style.animationDuration = (Math.random() * 3 + 2) + 's';
            star.style.animationDelay = (Math.random() * 2) + 's';
            starsContainer.appendChild(star);
        }
        document.body.appendChild(starsContainer);
    };

    // 2. Ripple Effect for Buttons
    const setupRippleEffect = () => {
        const buttons = document.querySelectorAll('.btn, button');
        buttons.forEach(btn => {
            // Avoid adding multiple listeners
            if (!btn.classList.contains('ripple-ready')) {
                btn.classList.add('ripple-ready');
                // Ensure position is relative for absolute ripple positioning
                const style = window.getComputedStyle(btn);
                if (style.position === 'static') {
                    btn.style.position = 'relative';
                }
                btn.style.overflow = 'hidden';

                btn.addEventListener('click', function(e) {
                    const rect = btn.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const y = e.clientY - rect.top;
                    
                    const ripple = document.createElement('span');
                    ripple.className = 'ripple-effect';
                    ripple.style.left = x + 'px';
                    ripple.style.top = y + 'px';
                    
                    this.appendChild(ripple);
                    setTimeout(() => ripple.remove(), 600);
                });
            }
        });
    };

    // 3. Shimmer/Loading effect removal
    const handleShimmer = () => {
        const cards = document.querySelectorAll('.card, .memory-card, .result-glass, .history-card');
        cards.forEach(card => card.classList.add('shimmer-card'));
        
        setTimeout(() => {
            cards.forEach(card => card.classList.remove('shimmer-card'));
        }, 800);
    };

    createStars();
    setupRippleEffect();
    handleShimmer();

    // Pulse animation for alerts
    const alerts = document.querySelectorAll('.alert, .calendar-warning, #errorCard:not(.hidden)');
    alerts.forEach(alert => alert.classList.add('pulse-alert'));
    
    // Observer for dynamically added elements (like history items)
    const observer = new MutationObserver((mutations) => {
        let shouldSetupRipple = false;
        mutations.forEach(m => {
            if (m.addedNodes.length > 0) {
                shouldSetupRipple = true;
            }
        });
        if (shouldSetupRipple) {
            setupRippleEffect();
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
});
