# Dash Display System (DDS)
This repo hosts all of the code and files related to Terrier Motorsport's DDS project. This page is maintained by the Processing Systems subteam. For information, please contact Anna LaPrade (alaprade@bu.edu).

## About the Project
The Dash Display System (DDS) is a monitoring and display solution developed by Terrier Motorsport. This system is designed to run on a Raspberry Pi and interface with various sensors and devices, providing real-time data visualization and logging for motorsport applications. The DDS integrates both hardware and software components.

## Key Features:
- **Real-Time Data Acquisition**: Utilizes CAN and I2C protocols to gather data from multiple sensors, including accelerometers and analog inputs.
- **User Interface**: Developed using Kivy, the UI provides a dynamic and interactive display for monitoring critical parameters such as battery status, temperature, and warnings.
- **Data Logging**: Implements robust data logging mechanisms to record and store sensor data for post-race analysis.
- **Modular Design**: The system is designed with modularity in mind, allowing for easy integration of additional sensors and components.

## Components:
- **Backend**: Manages all device communications and data processing. Key files include:
  - `DDS_IO.py`: Handles device management and data accessibility.
- **Frontend**: Provides the user interface for data visualization. Key files include:
  - `UI/DDS_UI.py`: Contains the main UI components and layout.


## Credits
__Project Leads:__ <br>
Anna LaPrade - Frontend (Kivy, UI Design) -- alaprade@bu.edu <br>
Jackson Justus - Backend (CAN, I2C Decoding) -- jackjust@bu.edu <br>
Michael Waetzman - THINGS WORKED ON       -- mwae@bu.edu <br>

__Club Leadership:__ <br>
Chief Electrical Engineer: Michael Waetzman (mwae@bu.edu) <br>
Software Lead: Anna LaPrade (alaprade@bu.edu) <br>
Software Deputy: Jackson Justus (jackjust@bu.edu) <br>

