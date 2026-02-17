import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getMessaging, getToken, onMessage } from "firebase/messaging";
import { getAuthToken } from "./hooks/useApi";

const firebaseConfig = {
  apiKey: "AIzaSyDw67sQGwEAT6rB-lJNXo56JBc_GXqYVaM",
  authDomain: "sharp-picks.firebaseapp.com",
  projectId: "sharp-picks",
  storageBucket: "sharp-picks.firebasestorage.app",
  messagingSenderId: "467560918995",
  appId: "1:467560918995:web:5ca04db7b6a03c4794c926",
  measurementId: "G-1LS5FPFB54"
};

const VAPID_KEY = "BOLnIRohw31kaiPA9p9bvVLfepnNRJVP8An0SanQB8hZq9s0qInTTV9-LgVh77iyRr0HGtAe09luMvibSNVa0pQ";

const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);

let messaging = null;
try {
  messaging = getMessaging(app);
} catch (e) {
  console.warn("Firebase Messaging not supported in this browser");
}

async function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    try {
      const reg = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
      return reg;
    } catch (err) {
      console.error("SW registration failed:", err);
      return null;
    }
  }
  return null;
}

async function requestNotificationPermission() {
  if (!messaging) return null;
  try {
    const permission = await Notification.requestPermission();
    if (permission !== "granted") return null;

    const swReg = await registerServiceWorker();
    const tokenOptions = { vapidKey: VAPID_KEY };
    if (swReg) tokenOptions.serviceWorkerRegistration = swReg;

    const fcmToken = await getToken(messaging, tokenOptions);
    if (fcmToken) {
      const authToken = getAuthToken();
      if (authToken) {
        await fetch('/api/user/fcm-token', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
          },
          body: JSON.stringify({ token: fcmToken, platform: 'web' })
        });
      }
    }
    return fcmToken;
  } catch (err) {
    console.error("FCM token error:", err);
    return null;
  }
}

if (messaging) {
  onMessage(messaging, (payload) => {
    const { title, body } = payload.notification || {};
    if (title) {
      new Notification(title, {
        body,
        icon: "/icon-192x192.png",
        badge: "/favicon-32x32.png"
      });
    }
  });
}

export { app, analytics, messaging, requestNotificationPermission };
