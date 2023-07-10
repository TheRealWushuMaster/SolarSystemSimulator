# ☀🌎🪐⭐☄ Solar System Simulator
This program creates a representation of the Solar System and its main celestial bodies using JPL ephemeris data. Its objective is to provide an accurate simulation that respects distances and sizes.
## How to use
### 1. Center view
You can double click on an object or its name to refocus the simulation on the object.
### 2. Adjust scale
The scale is adjusted using the mouse wheel, with three levels of granularity:
* **Shift + mouse wheel**: adjust the scale in 0.1 increments
* **Mouse wheel**: adjust the scale in 1 increments
* **Ctrl + mouse wheel**: double of half the previous scale
### 3. Rotate view
Drag the window using the left mouse button to adjust *yaw* and *roll*, or using the right mouse button to adjust *pitch*.

Pressing the *escape* key will reset the view to its original state (scale=1.0 and view from above)
### 4. Time adjustment
You can use the left or right keys to adjust the time backwards or forwards respectively, with the following modifiers:
* **Shift**: adjust time in days
* **No modifier**: adjust time in months
* **Ctrl**: adjust time in years
The date range is roughly between the years 1900 and 2050.
## HUD information
* **Current date**: shows the current time and the adjustments applied
* **Scale**: shows the scale being applied
* **Position**: calculates a rough estimate of distances between the cursor position and the focused object, both in *km* and *AU*; it assumes a flat projection
* **Following**: shows the focused object
* **Information**: shows basic information of the focused object
## Future improvements
* Add additional bodies for representation
* Calculate and represent spaceship trajectories between two objects
* Represent real spaceships' trajectories (e.g. Voyager probes)
## Trivia
* Even though Pluto is no longer considered a planet (thanks to @plutokiller), it's represented for nostalgia's sake
* The orbits of Pluto and Neptune do not cross (check it out for yourself)
* Orbits are represented as an approximation, as the positions change slightly on each revolution
