
// Hybrid database implementation (server + localStorage)
const userDB = {
    SERVER_URL: 'http://127.0.0.1:5000',
    
    init: function() {
        // Initialize the local database if it doesn't exist
        if (!localStorage.getItem('users')) {
            localStorage.setItem('users', JSON.stringify([]));
        }
    },
    
    getUsers: function() {
        return JSON.parse(localStorage.getItem('users')) || [];
    },
    
    saveUsers: function(users) {
        localStorage.setItem('users', JSON.stringify(users));
    },
    
    addUser: async function(user) {
        try {
            // Try to register user on the server
            const response = await fetch(`${this.SERVER_URL}/api/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: user.username,
                    email: user.email,
                    password: user.password
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Registration failed');
            }
            
            // If server registration succeeded, also add to local storage
            const users = this.getUsers();
            users.push(user);
            this.saveUsers(users);
            
            return {
                success: true,
                message: data.message
            };
        } catch (error) {
            console.error('Server registration error:', error);
            
            // Fallback to local-only registration if server is unreachable
            if (error.message === 'Failed to fetch') {
                const users = this.getUsers();
                
                // Check if email or username already exists locally
                if (users.some(u => u.email === user.email)) {
                    return {
                        success: false,
                        message: 'Email already registered'
                    };
                }
                
                if (users.some(u => u.username === user.username)) {
                    return {
                        success: false,
                        message: 'Username already taken'
                    };
                }
                
                users.push(user);
                this.saveUsers(users);
                
                return {
                    success: true,
                    message: 'User registered successfully (local mode)'
                };
            }
            
            return {
                success: false,
                message: error.message
            };
        }
    },
    
    login: async function(username, password) {
        try {
            // Try server login first
            const response = await fetch(`${this.SERVER_URL}/api/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Login failed');
            }
            
            return {
                success: true,
                user: data.user,
                message: data.message,
                source: 'server'
            };
        } catch (error) {
            console.error('Server login error:', error);
            
            // Fallback to local login if server is unreachable
            if (error.message === 'Failed to fetch') {
                const users = this.getUsers();
                const user = users.find(u => u.username === username && u.password === password);
                
                if (user) {
                    return {
                        success: true,
                        user: {
                            username: user.username,
                            email: user.email,
                            join_date: user.joinDate,
                            last_login: new Date().toISOString()
                        },
                        message: 'Login successful (local mode)',
                        source: 'local'
                    };
                }
            }
            
            return {
                success: false,
                message: error.message
            };
        }
    },
    
    emailExists: function(email) {
        const users = this.getUsers();
        return users.some(u => u.email === email);
    },
    
    usernameExists: function(username) {
        const users = this.getUsers();
        return users.some(u => u.username === username);
    }
};

// Initialize database on page load
document.addEventListener('DOMContentLoaded', function() {
    userDB.init();
    
    // Check if user is already logged in
    const currentUser = sessionStorage.getItem('currentUser');
    if (currentUser) {
        showChat();
    }
});

function showForm(formType) {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const loginTab = document.querySelector('.auth-tab:nth-child(1)');
    const registerTab = document.querySelector('.auth-tab:nth-child(2)');

    if (formType === 'login') {
        loginForm.style.display = 'flex';
        registerForm.style.display = 'none';
        loginTab.classList.add('active');
        registerTab.classList.remove('active');
    } else {
        loginForm.style.display = 'none';
        registerForm.style.display = 'flex';
        loginTab.classList.remove('active');
        registerTab.classList.add('active');
    }
}

// Handle login form submission
document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const loginButton = this.querySelector('button[type="submit"]');
    const originalText = loginButton.textContent;
    loginButton.disabled = true;
    loginButton.textContent = 'Logging in...';
    
    const username = this.querySelector('input[type="text"]').value;
    const password = this.querySelector('input[type="password"]').value;

    try {
        const result = await userDB.login(username, password);
        
        if (result.success) {
            // Store current user in session
            sessionStorage.setItem('currentUser', JSON.stringify({
                username: result.user.username,
                email: result.user.email,
                source: result.source
            }));
            
            showChat();
        } else {
            alert(result.message || 'Login failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('An error occurred during login');
    } finally {
        loginButton.disabled = false;
        loginButton.textContent = originalText;
    }
});

// Handle register form submission
document.getElementById('registerForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const registerButton = this.querySelector('button[type="submit"]');
    const originalText = registerButton.textContent;
    registerButton.disabled = true;
    registerButton.textContent = 'Registering...';
    
    const username = this.querySelector('input[type="text"]').value;
    const email = this.querySelector('input[type="email"]').value;
    const password = this.querySelector('input[type="password"]').value;

    try {
        const result = await userDB.addUser({
            username,
            email,
            password,
            joinDate: new Date().toISOString(),
            lastLogin: new Date().toISOString()
        });
        
        if (result.success) {
            alert(result.message);
            showForm('login');
        } else {
            alert(result.message || 'Registration failed');
        }
    } catch (error) {
        console.error('Registration error:', error);
        alert('An error occurred during registration');
    } finally {
        registerButton.disabled = false;
        registerButton.textContent = originalText;
    }
});

// Show chat interface
function showChat() {
    document.getElementById('authContainer').style.display = 'none';
    document.getElementById('chatContainer').style.display = 'block';
    
    // Display welcome message with username
    const currentUser = JSON.parse(sessionStorage.getItem('currentUser'));
    if (currentUser) {
        const sourceText = currentUser.source === 'local' ? 
            '' : '';
        addMessage('bot', `Welcome back, ${currentUser.username}!${sourceText} How can I help you today?`);
    }
}

// Logout functionality
function logout() {
    // Clear session data
    sessionStorage.removeItem('currentUser');
    
    document.getElementById('authContainer').style.display = 'flex';
    document.getElementById('chatContainer').style.display = 'none';
    document.getElementById('chatMessages').innerHTML = '';
    
    // Reset form fields
    document.getElementById('loginForm').reset();
    document.getElementById('registerForm').reset();
    
    showForm('login');
}

// Handle message sending
async function sendMessage() {
    const input = document.getElementById('userInput');
    const message = input.value.trim();
    
    if (message) {
        addMessage('user', message);
        
        try {
            const currentUser = JSON.parse(sessionStorage.getItem('currentUser'));
            const username = currentUser ? currentUser.username : 'guest';
            
            const response = await fetch('http://127.0.0.1:5000/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    message: message,
                    user: username
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            addMessage('bot', data.response);
        } catch (error) {
            console.error('Error:', error);
            addMessage('bot', 'Sorry, I don\'t have enough information to answer that question');
        }

        input.value = '';
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// Add message to chat
function addMessage(type, text) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const avatar = document.createElement('img');
    avatar.className = 'avatar';
    avatar.src = type === 'user' 
        ? 'https://cdn-icons-png.flaticon.com/512/149/149071.png'
        : 'https://cdn-icons-png.flaticon.com/512/4712/4712027.png';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    content.textContent = text;
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 50);
}
