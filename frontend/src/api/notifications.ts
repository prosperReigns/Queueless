import { apiClient } from './client'

interface FcmTokenPayload {
  fcm_token: string
}

const notificationTokenEndpoint = import.meta.env.VITE_NOTIFICATIONS_TOKEN_ENDPOINT

export async function syncFcmTokenWithBackend(fcmToken: string): Promise<boolean> {
  if (!notificationTokenEndpoint) {
    return false
  }

  await apiClient.post<FcmTokenPayload>(notificationTokenEndpoint, { fcm_token: fcmToken })
  return true
}
