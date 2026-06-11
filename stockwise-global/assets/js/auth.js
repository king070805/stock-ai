/**
 * StockWise - Authentication JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    // Tab switching
    const authTabs = document.querySelectorAll('.auth-tab');
    const authForms = document.querySelectorAll('.auth-form');

    authTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.dataset.tab;

            // Update tabs
            authTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Update forms
            authForms.forEach(form => {
                form.classList.remove('active');
                if (form.id === `${targetTab}Form`) {
                    form.classList.add('active');
                }
            });
        });
    });

    // Password toggle
    const togglePassword = document.querySelector('.btn-toggle-password');
    const passwordInput = document.querySelector('.password-input input');

    togglePassword?.addEventListener('click', () => {
        const type = passwordInput.type === 'password' ? 'text' : 'password';
        passwordInput.type = type;
        togglePassword.innerHTML = `<i class="fas fa-eye${type === 'text' ? '-slash' : ''}"></i>`;
    });

    // Send code button
    const sendCodeBtn = document.querySelector('.btn-send-code');
    
    sendCodeBtn?.addEventListener('click', () => {
        let countdown = 60;
        sendCodeBtn.disabled = true;
        sendCodeBtn.textContent = `${countdown}s`;

        const timer = setInterval(() => {
            countdown--;
            sendCodeBtn.textContent = `${countdown}s`;

            if (countdown <= 0) {
                clearInterval(timer);
                sendCodeBtn.disabled = false;
                sendCodeBtn.textContent = 'Send Code';
            }
        }, 1000);

        // Simulate sending code
        alert('Verification code sent to your email!');
    });

    // Form submissions
    document.getElementById('passwordForm')?.addEventListener('submit', (e) => {
        e.preventDefault();
        // Simulate login
        alert('Login successful! Redirecting...');
        window.location.href = 'index.html';
    });

    document.getElementById('emailForm')?.addEventListener('submit', (e) => {
        e.preventDefault();
        // Simulate login
        alert('Login successful! Redirecting...');
        window.location.href = 'index.html';
    });

    // Social login buttons
    document.querySelector('.btn-social.google')?.addEventListener('click', () => {
        alert('Google login coming soon!');
    });

    document.querySelector('.btn-social.github')?.addEventListener('click', () => {
        alert('GitHub login coming soon!');
    });
});
