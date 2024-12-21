# Data Logging for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)


# Testing the File class
import random
import time

from Backend.data_logger import DataLogger

f = DataLogger("DDS_Logs")

for i in range(10):
    f.writeTelemetry("Speed", random.randint(0, 100), random.randint(0, 100), random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
    f.writeTelemetry("wheel temp", random.uniform(0, 1),random.uniform(0, 1),random.uniform(0, 1),random.uniform(0, 1))
    time.sleep(0.1)
