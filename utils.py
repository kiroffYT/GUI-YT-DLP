import os
import platform
from plyer import notification

def send_system_notification(title, message):
    try:
        notification.notify(title=title, message=message, app_name="YT Downloader", timeout=5)
    except: pass

def get_default_download_path():
    if platform.system() == "Windows":
        return os.path.join(os.environ["USERPROFILE"], "Downloads")
    return os.path.join(os.path.expanduser("~"), "Downloads")