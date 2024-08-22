# Add:
#   execfile('get.py')
# to boot.py
#
# shortcut to re-run get.py:
# >>> g()
#
# shortcut to run grids:
# >>> d()

# Change this to the IP where file_server.py is running ...
server = "http://192.168.86.36:8000"

files = [
    #"grids.py",
    #"resources_drum_map.py",
    #"resources_euclidean.py",
    #"tulip_grids.py",
    "tworld_grids.py",
]

for f in files:
    tulip.url_save(f"{server}/{f}", f)
    print("Downloaded: ", f)


def g():
    execfile("get.py")


def d():
    run("tworld_grids")
