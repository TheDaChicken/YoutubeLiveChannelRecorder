import os
from ..log import warning
import platform

# Windows ToastNotifier

if platform.release() is '10':
    from win10toast import ToastNotifier

    toaster = ToastNotifier()
else:
    pywintypes = None
    toaster = None


# Windows Notification
def show_windows_toast_notification(title, description):
    if toaster:
        # noinspection PyBroadException
        try:
            toaster.show_toast(title, description, icon_path=os.path.join("NotificationIcon", 'python.ico'))
        except Exception:
            warning("Unable to send Windows Toast Notification.")
