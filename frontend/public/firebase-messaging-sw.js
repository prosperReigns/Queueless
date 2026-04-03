/* global importScripts, firebase */
importScripts('https://www.gstatic.com/firebasejs/12.11.0/firebase-app-compat.js')
importScripts('https://www.gstatic.com/firebasejs/12.11.0/firebase-messaging-compat.js')

const url = new URL(self.location.href)
const firebaseConfig = {
  apiKey: url.searchParams.get('apiKey') || '',
  authDomain: url.searchParams.get('authDomain') || '',
  projectId: url.searchParams.get('projectId') || '',
  storageBucket: url.searchParams.get('storageBucket') || '',
  messagingSenderId: url.searchParams.get('messagingSenderId') || '',
  appId: url.searchParams.get('appId') || '',
}

if (
  typeof firebase !== 'undefined' &&
  firebaseConfig.apiKey &&
  firebaseConfig.projectId &&
  firebaseConfig.messagingSenderId &&
  firebaseConfig.appId
) {
  firebase.initializeApp(firebaseConfig)
  const messaging = firebase.messaging()

  messaging.onBackgroundMessage((payload) => {
    const title = payload?.notification?.title || payload?.data?.title || 'Notification'
    const body = payload?.notification?.body || payload?.data?.body || 'You have a new update.'
    const orderId = payload?.data?.order_id

    const notificationOptions = {
      body,
      data: orderId ? { url: `/orders/${orderId}` } : undefined,
    }

    void self.registration.showNotification(title, notificationOptions)
  })
}

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const targetUrl = event.notification?.data?.url || '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientsArr) => {
      for (const client of clientsArr) {
        if ('focus' in client) {
          client.postMessage({ type: 'notification-click', url: targetUrl })
          return client.focus()
        }
      }

      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl)
      }

      return undefined
    }),
  )
})
