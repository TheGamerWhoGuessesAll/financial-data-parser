
document.addEventListener('DOMContentLoaded', () => {
    // Check if already logged in -> redirect to dashboard
    if (localStorage.getItem('access_token')) {
        const loginBtn = document.getElementById('navLoginBtn');
        const signupBtn = document.getElementById('navSignupBtn');
        if(loginBtn) {
            loginBtn.innerText = 'Go to Dashboard';
            loginBtn.href = 'dashboard.html';
        }
        if(signupBtn) {
            signupBtn.style.display = 'none';
        }
    }

    
    
    // Banner
    const promoBanner = document.getElementById('promoBanner');
    const closeBanner = document.getElementById('closeBanner');
    if (closeBanner && promoBanner) {
        closeBanner.addEventListener('click', () => {
            promoBanner.style.display = 'none';
        });
    }
});
