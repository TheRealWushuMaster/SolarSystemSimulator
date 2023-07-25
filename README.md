# ☀🌎🪐⭐☄ SOLARA: Solar System Simulator
This program creates a representation of the Solar System and its main celestial bodies using NASA's JPL ephemeris data. Its objective is to provide an accurate simulation that respects distances and sizes.
## How to use
### 1. Center view
Double click on any object or its name to focus the simulation on it.
### 2. Adjust scale
By default, the scale is calculated so that all objects will be visible at *scale=1.0*. The scale is adjusted using the mouse wheel, with three levels of granularity:
* **Shift + mouse wheel**: adjusts the scale in 0.1 increments
* **Mouse wheel**: adjusts the scale in 1 increments
* **Ctrl + mouse wheel**: doubles of halves the previous scale

The minimum scale is *0.1*.
### 3. Rotate view
By default, the simulation is viewed straight down from the z axis. Drag the window using the left mouse button to adjust *yaw* and *roll*, or using the right mouse button to adjust *pitch*.
### 4. Time adjustment
Use the up and down keys to cycle through the available time steps:
* 1 - 10 seconds
* 1 - 15 - 30 minutes
* 1 - 12 hours
* Days
* Weeks
* Months
* Years

Use the left or right keys to adjust the time backwards or forwards, respectively, with the selected time step.

The date range is roughly between the years 1550 and 2650 (from the *de440t.bsp* ephemeris).
### 5. Auto simulation
Use the spacebar to start or stop the automatic time advancement using the selected time step. The speed of the simulation is determined by the `FRAMES_PER_SECOND` parameter in `settings.py` (default is 10).
### 6. Reset view and scale
Use the *escape* key to reset the view to its default state (*scale=1.0* viewed from above)
## HUD information
* **Current date**: shows the current time and the adjustments applied
* **Scale**: shows the scale being applied
* **Position**: calculates a rough estimate of distances between the cursor position and the focused object, both in *km* and *AU*; it assumes a flat projection
* **Following**: shows the focused object
* **Information**: shows basic information of the focused object
## Future improvements
* Add additional bodies for representation
* Calculate and represent spaceship trajectories between two objects, solving for fast travel or less fuel usage
* Represent real spaceships' mission trajectories (e.g. Voyager probes)
## Trivia
* Even though Pluto is no longer considered a planet (thanks to @plutokiller), it's represented for nostalgia's sake
* The orbits of Pluto and Neptune do not cross (check it out for yourself)
* Orbits are represented as approximations, as the positions change slightly with each revolution
