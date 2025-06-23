// Main JavaScript file for Wavelet Fusion App

// Global variables
let uploadedImages = [];
let fusionSessionId = null;
let processingInProgress = false;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize file upload handlers
    initializeFileUpload();
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize progress tracking
    initializeProgressTracking();
    
    console.log('Wavelet Fusion App initialized');
}

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// File upload functionality
function initializeFileUpload() {
    const uploadArea = document.querySelector('.upload-area');
    const fileInput = document.getElementById('imageInput');
    
    if (uploadArea && fileInput) {
        // Drag and drop handlers
        uploadArea.addEventListener('dragover', handleDragOver);
        uploadArea.addEventListener('drop', handleDrop);
        uploadArea.addEventListener('dragleave', handleDragLeave);
        
        // File input change handler
        fileInput.addEventListener('change', handleFileSelect);
    }
}

function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    processFiles(files);
}

function handleDragLeave(e) {
    e.currentTarget.classList.remove('dragover');
}

function handleFileSelect(e) {
    const files = e.target.files;
    processFiles(files);
}

function processFiles(files) {
    const allowedTypes = ['image/jpeg', 'image/png', 'image/tiff'];
    const maxSize = 16 * 1024 * 1024; // 16MB
    
    Array.from(files).forEach(file => {
        if (!allowedTypes.includes(file.type)) {
            showAlert('Invalid file type: ' + file.name, 'error');
            return;
        }
        
        if (file.size > maxSize) {
            showAlert('File too large: ' + file.name + ' (max 16MB)', 'error');
            return;
        }
        
        uploadFile(file);
    });
}

function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Get session ID from global variable or window
    const sessionId = window.fusionSessionId || fusionSessionId;

    // Show upload progress
    const progressContainer = createProgressIndicator(file.name);
    const previewContainer = document.getElementById('imagePreview');
    if (previewContainer) {
        previewContainer.appendChild(progressContainer);
    }

    fetch(`/upload_file/${sessionId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Remove progress indicator
            progressContainer.remove();
            
            // Add image preview
            addImagePreview(data);
            
            // Update counter
            updateImageCounter(data.current_count, data.total_needed);
            
            // Enable process button if all images uploaded
            if (data.current_count >= data.total_needed) {
                enableProcessButton();
            }
        } else {
            progressContainer.remove();
            showAlert(data.error, 'error');
        }
    })
    .catch(error => {
        progressContainer.remove();
        showAlert('Upload failed: ' + error.message, 'error');
    });
}

function createProgressIndicator(filename) {
    const div = document.createElement('div');
    div.className = 'col-md-4 mb-3';
    div.innerHTML = `
        <div class="card">
            <div class="card-body text-center">
                <div class="spinner-border text-primary mb-2" role="status">
                    <span class="visually-hidden">Uploading...</span>
                </div>
                <p class="small mb-0">${filename}</p>
                <div class="progress mt-2">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" style="width: 100%"></div>
                </div>
            </div>
        </div>
    `;
    return div;
}

function addImagePreview(data) {
    const previewContainer = document.getElementById('imagePreview');
    const imageDiv = document.createElement('div');
    imageDiv.className = 'col-md-4 mb-3 fade-in';
    
    imageDiv.innerHTML = `
        <div class="card image-preview">
            <img src="/uploads/${data.filename}" alt="${data.original_filename}" class="card-img-top">
            <div class="card-body p-2">
                <p class="small mb-0 text-truncate" title="${data.original_filename}">
                    ${data.original_filename}
                </p>
            </div>
            <button class="remove-btn" onclick="removeImage('${data.filename}')">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    previewContainer.appendChild(imageDiv);
    uploadedImages.push(data);
}

function removeImage(filename) {
    // Remove from uploaded images array
    uploadedImages = uploadedImages.filter(img => img.filename !== filename);
    
    // Remove from DOM
    const imageElements = document.querySelectorAll('.image-preview img');
    imageElements.forEach(img => {
        if (img.src.includes(filename)) {
            img.closest('.col-md-4').remove();
        }
    });
    
    // Update counter and disable process button if needed
    updateImageCounter(uploadedImages.length, uploadedImages.length > 0 ? uploadedImages[0].total_needed : 0);
    
    if (uploadedImages.length === 0) {
        disableProcessButton();
    }
}

function updateImageCounter(current, total) {
    const counter = document.getElementById('imageCounter');
    if (counter) {
        counter.textContent = `${current}/${total} images uploaded`;
    }
}

function enableProcessButton() {
    const processBtn = document.getElementById('processBtn');
    if (processBtn) {
        processBtn.disabled = false;
        processBtn.innerHTML = '<i class="fas fa-cog me-2"></i>Process Fusion';
    }
}

