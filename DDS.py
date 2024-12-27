# DDS file for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from Backend.DDS_IO import DDS_IO
from UI.DDS_UI import MyApp


io = DDS_IO(debug=False, demo_mode=True)

app = MyApp(io=io, demoMode=True)

app.run()