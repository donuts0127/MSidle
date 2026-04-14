# to build executable file
python -m PyInstaller --onefile --noconsole --add-data "assets;assets" gui.py

####
# will need to change images in assets
# to you own screenshot crops of your emulator 
# so they are the same size
####
# make sure file names are the same
####


pip freeze > requirements.txt