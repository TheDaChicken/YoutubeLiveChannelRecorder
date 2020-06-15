import os
from ..log import warning
import platform

# Windows ToastNotifier
if platform.release() == '10':
    try:
        from win10toast import ToastNotifier

        toaster = ToastNotifier()
    except ImportError:
        warning("win10toast isn't installed! "
                "Since you are using Windows 10, you can use that!")
        ToastNotifier = None
        toaster = None
else:
    toaster = None


# Windows Notification
def show_windows_toast_notification(title, description):
    if toaster:
        # noinspection PyBroadException
        try:
            toaster.show_toast(title, description)
        except Exception:
            warning("Unable to send Windows Toast Notification.")
