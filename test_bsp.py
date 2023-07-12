from jplephem.spk import SPK

kernel = SPK.open('de440t.bsp')
print(kernel)
segment = kernel[3, 399]
print(segment.describe())
position, velocity = kernel[0, 1].compute_and_differentiate(2457061.5)
print(f"Position: {position}")
print(f"Velocity: {velocity/86400.0}")
kernel.close()