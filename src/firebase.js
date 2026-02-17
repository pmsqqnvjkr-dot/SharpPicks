import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getMessaging, getToken, onMessage } from "firebase/messaging";
import { getAuthToken } from "./hooks/useApi";
import { Capacitor } from "@capacitor/core";

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
const API_BASE = "https://app.sharppicks.ai";

const isNative = Capacitor.isNativePlatform();
console.log("[Push] platform:", isNative ? Capacitor.getPlatform() : "web");

const app = initializeApp(firebaseConfig);
let analytics = null;
try { analytics = getAnalytics(app); } catch (e) {}

async function sendTokenToServer(token, platform) {
  const authToken = getAuthToken();
  console.log("[Push] auth token available:", !!authToken);
  if (!authToken) return;
  const base = isNative ? API_BASE : '';
  const resp = await fetch(base + '/api/user/fcm-token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`
    },
    body: JSON.stringify({ token, platform })
  });
  console.log("[Push] token POST status:", resp.status);
  return resp;
}

async function requestNativePush() {
  const { PushNotifications } = await import("@capacitor/push-notifications");

  let permResult = await PushNotifications.checkPermissions();
  console.log("[Push] native permission status:", permResult.receive);

  if (permResult.receive === 'prompt') {
    permResult = await PushNotifications.requestPermissions();
  }

  if (permResult.receive !== 'granted') {
    console.log("[Push] native permission denied");
    return null;
  }

  return new Promise((resolve) => {
    PushNotifications.addListener('registration', async (token) => {
      console.log("[Push] native token:", token.value.substring(0, 20) + "...");
      const platform = Capacitor.getPlatform();
      await sendTokenToServer(token.value, platform);
      resolve(token.value);
    });

    PushNotifications.addListener('registrationError', (err) => {
      console.error("[Push] native registration error:", err.error);
      resolve(null);
    });

    PushNotifications.addListener('pushNotificationReceived', (notification) => {
      console.log("[Push] foreground notification:", notification.title);
    });

    PushNotifications.addListener('pushNotificationActionPerformed', (action) => {
      console.log("[Push] notification tapped:", action.notification.title);
    });

    PushNotifications.register();
  });
}

let messagingInstance = null;

function canUseWebMessaging() {
  if (typeof window === 'undefined') return false;
  const hasNotification = 'Notification' in window;
  const hasSW = 'serviceWorker' in navigator;
  const hasIDB = 'indexedDB' in window;
  return hasNotification && hasSW && hasIDB;
}

function getOrInitMessaging() {
  if (messagingInstance) return messagingInstance;
  if (!canUseWebMessaging()) return null;
  try {
    messagingInstance = getMessaging(app);
    onMessage(messagingInstance, (payload) => {
      const { title, body } = payload.notification || {};
      if (title) {
        new Notification(title, { body, icon: "/icon-192x192.png", badge: "/favicon-32x32.png" });
      }
    });
    return messagingInstance;
  } catch (e) {
    console.warn("[Push] web messaging init failed:", e.message);
    return null;
  }
}

if (!isNative) {
  getOrInitMessaging();
}

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

async function requestWebPush() {
  const msg = getOrInitMessaging();
  if (!msg) {
    console.warn("[Push] web messaging not available");
    return null;
  }
  try {
    const permission = await Notification.requestPermission();
    console.log("[Push] web permission result:", permission);
    if (permission !== "granted") return null;

    const swReg = await registerServiceWorker();
    if (!swReg) return null;

    const fcmToken = await getToken(msg, { vapidKey: VAPID_KEY, serviceWorkerRegistration: swReg });
    console.log("[Push] FCM token obtained:", fcmToken ? fcmToken.substring(0, 20) + "..." : "null");

    if (fcmToken) {
      const isIOS = /iPhone|iPad|iPod/.test(navigator.userAgent);
      await sendTokenToServer(fcmToken, isIOS ? 'ios' : 'web');
    }
    return fcmToken;
  } catch (err) {
    console.error("[Push] web push error:", err.message || err);
    return null;
  }
}

async function requestNotificationPermission() {
  if (isNative) {
    return requestNativePush();
  }
  return requestWebPush();
}

function getNotificationPermissionStatus() {
  if (!('Notification' in window)) return 'unsupported';
  return Notification.permission;
}

async function getNativePermissionStatus() {
  if (!isNative) return getNotificationPermissionStatus();
  try {
    const { PushNotifications } = await import("@capacitor/push-notifications");
    const result = await PushNotifications.checkPermissions();
    if (result.receive === 'granted') return 'granted';
    if (result.receive === 'denied') return 'denied';
    return 'default';
  } catch {
    return 'unsupported';
  }
}

export {
  app,
  analytics,
  messagingInstance as messaging,
  requestNotificationPermission,
  getNotificationPermissionStatus,
  getNativePermissionStatus,
  isNative
};
