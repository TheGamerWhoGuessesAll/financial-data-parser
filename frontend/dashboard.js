
const baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://127.0.0.1:8000' 
    : 'https://financial-data-parser.onrender.com';


document.addEventListener('DOMContentLoaded', () => {
    // Check URL for OAuth token
    const urlParams = new URLSearchParams(window.location.search);
    const oauthToken = urlParams.get('token');
    const paymentSuccess = urlParams.get('success');
    
    if (oauthToken) {
        localStorage.setItem('access_token', oauthToken);
        window.history.replaceState({}, document.title, window.location.pathname);
    }
    
    if (paymentSuccess) {
        const banner = document.getElementById('successBanner');
        if (banner) banner.style.display = 'block';
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    const token = localStorage.getItem('access_token');
    const mainApp = document.getElementById('mainApp');
    
    // Auth Guard
    if (!token) {
        window.location.href = 'login.html';
        return;
    } else {
        if(mainApp) mainApp.style.display = 'block'; // Show app if authenticated
    }
    // Fetch User Info
    async function fetchUserInfo() {
        try {
            const res = await fetch(`${baseUrl}/user/me`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                const planEl = document.getElementById('planDisplay');
                const creditEl = document.getElementById('creditDisplay');
                if (planEl) {
                    const planName = data.plan.charAt(0).toUpperCase() + data.plan.slice(1);
                    planEl.innerText = `Plan: ${planName}`;
                }
                if (creditEl) {
                    let limitText = data.limit === 'Unlimited' ? '∞' : data.limit;
                    creditEl.innerText = `Usage: ${data.rows_processed_this_month} / ${limitText} rows`;
                    
                    const usageBar = document.getElementById('usageBar');
                    if (usageBar) {
                        if (data.limit === 'Unlimited') {
                            usageBar.style.width = '100%';
                            usageBar.style.background = '#10b981';
                        } else {
                            let pct = (data.rows_processed_this_month / data.limit) * 100;
                            if (pct > 100) pct = 100;
                            usageBar.style.width = `${pct}%`;
                            if (pct > 90) usageBar.style.background = '#ef4444';
                            else usageBar.style.background = 'var(--primary)';
                        }
                    }
                }
                const upgradeBtn = document.getElementById('upgradeBtn');
                if (upgradeBtn && data.plan === 'unlimited') {
                    upgradeBtn.style.display = 'none';
                }
            } else if (res.status === 401) {
                localStorage.removeItem('access_token');
                window.location.href = 'login.html';
            }
        } catch (e) {
            console.error(e);
        }
    }
    fetchUserInfo();


    // Logout
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            localStorage.removeItem('access_token');
            window.location.href = 'login.html';
        });
    }

    // Upload Logic
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const statusDiv = document.getElementById('status');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');

    if(dropzone && fileInput) {
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
    }

    let currentTaskId = null;
    let pollInterval = null;
    let visualProgress = 0;
    let targetProgress = 0;
    let animationFrameId = null;

    function updateVisualProgress() {
        // Smoothly interpolate towards the target
        if (visualProgress < targetProgress) {
            visualProgress += (targetProgress - visualProgress) * 0.05;
        } 
        // Creep forward slowly while waiting for the next update (to make it feel continuous)
        else if (visualProgress < 95 && targetProgress > 0 && targetProgress < 100) {
            visualProgress += 0.02;
        }
        
        if (visualProgress > 100) visualProgress = 100;
        
        progressBar.style.width = `${visualProgress}%`;
        progressPercent.innerText = `${Math.floor(visualProgress)}%`;
        
        animationFrameId = requestAnimationFrame(updateVisualProgress);
    }

    async function handleFile(file) {
        // Reset file input so the same file can be selected again
        if (fileInput) fileInput.value = '';

        const formData = new FormData();
        formData.append('file', file);

        statusDiv.className = 'status loading';
        statusDiv.innerText = 'Uploading file...';
        progressContainer.style.display = 'none';
        
        visualProgress = 0;
        targetProgress = 0;
        if (animationFrameId) cancelAnimationFrame(animationFrameId);

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
                window.location.href = 'login.html';
                return;
            }

            const data = await response.json();
            if (response.ok) {
                currentTaskId = data.task_id;
                statusDiv.innerText = 'Processing started...';
                progressContainer.style.display = 'block';
                updateVisualProgress(); // start animation loop
                pollStatus();
            } else {
                statusDiv.className = 'status error';
                statusDiv.innerText = data.detail || 'An error occurred';
                fetchUserInfo();
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
                const response = await fetch(`${baseUrl}/status/${currentTaskId}`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                const data = await response.json();
                
                if (response.ok) {
                    targetProgress = data.progress;
                    progressText.innerText = data.message;
                    
                    if (data.status === 'completed') {
                        clearInterval(pollInterval);
                        targetProgress = 100;
                        visualProgress = 100; // snap to 100 on completion
                        progressBar.style.width = '100%';
                        progressPercent.innerText = '100%';
                        setTimeout(() => { if(animationFrameId) cancelAnimationFrame(animationFrameId); }, 100);
                        
                        statusDiv.className = 'status success';
                        statusDiv.innerText = 'Processing complete!';
                        progressContainer.style.display = 'none';
                        
                        setTimeout(async () => {
                            try {
                                const downloadRes = await fetch(`${baseUrl}/download/${currentTaskId}`, {
                                    headers: {
                                        'Authorization': `Bearer ${token}`
                                    }
                                });
                                
                                if (!downloadRes.ok) throw new Error('Download failed');
                                
                                const blob = await downloadRes.blob();
                                const url = window.URL.createObjectURL(blob);
                                const link = document.createElement('a');
                                link.href = url;
                                // We can try to extract the filename from the Content-Disposition header if needed,
                                // but for simplicity, we can default it.
                                link.download = 'anomalies.xlsx';
                                document.body.appendChild(link);
                                link.click();
                                document.body.removeChild(link);
                                window.URL.revokeObjectURL(url);
                            } catch (e) {
                                console.error('Download error:', e);
                                statusDiv.className = 'status error';
                                statusDiv.innerText = 'Failed to download file.';
                            }
                        }, 1000);
                    } else if (data.status === 'error') {
                        clearInterval(pollInterval);
                        progressContainer.style.display = 'none';
                        statusDiv.className = 'status error';
                        statusDiv.innerText = 'Error: ' + data.message;
                        fetchUserInfo();
                    }
                }
            } catch (error) {
                console.error("Polling error", error);
            }
        }, 1500);
    }
});
