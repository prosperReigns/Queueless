export function requestPushPermission() {
  if (!('Notification' in window)) {
    return Promise.resolve('denied' as NotificationPermission)
  }

  return Notification.requestPermission()
}
