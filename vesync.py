from pyvesync import VeSync


def get_data():
    manager = VeSync("ferocemarcello@gmail.com", "password", time_zone="Europe/Oslo")
    manager.login()
    manager.update()
    return manager.get_devices()
