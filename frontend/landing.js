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
            
            // simulate 1-second scanning animation
            setTimeout(() => {
                sandboxBtn.innerText = 'Scan Complete';
                
                tableBody.innerHTML = `
                    <tr>
                        <td>06/01/2026</td>
                        <td>Microsoft 365</td>
                        <td>$12.50</td>
                        <td>-</td>
                    </tr>
                    <tr>
                        <td>06/03/2026</td>
                        <td>Uber Rides</td>
                        <td>$42.10</td>
                        <td>-</td>
                    </tr>
                    <tr class="row-exception">
                        <td>06/05/2026</td>
                        <td>Netflix</td>
                        <td>$15.49</td>
                        <td>Requires Review: AI Flag - Personal entertainment on company card</td>
                    </tr>
                    <tr>
                        <td>06/10/2026</td>
                        <td>Amazon Web Services</td>
                        <td>$412.00</td>
                        <td>-</td>
                    </tr>
                    <tr class="row-exception">
                        <td>06/12/2026</td>
                        <td>Best Buy</td>
                        <td>$4,500.00</td>
                        <td>HIGH AMOUNT: MAY REQUIRE REVIEW. Severe Exception. Amount 4500.0 is 10.5x higher than category norm.</td>
                    </tr>
                    <tr class="row-exception">
                        <td>06/14/2026</td>
                        <td>Amazon Web Services</td>
                        <td>$412.00</td>
                        <td>Requires Review: AI Flag - Duplicate active subscription payment</td>
                    </tr>
                    <tr>
                        <td>06/18/2026</td>
                        <td>Delta Airlines</td>
                        <td>$350.00</td>
                        <td>-</td>
                    </tr>
                    <tr>
                        <td>06/20/2026</td>
                        <td>FedEx Shipping</td>
                        <td>$18.50</td>
                        <td>-</td>
                    </tr>
                    <tr class="row-exception">
                        <td>06/24/2026</td>
                        <td>Joe's Coffee Shop</td>
                        <td>$112.50</td>
                        <td>Requires Review: Amount 112.50 exceeds meals policy limit of 100.00</td>
                    </tr>
                    <tr class="row-exception">
                        <td>06/28/2026</td>
                        <td>MGM Grand Casino</td>
                        <td>$500.00</td>
                        <td>Requires Review: AI Flag - Gambling on company ledger</td>
                    </tr>
                `;
            }, 1000);
        });
    }
});
