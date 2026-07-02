document.addEventListener('DOMContentLoaded', () => {
    // Check if already logged in -> redirect to dashboard
    try {
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
    } catch (e) {
        console.warn("localStorage not available:", e);
    }

    // Banner
    const promoBanner = document.getElementById('promoBanner');
    const closeBanner = document.getElementById('closeBanner');
    if (closeBanner && promoBanner) {
        closeBanner.addEventListener('click', () => {
            promoBanner.style.display = 'none';
        });
    }

    // Sandbox Logic
    const sandboxBtn = document.getElementById('sandbox-btn');
    const tableBody = document.getElementById('sandbox-table-body');
    if (sandboxBtn && tableBody) {
            sandboxBtn.addEventListener('click', () => {
            sandboxBtn.disabled = true;
            sandboxBtn.innerText = 'Scanning...';
            
            // AI variation phrases
            const aiPhrases = [
                "Requires Review: AI Flag",
                "Flagged by AI",
                "Attention Needed: AI Detection",
                "AI Exception Detected",
                "Automated Flag",
                "Review Suggested: AI System",
                "Suspicious Activity Detected by AI"
            ];
            
            const getRandomPhrase = (suffix) => {
                const prefix = aiPhrases[Math.floor(Math.random() * aiPhrases.length)];
                return `${prefix} - ${suffix}`;
            };
            
            // simulate 1-second scanning animation
            setTimeout(() => {
                sandboxBtn.innerText = 'Scan Complete';
                
                // Add exception class to rows
                document.getElementById('row-3').className = 'row-exception';
                document.getElementById('row-5').className = 'row-exception';
                document.getElementById('row-6').className = 'row-exception';
                document.getElementById('row-9').className = 'row-exception';
                document.getElementById('row-10').className = 'row-exception';
                
                // Update reason text
                document.querySelector('#row-3 .reason-cell').innerText = getRandomPhrase("Personal entertainment on company card");
                document.querySelector('#row-5 .reason-cell').innerText = "HIGH AMOUNT: MAY REQUIRE REVIEW. Severe Exception. Amount 4500.0 is 10.5x higher than category norm.";
                document.querySelector('#row-6 .reason-cell').innerText = getRandomPhrase("Duplicate active subscription payment");
                document.querySelector('#row-9 .reason-cell').innerText = "Requires Review: Amount 112.50 exceeds meals policy limit of 100.00";
                document.querySelector('#row-10 .reason-cell').innerText = getRandomPhrase("Gambling on company ledger");
                
            }, 1000);
        });
    }
});
