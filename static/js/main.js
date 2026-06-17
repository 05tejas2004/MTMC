// Main JavaScript for Municipal Grievance System

document.addEventListener('DOMContentLoaded', function() {
    console.log('MuniSys Loaded');
    
    // Auto-get location if on complaint page
    const latInput = document.getElementById('lat');
    if (latInput) {
        initGeolocation();
    }
    
    // Initialize charts if on admin dashboard
    if (document.getElementById('complaintChart')) {
        initCharts();
    }
});

// Geolocation Function
function initGeolocation() {
    // Only attempt if browser supports geolocation
    if ("geolocation" in navigator) {
        console.log("Geolocation available");
    }
}

function getLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                document.getElementById('lat').value = position.coords.latitude.toFixed(6);
                document.getElementById('lng').value = position.coords.longitude.toFixed(6);
                document.getElementById('location_status').innerHTML = '<i class="fas fa-check-circle"></i> Location Captured!';
                
                // Show success message
                showAlert('Location captured successfully!', 'success');
            },
            function(error) {
                showAlert('Error getting location: ' + error.message, 'danger');
            }
        );
    } else {
        showAlert('Geolocation is not supported by this browser.', 'warning');
    }
}

function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Charts Initialization
function initCharts() {
    // This will be initialized by Chart.js in admin_dashboard.html
    console.log('Initializing Dashboard Charts');
}

// File upload preview
function previewImage(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            // You can add image preview logic here
            console.log('Image selected:', input.files[0].name);
        };
        reader.readAsDataURL(input.files[0]);
    }
}