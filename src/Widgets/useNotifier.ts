import { ref } from 'vue'

export type NotificationKind = 'info' | 'success' | 'warning' | 'error'
export interface NotificationItem {
  id: number
  message: string
  kind: NotificationKind
  duration: number
}

const notifications = ref<NotificationItem[]>([])
let nextId = 1

export function useNotifier() {
  function dismiss(id: number) {
    notifications.value = notifications.value.filter((item) => item.id !== id)
  }

  function notify(message: string, kind: NotificationKind = 'info', duration = 4000) {
    const item = { id: nextId++, message, kind, duration }
    notifications.value.push(item)
    if (duration > 0) window.setTimeout(() => dismiss(item.id), duration)
    return item.id
  }

  return { notifications, notify, dismiss }
}