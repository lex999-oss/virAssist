from threading import Thread, ThreadError, Lock
from time import time, sleep
from tkinter import Tk, Label, Button
from cv2 import CascadeClassifier, VideoCapture, cvtColor, COLOR_BGR2GRAY, rectangle, FONT_HERSHEY_SIMPLEX, putText, \
                imshow, destroyWindow, waitKey, LINE_AA, destroyAllWindows
from PIL import Image
from notifypy import Notify
from pystray import Icon, MenuItem, Menu
from os import startfile
from ctypes import Structure, windll, c_uint, sizeof, byref
from yaml import load, FullLoader


class LASTINPUTINFO(Structure):
    _fields_ = [
        ('cbSize', c_uint),
        ('dwTime', c_uint),
    ]


def get_idle_duration():
    lastInputInfo = LASTINPUTINFO()
    lastInputInfo.cbSize = sizeof(lastInputInfo)
    windll.user32.GetLastInputInfo(byref(lastInputInfo))
    millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
    return millis / 1000.0


"""
Global variables 
"""
distance_limit = 60  # centimeters
notification_count = 0
idle_time = 0
active_time = 0
idle_time_limit = 300  # seconds
active_time_limit = 3600  # seconds
system_tray_thread = Thread
notification_watchdog_thread = Thread
active_time_measure_thread = Thread
monitor_thread = Thread
stop_time_monitor = 0
active_time_mutex = Lock()

start_camera = False
stop_camera = False
stop_monitor = True
monitor_thread_started = False


def exit_action(icon):
    """
    :param icon: Icon from PySTray
    :return: --
    Close the GUI menu in the System Tray
    """
    global stop_monitor
    if not stop_monitor:
        stop_monitor = True
    icon.visible = False
    icon.stop()


def setup(icon):
    """
    :param icon: Icon from PySTray
    :return: --
    Set up the GUI menu in the System Tray
    """
    icon.visible = True

    i = 0
    while icon.visible:
        i += 1

        sleep(5)


def notification_watchdog():
    # reset notification every 10 seconds -> prevents notification flood
    global notification_count, stop_monitor
    while True:
        sleep(10)
        notification_count = 0
        if stop_monitor:
            break


def notify(notif_type):
    global notification_count
    notification = Notify(default_notification_application_name="virAssist",
                          default_notification_icon=".\\icons8-eye-40.png")
    if notif_type == 0:
        notification.title = 'You are too close to the monitor!'
        notification.message = 'Please stand further away from your monitor!'
        notification_count += 1
    elif notif_type == 1:
        notification.title = 'You should take a break!'
        notification.message = 'Please take some time away from the computer!'
    elif notif_type == 2:
        notification.title = 'Break is over!'
        notification.message = 'You can resume work!'
    notification.send(block=False)


def init_icon():
    """
    :return: --
    Initialise the GUI menu in the System Tray
    """
    icon = Icon('mon')
    item = MenuItem("Start Monitor", monitor_thread_cb)
    item1 = MenuItem("Start Camera", start_cam_button)
    item2 = MenuItem("Exit", lambda: exit_action(icon))
    item3 = MenuItem("Stop Camera", stop_cam_button)
    item4 = MenuItem("Stop Monitor", stop_monitor_button)
    menu = Menu(item, item1, item3, item4, item2)

    icon.menu = menu

    icon.icon = Image.open('icons8-eye-40.png')
    icon.title = 'User Monitor'

    icon.run(setup)


def sys_tray_icon():
    """
    Icon file imported from Icons8.com
    run system tray app function
    """
    init_icon()


