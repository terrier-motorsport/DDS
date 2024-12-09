# Data Logging for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)


from time import strftime,localtime       # Used for creating file names
from time import time as currentTime      # Used for creating timestamps
from csv import writer as csvWriter
from csv import reader as csvReader
import re          # Used for checking if the file name is valid

class File:

    baseFilePath = './Backend/logs/'
    filePath = ''     # File path of the file


    def __init__(self, fileName):

        # Validate the file name
        self.validateFileName(fileName)

        # Name of file is based on the date & time of running it
        currentTime = strftime("%Y-%m-%d-%H:%M:%S", localtime())

        # Create the file name
        self.filePath = self.baseFilePath + currentTime + "-" + fileName + ".csv"

        # Log creation of file
        print("Log file created at " + self.filePath)
        
        # Create the file
        with open(self.filePath, "w") as file:

            # Create the CSV writer
            writer = csvWriter(file)

            # Write the header row
            writer.writerow(["Parameter", "Time", "Data..."])

            # The 'with as' block automatically closes the file when it is done
    

    def writeData(self, logger_name: str, param_name: str, parameter):

        # Ensure the data values are up to 5, otherwise fill with None if fewer than 5 are provided
        # dataValues = list(dataValues) + [None] * (5 - len(dataValues))

        # Generate a timestamp for the entry
        time = currentTime()

        # Open the file in append ('a') mode
        with open(self.filePath, "a", newline='') as file:

            # Create the CSV writer
            writer = csvWriter(file)

            # Write the data
            writer.writerow([time, logger_name, param_name, parameter])


    def readData(self):

        # Open the file
        with open(self.filePath, "r") as file:

            # Create the CSV reader
            reader = csvReader(file)

            # Read the data
            data = list(reader)

        return data



    def validateFileName(self, fileName):

        # Check if the fileName contains only valid characters
        for char in fileName:
            if not (char.isalnum() or char in ['_', '-']):
                raise ValueError("Invalid file name. Only alphanumeric characters, underscores, and hyphens are allowed.")


