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
let analytics = null;
try { analytics = getAnalytics(app); } catch (e) {}

function canUseMessaging() {
  if (typeof window === 'undefined') return false;
  const hasNotification = 'Notification' in window;
  const hasSW = 'serviceWorker' in navigator;
  const hasIDB = 'indexedDB' in window;
  console.log("[Push] capabilities:", { hasNotification, hasSW, hasIDB });
  return hasNotification && hasSW && hasIDB;
}

let messagingInstance = null;

function getOrInitMessaging() {
  if (messagingInstance) return messagingInstance;
  if (!canUseMessaging()) return null;
  try {
    messagingInstance = getMessaging(app);
    console.log("[Push] messaging initialized");
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
    return messagingInstance;
  } catch (e) {
    console.warn("[Push] messaging init failed:", e.message);
    return null;
  }
}

getOrInitMessaging();

async function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    try {
      const reg = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
      console.log("[Push] SW registered, scope:", reg.scope);
      return reg;
    } catch (err) {
      console.error("[Push] SW registration failed:", err);
      return null;
    }
  }
  return null;
}

async function requestNotificationPermission() {
  const msg = getOrInitMessaging();
  if (!msg) {
    console.warn("[Push] messaging not available on this device");
    return null;
  }
  try {
    const permission = await Notification.requestPermission();
    console.log("[Push] permission result:", permission);
    if (permission !== "granted") return null;

    const swReg = await registerServiceWorker();
    console.log("[Push] SW ready:", !!swReg);
    if (!swReg) {
      console.error("[Push] no service worker registration — cannot get token");
      return null;
    }

    const fcmToken = await getToken(msg, {
      vapidKey: VAPID_KEY,
      serviceWorkerRegistration: swReg
    });
    console.log("[Push] FCM token obtained:", fcmToken ? fcmToken.substring(0, 20) + "..." : "null");

    if (fcmToken) {
      const authToken = getAuthToken();
      console.log("[Push] auth token available:", !!authToken);
      if (authToken) {
        const isIOS = /iPhone|iPad|iPod/.test(navigator.userAgent);
        const resp = await fetch('/api/user/fcm-token', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
          },
          body: JSON.stringify({ token: fcmToken, platform: isIOS ? 'ios' : 'web' })
        });
        console.log("[Push] token POST status:", resp.status);
        const result = await resp.json();
        console.log("[Push] token POST result:", result);
      }
    }
    return fcmToken;
  } catch (err) {
    console.error("[Push] error:", err.message || err);
    return null;
  }
}

function getNotificationPermissionStatus() {
  if (!('Notification' in window)) return 'unsupported';
  return Notification.permission;
}

export { app, analytics, messagingInstance as messaging, requestNotificationPermission, getNotificationPermissionStatus };
