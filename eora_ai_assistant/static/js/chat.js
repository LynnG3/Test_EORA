document.addEventListener('DOMContentLoaded', function() {
    let sessionId = localStorage.getItem('chatSessionId');
    const chatContainer = document.getElementById('chat-container');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');

    // Загружаем историю чата при открытии страницы
    if (sessionId) {
        loadChatHistory();
    }

    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        // Добавляем сообщение пользователя в чат
        addMessage('user', message);
        messageInput.value = '';

        // Отправляем запрос на сервер
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.detail) {
                addMessage('assistant', 'Произошла ошибка: ' + data.detail);
            } else {
                // Сохраняем ID сессии
                if (!sessionId) {
                    sessionId = data.session_id;
                    localStorage.setItem('chatSessionId', sessionId);
                }
                
                // Добавляем ответ ассистента
                addMessage('assistant', data.message, data.sources);
            }
        })
        .catch(error => {
            addMessage('assistant', 'Ошибка соединения с сервером');
            console.error('Error:', error);
        });
    }

    function addMessage(role, content, sources = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        messageDiv.textContent = content;
        
        // Добавляем источники, если они есть
        if (sources && sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'sources';
            
            let sourcesText = 'Источники: ';
            sources.forEach((source, index) => {
                sourcesText += `<a href="${source.url}" target="_blank" class="source-link">[${index + 1}]</a> `;
            });
            
            sourcesDiv.innerHTML = sourcesText;
            messageDiv.appendChild(sourcesDiv);
        }
        
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function loadChatHistory() {
        fetch(`/api/sessions/${sessionId}`)
            .then(response => response.json())
            .then(data => {
                if (data.messages) {
                    chatContainer.innerHTML = '';
                    data.messages.forEach(msg => {
                        addMessage(msg.role, msg.content, msg.sources);
                    });
                }
            })
            .catch(error => {
                console.error('Error loading chat history:', error);
            });
    }
});
