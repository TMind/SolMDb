from setuptools import setup
import sys

#mac - virtualenv then python setup.py py2app
#linux -  pyi-makespec sfftk.py -n SFFToolKit --onefile --icon=./data/icon.ico --windowed --add-data 'data/*:./data'
#windows - pyi-makespec sfftk.py -n SFFToolKit --onefile --icon=./data/icon.ico --windowed --add-data data\*;data\
#linux and win - pyinstaller SFFToolKit.spec

if sys.platform == "win32":
    #windows
    setup(name='SolDB',
      version='0.1',
      description='Tools to pull data from Solforge Fusion Website and analyze it',
      url='na',
      author='gchristian',
      author_email='na',
      license='',
      packages=find_packages(),
      zip_safe=False,
      install_requires=[
          'graph','argparse','wxPython','requests'
      ],
      include_package_data=True)
elif sys.platform == 'darwin':
    #mac
    APP = ['./SolDB-GUI.py']
    DATA_FILES = ["./data"]
    OPTIONS = {
        'argv_emulation': False, 
        'site_packages': True,
        'iconfile': './icon.icns',
        'packages': ['wx', 'requests','graph','argparse'],
        'plist': {
            'CFBundleName': 'SolDB',
            'CFBundleShortVersionString':'0.1.0', # must be in X.X.X format
            'CFBundleVersion': '0.1.0',
            'CFBundleIdentifier':'com.extraneous.SolDB', 
            'NSHumanReadableCopyright': '@ Gorman Christian 2022',
            }   
    }
    setup(
        app=APP,
        data_files=DATA_FILES,
        options={'py2app': OPTIONS},
        setup_requires=['py2app'],
    )
else:
    #unix/linux
    setup(name='SolDB',
      version='0.1',
      description='Tools to pull data from Solforge Fusion Website and analyze it.',
      url='na',
      author='gchristian',
      author_email='na',
      license='',
      packages=find_packages(), 
      zip_safe=False,
      install_requires=[
          'graph','argparse','wxPython','requests'
      ],
      include_package_data=True)
