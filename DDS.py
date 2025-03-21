# DDS file for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

'''
NOTE: To run individual files from this repo, you must do the following

1. Make sure you have a virtual environment with requirements.txt installed
2. Use the following command structure EX: python -m Backend.tests.datalogger_test
'''

from Backend.config.config_loader import CONFIG
from UI.DDS_UI import MyApp
from Backend.DDS_IO import DDS_IO



io = DDS_IO()

ui = MyApp(io=io, demoMode=True)



ui.run()