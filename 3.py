import subprocess

def get_usb_serials():
    result = subprocess.run(
        ["wmic", "diskdrive", "get", "DeviceID,SerialNumber,Model"],
        capture_output=True, text=True
    )
    print(result.stdout)

get_usb_serials()
