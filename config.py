START_END_LAT_LON = (51.908571, -2.086392)  # start and end coordinate of looped route
WAYPOINTS = [(51.931178, -2.069347), (51.913158, -2.040591), (51.904085, -2.069953)]  # list of waypoints that must be visited
TARGET_DISTANCE_KM = 6  # target distance for generated route
TARGET_ELEVATION_M = 200  # target elevation for generated route
MIN_OUT_AND_BACK_FRAC = 0.15  # how short (proportion) out-and-back sections can be before they are removed during post-process
NETWORK_TYPE = "walk"  # walk, bike, or drive



RADIUS_KM = TARGET_DISTANCE_KM / 2
MAX_ITERATIONS = 10  # max iterations of post-processing route clean
