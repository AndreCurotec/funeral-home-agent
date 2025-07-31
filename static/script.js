class ChatBot {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.requirementsStatus = document.getElementById('requirementsStatus');
        this.sessionId = this.generateSessionId();
        this.currentRequirements = {};
        
        this.setupEventListeners();
        this.initializeChat();
    }
    
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    initializeChat() {
        // Clear the default welcome message and let the backend handle it
        this.chatMessages.innerHTML = '';
        
        // Send initial message to get welcome from backend
        setTimeout(() => {
            this.sendMessage('Hello');
        }, 500);
    }
    
    setupEventListeners() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-focus input when page loads
        this.messageInput.focus();
    }
    
    async sendMessage(customMessage = null) {
        const message = customMessage || this.messageInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input and disable send button
        this.messageInput.value = '';
        this.sendButton.disabled = true;
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            // Send message to backend
            const response = await this.callChatAPI(message);
            
            // Remove typing indicator
            this.removeTypingIndicator();
            
            // Add bot response
            this.addMessage(response.response, 'bot');
            
            // Update requirements status
            if (response.requirements_status) {
                this.updateRequirementsStatus(response.requirements_status);
            }
            
            // If funeral homes are provided, display them
            if (response.funeral_homes && response.funeral_homes.length > 0) {
                this.displayFuneralHomes(response.funeral_homes, response.requirements_status);
            }
            
            // Add quick action buttons if appropriate
            this.addQuickActions(response);
            
        } catch (error) {
            console.error('Error:', error);
            this.removeTypingIndicator();
            this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
        } finally {
            this.sendButton.disabled = false;
            this.messageInput.focus();
        }
    }
    
    async callChatAPI(message) {
        const apiBaseUrl = window.getApiBaseUrl();
        const response = await fetch(`${apiBaseUrl}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: this.sessionId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    addMessage(content, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = content; // Using innerHTML to support HTML formatting
        
        messageDiv.appendChild(messageContent);
        this.chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot-message';
        typingDiv.id = 'typing-indicator';
        
        const typingContent = document.createElement('div');
        typingContent.className = 'typing-indicator';
        
        const typingDots = document.createElement('div');
        typingDots.className = 'typing-dots';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'typing-dot';
            typingDots.appendChild(dot);
        }
        
        typingContent.appendChild(typingDots);
        typingDiv.appendChild(typingContent);
        this.chatMessages.appendChild(typingDiv);
        
        // Scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    updateRequirementsStatus(status) {
        this.currentRequirements = status;
        if (!this.requirementsStatus) return;
        
        const completedFields = [];
        const missingFields = status.missing_fields || [];
        
        if (status.location) completedFields.push(`📍 ${status.location}`);
        if (status.service_type) completedFields.push(`⚱️ ${status.service_type.replace(/_/g, ' ')}`);
        if (status.timeframe) completedFields.push(`⏰ ${status.timeframe.replace(/_/g, ' ')}`);
        if (status.preference) completedFields.push(`💰 ${status.preference}`);
        
        let html = '<div class="requirements-header">Your Requirements:</div>';
        
        if (completedFields.length > 0) {
            html += '<div class="completed-requirements">' + completedFields.join(' • ') + '</div>';
        }
        
        if (missingFields.length > 0) {
            html += '<div class="missing-requirements">Still needed: ' + 
                   missingFields.map(field => field.replace(/_/g, ' ')).join(', ') + '</div>';
        }
        
        if (status.shown_homes_count > 0) {
            html += `<div class="homes-count">Shown: ${status.shown_homes_count} funeral homes</div>`;
        }
        
        this.requirementsStatus.innerHTML = html;
    }
    
    displayFuneralHomes(funeralHomes, requirementsStatus) {
        const funeralHomesContainer = document.createElement('div');
        funeralHomesContainer.className = 'message bot-message';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const shownCount = requirementsStatus?.shown_homes_count || 0;
        const currentCount = funeralHomes.length;
        const isFirstSet = shownCount <= currentCount;
        
        // Dynamic message based on actual number of results
        let countText = currentCount === 1 ? '1 funeral home' : `${currentCount} funeral homes`;
        
        let html = isFirstSet 
            ? `<strong>🎯 Here ${currentCount === 1 ? 'is' : 'are'} ${countText} that ${currentCount === 1 ? 'matches' : 'match'} your criteria:</strong><br><br>`
            : `<strong>🔄 Here ${currentCount === 1 ? 'is' : 'are'} ${countText} additional ${currentCount === 1 ? 'option' : 'options'} (total shown: ${shownCount}):</strong><br><br>`;
        
        funeralHomes.forEach((home, index) => {
            const ratingStars = '⭐'.repeat(Math.floor(home.rating)) + (home.rating % 1 >= 0.5 ? '⭐' : '');
            html += `
                <div class="funeral-home-card">
                    <h3>${home.name}</h3>
                    <p><strong>📍 Location:</strong> ${home.location}</p>
                    <p><strong>⭐ Rating:</strong> <span class="rating">${home.rating}/5</span> ${ratingStars}</p>
                    <p><strong>💰 Estimated Price:</strong> <span class="price">${home.price}</span></p>
                </div>
            `;
        });
        
        content.innerHTML = html;
        funeralHomesContainer.appendChild(content);
        this.chatMessages.appendChild(funeralHomesContainer);
        
        // Scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    addQuickActions(response) {
        const requirementsStatus = response.requirements_status;
        
        // Add quick actions for different states
        if (response.funeral_homes && response.funeral_homes.length > 0) {
            // Showing funeral homes - add standard actions
            this.addFuneralHomeActions(response, requirementsStatus);
        } else if (response.is_complete && (!response.funeral_homes || response.funeral_homes.length === 0)) {
            // No results found - add suggested locations
            this.addNoResultsActions(requirementsStatus);
        } else if (requirementsStatus && requirementsStatus.state === "adjusting_preferences") {
            // In adjustment state - add preference adjustment actions
            this.addPreferenceAdjustmentActions(requirementsStatus);
        } else if (requirementsStatus && requirementsStatus.missing_fields && requirementsStatus.missing_fields.length > 0) {
            // Missing info - add helpful suggestions
            this.addInfoCollectionActions(requirementsStatus);
        }
    }
    
    addFuneralHomeActions(response, requirementsStatus) {
        const shownCount = requirementsStatus?.shown_homes_count || 0;
        
        const actionsContainer = document.createElement('div');
        actionsContainer.className = 'message bot-message';
        
        const content = document.createElement('div');
        content.className = 'message-content quick-actions';
        
        let html = '<div class="quick-actions-header">What would you like to do next?</div>';
        html += '<div class="quick-actions-buttons">';
        
        // Always show "These look good" option
        html += '<button class="quick-action-btn satisfied" onclick="chatBot.sendMessage(\'These look good\')">✅ These look good</button>';
        
        // Show "Show more options" if we haven't hit the limit
        if (shownCount < 9) {
            html += '<button class="quick-action-btn more-options" onclick="chatBot.sendMessage(\'Show me more options\')">Show more options</button>';
        }
        
        // Always show "Different options" 
        html += '<button class="quick-action-btn different" onclick="chatBot.sendMessage(\'I want different options\')">🔄 Different criteria</button>';
        
        html += '</div>';
        
        content.innerHTML = html;
        actionsContainer.appendChild(content);
        this.chatMessages.appendChild(actionsContainer);
        
        // Scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    addPreferenceAdjustmentActions(requirementsStatus) {
        const actionsContainer = document.createElement('div');
        actionsContainer.className = 'message bot-message';
        
        const content = document.createElement('div');
        content.className = 'message-content quick-actions';
        
        let html = '<div class="quick-actions-header">Quick preference changes:</div>';
        html += '<div class="quick-actions-buttons">';
        
        // Location change
        html += '<button class="quick-action-btn location" onclick="chatBot.sendMessage(\'Change location\')">📍 Different location</button>';
        
        // Service type changes
        if (requirementsStatus.service_type !== 'direct_cremation') {
            html += '<button class="quick-action-btn service" onclick="chatBot.sendMessage(\'Direct cremation instead\')">⚱️ Direct cremation</button>';
        }
        if (requirementsStatus.service_type !== 'traditional_funeral') {
            html += '<button class="quick-action-btn service" onclick="chatBot.sendMessage(\'Traditional funeral instead\')">⚰️ Traditional funeral</button>';
        }
        
        // Preference changes
        if (requirementsStatus.preference !== 'cheapest') {
            html += '<button class="quick-action-btn preference" onclick="chatBot.sendMessage(\'Switch to cheapest options\')">💰 Cheapest</button>';
        }
        if (requirementsStatus.preference !== 'nearest') {
            html += '<button class="quick-action-btn preference" onclick="chatBot.sendMessage(\'Switch to nearest options\')">📍 Nearest</button>';
        }
        
        html += '</div>';
        
        content.innerHTML = html;
        actionsContainer.appendChild(content);
        this.chatMessages.appendChild(actionsContainer);
        
        // Scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    addInfoCollectionActions(requirementsStatus) {
        const missingFields = requirementsStatus.missing_fields || [];
        if (missingFields.length === 0) return;
        
        const actionsContainer = document.createElement('div');
        actionsContainer.className = 'message bot-message';
        
        const content = document.createElement('div');
        content.className = 'message-content quick-actions';
        
        let html = '<div class="quick-actions-header">Quick options to get started:</div>';
        html += '<div class="quick-actions-buttons">';
        
        // Common location suggestions
        if (missingFields.includes('location')) {
            html += '<button class="quick-action-btn location" onclick="chatBot.sendMessage(\'Los Angeles CA\')">📍 Los Angeles</button>';
            html += '<button class="quick-action-btn location" onclick="chatBot.sendMessage(\'New York NY\')">📍 New York</button>';
            html += '<button class="quick-action-btn location" onclick="chatBot.sendMessage(\'Miami FL\')">📍 Miami</button>';
        }
        
        // Common service suggestions
        if (missingFields.includes('service_type')) {
            html += '<button class="quick-action-btn service" onclick="chatBot.sendMessage(\'Direct cremation\')">⚱️ Direct cremation</button>';
            html += '<button class="quick-action-btn service" onclick="chatBot.sendMessage(\'Traditional funeral\')">⚰️ Traditional funeral</button>';
        }
        
        // Common timeframe suggestions
        if (missingFields.includes('timeframe')) {
            html += '<button class="quick-action-btn timeframe" onclick="chatBot.sendMessage(\'Immediately\')">⏰ Immediately</button>';
            html += '<button class="quick-action-btn timeframe" onclick="chatBot.sendMessage(\'Within 4 weeks\')">⏰ Within 4 weeks</button>';
        }
        
        // Common preference suggestions
        if (missingFields.includes('preference')) {
            html += '<button class="quick-action-btn preference" onclick="chatBot.sendMessage(\'Cheapest options\')">💰 Cheapest</button>';
            html += '<button class="quick-action-btn preference" onclick="chatBot.sendMessage(\'Nearest options\')">📍 Nearest</button>';
        }
        
        html += '</div>';
        
        content.innerHTML = html;
        actionsContainer.appendChild(content);
        this.chatMessages.appendChild(actionsContainer);
        
        // Scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    addNoResultsActions(requirementsStatus) {
        const quickActionsDiv = document.createElement('div');
        quickActionsDiv.className = 'message bot-message';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const currentService = requirementsStatus.service_type || 'direct_cremation';
        const currentTimeframe = requirementsStatus.timeframe || 'immediately';
        const currentPreference = requirementsStatus.preference || 'cheapest';
        
        content.innerHTML = `
            <div class="quick-actions">
                <strong>🎯 Try these cities with available funeral homes:</strong>
                <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px;">
                    <button class="quick-action-btn location" onclick="chatBot.sendMessage('Houston Texas ${currentService.replace('_', ' ')} ${currentTimeframe} ${currentPreference}')">Houston, TX</button>
                    <button class="quick-action-btn location" onclick="chatBot.sendMessage('Dallas Texas ${currentService.replace('_', ' ')} ${currentTimeframe} ${currentPreference}')">Dallas, TX</button>
                    <button class="quick-action-btn location" onclick="chatBot.sendMessage('Miami Florida ${currentService.replace('_', ' ')} ${currentTimeframe} ${currentPreference}')">Miami, FL</button>
                    <button class="quick-action-btn location" onclick="chatBot.sendMessage('Los Angeles California ${currentService.replace('_', ' ')} ${currentTimeframe} ${currentPreference}')">Los Angeles, CA</button>
                    <button class="quick-action-btn location" onclick="chatBot.sendMessage('Chicago Illinois ${currentService.replace('_', ' ')} ${currentTimeframe} ${currentPreference}')">Chicago, IL</button>
                    <button class="quick-action-btn service" onclick="chatBot.sendMessage('Change service type')">Different Service</button>
                </div>
            </div>
        `;
        
        quickActionsDiv.appendChild(content);
        this.chatMessages.appendChild(quickActionsDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
}

// Initialize the chatbot when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.chatBot = new ChatBot();
});