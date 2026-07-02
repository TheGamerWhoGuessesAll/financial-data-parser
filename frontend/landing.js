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
            
            // Full sentence AI variations for Row 3 (Netflix)
            const netflixPhrases = [
                "Flagged by AI: Netflix is typically considered personal entertainment and may violate company card policy.",
                "Requires Review: AI detected a subscription service (Netflix) which often falls outside approved business expenses.",
                "AI Exception Detected: Streaming services like Netflix are usually not permitted on corporate ledgers.",
                "Attention Needed: Potential policy violation. AI flagged Netflix as a non-business entertainment expense."
            ];
            
            // Full sentence AI variations for Row 6 (AWS Duplicate)
            const awsPhrases = [
                "Review Suggested: AI System noticed this is the second AWS charge in a short timeframe, indicating a possible duplicate.",
                "Automated Flag: AI detected a duplicate active subscription payment for Amazon Web Services.",
                "Flagged by AI: This AWS transaction appears to be a redundant or duplicate charge.",
                "AI Exception: Multiple Amazon Web Services charges detected. Please verify if this is a duplicate billing."
            ];
            
            // Full sentence AI variations for Row 10 (Gambling)
            const casinoPhrases = [
                "Suspicious Activity Detected by AI: Transactions at casinos (MGM Grand) are strictly prohibited.",
                "AI Flag: High-risk vendor identified. Gambling and casino charges are not allowed.",
                "Requires Review: AI categorized this vendor as a casino/gambling establishment, violating policy.",
                "Automated Exception: AI flagged MGM Grand Casino. Corporate funds cannot be used for gambling."
            ];
            
            const getRandom = (arr) => arr[Math.floor(Math.random() * arr.length)];
            
            // Clear existing formatting if rescanning
            const exceptionRows = document.querySelectorAll('.row-exception');
            exceptionRows.forEach(row => {
                row.className = '';
                row.querySelector('.reason-cell').innerText = '-';
            });
            
            // simulate 1-second scanning animation
            setTimeout(() => {
                // Re-enable button for another scan
                sandboxBtn.disabled = false;
                sandboxBtn.innerText = 'Scan Again';
                
                // Add exception class to rows
                document.getElementById('row-3').className = 'row-exception';
                document.getElementById('row-5').className = 'row-exception';
                document.getElementById('row-6').className = 'row-exception';
                document.getElementById('row-9').className = 'row-exception';
                document.getElementById('row-10').className = 'row-exception';
                
                // Update reason text
                document.querySelector('#row-3 .reason-cell').innerText = getRandom(netflixPhrases);
                document.querySelector('#row-5 .reason-cell').innerText = "HIGH AMOUNT: MAY REQUIRE REVIEW. Severe Exception. Amount 4500.0 is 10.5x higher than category norm.";
                document.querySelector('#row-6 .reason-cell').innerText = getRandom(awsPhrases);
                document.querySelector('#row-9 .reason-cell').innerText = "Requires Review: Amount 112.50 exceeds meals policy limit of 100.00";
                document.querySelector('#row-10 .reason-cell').innerText = getRandom(casinoPhrases);
                
            }, 1000);
        });
    }
});
