
const baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://127.0.0.1:8000' 
    : 'https://financial-data-parser.onrender.com';

document.addEventListener('DOMContentLoaded', () => {
    // If already logged in, redirect to dashboard immediately
    if (localStorage.getItem('access_token')) {
        window.location.href = 'dashboard.html';
        return;
    }

    const authBtn = document.getElementById('authBtn');
    const emailInput = document.getElementById('authEmail');
    const passwordInput = document.getElementById('authPassword');
    const authStatus = document.getElementById('authStatus');

    // Get mode from script tag data attribute (login or signup)
    const scriptTag = document.querySelector('script[data-mode]');
    const mode = scriptTag ? scriptTag.getAttribute('data-mode') : 'login';

    if (authBtn) {
        authBtn.addEventListener('click', async () => {
            const email = emailInput.value;
            const password = passwordInput.value;

            if (!email || !password) {
                authStatus.innerText = 'Please enter email and password';
                return;
            }

            authBtn.disabled = true;
            authBtn.innerText = 'Connecting...';
            authStatus.innerText = '';

            try {
                const response = await fetch(`${baseUrl}/${mode}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });

                const data = await response.json();

                if (response.ok) {
                    localStorage.setItem('access_token', data.access_token);
                    window.location.href = 'dashboard.html';
                } else {
                    authStatus.innerText = data.detail || 'Authentication failed.';
                    authBtn.disabled = false;
                    authBtn.innerText = mode === 'login' ? 'Log In' : 'Sign Up';
                }
            } catch (e) {
                authStatus.innerText = 'Network error. Please try again.';
                authBtn.disabled = false;
                authBtn.innerText = mode === 'login' ? 'Log In' : 'Sign Up';
            }
        });
    }
    // Forgot Password Logic
    const forgotPasswordLink = document.getElementById('forgotPasswordLink');
    const forgotPasswordModal = document.getElementById('forgotPasswordModal');
    const resetEmailInput = document.getElementById('resetEmailInput');
    const sendResetBtn = document.getElementById('sendResetBtn');
    const resetStatus = document.getElementById('resetStatus');

    if (forgotPasswordLink && forgotPasswordModal) {
        forgotPasswordLink.addEventListener('click', (e) => {
            e.preventDefault();
            forgotPasswordModal.style.display = 'flex';
        });
    }

    if (sendResetBtn) {
        sendResetBtn.addEventListener('click', async () => {
            const email = resetEmailInput.value;
            if (!email) {
                resetStatus.style.color = '#ef4444';
                resetStatus.innerText = 'Please enter an email address';
                return;
            }

            sendResetBtn.disabled = true;
            sendResetBtn.innerText = 'Sending...';
            resetStatus.innerText = '';

            try {
                const response = await fetch(`${baseUrl}/forgot-password`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email })
                });
                
                const data = await response.json();
                
                resetStatus.style.color = response.ok ? '#22c55e' : '#ef4444';
                resetStatus.innerText = data.message || data.detail || 'Failed to send reset email';
            } catch (e) {
                resetStatus.style.color = '#ef4444';
                resetStatus.innerText = 'Network error. Please try again.';
            } finally {
                sendResetBtn.disabled = false;
                sendResetBtn.innerText = 'Send Recovery Link';
            }
        });
    }
});
