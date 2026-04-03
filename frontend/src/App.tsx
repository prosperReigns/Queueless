import { useEffect, useRef, useState } from 'react'
import type { MessagePayload } from 'firebase/messaging'
import { Link, useNavigate } from 'react-router-dom'
import { AppRouter } from './routes/AppRouter'
import { syncFcmTokenWithBackend } from './api/notifications'
import { useAuth } from './hooks/useAuth'
import {
  getCurrentNotificationPermission,
  getFcmRegistrationToken,
  listenForForegroundMessages,
  requestPushPermission,
} from './services/firebase'

const MAX_IN_APP_NOTIFICATIONS = 5
const LIFECYCLE_SYNC_THROTTLE_MS = 15000

interface InAppNotification {
  id: string
  title: string
  body: string
  orderId: string | null
}

function toInAppNotification(payload: MessagePayload): InAppNotification {
  const title = payload.notification?.title ?? payload.data?.title ?? 'Notification'
  const body = payload.notification?.body ?? payload.data?.body ?? 'You have a new update.'
  const orderId = payload.data?.order_id ?? null

  return {
    id: crypto.randomUUID(),
    title,
    body,
    orderId,
  }
}

function NotificationFeed({
  notifications,
  onDismiss,
}: {
  notifications: InAppNotification[]
  onDismiss: (id: string) => void
}) {
  if (notifications.length === 0) {
    return null
  }

  return (
    <section className="notification-feed" aria-live="polite">
      {notifications.map((notification) => (
        <article key={notification.id} className="notification-card">
          <div className="notification-card__content">
            <h3>{notification.title}</h3>
            <p>{notification.body}</p>
            {notification.orderId ? (
              <Link className="inline-link" to={`/orders/${notification.orderId}`}>
                View order
              </Link>
            ) : null}
          </div>
          <button
            type="button"
            className="notification-card__dismiss"
            onClick={() => onDismiss(notification.id)}
            aria-label="Dismiss notification"
          >
            ×
          </button>
        </article>
      ))}
    </section>
  )
}

function App() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [notifications, setNotifications] = useState<InAppNotification[]>([])
  const syncedTokenRef = useRef<string | null>(null)

  useEffect(() => {
    if (!('serviceWorker' in navigator)) {
      return
    }

    const handleServiceWorkerMessage = (event: MessageEvent<unknown>) => {
      const payload = event.data as { type?: string; url?: string } | null
      if (payload?.type !== 'notification-click' || typeof payload.url !== 'string') {
        return
      }
      navigate(payload.url)
    }

    navigator.serviceWorker.addEventListener('message', handleServiceWorkerMessage)
    return () => {
      navigator.serviceWorker.removeEventListener('message', handleServiceWorkerMessage)
    }
  }, [navigate])

  useEffect(() => {
    if (!user) {
      syncedTokenRef.current = null
      return
    }

    let active = true
    let unsubscribe: (() => void) | null = null
    let lastLifecycleSyncTimestamp = 0

    const syncToken = async () => {
      const permission =
        getCurrentNotificationPermission() === 'granted' ? 'granted' : await requestPushPermission()

      if (!active || permission !== 'granted') {
        return null
      }

      const fcmToken = await getFcmRegistrationToken()
      if (!active || !fcmToken) {
        return null
      }

      if (syncedTokenRef.current !== fcmToken) {
        await syncFcmTokenWithBackend(fcmToken)
        syncedTokenRef.current = fcmToken
      }

      return fcmToken
    }

    const initializePushNotifications = async () => {
      await syncToken()

      unsubscribe = await listenForForegroundMessages((payload) => {
        const inAppNotification = toInAppNotification(payload)
        setNotifications((current) => {
          if (current.length < MAX_IN_APP_NOTIFICATIONS) {
            return [inAppNotification, ...current]
          }
          return [inAppNotification, ...current.slice(0, MAX_IN_APP_NOTIFICATIONS - 1)]
        })
      })
    }

    const onLifecycleSync = () => {
      if (!active) {
        return
      }

      const now = Date.now()
      if (now - lastLifecycleSyncTimestamp < LIFECYCLE_SYNC_THROTTLE_MS) {
        return
      }

      lastLifecycleSyncTimestamp = now
      void syncToken().catch((error: unknown) => {
        if (import.meta.env.DEV) {
          console.warn('FCM token lifecycle sync failed', error)
        }
      })
    }

    initializePushNotifications().catch((error: unknown) => {
      if (import.meta.env.DEV) {
        console.warn('Push notification setup failed', error)
      }
    })

    window.addEventListener('focus', onLifecycleSync)
    window.addEventListener('online', onLifecycleSync)
    document.addEventListener('visibilitychange', onLifecycleSync)

    return () => {
      active = false
      window.removeEventListener('focus', onLifecycleSync)
      window.removeEventListener('online', onLifecycleSync)
      document.removeEventListener('visibilitychange', onLifecycleSync)
      unsubscribe?.()
    }
  }, [user])

  return (
    <>
      <NotificationFeed
        notifications={notifications}
        onDismiss={(id) => {
          setNotifications((current) => current.filter((notification) => notification.id !== id))
        }}
      />
      <AppRouter />
    </>
  )
}

export default App
