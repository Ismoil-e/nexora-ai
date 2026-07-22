export const firebaseConfig = {
  apiKey: 'YOUR_FIREBASE_API_KEY',
  authDomain: 'YOUR_PROJECT.firebaseapp.com',
  projectId: 'YOUR_PROJECT_ID',
  appId: 'YOUR_APP_ID',
};

export function hasFirebaseConfig() {
  return Object.values(firebaseConfig).every((value) => value && !String(value).startsWith('YOUR_'));
}
