from jplephem.spk import SPK

kernel = SPK.open('de440t.bsp')
print(kernel)
kernel.close()