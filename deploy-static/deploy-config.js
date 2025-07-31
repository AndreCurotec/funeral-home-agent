// Configuration for deployment
// Replace these URLs with your actual deployment URLs

const DEPLOYMENT_CONFIG = {
    // Replace with your actual Render backend URL
    BACKEND_URL: 'https://funeral-home-agent.onrender.com',
    
    // Replace with your actual Netlify frontend URL  
    FRONTEND_URL: 'https://funeral-home-finder.netlify.app'
};

// Auto-detect environment and return appropriate base URL
function getApiBaseUrl() {
    const isLocal = window.location.hostname === 'localhost' || 
                   window.location.hostname === '127.0.0.1' ||
                   window.location.hostname === '';
    
    if (isLocal) {
        // Local development - use same domain
        return '';
    } else {
        // Production deployment - use configured backend URL
        return DEPLOYMENT_CONFIG.BACKEND_URL;
    }
}

// Export for use in other scripts
window.DEPLOYMENT_CONFIG = DEPLOYMENT_CONFIG;
window.getApiBaseUrl = getApiBaseUrl;