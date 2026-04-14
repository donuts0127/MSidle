# install requirements
pip install -r requirements.txt
# to build executable file
python -m PyInstaller --onefile --noconsole --add-data "assets;assets" gui.py

####
# will need to change images in assets
# to you own screenshot crops of your emulator 
# so they are the same size
####
# make sure file names are the same
####

NPC chat - click on npc chat button when it shows up
party DC - start pq back if someone dced
joined Party (renamed to Auto-start PQ) - spam presses enter so it enters pq faster
invited pq - accept party invites
crash recovery - starts up game if it crashes to phone menu
auto login - presses the screen on login screen so game loads



pip freeze > requirements.txt