function disableProcessButton() {
    const processBtn = document.getElementById('processBtn');
    if (processBtn) {
        processBtn.disabled = true;
        processBtn.innerHTML = '<i class="fas fa-cog me-2"></i>Upload images first';
    }
}

function processFusion() {
    if (processingInProgress) return;
    
    processingInProgress = true;
    const processBtn = document.getElementById('processBtn');
    
    // Update button state
    processBtn.disabled = true;
    processBtn.innerHTML = '<i class="fas fa-cog fa-spin me-2"></i>Processing...';
    
    // Show processing overlay
    showProcessingOverlay();
    
    fetch(`/process_fusion/${fusionSessionId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Redirect to result page
            window.location.href = data.result_url;
        } else {
            hideProcessingOverlay();
            showAlert(data.error, 'error');
            processBtn.disabled = false;
            processBtn.innerHTML = '<i class="fas fa-cog me-2"></i>Process Fusion';
            processingInProgress = false;
        }
    })
    .catch(error => {
        hideProcessingOverlay();
        showAlert('Processing failed: ' + error.message, 'error');
        processBtn.disabled = false;
        processBtn.innerHTML = '<i class="fas fa-cog me-2"></i>Process Fusion';
        processingInProgress = false;
    });
}

function showProcessingOverlay() {
    const overlay = document.createElement('div');
    overlay.id = 'processing-overlay';
    overlay.className = 'spinner-overlay';
    overlay.innerHTML = `
        <div class="spinner-content">
            <div class="spinner-border text-light mb-3" style="width: 3rem; height: 3rem;" role="status">
                <span class="visually-hidden">Processing...</span>
            </div>
            <h4>Processing Fusion</h4>
            <p>Applying DWT algorithm to combine your images...</p>
            <div class="progress" style="width: 300px;">
                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                     role="progressbar" style="width: 100%"></div>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
}

function hideProcessingOverlay() {
    const overlay = document.getElementById('processing-overlay');
    if (overlay) {
        overlay.remove();
    }
}

// Form validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

// Progress tracking
function initializeProgressTracking() {
    // Check for processing sessions on dashboard
    const processingSessions = document.querySelectorAll('.status-processing');
    if (processingSessions.length > 0) {
        // Poll for updates every 5 seconds
        setInterval(checkProcessingStatus, 5000);
    }
}

function checkProcessingStatus() {
    const processingSessions = document.querySelectorAll('.status-processing');
    processingSessions.forEach(session => {
        const sessionId = session.dataset.sessionId;
        if (sessionId) {
            fetch(`/status/${sessionId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status !== 'processing') {
                        // Refresh the page to show updated status
                        window.location.reload();
                    }
                })
                .catch(error => {
                    console.error('Error checking status:', error);
                });
        }
    });
}

// Utility functions
function showAlert(message, type = 'info') {
    const alertContainer = document.createElement('div');
    alertContainer.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    alertContainer.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at the top of the main content
    const main = document.querySelector('main');
    if (main) {
        main.insertBefore(alertContainer, main.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alertContainer.remove();
        }, 5000);
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showAlert('Copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy: ', err);
        showAlert('Failed to copy to clipboard', 'error');
    });
}

// Session management functions
function setFusionSessionId(sessionId) {
    fusionSessionId = sessionId;
}

// Image comparison functionality for result page
function initializeImageComparison() {
    const compareBtn = document.getElementById('compareBtn');
    if (compareBtn) {
        compareBtn.addEventListener('click', toggleImageComparison);
    }
}

function toggleImageComparison() {
    const originalImages = document.getElementById('originalImages');
    const fusedResult = document.getElementById('fusedResult');
    
    if (originalImages.style.display === 'none') {
        originalImages.style.display = 'block';
        fusedResult.style.display = 'none';
        document.getElementById('compareBtn').innerHTML = '<i class="fas fa-eye me-2"></i>Show Result';
    } else {
        originalImages.style.display = 'none';
        fusedResult.style.display = 'block';
        document.getElementById('compareBtn').innerHTML = '<i class="fas fa-images me-2"></i>Show Originals';
    }
}

// Export functions for global access
window.handleDrop = handleDrop;
window.handleDragOver = handleDragOver;
window.handleFileSelect = handleFileSelect;
window.processFusion = processFusion;
window.removeImage = removeImage;
window.setFusionSessionId = setFusionSessionId;
window.shareResult = function() {
    if (navigator.share) {
        navigator.share({
            title: 'Wavelet Fusion Result',
            text: 'Check out my image fusion result created with DWT algorithm!',
            url: window.location.href
        });
    } else {
        copyToClipboard(window.location.href);
    }
};

console.log('Wavelet Fusion App JavaScript loaded successfully');
