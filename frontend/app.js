document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const statusEl = document.getElementById('status');

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

    async function handleFiles(file) {
        setStatus('Processing file...', 'loading');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('https://financial-data-parser.onrender.com/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                let errorMessage = `Server error: ${response.status}`;
                try {
                    const errData = await response.json();
                    if (errData && errData.detail) {
                        errorMessage = errData.detail;
                    }
                } catch (e) {
                    // Response was not JSON
                }
                throw new Error(errorMessage);
            }

            // Expecting the backend to return the parsed Excel file (.xlsx)
            const blob = await response.blob();
            
            // Create a temporary link to download the blob
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            
            // Attempt to get filename from Content-Disposition header, fallback to default
            let filename = 'processed_financial_data.xlsx';
            const disposition = response.headers.get('Content-Disposition');
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
            
            // Cleanup
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            setStatus('File processed and downloaded!', 'success');
            
            // Reset dropzone state after delay
            setTimeout(() => {
                statusEl.textContent = '';
                statusEl.className = 'status';
                fileInput.value = '';
            }, 3000);

        } catch (error) {
            console.error('Upload error:', error);
            setStatus(error.message || 'Error processing file. Ensure backend is running.', 'error');
        }
    }
});
