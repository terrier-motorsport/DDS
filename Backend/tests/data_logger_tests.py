# Data Logging for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)


# Testing the File class
import random
import time

from resources.data_logger import File

f = File("DDS_Logs")

for i in range(10):
    f.writeData("Speed", random.randint(0, 100), random.randint(0, 100), random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
    f.writeData("wheel temp", random.uniform(0, 1),random.uniform(0, 1),random.uniform(0, 1),random.uniform(0, 1))
    time.sleep(0.1)
