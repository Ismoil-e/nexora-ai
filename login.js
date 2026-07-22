const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const registerLink = document.getElementById('registerLink');

function getUsers() {
  return JSON.parse(localStorage.getItem('users') || '[]');
}

function saveUsers(users) {
  localStorage.setItem('users', JSON.stringify(users));
}

function createAccountNumber() {
  return `NX-${Math.floor(100000 + Math.random() * 900000)}`;
}

function createProfileFromEmail(email) {
  const namePart = email.split('@')[0] || 'user';
  const normalized = namePart.replace(/[._-]+/g, ' ').trim();
  const firstName = normalized ? normalized.split(' ')[0] : 'Nexora';
  const lastName = normalized ? normalized.split(' ').slice(1).join(' ') : 'User';

  return {
    firstName: firstName.charAt(0).toUpperCase() + firstName.slice(1),
    lastName: lastName ? lastName.charAt(0).toUpperCase() + lastName.slice(1) : 'User',
    businessName: 'Nexora Business',
    accountNumber: createAccountNumber(),
    balance: '0 UZS',
    photoData: '',
  };
}

function setSession(user) {
  localStorage.setItem('isLoggedIn', 'true');
  localStorage.setItem('userEmail', user.email);
  localStorage.setItem('userProfile', JSON.stringify({
    firstName: user.firstName,
    lastName: user.lastName,
    businessName: user.businessName,
    accountNumber: user.accountNumber,
    balance: user.balance,
    email: user.email,
    photoData: user.photoData || '',
  }));
}

if (registerLink) {
  registerLink.addEventListener('click', (event) => {
    event.preventDefault();
    loginForm.style.display = 'none';
    registerForm.style.display = 'block';
  });
}

if (loginForm) {
  loginForm.addEventListener('submit', (event) => {
    event.preventDefault();

    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value.trim();
    if (!email || !password) {
      alert('Iltimos, barcha maydonlarni to‘ldiring.');
      return;
    }

    const users = getUsers();
    let user = users.find((item) => item.email === email);

    if (!user) {
      const profile = createProfileFromEmail(email);
      user = { email, password, ...profile };
      users.push(user);
      saveUsers(users);
    }

    setSession(user);
    alert('Login muvaffaqiyatli bajarildi.');
    window.location.href = 'chat.html';
  });
}

if (registerForm) {
  registerForm.addEventListener('submit', (event) => {
    event.preventDefault();

    const firstName = document.getElementById('regFirstName').value.trim();
    const lastName = document.getElementById('regLastName').value.trim();
    const businessName = document.getElementById('regBusinessName').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const password = document.getElementById('regPassword').value.trim();

    if (!firstName || !lastName || !businessName || !email || !password) {
      alert('Iltimos, barcha maydonlarni to‘ldiring.');
      return;
    }

    const users = getUsers();
    const existingUser = users.find((item) => item.email === email);
    if (existingUser) {
      alert('Bu email bilan profil allaqachon mavjud.');
      return;
    }

    const user = {
      firstName,
      lastName,
      businessName,
      email,
      password,
      accountNumber: createAccountNumber(),
      balance: '0 UZS',
      photoData: '',
    };

    users.push(user);
    saveUsers(users);
    setSession(user);
    alert('Ro‘yxatdan o‘tish muvaffaqiyatli bajarildi.');
    window.location.href = 'chat.html';
  });
}
