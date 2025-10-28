import rasterio
import numpy as np
import matplotlib.pyplot as plt
from rasterio.plot import show

tile = "data/dem/Copernicus_DSM_COG_10_N51_00_W002_00_DEM.tif"

with rasterio.open(tile) as src:
    arr = src.read(1)
    print("dtype:", arr.dtype)
    print("min:", np.nanmin(arr), "max:", np.nanmax(arr))
    print("nodata:", src.nodata)
    print("bounds:", src.bounds)

with rasterio.open(tile) as src:
    show(src, cmap='terrain')
plt.show()
