import ctypes
import threading
import time
from tkinter import *

import cv2
from PIL import Image
from plyer import notification
from pystray import *

"""
Global variables 
"""
limit = 60
notification_count = 0
system_tray_thread = None
notification_watchdog_thread = None
monitor_thread = None
mutex = threading.Lock()

start_camera = False
stop_camera = False
stop_monitor = True


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
    Setup the GUI menu in the System Tray
    """
    icon.visible = True

    i = 0
    while icon.visible:
        i += 1

        time.sleep(5)


def notification_watchdog():
    global notification_count, stop_monitor
    while True:
        time.sleep(10)
        notification_count = 0
        if stop_monitor:
            break


def notify():
    global notification_count
    notification_count += 1
    notification.notify(
        title='You are too close to the monitor!',
        message='Please stand further away from your monitor!',
        app_icon=None,  # e.g. 'C:\\icon_32x32.ico'
        # TODO: Get an icon
        timeout=1,  # seconds
    )
    # notifications cannot be sent one after another.
    # they are sent in bursts of 2, a watchdog on a separate thread keeps track of them


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
    face_cascade = cv2.CascadeClassifier('./haar-cascade-files-master/haarcascade_frontalface_default.xml')
    cap = cv2.VideoCapture(0)
    global notification_count, stop_monitor
    stop_monitor = False

    if cap is None or not cap.isOpened():
        # if camera cannot be opened, error
        ctypes.windll.user32.MessageBoxW(0, u"Could not access camera!", u"Error", 0)
    while True:
        # Read, convert to grayscale and calculate the distance to the detected face.
        ret, img = cap.read()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        for (x, y, z, h) in faces:
            cv2.rectangle(img, (x, y), (x + z, y + h), (0, 255, 0), 2)
            roi = gray[x:x + z, y:y + h]
            length = roi.shape[0]
            breadth = roi.shape[1]
            area = length * breadth
            distance = 3 * (10 ** (-9)) * (area ** 2) - 0.001 * area + 108.6
            display = 'Distance = ' + str(distance)
            # if the distance is smaller than a certain number, send notification to user
            if distance < limit:
                if notification_count < 1:
                    notify()
            font = cv2.FONT_HERSHEY_SIMPLEX
            if area > 0:
                cv2.putText(img, display, (5, 50), font, 2, (255, 255, 0), 2, cv2.LINE_AA)

        if start_camera:
            cv2.imshow("Camera", img)

        if stop_camera:
            cv2.destroyWindow("Camera")

        key = cv2.waitKey(5) & 0xFF
        if key == ord("v") or stop_monitor:
            break

    # release all Video streams and destroy Windows
    cap.release()
    cv2.destroyAllWindows()


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
    global stop_monitor
    stop_monitor = True


def monitor_thread_cb():
    """
    callback function for distance monitor thread
    """
    global monitor_thread
    try:
        # start the daemon for monitoring the camera
        monitor_thread = threading.Thread(target=measure_distance)
        monitor_thread.start()
    except:
        print("error creating thread")


def enter_limit(limit_string, label_string):
    global limit
    local = limit_string.get()
    if local <= 25 or local >= 60:
        ctypes.windll.user32.MessageBoxW(0, u"For safety reasons, you cannot set the distance lower than 25 cm or higher than 60 cm", u"Error", 0)
    else:
        limit = local
    label_string.set("Distance:" + str(limit))


def tk_main_window():
    """
    main window GUI
    """
    global limit, stop_monitor
    mainWindow = Tk()
    mainWindowTitle = Label(mainWindow, text="User Monitor GUI")
    mainWindowTitle.pack()
    # Buttons call appropriate callback functions
    B = Button(mainWindow, text="start monitor", command=monitor_thread_cb)
    C = Button(mainWindow, text="start camera", command=start_cam_button)
    D = Button(mainWindow, text="stop camera", command=stop_cam_button)
    F = Button(mainWindow, text="stop monitor", command=stop_monitor_button)
    limit_string = IntVar()
    distance_string = StringVar()
    distance_string.set("Distance:" + str(limit))
    E_b = Button(mainWindow, text="Submit", command=lambda: enter_limit(limit_string, distance_string))
    # Text box for distance input
    limitEntered = Entry(mainWindow, width=15, textvariable=limit_string)
    B.pack()
    C.pack()
    D.pack()
    F.pack()
    label = Label(mainWindow, text="Enter minimum limit for distance:")
    label.pack()
    limitEntered.pack()
    E_b.pack()
    label1 = Label(mainWindow, textvariable=distance_string)
    label1.pack()
    # run window loop
    mainWindow.mainloop()
    if not stop_monitor:
        stop_monitor = True
    mainWindow.quit()


def main():
    """
    main function of the program
    """
    global system_tray_thread, notification_count, notification_watchdog_thread
    try:
        # create thread for the System Tray
        system_tray_thread = threading.Thread(target=sys_tray_icon)
        system_tray_thread.start()
    except:
        print("error")

    try:
        # create thread for the notification watchdog
        notification_watchdog_thread = threading.Thread(target=notification_watchdog)
        notification_watchdog_thread.start()
    except:
        print("error")

    tk_main_window()


if __name__ == "__main__":
    main()
