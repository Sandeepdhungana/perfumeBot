class PerfumeChatbot {
    constructor() {
        this.conversationId = null;
        this.isLoading = false;
        this.currentPerfumes = [];
        this.remainingCount = 0;
        
        this.initializeElements();
        this.attachEventListeners();
    }
    
    initializeElements() {
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendButton = document.getElementById('sendButton');
        this.clearChatBtn = document.getElementById('clearChat');
        this.loadingOverlay = document.getElementById('loadingOverlay');
    }
    
    attachEventListeners() {
        // Send message on button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Send message on Enter key
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Clear chat
        this.clearChatBtn.addEventListener('click', () => this.clearChat());
        
        // Quick suggestions
        document.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const message = btn.getAttribute('data-message');
                this.chatInput.value = message;
                this.sendMessage();
            });
        });
        
        // Auto-resize input
        this.chatInput.addEventListener('input', () => this.autoResizeInput());
    }
    
    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message || this.isLoading) return;
        
        // Clear input and show user message
        this.chatInput.value = '';
        this.addMessage(message, 'user');
        
        // Show typing indicator while processing
        this.showTypingIndicator();
        this.setLoading(true);
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.conversationId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Update conversation ID
            this.conversationId = data.conversation_id;
            
            // Hide typing indicator and add bot response
            this.hideTypingIndicator();
            this.addMessage(data.response, 'bot');
            
            // Show perfume results if available
            if (data.matched_perfumes && data.matched_perfumes.length > 0) {
                this.showPerfumeResults(data.matched_perfumes, data.returned_count, data.remaining_count);
            }
            
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage('Sorry, I encountered an error. Please try again.', 'bot', true);
        } finally {
            this.setLoading(false);
        }
    }
    
    addMessage(text, sender, isError = false, isWelcome = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        if (isError) messageDiv.classList.add('error-message');
        if (isWelcome) messageDiv.classList.add('welcome-message');
        
        const avatar = document.createElement('div');
        avatar.className = `message-avatar ${sender}-avatar`;
        avatar.innerHTML = sender === 'bot' ? '<i class="fas fa-robot"></i>' : '<i class="fas fa-user"></i>';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        textDiv.innerHTML = this.formatMessage(text);
        
        content.appendChild(textDiv);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    formatMessage(text) {
        // Convert line breaks to <br> tags
        let formatted = text.replace(/\n/g, '<br>');
        
        // Make perfume names bold
        formatted = formatted.replace(/([A-Z][a-z]+(?: [A-Z][a-z]+)*(?:,|$))/g, '<strong>$1</strong>');
        
        return formatted;
    }
    
    showPerfumeResults(perfumes, returnedCount, remainingCount) {
        this.currentPerfumes = perfumes;
        this.remainingCount = remainingCount;
        
        // Create results content as a message
        const resultsHtml = `
            <div class="results-header">
                <div class="results-title">
                    <i class="fas fa-search"></i> Search Results
                </div>
                <div class="results-count">
                    Showing ${returnedCount} perfume${returnedCount !== 1 ? 's' : ''}
                    ${remainingCount > 0 ? ` (${remainingCount} more available)` : ''}
                </div>
            </div>
            <div class="perfume-grid">
                ${perfumes.map(perfume => `
                    <div class="perfume-card" onclick="chatbot.showPerfumeDetails('${perfume.replace(/'/g, "\\'")}')">
                        <div class="perfume-name">${perfume}</div>
                        <div class="perfume-click-hint">Click for details</div>
                    </div>
                `).join('')}
            </div>
            ${remainingCount > 0 ? `
                <button class="load-more-btn" onclick="chatbot.loadMoreResults()">
                    <i class="fas fa-plus"></i> Show More Results (${remainingCount} remaining)
                </button>
            ` : ''}
        `;
        
        // Add results as a message in the chat
        this.addPerfumeResultsMessage(resultsHtml);
    }
    
    addPerfumeResultsMessage(resultsHtml) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message perfume-results-message';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar bot-avatar';
        avatar.innerHTML = '<i class="fas fa-search"></i>';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text perfume-results-content';
        textDiv.innerHTML = resultsHtml;
        
        content.appendChild(textDiv);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    hidePerfumeResults() {
        // Remove any existing perfume results messages
        const existingResults = this.chatMessages.querySelectorAll('.perfume-results-message');
        existingResults.forEach(result => result.remove());
    }
    
    async loadMoreResults() {
        if (this.isLoading || this.remainingCount === 0) return;
        
        // Show typing indicator while loading more results
        this.showTypingIndicator();
        this.setLoading(true);
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: 'show more',
                    conversation_id: this.conversationId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Hide typing indicator and add bot response
            this.hideTypingIndicator();
            this.addMessage(data.response, 'bot');
            
            // Update perfume results
            if (data.matched_perfumes && data.matched_perfumes.length > 0) {
                this.showPerfumeResults(data.matched_perfumes, data.returned_count, data.remaining_count);
            }
            
        } catch (error) {
            console.error('Error loading more results:', error);
            this.hideTypingIndicator();
            this.addMessage('Sorry, I couldn\'t load more results. Please try again.', 'bot', true);
        } finally {
            this.setLoading(false);
        }
    }
    
    async showPerfumeDetails(perfumeName) {
        if (this.isLoading) return;
        
        this.setLoading(true);
        this.showTypingIndicator();
        
        try {
            const encodedName = encodeURIComponent(perfumeName);
            const response = await fetch(`/api/perfume/${encodedName}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const details = await response.json();
            
            // Hide typing indicator and show details
            this.hideTypingIndicator();
            this.displayPerfumeDetails(details);
            
        } catch (error) {
            console.error('Error fetching perfume details:', error);
            this.hideTypingIndicator();
            this.addMessage('Sorry, I couldn\'t retrieve the details for this perfume.', 'bot', true);
        } finally {
            this.setLoading(false);
        }
    }
    
    displayPerfumeDetails(details) {
        // Remove any existing perfume details messages
        const existingDetails = this.chatMessages.querySelectorAll('.perfume-details-message');
        existingDetails.forEach(detail => detail.remove());
        
        const detailsHtml = `
            <div class="perfume-details">
                <div class="perfume-details-header">
                    <h3><i class="fas fa-spray-can"></i> ${details.name}</h3>
                </div>
                
                <div class="perfume-details-content">
                    <div class="details-section">
                        <h4><i class="fas fa-leaf"></i> Top Notes</h4>
                        <div class="notes-list">
                            ${details.top_notes.length > 0 ? 
                                details.top_notes.map(note => `<span class="note-tag">${note}</span>`).join('') : 
                                '<span class="no-data">Not available</span>'
                            }
                        </div>
                    </div>
                    
                    <div class="details-section">
                        <h4><i class="fas fa-flower"></i> Middle Notes</h4>
                        <div class="notes-list">
                            ${details.middle_notes.length > 0 ? 
                                details.middle_notes.map(note => `<span class="note-tag">${note}</span>`).join('') : 
                                '<span class="no-data">Not available</span>'
                            }
                        </div>
                    </div>
                    
                    <div class="details-section">
                        <h4><i class="fas fa-tree"></i> Base Notes</h4>
                        <div class="notes-list">
                            ${details.base_notes.length > 0 ? 
                                details.base_notes.map(note => `<span class="note-tag">${note}</span>`).join('') : 
                                '<span class="no-data">Not available</span>'
                            }
                        </div>
                    </div>
                    
                    <div class="details-section">
                        <h4><i class="fas fa-palette"></i> Main Accords</h4>
                        <div class="accords-list">
                            ${details.main_accords.length > 0 ? 
                                details.main_accords.map(accord => `<span class="accord-tag">${accord}</span>`).join('') : 
                                '<span class="no-data">Not available</span>'
                            }
                        </div>
                    </div>
                    
                    <div class="details-section">
                        <h4><i class="fas fa-users"></i> Gender</h4>
                        <div class="gender-list">
                            ${details.gender.length > 0 ? 
                                details.gender.map(g => `<span class="gender-tag">${g}</span>`).join('') : 
                                '<span class="no-data">Not available</span>'
                            }
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add details as a message in the chat
        this.addPerfumeDetailsMessage(detailsHtml);
    }
    
    addPerfumeDetailsMessage(detailsHtml) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message perfume-details-message';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar bot-avatar';
        avatar.innerHTML = '<i class="fas fa-info-circle"></i>';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text perfume-details-content';
        textDiv.innerHTML = detailsHtml;
        
        content.appendChild(textDiv);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    clearChat() {
        // Remove all messages except welcome message
        const messages = this.chatMessages.querySelectorAll('.message');
        messages.forEach((message, index) => {
            if (index > 0) { // Keep the first message (welcome message)
                message.remove();
            }
        });
        
        // Reset state
        this.conversationId = null;
        this.currentPerfumes = [];
        this.remainingCount = 0;
        
        // Scroll to top to show welcome message
        this.chatMessages.scrollTop = 0;
        
        // Focus on input
        this.chatInput.focus();
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        this.sendButton.disabled = loading;
        this.chatInput.disabled = loading;
        
        // Don't show the overlay loading since we use typing indicator
        if (!loading) {
            this.chatInput.focus();
        }
    }
    
    showTypingIndicator() {
        const existingTyping = this.chatMessages.querySelector('.typing-indicator');
        if (existingTyping) return;
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot-message typing-indicator';
        typingDiv.innerHTML = `
            <div class="message-avatar bot-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="message-text">
                    <span>Thinking</span>
                    <div class="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        
        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        const typingIndicator = this.chatMessages.querySelector('.typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    autoResizeInput() {
        this.chatInput.style.height = 'auto';
        this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 100) + 'px';
    }
    
    scrollToBottom() {
        // Use requestAnimationFrame for smooth scrolling
        requestAnimationFrame(() => {
            const chatMessages = this.chatMessages;
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Ensure it scrolls even if content is still loading
            setTimeout(() => {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }, 50);
        });
    }
    
    // Show welcome message with typing animation (for message responses)
    showWelcomeMessage() {
        // First show typing indicator
        this.showTypingIndicator();
        
        // After 2 seconds, show the welcome message
        setTimeout(() => {
            this.hideTypingIndicator();
            
            const welcomeMessage = `
                <h3>Welcome to FragranceBot! 🌸</h3>
                <p>I'm here to help you discover your perfect fragrance. You can ask me about:</p>
                <ul>
                    <li>Perfumes with specific notes (citrus, floral, woody, etc.)</li>
                    <li>Fragrances for men or women</li>
                    <li>Scents by main accords</li>
                    <li>Similar perfumes to ones you love</li>
                </ul>
                <p>What kind of fragrance are you looking for today?</p>
            `;
            
            this.addMessageWithAnimation(welcomeMessage, 'bot', true);
        }, 2000);
    }
    
    // Add message with typing animation
    addMessageWithAnimation(text, sender, isWelcome = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        if (isWelcome) messageDiv.classList.add('welcome-message');
        
        const avatar = document.createElement('div');
        avatar.className = `message-avatar ${sender}-avatar`;
        avatar.innerHTML = sender === 'bot' ? '<i class="fas fa-robot"></i>' : '<i class="fas fa-user"></i>';
        
        const content = document.createElement('div');
        content.className = 'message-content typing';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        textDiv.innerHTML = text;
        
        content.appendChild(textDiv);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    // Handle connection errors
    handleConnectionError() {
        this.addMessage(
            'Connection lost. Please check your internet connection and try again.',
            'bot',
            true
        );
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chatbot = new PerfumeChatbot();
});

// Handle offline/online events
window.addEventListener('offline', () => {
    document.querySelector('.status-dot').classList.remove('online');
    document.querySelector('.status-indicator span').textContent = 'Offline';
});

window.addEventListener('online', () => {
    document.querySelector('.status-dot').classList.add('online');
    document.querySelector('.status-indicator span').textContent = 'Online';
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K to focus on input
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('chatInput').focus();
    }
    
    // Escape to clear input
    if (e.key === 'Escape') {
        document.getElementById('chatInput').value = '';
        document.getElementById('chatInput').blur();
    }
});

// Add some CSS for error messages
const style = document.createElement('style');
style.textContent = `
    .error-message .message-text {
        background: linear-gradient(135deg, #fef2f2, #fee2e2) !important;
        border-color: #ef4444 !important;
        color: #dc2626 !important;
    }
    
    .status-dot:not(.online) {
        background: #ef4444 !important;
    }
`;
document.head.appendChild(style);