from jplephem.spk import SPK

kernel = SPK.open('de440s.bsp')
print(kernel)
kernel.close()