const chatForm = document.getElementById('chatForm');
const chatHistory = document.getElementById('chatHistory');
const promptInput = document.getElementById('promptInput');
const menuBtn = document.getElementById('menuBtn');
const menuCloseBtn = document.getElementById('menuCloseBtn');
const dropdownMenu = document.getElementById('dropdownMenu');
const menuOverlay = document.getElementById('menuOverlay');
const menuContent = document.getElementById('menuContent');

const STORAGE_KEY = 'nexora_single_chat';
let messages = [];

function loadMessages() {
  const email = localStorage.getItem('userEmail') || 'guest';
  const data = localStorage.getItem(`${STORAGE_KEY}_${email}`);
  messages = data ? JSON.parse(data) : [];
}

function saveMessages() {
  const email = localStorage.getItem('userEmail') || 'guest';
  localStorage.setItem(`${STORAGE_KEY}_${email}`, JSON.stringify(messages));
}

function getStoredProfile() {
  return JSON.parse(localStorage.getItem('userProfile') || 'null');
}

function getInitials(profile) {
  const first = profile?.firstName?.trim()?.charAt(0) || 'N';
  const last = profile?.lastName?.trim()?.charAt(0) || 'A';
  return `${first}${last}`.toUpperCase();
}

function renderProfileAvatar(profile) {
  if (profile?.photoData) {
    return `<img class="profile-avatar-image" src="${profile.photoData}" alt="Profile photo">`;
  }
  return getInitials(profile);
}

function renderMenu() {
  if (!menuContent) return;

  const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
  const profile = getStoredProfile();

  if (!isLoggedIn || !profile) {
    menuContent.innerHTML = `<a href="login.html" class="menu-link">Login</a>`;
    return;
  }

  menuContent.innerHTML = `
    <section class="profile-card">
      <div class="profile-avatar">${renderProfileAvatar(profile)}</div>
      <div class="profile-heading">
        <h2 class="profile-name">${profile.firstName} ${profile.lastName}</h2>
        <p class="profile-email">${profile.email || ''}</p>
      </div>
      <div class="profile-details">
        <div class="profile-row">
          <span class="profile-label">Biznes nomi</span>
          <span class="profile-value">${profile.businessName || 'Nexora Business'}</span>
        </div>
      </div>
      <div class="profile-balance">
        <div class="profile-row">
          <span class="profile-label">Hisob</span>
          <span class="profile-value">${profile.balance || '0 UZS'}</span>
        </div>
      </div>
      <div class="profile-actions">
        <a class="menu-link menu-link-button" href="edit-profile.html">Profilni o'zgartirish</a>
        <button class="menu-action-btn" id="topUpBtn" type="button">Hisobni to'ldirish</button>
      </div>
      <button class="menu-logout-btn menu-logout-bottom" id="logoutBtn" type="button">Log out</button>
    </section>
  `;

  const topUpBtn = document.getElementById('topUpBtn');
  const logoutBtn = document.getElementById('logoutBtn');

  if (topUpBtn) {
    topUpBtn.addEventListener('click', () => {
      alert('Hisobni to\'ldirish bo\'limi keyingi qadamda ulanadi.');
    });
  }

  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      localStorage.setItem('isLoggedIn', 'false');
      localStorage.removeItem('userProfile');
      localStorage.removeItem('userEmail');
      renderMenu();
      closeMenu();
    });
  }
}

function setMenuState(isOpen) {
  if (!dropdownMenu || !menuBtn || !menuOverlay) return;
  dropdownMenu.classList.toggle('show', isOpen);
  menuOverlay.classList.toggle('show', isOpen);
  dropdownMenu.setAttribute('aria-hidden', String(!isOpen));
  menuBtn.setAttribute('aria-expanded', String(isOpen));
  document.body.style.overflow = isOpen ? 'hidden' : '';
}

function toggleMenu() {
  if (!dropdownMenu) return;
  setMenuState(!dropdownMenu.classList.contains('show'));
}

function closeMenu() {
  setMenuState(false);
}

function renderMarkdown(text) {
  if (typeof marked !== 'undefined') {
    marked.setOptions({ breaks: true, gfm: true });
    return marked.parse(text);
  }
  return text.replace(/\n/g, '<br>');
}

function appendMessage(text, type, isTyping = false) {
  if (!chatHistory) return;

  const msg = document.createElement('div');
  msg.className = `message ${type}`;

  if (type === 'ai') {
    msg.innerHTML = renderMarkdown(text);
  } else {
    msg.textContent = text;
  }

  if (isTyping) msg.classList.add('typing');

  chatHistory.appendChild(msg);
  chatHistory.scrollTop = chatHistory.scrollHeight;
  return msg;
}

async function typeMessage(msgElement, text) {
  msgElement.classList.remove('typing');
  msgElement.innerHTML = '';

  const words = text.split(' ');
  let currentText = '';

  for (let i = 0; i < words.length; i++) {
    currentText += (i === 0 ? '' : ' ') + words[i];
    msgElement.innerHTML = renderMarkdown(currentText);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    await new Promise(resolve => setTimeout(resolve, 30));
  }
}

function renderChat() {
  if (!chatHistory) return;
  chatHistory.innerHTML = '';
  messages.forEach(item => appendMessage(item.text, item.type));
}

async function getGeminiReply(userText) {
  try {
    const history = messages.slice(-20).map(msg => ({
      role: msg.type === 'user' ? 'user' : 'model',
      parts: [{ text: msg.text }]
    }));

    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userText, history })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || `API xatosi: ${response.status}`);
    }

    const data = await response.json();
    return data.reply || 'Javob olinmadi.';
  } catch (error) {
    console.error('Chat API xatosi:', error);
    return `Xatolik yuz berdi: ${error.message}`;
  }
}

async function onSubmit(event) {
  event.preventDefault();
  if (!promptInput) return;

  const prompt = promptInput.value.trim();
  if (!prompt) return;

  messages.push({ text: prompt, type: 'user' });
  saveMessages();

  appendMessage(prompt, 'user');
  promptInput.value = '';
  promptInput.style.height = 'auto';

  const typingMsg = appendMessage('Yozmoqda...', 'ai', true);

  const aiReply = await getGeminiReply(prompt);

  messages.push({ text: aiReply, type: 'ai' });
  saveMessages();

  await typeMessage(typingMsg, aiReply);
}

function autoResize() {
  promptInput.style.height = 'auto';
  promptInput.style.height = Math.min(promptInput.scrollHeight, 150) + 'px';
}

function init() {
  loadMessages();
  renderMenu();

  if (menuBtn) menuBtn.addEventListener('click', toggleMenu);
  if (menuCloseBtn) menuCloseBtn.addEventListener('click', closeMenu);
  if (menuOverlay) menuOverlay.addEventListener('click', closeMenu);

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeMenu();
  });

  if (chatForm) chatForm.addEventListener('submit', onSubmit);
  if (promptInput) promptInput.addEventListener('input', autoResize);

  renderChat();
}

init();
