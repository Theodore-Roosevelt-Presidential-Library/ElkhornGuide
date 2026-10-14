Working scripts behind docs/model (October 2026). They were run in a temporary workspace,
so input/output paths at the top of each script (and lidar/common.py) point there; set them
to your own folders before rerunning.

footprint/  360-panorama stone measurement and least-squares footprint fit (crop, solve, fit, final, plan)
lidar/      3DEP point-cloud fetch (public EPT on S3), 0.5 m ground model, visualizations,
            pit/mound detection, ring test, profiles (run 01_ to 13_ in order)
overlay/    render.py: registers the 1957-59 Beaubien-Taylor plan to the footprint and draws
            it over the lidar (site_evidence.jpg)
Python 3 with numpy, scipy, pillow, rasterio, pyproj, laspy[lazrs], matplotlib.
