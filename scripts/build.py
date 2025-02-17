import shutil
import os

import PyInstaller.__main__

PyInstaller.__main__.run([
    'app.py',
    '--name=ATE_UTP_PLL',
    '--onefile',
    '--windowed',
    '--add-data=Volex-Logo.ico:.',
    '-y',
])

print('Copying resource ...')
shutil.copytree('PLL_Screen', 'dist/PLL_Screen', dirs_exist_ok=True)
shutil.copy('config.ini', 'dist/config.ini')

print('Packaging ...')
os.system('tar zcvf dist/ATE_UTP_PLL.tar.gz -C dist ATE_UTP_PLL PLL_Screen config.ini')
