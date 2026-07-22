const chatForm = document.getElementById('chatForm');
const chatHistory = document.getElementById('chatHistory');
const promptInput = document.getElementById('promptInput');
const menuBtn = document.getElementById('menuBtn');
const menuCloseBtn = document.getElementById('menuCloseBtn');
const dropdownMenu = document.getElementById('dropdownMenu');
const menuOverlay = document.getElementById('menuOverlay');
const menuContent = document.getElementById('menuContent');

const session = { title: 'Chat', log: [] };

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
    menuContent.innerHTML = `
      <a href="login.html" class="menu-link">Login</a>
    `;
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
      alert('Hisobni to‘ldirish bo‘limi keyingi qadamda ulanadi.');
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

function appendMessage(text, type) {
  if (!chatHistory) return;

  const msg = document.createElement('div');
  msg.className = `message ${type}`;
  msg.textContent = text;
  chatHistory.appendChild(msg);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

function renderChat() {
  if (!chatHistory) return;

  chatHistory.innerHTML = '';
  session.log.forEach((item) => appendMessage(item.text, item.type));
}

const GEMINI_API_KEY = 'AIzaSyC5vYonQWe45z07J5lIitdIfTDTqUw2BmU';
const GEMINI_API_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}`;

const SYSTEM_INSTRUCTION = `Sen "Nexora AI" — bizneslar uchun yaratilgan AI yordamchisisan.
Sening vazifang:
- Foydalanuvchining savollariga toliq, aniq va foydali javob berish
- Loyiha haqida so'rashsa — Nexora AI platformasi haqida tushuntirish (login, profil, chat tizimi)
- Dasturlash haqida so'rashsa — yordam berish (HTML, CSS, JS, Firebase)
- Har doim professional va do'stona javob berish
- Javoblarni qisqa va tushunarli yozish
- Agar kerak bo'lsa, kod misollari bilan tushuntirish`;

async function getGeminiReply(userText) {
  try {
    const response = await fetch(GEMINI_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: SYSTEM_INSTRUCTION }] },
        contents: [{ parts: [{ text: userText }] }]
      })
    });

    if (!response.ok) {
      throw new Error(`API xatosi: ${response.status}`);
    }

    const data = await response.json();
    return data.candidates?.[0]?.content?.parts?.[0]?.text || 'Javob olinmadi.';
  } catch (error) {
    console.error('Gemini API xatosi:', error);
    return `Xatolik yuz berdi: ${error.message}`;
  }
}

async function onSubmit(event) {
  event.preventDefault();

  if (!promptInput) return;
  const prompt = promptInput.value.trim();
  if (!prompt) return;

  session.log.push({ text: prompt, type: 'user' });
  appendMessage(prompt, 'user');
  promptInput.value = '';

  const typingIndicator = { text: 'Nexora AI javob yozmoqda...', type: 'ai' };
  session.log.push(typingIndicator);
  appendMessage(typingIndicator.text, 'ai');

  const aiReply = await getGeminiReply(prompt);
  session.log[session.log.length - 1] = { text: aiReply, type: 'ai' };
  renderChat();
}

function init() {
  renderMenu();

  if (menuBtn) {
    menuBtn.addEventListener('click', toggleMenu);
  }

  if (menuCloseBtn) {
    menuCloseBtn.addEventListener('click', closeMenu);
  }

  if (menuOverlay) {
    menuOverlay.addEventListener('click', closeMenu);
  }

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeMenu();
    }
  });

  if (chatForm) {
    chatForm.addEventListener('submit', onSubmit);
  }

  renderChat();
}

init();
