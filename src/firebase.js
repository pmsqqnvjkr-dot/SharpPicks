import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getMessaging, getToken, onMessage, isSupported } from "firebase/messaging";
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

let messagingInstance = null;
let messagingReady = false;

async function initMessaging() {
  try {
    const supported = await isSupported();
    console.log("[Push] isSupported:", supported);
    if (supported) {
      messagingInstance = getMessaging(app);
      messagingReady = true;
      onMessage(messagingInstance, (payload) => {
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
  } catch (e) {
    console.warn("[Push] messaging init failed:", e);
  }
}

initMessaging();

async function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    try {
      const reg = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
      return reg;
    } catch (err) {
      console.error("[Push] SW registration failed:", err);
      return null;
    }
  }
  return null;
}

async function requestNotificationPermission() {
  if (!messagingReady || !messagingInstance) {
    const supported = await isSupported();
    if (!supported) {
      console.warn("[Push] messaging not supported on this device/browser");
      return null;
    }
    if (!messagingInstance) {
      messagingInstance = getMessaging(app);
      messagingReady = true;
    }
  }
  try {
    const permission = await Notification.requestPermission();
    console.log("[Push] permission result:", permission);
    if (permission !== "granted") return null;

    const swReg = await registerServiceWorker();
    console.log("[Push] SW registered:", !!swReg);
    const tokenOptions = { vapidKey: VAPID_KEY };
    if (swReg) tokenOptions.serviceWorkerRegistration = swReg;

    const fcmToken = await getToken(messagingInstance, tokenOptions);
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
          body: JSON.stringify({ token: fcmToken, platform: navigator.userAgent.includes('iPhone') ? 'ios' : 'web' })
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

function getNotificationPermissionStatus() {
  if (!('Notification' in window)) return 'unsupported';
  return Notification.permission;
}

export { app, analytics, messagingInstance as messaging, requestNotificationPermission, getNotificationPermissionStatus };
