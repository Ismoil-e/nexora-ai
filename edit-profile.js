const editProfileForm = document.getElementById('editProfileForm');
const firstNameInput = document.getElementById('firstName');
const lastNameInput = document.getElementById('lastName');
const businessNameInput = document.getElementById('businessName');
const profilePhotoInput = document.getElementById('profilePhoto');
const photoPreview = document.getElementById('photoPreview');

let photoData = '';

function getStoredProfile() {
  return JSON.parse(localStorage.getItem('userProfile') || 'null');
}

function getInitials(profile) {
  const first = profile?.firstName?.trim()?.charAt(0) || 'N';
  const last = profile?.lastName?.trim()?.charAt(0) || 'A';
  return `${first}${last}`.toUpperCase();
}

function renderPreview(profile) {
  if (!photoPreview) return;

  if (photoData || profile?.photoData) {
    const src = photoData || profile.photoData;
    photoPreview.innerHTML = `<img class="profile-avatar-image" src="${src}" alt="Profile photo">`;
    return;
  }

  photoPreview.textContent = getInitials(profile);
}

function loadProfile() {
  const profile = getStoredProfile();
  if (!profile) {
    window.location.href = 'login.html';
    return null;
  }

  firstNameInput.value = profile.firstName || '';
  lastNameInput.value = profile.lastName || '';
  businessNameInput.value = profile.businessName || '';
  photoData = profile.photoData || '';
  renderPreview(profile);
  return profile;
}

function saveProfile(profile) {
  localStorage.setItem('userProfile', JSON.stringify(profile));

  const users = JSON.parse(localStorage.getItem('users') || '[]');
  const updatedUsers = users.map((user) => {
    if (user.email !== profile.email) return user;

    return {
      ...user,
      firstName: profile.firstName,
      lastName: profile.lastName,
      businessName: profile.businessName,
      photoData: profile.photoData || '',
    };
  });

  localStorage.setItem('users', JSON.stringify(updatedUsers));
}

if (profilePhotoInput) {
  profilePhotoInput.addEventListener('change', () => {
    const file = profilePhotoInput.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      photoData = typeof reader.result === 'string' ? reader.result : '';
      renderPreview({
        firstName: firstNameInput.value,
        lastName: lastNameInput.value,
        photoData,
      });
    };
    reader.readAsDataURL(file);
  });
}

if (editProfileForm) {
  const profile = loadProfile();

  editProfileForm.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!profile) return;

    const updatedProfile = {
      ...profile,
      firstName: firstNameInput.value.trim(),
      lastName: lastNameInput.value.trim(),
      businessName: businessNameInput.value.trim(),
      photoData,
    };

    saveProfile(updatedProfile);
    alert('Profil saqlandi.');
    window.location.href = 'chat.html';
  });
}
