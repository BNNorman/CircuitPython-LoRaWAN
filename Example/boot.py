import storage

# make the filesystem writeable so we can write a log file on it
# if you are not using logging don't install this file
try:
    storage.remount("/",False)
    print("Filesystem remounted r/w")
    print("NOTE: CIRCUITPY drive will be write protected but Thonny can still delete/add files")
except Exception as e:
    print(f"boot.py exception: {e}")