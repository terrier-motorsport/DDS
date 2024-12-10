# Data Logging for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)


from time import strftime,localtime       # Used for creating file names
from time import time as currentTime      # Used for creating timestamps
from csv import writer as csvWriter
from csv import reader as csvReader
from enum import Enum
import os
import logging

class DataLogger:
    '''
    This class manages writing system logs & telemetry data.
    '''

    baseFilePath = './Backend/logs/'
    directoryPath: str        # Path of the parent directory
    telemetryPath: str        # Path of the telemetry data 
    systemLogPath: str        # Path of the system logs

    LOG_FORMAT = '%(asctime)s [%(name)s]: %(levelname)s - %(message)s'

    
    class LogSeverity(Enum):
        '''Severity of logs (= to the logging module everity codes)'''
        CRITICAL = 50   # Represents a critical failure that prevents the program from continuing; logged just before an exception is raised.
        ERROR = 40      # Signals a failure where some functionality is not working as expected.
        WARNING = 30    # Indicates an abnormal condition that might require attention but does not interrupt functionality.
        INFO = 20       # General system message for logging routine operations (basically print() which is logged). [DEFAULT]
        DEBUG = 10      # Debug Message


    def __init__(self, fileName):
        '''Initialize the Data Logger.'''

        # Validate the file name
        self.__validateFileName(fileName)

        # Create the directory file path (date & time + name)
        currentTime = self.__getFormattedTime()
        self.directoryPath = os.path.join(self.baseFilePath, f"{currentTime}-{fileName}")

        # Ensure the base directory exists, create it if not.
        if not os.path.exists(self.directoryPath):
            os.makedirs(self.directoryPath)
            self.writeLog(DataLogger.__name__, f"Directory created at {self.directoryPath}")
        else:
            self.writeLog(DataLogger.__name__, f"Directory already exists at {self.directoryPath}, continuing.")

        # Create the paths for the files
        self.telemetryPath = os.path.join(self.directoryPath, "Telemetry.csv")
        self.systemLogPath = os.path.join(self.directoryPath, "System.log")

        # Create the files
        self.__createCSVFile(self.telemetryPath)
        self.__createLogFile(self.systemLogPath)

        # Log creation of file
        self.writeLog("DataLogger", "Log & Telemetry file setup complete!")
        

    def writeTelemetry(self, device_name: str, param_name: str, value, units: str):
        '''Writes to the telemetry data with the specified parameters'''

        # Generate a timestamp for the entry
        time = currentTime()

        # Open the file in append ('a') mode
        with open(self.telemetryPath, "a", newline='') as file:

            # Create the CSV writer
            writer = csvWriter(file)

            # Write the data
            writer.writerow([time, device_name, param_name, value, units])


    def getTelemetry(self) -> list[list]:
        '''Returns a list of lines, which contain data in the following format:
        "Time", "Device", "Parameter", "Value", "Units"'''

        # Open the file
        with open(self.telemetryPath, "r") as file:

            # Create the CSV reader
            reader = csvReader(file)

            # Read the data
            data = list(reader)

        return data
    

    def writeLog(self, logger_name: str, msg: str, severity: LogSeverity = LogSeverity.INFO):
        '''Writes to the system log with the specified parameters'''

        # Write the log
        logger = logging.getLogger(logger_name)
        logger.log(severity.value, msg)
        
        # Print to the console aswell
        log_data = {
            "asctime": self.__getFormattedTime(),
            "name": logger_name,
            "levelname": severity.name,
            "message": msg
        }
        formatted_message = self.LOG_FORMAT % log_data
        print(formatted_message)


    def __createLogFile(self, path):
        logging.basicConfig(
            filename=path,
            level=logging.INFO,
            format=self.LOG_FORMAT)
        

    def __getFormattedTime(self):
        return strftime("%Y-%m-%d-%H:%M:%S", localtime())


    def __createCSVFile(self, path):
        '''Create the telemetry file'''

        with open(path, "w") as file:
            # Create the CSV writer
            writer = csvWriter(file)

            # Write the header row
            writer.writerow(["Time", "Device", "Parameter", "Value", "Units"])

            # The 'with as' block automatically closes the file when it is done

    
    def __validateFileName(self, fileName):
        '''Validates the file name passed in. If the file name is not valid, a ValueError is raised'''

        # Check if the file name is empty or contains only whitespace
        if not fileName or not fileName.strip():
            raise ValueError("File name cannot be empty or whitespace.")

        # Check if the file name contains only valid characters
        invalid_chars = '/\\:*?"<>|'
        for char in fileName:
            if not (char.isalnum() or char in ['_', '-']):
                raise ValueError(f"Invalid file name. Only alphanumeric characters, underscores, and hyphens are allowed. Invalid character: '{char}'")
            if char in invalid_chars:
                raise ValueError(f"Invalid file name. Contains prohibited characters: {invalid_chars}")





# Example Usage of DataLogger
DEBUG_ENABLED = False

if DEBUG_ENABLED:

    # Initialize the DataLogger with a valid file name
    data_logger = DataLogger("example_log")

    # Write some sample data to the log file
    data_logger.writeTelemetry(device_name="EngineSensor", param_name="RPM", value=3500, units="RPM")
    data_logger.writeTelemetry(device_name="BatteryMonitor", param_name="Voltage", value=12.7, units="v")
    data_logger.writeTelemetry(device_name="TemperatureSensor", param_name="Temp", value=95.3, units="°C")

    # Write a log message
    data_logger.writeLog(
        logger_name="SystemLogger",
        msg="System startup complete.",
    )
    data_logger.writeLog(
        logger_name="EngineSensor",
        msg="RPM exceeds safe limit!",
        severity=DataLogger.LogSeverity.WARNING
    )

    # Read and print the data from the telemetry file
    print("Logged Data:")
    print(data_logger.getTelemetry())
