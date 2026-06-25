document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const statusEl = document.getElementById('status');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Highlight dropzone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        dropzone.classList.add('dragover');
    }

    function unhighlight() {
        dropzone.classList.remove('dragover');
    }

    // Handle dropped files
    dropzone.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleFiles(files[0]);
        }
    }

    // Handle click to upload
    dropzone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            handleFiles(this.files[0]);
        }
    });

    function setStatus(message, type) {
        statusEl.textContent = message;
        statusEl.className = 'status ' + type;
    }

    function updateProgress(percent, message) {
        progressContainer.style.display = 'block';
        progressBar.style.width = percent + '%';
        progressText.textContent = message;
        progressPercent.textContent = percent + '%';
    }

    async function handleFiles(file) {
        setStatus('', '');
        updateProgress(0, 'Uploading file...');

        const formData = new FormData();
        formData.append('file', file);
        
        const keywords = document.getElementById('keywords').value;
        formData.append('keywords', keywords);

        const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:';
        const baseUrl = isLocalhost 
            ? 'http://127.0.0.1:8000' 
            : 'https://financial-data-parser.onrender.com';

        try {
            // Step 1: Upload file and get task_id
            const uploadResponse = await fetch(`${baseUrl}/upload`, {
                method: 'POST',
                body: formData
            });

            if (!uploadResponse.ok) {
                throw new Error(`Server error: ${uploadResponse.status}`);
            }

            const data = await uploadResponse.json();
            const taskId = data.task_id;

            // Step 2: Poll for status
            let completed = false;
            while (!completed) {
                await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
                
                const statusResponse = await fetch(`${baseUrl}/status/${taskId}`);
                if (!statusResponse.ok) continue;

                const statusData = await statusResponse.json();
                updateProgress(statusData.progress, statusData.message);

                if (statusData.status === 'completed') {
                    completed = true;
                } else if (statusData.status === 'error') {
                    throw new Error(statusData.message || "An error occurred during processing.");
                }
            }

            // Step 3: Download the file
            updateProgress(100, 'Downloading report...');
            const downloadResponse = await fetch(`${baseUrl}/download/${taskId}`);
            
            if (!downloadResponse.ok) throw new Error("Failed to download result.");

            const blob = await downloadResponse.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            
            let filename = 'processed_financial_data.xlsx';
            const disposition = downloadResponse.headers.get('Content-Disposition');
            if (disposition && disposition.indexOf('attachment') !== -1) {
                const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                const matches = filenameRegex.exec(disposition);
                if (matches != null && matches[1]) { 
                     filename = matches[1].replace(/['"]/g, '');
                }
            }

            a.download = filename;
            document.body.appendChild(a);
            a.click();
            
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            setStatus('File processed and downloaded successfully!', 'success');
            
            setTimeout(() => {
                progressContainer.style.display = 'none';
                statusEl.textContent = '';
                statusEl.className = 'status';
                fileInput.value = '';
            }, 3000);

        } catch (error) {
            console.error('Upload error:', error);
            progressContainer.style.display = 'none';
            setStatus(error.message || 'Error processing file. Ensure backend is running.', 'error');
        }
    }
});
