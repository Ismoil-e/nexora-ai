import { initializeApp } from 'https://www.gstatic.com/firebasejs/12.7.0/firebase-app.js';
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
} from 'https://www.gstatic.com/firebasejs/12.7.0/firebase-auth.js';
import { firebaseConfig, hasFirebaseConfig } from './firebase-config.js';

const googleSignInBtn = document.getElementById('googleSignInBtn');
const googleAuthStatus = document.getElementById('googleAuthStatus');

function createAccountNumber() {
  return `NX-${Math.floor(100000 + Math.random() * 900000)}`;
}

function getUsers() {
  return JSON.parse(localStorage.getItem('users') || '[]');
}

function saveUsers(users) {
  localStorage.setItem('users', JSON.stringify(users));
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

function splitName(displayName, email) {
  const name = (displayName || email || 'Nexora User').trim();
  const parts = name.split(/\s+/).filter(Boolean);

  return {
    firstName: parts[0] || 'Nexora',
    lastName: parts.slice(1).join(' ') || 'User',
  };
}

async function handleGoogleSignIn() {
  if (!hasFirebaseConfig()) {
    if (googleAuthStatus) {
      googleAuthStatus.textContent = 'Avval firebase-config.js ichiga haqiqiy Firebase qiymatlarini qo‘ying.';
    }
    return;
  }

  try {
    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);
    const provider = new GoogleAuthProvider();
    const result = await signInWithPopup(auth, provider);
    const googleUser = result.user;
    const { firstName, lastName } = splitName(googleUser.displayName, googleUser.email);

    const users = getUsers();
    const existingIndex = users.findIndex((item) => item.email === googleUser.email);
    const baseUser = {
      firstName,
      lastName,
      businessName: 'Nexora Business',
      email: googleUser.email || '',
      password: '',
      accountNumber: existingIndex >= 0 ? users[existingIndex].accountNumber : createAccountNumber(),
      balance: existingIndex >= 0 ? users[existingIndex].balance : '0 UZS',
      photoData: googleUser.photoURL || '',
    };

    if (existingIndex >= 0) {
      users[existingIndex] = {
        ...users[existingIndex],
        ...baseUser,
      };
    } else {
      users.push(baseUser);
    }

    saveUsers(users);
    setSession(baseUser);
    window.location.href = 'chat.html';
  } catch (error) {
    if (googleAuthStatus) {
      googleAuthStatus.textContent = 'Google login ishlamadi. Firebase config va authorized domain sozlamalarini tekshiring.';
    }
    console.error(error);
  }
}

if (googleSignInBtn) {
  googleSignInBtn.addEventListener('click', handleGoogleSignIn);

  if (!hasFirebaseConfig()) {
    if (googleAuthStatus) {
      googleAuthStatus.textContent = "Google login ishlashi uchun firebase-config.js ichiga haqiqiy Firebase qiymatlarini qo'ying va sahifani local server orqali oching.";
    }
  } else if (googleAuthStatus) {
    googleAuthStatus.textContent = 'Google orqali xavfsiz kirish tayyor.';
  }
}
