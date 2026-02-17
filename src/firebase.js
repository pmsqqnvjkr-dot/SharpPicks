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
  if (!messaging) {
    console.warn("[Push] messaging not initialized");
    return null;
  }
  try {
    const permission = await Notification.requestPermission();
    console.log("[Push] permission result:", permission);
    if (permission !== "granted") return null;

    const swReg = await registerServiceWorker();
    console.log("[Push] SW registered:", !!swReg);
    const tokenOptions = { vapidKey: VAPID_KEY };
    if (swReg) tokenOptions.serviceWorkerRegistration = swReg;

    const fcmToken = await getToken(messaging, tokenOptions);
    console.log("[Push] FCM token obtained:", !!fcmToken);
    if (fcmToken) {
      const authToken = getAuthToken();
      console.log("[Push] auth token available:", !!authToken);
      if (authToken) {
        const resp = await fetch('/api/user/fcm-token', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
          },
          body: JSON.stringify({ token: fcmToken, platform: 'web' })
        });
        console.log("[Push] token POST status:", resp.status);
      }
    }
    return fcmToken;
  } catch (err) {
    console.error("[Push] FCM token error:", err);
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
