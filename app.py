const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');

const API_URL = 'https://ia-backend-6mtu.onrender.com/chat';

function scrollToChat() {
    const chatSection = document.getElementById('chat');
    if (chatSection) {
        chatSection.scrollIntoView({ behavior: 'smooth' });
    }
}

function getCurrentTime() {
    const now = new Date();
    return now.getHours().toString().padStart(2, '0') + ':' + 
           now.getMinutes().toString().padStart(2, '0');
}

function addMessage(text, sender, images = []) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    if (sender === 'bot') {
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = '💕';
        messageDiv.appendChild(avatar);
    }
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';
    textDiv.innerHTML = text.replace(/\n/g, '<br>');
    contentDiv.appendChild(textDiv);
    
    if (images && images.length > 0) {
        images.forEach(function(img) {
            const imgElement = document.createElement('img');
            imgElement.src = img.url;
            imgElement.alt = img.description;
            imgElement.className = 'message-image';
            imgElement.onclick = function() {
                window.open(img.url, '_blank');
            };
            contentDiv.appendChild(imgElement);
        });
    }
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = getCurrentTime();
    contentDiv.appendChild(timeDiv);
    
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showTyping() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot';
    typingDiv.id = 'typing-indicator';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '💕';
    typingDiv.appendChild(avatar);
    
    const typingContent = document.createElement('div');
    typingContent.className = 'message-content';
    typingContent.innerHTML = '<div class="message-text">Sophia écrit...</div>';
    typingDiv.appendChild(typingContent);
    
    chatContainer.appendChild(typingDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function removeTyping() {
    const typing = document.getElementById('typing-indicator');
    if (typing) typing.remove();
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;
    
    addMessage(message, 'user');
    messageInput.value = '';
    
    showTyping();
    
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        removeTyping();
        
        if (data.reply) {
            addMessage(data.reply, 'bot', data.images || []);
        } else if (data.error) {
            addMessage('Erreur: ' + data.error, 'bot');
        }
    } catch (error) {
        removeTyping();
        addMessage('Erreur de connexion. Réessaie plus tard, mon amour. 💕', 'bot');
    }
}

sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') sendMessage();
});

window.addEventListener('load', function() {
    messageInput.focus();
});
