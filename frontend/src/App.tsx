import { useEffect, useRef, useState } from 'react'
import type { MessagePayload } from 'firebase/messaging'
import { Link } from 'react-router-dom'
import { AppRouter } from './routes/AppRouter'
import { syncFcmTokenWithBackend } from './api/notifications'
import { useAuth } from './hooks/useAuth'
import {
  getCurrentNotificationPermission,
  getFcmRegistrationToken,
  listenForForegroundMessages,
  requestPushPermission,
} from './services/firebase'

interface InAppNotification {
  id: number
  title: string
  body: string
  orderId: string | null
}

function toInAppNotification(payload: MessagePayload): InAppNotification | null {
  const title = payload.notification?.title ?? payload.data?.title ?? 'Notification'
  const body = payload.notification?.body ?? payload.data?.body ?? 'You have a new update.'
  const orderId = payload.data?.order_id ?? null

  if (!title && !body) {
    return null
  }

  return {
    id: Date.now() + Math.floor(Math.random() * 1000),
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
  onDismiss: (id: number) => void
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
  const [notifications, setNotifications] = useState<InAppNotification[]>([])
  const syncedTokenRef = useRef<string | null>(null)

  useEffect(() => {
    if (!user) {
      setNotifications([])
      syncedTokenRef.current = null
      return
    }

    let active = true
    let unsubscribe: (() => void) | null = null

    void (async () => {
      try {
        const permission =
          getCurrentNotificationPermission() === 'granted'
            ? 'granted'
            : await requestPushPermission()

        if (!active || permission !== 'granted') {
          return
        }

        const fcmToken = await getFcmRegistrationToken()
        if (!active || !fcmToken) {
          return
        }

        if (syncedTokenRef.current !== fcmToken) {
          await syncFcmTokenWithBackend(fcmToken)
          syncedTokenRef.current = fcmToken
        }

        unsubscribe = await listenForForegroundMessages((payload) => {
          const inAppNotification = toInAppNotification(payload)
          if (!inAppNotification) {
            return
          }
          setNotifications((current) => [inAppNotification, ...current].slice(0, 5))
        })
      } catch (error) {
        if (import.meta.env.DEV) {
          console.warn('Push notification setup failed', error)
        }
      }
    })()

    return () => {
      active = false
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
