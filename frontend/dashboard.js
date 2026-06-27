
const baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://127.0.0.1:8000' 
    : 'https://financial-data-parser.onrender.com';

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('access_token');
    const mainApp = document.getElementById('mainApp');
    
    // Auth Guard
    if (!token) {
        window.location.href = 'login.html';
        return;
    } else {
        if(mainApp) mainApp.style.display = 'block'; // Show app if authenticated
    }

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

    async function handleFile(file) {
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
                window.location.href = 'login.html';
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
