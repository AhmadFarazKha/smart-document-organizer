document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.querySelector('.file-info');
    const fileLabel = document.querySelector('.file-label');
    
    if (fileInput) {
        // Handle file selection change
        fileInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const file = this.files[0];
                fileInfo.textContent = `Selected file: ${file.name} (${formatFileSize(file.size)})`;
                fileLabel.style.borderColor = '#4285f4';
            } else {
                fileInfo.textContent = 'No file selected';
                fileLabel.style.borderColor = '';
            }
        });
        
        // Handle drag and drop events
        const dropArea = document.querySelector('.file-upload');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight() {
            fileLabel.style.borderColor = '#4285f4';
            fileLabel.style.backgroundColor = 'rgba(66, 133, 244, 0.05)';
        }
        
        function unhighlight() {
            fileLabel.style.borderColor = '';
            fileLabel.style.backgroundColor = '';
        }
        
        dropArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files && files.length) {
                fileInput.files = files;
                const file = files[0];
                fileInfo.textContent = `Selected file: ${file.name} (${formatFileSize(file.size)})`;
            }
        }
    }
    
    // Format file size in human-readable format
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
});