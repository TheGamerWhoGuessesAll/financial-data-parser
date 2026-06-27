
const baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://127.0.0.1:8000' 
    : 'https://financial-data-parser.onrender.com';

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const authOverlay = document.getElementById('authOverlay');
    const landingPage = document.getElementById('landingPage');
    const mainApp = document.getElementById('mainApp');
    const cookieOverlay = document.getElementById('cookieOverlay');
    
    const loginBtn = document.getElementById('loginBtn');
    const signupBtn = document.getElementById('signupBtn');
    const closeAuthBtn = document.getElementById('closeAuthBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    
    const navLoginBtn = document.getElementById('navLoginBtn');
    const navSignupBtn = document.getElementById('navSignupBtn');
    
    const acceptCookiesBtn = document.getElementById('acceptCookiesBtn');
    const manageCookiesBtn = document.getElementById('manageCookiesBtn');
    const promoBanner = document.getElementById('promoBanner');
    const closeBanner = document.getElementById('closeBanner');
    
    // Cookie Popup logic
    if (localStorage.getItem('cookiesAccepted') === 'true') {
        cookieOverlay.style.display = 'none';
    }
    
    const dismissCookies = () => {
        cookieOverlay.style.display = 'none';
        localStorage.setItem('cookiesAccepted', 'true');
    };
    
    acceptCookiesBtn.addEventListener('click', dismissCookies);
    manageCookiesBtn.addEventListener('click', dismissCookies);
    
    if (closeBanner) {
        closeBanner.addEventListener('click', () => {
            promoBanner.style.display = 'none';
        });
    }

    // Check auth status
    const token = localStorage.getItem('access_token');
    if (token) {
        landingPage.style.display = 'none';
        mainApp.style.display = 'block';
    }

    // Show Auth Modal
    const showAuth = () => {
        authOverlay.style.display = 'flex';
    };
    
    const hideAuth = () => {
        authOverlay.style.display = 'none';
    };

    if (navLoginBtn) navLoginBtn.addEventListener('click', showAuth);
    if (navSignupBtn) navSignupBtn.addEventListener('click', showAuth);
    if (closeAuthBtn) closeAuthBtn.addEventListener('click', hideAuth);

    // Auth Actions
    const handleAuth = async (endpoint) => {
        const email = document.getElementById('authEmail').value;
        const password = document.getElementById('authPassword').value;
        const authStatus = document.getElementById('authStatus');

        if (!email || !password) {
            authStatus.innerText = 'Please enter email and password';
            return;
        }

        authStatus.innerText = 'Connecting...';

        try {
            const response = await fetch(`${baseUrl}/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                localStorage.setItem('access_token', data.access_token);
                authOverlay.style.display = 'none';
                landingPage.style.display = 'none';
                mainApp.style.display = 'block';
            } else {
                authStatus.innerText = data.detail || 'Authentication failed.';
            }
        } catch (e) {
            authStatus.innerText = 'Network error. Please try again.';
        }
    };

    loginBtn.addEventListener('click', () => handleAuth('login'));
    signupBtn.addEventListener('click', () => handleAuth('signup'));

    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('access_token');
        mainApp.style.display = 'none';
        landingPage.style.display = 'block';
    });

    // App Logic (Drag & Drop, Upload)
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const statusDiv = document.getElementById('status');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');

    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFile(e.target.files[0]);
        }
    });

    let currentTaskId = null;
    let pollInterval = null;

    async function handleFile(file) {
        const token = localStorage.getItem('access_token');
        if (!token) {
            showAuth();
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('keywords', document.getElementById('keywords').value);

        statusDiv.className = 'status loading';
        statusDiv.innerText = 'Uploading file...';
        progressContainer.style.display = 'none';

        try {
            const response = await fetch(`${baseUrl}/upload`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });

            if (response.status === 401) {
                localStorage.removeItem('access_token');
                mainApp.style.display = 'none';
                landingPage.style.display = 'block';
                showAuth();
                return;
            }

            const data = await response.json();
            if (response.ok) {
                currentTaskId = data.task_id;
                statusDiv.innerText = 'Processing started...';
                progressContainer.style.display = 'block';
                pollStatus();
            } else {
                statusDiv.className = 'status error';
                statusDiv.innerText = data.detail || 'An error occurred';
            }
        } catch (error) {
            statusDiv.className = 'status error';
            statusDiv.innerText = 'Failed to connect to server';
        }
    }

    async function pollStatus() {
        if (pollInterval) clearInterval(pollInterval);
        
        pollInterval = setInterval(async () => {
            if (!currentTaskId) return;
            
            try {
                const token = localStorage.getItem('access_token');
                const response = await fetch(`${baseUrl}/status/${currentTaskId}`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                const data = await response.json();
                
                if (response.ok) {
                    progressBar.style.width = `${data.progress}%`;
                    progressPercent.innerText = `${data.progress}%`;
                    progressText.innerText = data.message;
                    
                    if (data.status === 'completed') {
                        clearInterval(pollInterval);
                        statusDiv.className = 'status success';
                        statusDiv.innerText = 'Processing complete!';
                        
                        setTimeout(() => {
                            const link = document.createElement('a');
                            link.href = `${baseUrl}/download/${currentTaskId}?token=${token}`;
                            link.style.display = 'none';
                            document.body.appendChild(link);
                            link.click();
                            document.body.removeChild(link);
                        }, 1000);
                    } else if (data.status === 'error') {
                        clearInterval(pollInterval);
                        statusDiv.className = 'status error';
                        statusDiv.innerText = 'Error: ' + data.message;
                    }
                }
            } catch (error) {
                console.error("Polling error", error);
            }
        }, 1500);
    }
});
