importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyDw67sQGwEAT6rB-lJNXo56JBc_GXqYVaM",
  authDomain: "sharp-picks.firebaseapp.com",
  projectId: "sharp-picks",
  storageBucket: "sharp-picks.firebasestorage.app",
  messagingSenderId: "467560918995",
  appId: "1:467560918995:web:5ca04db7b6a03c4794c926",
  measurementId: "G-1LS5FPFB54"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  const { title, body } = payload.notification || {};
  const data = payload.data || {};
  if (title) {
    self.registration.showNotification(title, {
      body: body || '',
      icon: '/icon-192x192.png',
      badge: '/favicon-32x32.png',
      data: data
    });
  }
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const data = event.notification.data || {};
  let urlPath = '/';

  if (data.type === 'weekly_summary') {
    urlPath = '/?push=weekly_summary';
  } else if (data.type === 'pick' || data.type === 'result' || data.type === 'revoke') {
    urlPath = data.pick_id ? '/?push=picks&pick_id=' + encodeURIComponent(data.pick_id) : '/?push=picks';
  } else if (data.type === 'pass') {
    urlPath = '/?push=picks';
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes(self.location.origin)) {
          client.focus();
          client.postMessage({ type: 'sp-push-navigate', data: data });
          return;
        }
      }
      return clients.openWindow(urlPath);
    })
  );
});
