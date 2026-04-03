import { initializeApp, type FirebaseApp } from 'firebase/app'
import { getMessaging, getToken, isSupported, onMessage, type MessagePayload } from 'firebase/messaging'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

const hasFirebaseConfig = Boolean(
  firebaseConfig.apiKey &&
    firebaseConfig.projectId &&
    firebaseConfig.messagingSenderId &&
    firebaseConfig.appId,
)

let firebaseApp: FirebaseApp | null = null
let supportedPromise: Promise<boolean> | null = null

const getFirebaseApp = () => {
  if (!hasFirebaseConfig) {
    return null
  }

  if (!firebaseApp) {
    firebaseApp = initializeApp(firebaseConfig)
  }

  return firebaseApp
}

const getMessagingSupport = () => {
  if (!supportedPromise) {
    supportedPromise = isSupported()
  }

  return supportedPromise
}

const registerMessagingServiceWorker = async () => {
  if (!('serviceWorker' in navigator)) {
    return null
  }

  return navigator.serviceWorker.register('/firebase-messaging-sw.js')
}

export function getCurrentNotificationPermission(): NotificationPermission {
  if (!('Notification' in window)) {
    return 'denied'
  }

  return Notification.permission
}

export function requestPushPermission() {
  if (!('Notification' in window)) {
    return Promise.resolve('denied' as NotificationPermission)
  }

  return Notification.requestPermission()
}

export async function getFcmRegistrationToken(): Promise<string | null> {
  const app = getFirebaseApp()
  if (!app) {
    return null
  }

  if (!(await getMessagingSupport())) {
    return null
  }

  const serviceWorkerRegistration = await registerMessagingServiceWorker()
  const messaging = getMessaging(app)
  const token = await getToken(messaging, {
    vapidKey: import.meta.env.VITE_FIREBASE_VAPID_KEY,
    serviceWorkerRegistration: serviceWorkerRegistration ?? undefined,
  })

  return token || null
}

export async function listenForForegroundMessages(
  onForegroundMessage: (payload: MessagePayload) => void,
): Promise<(() => void) | null> {
  const app = getFirebaseApp()
  if (!app) {
    return null
  }

  if (!(await getMessagingSupport())) {
    return null
  }

  const messaging = getMessaging(app)
  return onMessage(messaging, onForegroundMessage)
}
