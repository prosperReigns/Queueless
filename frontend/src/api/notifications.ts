import { apiClient } from './client'

interface FcmTokenPayload {
  fcm_token: string
}

const notificationTokenEndpoint =
  import.meta.env.VITE_NOTIFICATIONS_TOKEN_ENDPOINT ?? '/notifications/token'
const MAX_SYNC_ATTEMPTS = 3
const RETRY_DELAYS_MS = [500, 1000]

const sleep = (delayMs: number) =>
  new Promise<void>((resolve) => {
    window.setTimeout(resolve, delayMs)
  })

export async function syncFcmTokenWithBackend(fcmToken: string): Promise<boolean> {
  if (!fcmToken.trim()) {
    throw new Error('Cannot sync an empty FCM token')
  }

  let lastError: unknown = null

  for (let attempt = 1; attempt <= MAX_SYNC_ATTEMPTS; attempt += 1) {
    try {
      await apiClient.post<FcmTokenPayload>(notificationTokenEndpoint, { fcm_token: fcmToken })
      return true
    } catch (error) {
      lastError = error

      if (attempt < MAX_SYNC_ATTEMPTS) {
        const retryDelayMs = RETRY_DELAYS_MS[attempt - 1] ?? RETRY_DELAYS_MS[RETRY_DELAYS_MS.length - 1]
        await sleep(retryDelayMs)
      }
    }
  }

  if (lastError) {
    throw lastError
  }

  throw new Error('Failed to sync FCM token')
}
