# Surface textures

Solara renders planets with equirectangular surface maps when they are
present in this folder. Any that are missing simply fall back to a flat
colour, so the app runs fine without them — drop the files in and they
appear on next launch.

## Where to get them

Download the **2k** textures from Solar System Scope:

  https://www.solarsystemscope.com/textures/

They are distributed under the **Creative Commons Attribution 4.0
International** licence (CC BY 4.0) — credit: *Solar System Scope
(solarsystemscope.com)*.

## Expected files

Place these in this folder, with exactly these names:

| Body    | File                          |
|---------|-------------------------------|
| Sun     | `2k_sun.jpg`                  |
| Mercury | `2k_mercury.jpg`              |
| Venus   | `2k_venus_atmosphere.jpg`     |
| Earth   | `2k_earth_daymap.jpg`         |
| Moon    | `2k_moon.jpg`                 |
| Mars    | `2k_mars.jpg`                 |
| Jupiter | `2k_jupiter.jpg`              |
| Saturn  | `2k_saturn.jpg`               |
| Saturn's rings | `2k_saturn_ring_alpha.png` (PNG, has transparency) |
| Uranus  | `2k_uranus.jpg`               |
| Neptune | `2k_neptune.jpg`              |

Pluto has no Solar System Scope texture, so it stays a coloured sphere.

The names above match Solar System Scope's own download filenames, so in
most cases you can download and drop them straight in. (For Venus the
*atmosphere* map is the visible cloud deck; swap in `2k_venus_surface.jpg`
under the same name if you'd rather see the radar surface.)
