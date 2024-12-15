# Data Logging for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)


from time import strftime,localtime       # Used for creating file names
from time import time as currentTime      # Used for creating timestamps
from csv import writer as csvWriter
from csv import reader as csvReader
from enum import Enum
import os
import logging
import time
from typing import Dict, List

class DataLogger:
    '''
    This class manages writing system logs & telemetry data.
    '''

    baseDirectoryPath = './Backend/logs/'
    directoryPath: str        # Path of the parent directory
    telemetryPath: str        # Path of the telemetry data 
    systemLogPath: str        # Path of the system logs

    LOG_FORMAT = '%(asctime)s [%(name)s]: %(levelname)s - %(message)s'
    LOG_TIMEOUT = 10          # Time before duplicate messages are logged again (seconds)

    
    class LogSeverity(Enum):
        '''Severity of logs (= to the logging module everity codes)'''
        CRITICAL = 50   # Represents a critical failure that prevents the program from continuing; logged just before an exception is raised.
        ERROR = 40      # Signals a failure where some functionality is not working as expected.
        WARNING = 30    # Indicates an abnormal condition that might require attention but does not interrupt functionality.
        INFO = 20       # General system message for logging routine operations (basically print() which is logged). [DEFAULT]
        DEBUG = 10      # Debug Message


    class Message:
        '''Helper class to encapuslate message equatablilty'''
        def __init__(self, logger_name: str, message: str, severity, timestamp: float):
            self.logger_name = logger_name
            self.message = message
            self.severity = severity
            self.timestamp = timestamp
        
        def is_equal(self, other) -> bool:
            '''Checks if this message matches another message in all attributes.'''
            return (
                self.logger_name == other.logger_name and
                self.message == other.message and
                self.severity == other.severity
            )
        
        def is_recent(self, current_time: float) -> bool:
            '''Checks if the message was logged within the threshold.'''
            return current_time - self.timestamp < self.LOG_TIMEOUT




    def __init__(self, fileName):
        '''Initialize the Data Logger.'''

        # Validate the file name
        self.__validateFileName(fileName)

        # Create the directory file path (date & time + name)
        currentTime = self.__getFormattedTime()
        self.directoryPath = os.path.join(self.baseDirectoryPath, f"{currentTime}-{fileName}")

        # Ensure the base directory exists, create it if not.
        if not os.path.exists(self.directoryPath):
            os.makedirs(self.directoryPath)
            self.writeLog(__class__.__name__, f"Directory created at {self.directoryPath}")
        else:
            self.writeLog(__class__.__name__, f"Directory already exists at {self.directoryPath}, continuing.")

        # Create the paths for the files
        self.telemetryPath = os.path.join(self.directoryPath, "Telemetry.csv")
        self.systemLogPath = os.path.join(self.directoryPath, "System.log")

        # Create the files
        self.__createCSVFile(self.telemetryPath)
        self.__createLogFile(self.systemLogPath)

        # Create the dictionary of recent log files:
        self._last_logged_messages: List[self.Message] = []

        # Log creation of file
        self.writeLog(__class__.__name__, "Log & Telemetry file setup complete!")
        

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
        '''Writes to the system log, avoiding duplicate messages logged within the threshold.'''
        current_time = time.time()  # Get the current time in seconds

        # Check if the message should be logged
        if not self._shouldLogMessage(logger_name, msg, severity, current_time):
            return

        # Write the log
        logger = logging.getLogger(logger_name)
        logger.log(severity.value, msg)

        # Print to the console
        formatted_message = self._formatLogData(logger_name, severity, msg)
        print(formatted_message)

        # Update the list of last logged messages
        self._updateLastLoggedMessages(logger_name, msg, severity, current_time)


    def _shouldLogMessage(self, logger_name: str, msg: str, severity, current_time: float) -> bool:
        '''Determines whether the message should be logged.'''
        # Iterate over stored messages to check for duplicates
        for last_message in self._last_logged_messages:
            if last_message.is_equal(self.Message(logger_name, msg, severity, current_time)):
                # Skip logging if the message is recent
                if last_message.is_recent(current_time):
                    return False
        return True
    
    def _updateLastLoggedMessages(self, logger_name: str, msg: str, severity, timestamp: float):
        '''Adds or replaces an old message in the list of logged messages.'''
        # Remove outdated messages (older than 10 seconds)
        self._last_logged_messages = [
            message for message in self._last_logged_messages
            if message.is_recent(timestamp)
        ]
        # Add the new message to the list
        self._last_logged_messages.append(self.Message(logger_name, msg, severity, timestamp))
    

    def __formatLogData(self, logger_name: str,  msg: str, severity: LogSeverity) -> str:
        '''Formats the log data for printing to the console.'''
        log_data = {
            "asctime": self.__getFormattedTime(),
            "name": logger_name,
            "levelname": severity.name,
            "message": msg
        }
        return self.LOG_FORMAT % log_data

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
DEBUG_ENABLED = True

if DEBUG_ENABLED:

    # Initialize the DataLogger with a valid file name
    data_logger = DataLogger("example_log")

    # Simulate writing telemetry data
    data_logger.writeTelemetry(device_name="EngineSensor", param_name="RPM", value=3500, units="RPM")
    data_logger.writeTelemetry(device_name="BatteryMonitor", param_name="Voltage", value=12.7, units="V")
    data_logger.writeTelemetry(device_name="TemperatureSensor", param_name="Temp", value=95.3, units="°C")

    # Simulate writing system log messages
    data_logger.writeLog(
        logger_name="SystemLogger",
        msg="System initialization complete.",
        severity=DataLogger.LogSeverity.INFO
    )
    data_logger.writeLog(
        logger_name="EngineSensor",
        msg="RPM exceeds safe limit!",
        severity=DataLogger.LogSeverity.WARNING
    )
    data_logger.writeLog(
        logger_name="SystemLogger",
        msg="System initialization complete.",  # Duplicate message, should not log again within 10 seconds.
        severity=DataLogger.LogSeverity.INFO
    )

    # Simulate retrieving telemetry data
    print("\nTelemetry Data Logged:")
    for row in data_logger.getTelemetry():
        print(row)

    # Log an error message after a delay (to avoid duplicate filtering)
    time.sleep(11)
    data_logger.writeLog(
        logger_name="BatteryMonitor",
        msg="Battery voltage dropped below threshold!",
        severity=DataLogger.LogSeverity.ERROR
    )