def measure_distance():
    """
    Function that measures the distance between user and web camera
    """
    # initialise CV2 library and Video stream
    face_cascade = CascadeClassifier('./haarcascade_frontalface_default.xml')
    cap = VideoCapture(0)
    global notification_count, stop_monitor
    stop_monitor = False

    if not cap.read()[0]:
        # if camera cannot be opened, error
        windll.user32.MessageBoxW(0, u"Could not access camera!", u"Error", 0)
        stop_monitor = True
        return

    while True:
        # Read, convert to grayscale and calculate the distance to the detected face.
        ret, img = cap.read()
        gray = cvtColor(img, COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        for (x, y, z, h) in faces:
            rectangle(img, (x, y), (x + z, y + h), (0, 255, 0), 2)
            roi = gray[x:x + z, y:y + h]
            length = roi.shape[0]
            breadth = roi.shape[1]
            area = length * breadth
            distance = 3 * (10 ** (-9)) * (area ** 2) - 0.001 * area + 108.6
            display = 'Distance = ' + str(distance)
            # if the distance is smaller than a certain number, send notification to user
            if distance < distance_limit:
                if notification_count < 1:
                    notify(0)
            font = FONT_HERSHEY_SIMPLEX
            if area > 0:
                putText(img, display, (5, 50), font, 2, (255, 255, 0), 2, LINE_AA)

        if start_camera:
            imshow("Camera", img)

        if stop_camera:
            destroyWindow("Camera")

        key = waitKey(5) & 0xFF
        if key == ord("v") or stop_monitor:
            stop_monitor = False
            break
    # release all Video streams and destroy Windows
    cap.release()
    destroyAllWindows()


def start_cam_button():
    """
    flags for starting the camera
    """
    global start_camera
    global stop_camera
    stop_camera = False
    start_camera = True


def stop_cam_button():
    """
    flags for stopping the camera
    """
    global start_camera
    global stop_camera
    start_camera = False
    stop_camera = True


def stop_monitor_button():
    global stop_monitor, monitor_thread_started
    stop_monitor = True
    if monitor_thread_started:
        monitor_thread.join()
        monitor_thread_started = False


def monitor_thread_cb():
    """
    callback function for distance monitor thread
    """
    global monitor_thread, monitor_thread_started, stop_monitor
    if not monitor_thread_started:
        try:
            # start the daemon for monitoring the camera
            monitor_thread = Thread(target=measure_distance)
            monitor_thread.start()
            monitor_thread_started = True
        except ThreadError:
            print("error creating thread")
            monitor_thread_started = False


def edit_conf_file():
    startfile(".\\conf.yaml")
    load_config()


def tk_main_window():
    """
    main window GUI
    """
    global distance_limit, stop_monitor
    mainWindow = Tk()
    mainWindow.title('virAssist')
    mainWindow.geometry('260x180')
    mainWindow.iconbitmap(".\\favicon.ico")
    mainWindowTitle = Label(mainWindow, text="User Monitor GUI")
    mainWindowTitle.pack()
    # Buttons call appropriate callback functions
    B = Button(mainWindow, text="start monitor", command=monitor_thread_cb)
    C = Button(mainWindow, text="start camera", command=start_cam_button)
    D = Button(mainWindow, text="stop camera", command=stop_cam_button)
    F = Button(mainWindow, text="stop monitor", command=stop_monitor_button)
    E = Button(mainWindow, text="edit config", command=edit_conf_file)
    edit_config_notice = Label(relief="sunken", text="Note: Restart app after editing config file.")
    B.pack()
    C.pack()
    D.pack()
    F.pack()
    E.pack()
    edit_config_notice.pack()
    # run window loop
    mainWindow.mainloop()
    mainWindow.quit()


def active_time_measure():
    global active_time, idle_time, active_time_limit
    if int(time() - active_time) >= active_time_limit:
        notify(1)
        idle_time_measure_wd()


def active_time_measure_wd():
    global active_time, stop_time_monitor
    active_time = time()

    while True:
        if stop_time_monitor:
            break
        sleep(10)
        active_time_measure()


def idle_time_measure_wd():
    global idle_time, active_time, idle_time_limit
    while True:
        if stop_time_monitor:
            break
        sleep(10)
        idle_time = get_idle_duration()
        if idle_time >= idle_time_limit:
            notify(2)
            break
    active_time = time()


def main():
    """
    main function of the program
    """
    global system_tray_thread, notification_count, notification_watchdog_thread, active_time_measure_thread, stop_time_monitor
    try:
        # create thread for the System Tray
        system_tray_thread = Thread(target=sys_tray_icon)
        system_tray_thread.start()
    except ThreadError:
        print("error")

    try:
        # create thread for the notification watchdog
        notification_watchdog_thread = Thread(target=notification_watchdog)
        notification_watchdog_thread.start()
    except ThreadError:
        print("error")

    try:
        # create thread for the notification watchdog
        active_time_measure_thread = Thread(target=active_time_measure_wd)
        active_time_measure_thread.start()
    except ThreadError:
        print("error")

    tk_main_window()
    stop_time_monitor = 1
    system_tray_thread.join()
    notification_watchdog_thread.join()
    active_time_measure_thread.join()


def load_config():
    global distance_limit, idle_time_limit, active_time_limit
    with open("conf.yaml", "r") as yamlfile:
        data = load(yamlfile, Loader=FullLoader)
    distance_limit = data['distance_limit']
    idle_time_limit = data['idle_time_limit']
    active_time_limit = data['active_time_limit']


if __name__ == "__main__":
    load_config()
    main()
