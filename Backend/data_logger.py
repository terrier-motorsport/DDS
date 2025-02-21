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
    - **Data Logger**
    - Logs all data from the DDS_IO (Telemetry), as well as keeps track of major changes in I/O status (Logs).
        - Telemetry
            - Every time a device has new data, it is written to the `Telemetry.csv` file.
            - This page details how to decode & interpret the log files:
                - [DDS Telemetry Interpretation](https://www.notion.so/DDS-Telemetry-Interpretation-bffed1cd9a70488e8eb383ce73dcf0a9?pvs=21)
        - Logs
            - This is treated more as a high level overview. When the status of the I/O changes, logs will be written to the `System.log` file.
                - There is also a debug.log file, which contains everything in System.log plus debug level logs
    '''

    childDirectoryPath: str        # Path of the parent directory
    telemetryPath: str        # Path of the telemetry data 
    systemLogPath: str        # Path of the system logs
    FALLBACK_DIR_PATH = './Backend/logs/'

    LOG_FORMAT = '%(asctime)s [%(name)s]: %(levelname)s - %(message)s'
    TIMEOUT_THRESH = 1

    
    class LogSeverity(Enum):
        '''Severity of logs (= to the logging module everity codes)'''
        CRITICAL = 50   # Represents a critical failure that prevents the program from continuing; logged just before an exception is raised.
        ERROR = 40      # Signals a failure where some functionality is not working as expected.
        WARNING = 30    # Indicates an abnormal condition that might require attention but does not interrupt functionality.
        INFO = 20       # General system message for logging routine operations (basically print() which is logged). [DEFAULT]
        DEBUG = 10      # Debug Message


    def __init__(self, directoryName: str, baseDirectoryPath = './Backend/logs/'):
        """
        Initialize the Data Logger with paths, handlers, and settings.
        """

        # Initialize variables
        self.__validateFileName(directoryName)
        self.parentDirectoryPath = baseDirectoryPath

        # Make the directory & save the path
        try:
            self.childDirectoryPath = self.__make_directory(directoryName)
        except OSError as e:
            # Warn user of failure
            print(f'&&&&&&&&&&& ~~~WARNING~~~ Data logger package failed to create log directory. ~~~WARNING~~~ &&&&&&&&&&&')
            print(f'\n Writing logs to {directoryName} will be disabled.')
            print(f'Logs will be written to {self.FALLBACK_DIR_PATH}.')
            print('Waiting 3 seconds.')
            time.sleep(3)

            # Set new path to local directory
            self.parentDirectoryPath = self.FALLBACK_DIR_PATH
            self.childDirectoryPath = self.__make_directory(directoryName)

        # Paths for telemetry and system logs
        self.telemetryPath = os.path.join(self.childDirectoryPath, "Telemetry.csv")
        self.systemLogPath = os.path.join(self.childDirectoryPath, "System.log")
        self.debugLogPath = os.path.join(self.childDirectoryPath, "debug.log")

        # Create files
        self.__createCSVFile("Telemetry.csv")
        self.__configureLogger(self.systemLogPath, self.debugLogPath)

        # Log setup completion
        self.writeLog("DataLogger", "Log & Telemetry file setup complete!")


    def __getLogger(self, loggerName: str) -> logging.Logger:
        """
        Gets a logger from the logging packqage and configures the logger.

        Parameters:
            loggerName (str): The name of the logger
         
        Returns:
            Logger (logging.Logger): The logger which correlates to the name provided.
        """
        # Get the logger with the specified name
        logger = logging.getLogger(loggerName)

        # Tell it to listen to any logs above the DEBUG level.
        logger.setLevel(logging.DEBUG)

        # Return that baby
        return logger


    def writeTelemetry(self, device_name: str, param_name: str, value, units: str):
        '''Writes to the telemetry data with the specified parameters'''

        # Generate a timestamp for the entry
        time = currentTime()

        self.sendTelemetry(time, device_name, param_name, value, units)

        # Open the file in append ('a') mode
        with open(self.telemetryPath, "a", newline='') as file:

            # Create the CSV writer
            writer = csvWriter(file)

            # Write the data
            writer.writerow([time, device_name, param_name, value, units])


    def sendTelemetry(time, device_name, param_name, value, units):
        """ Sends telemetry data on network"""
        

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
    

    def writeLog(self, loggerName: str, msg: str, severity: LogSeverity = LogSeverity.INFO):
        """
        Writes a log message, avoiding duplicate messages within the timeout threshold.

        Parameters:
            loggerName (str): Name of the system creating the log message
            msg (str): The content to be logged
            severity (LogSeverity): The level of the log
        """
        # Dictionary to track the last time each message was logged
        if not hasattr(self, "_last_log_times"):
            self._last_log_times = {}

        # Create a unique key for the logger and message
        log_key = f"{loggerName}:{msg}"

        # Get the current time
        current_time = time.time()

        # Check if the message was recently logged
        if log_key in self._last_log_times:
            last_log_time = self._last_log_times[log_key]
            # Skip logging if less than 1 second has passed
            if current_time - last_log_time < self.TIMEOUT_THRESH:
                return

        # Update the last logged time for the message
        self._last_log_times[log_key] = current_time

        # Get the logger and log the message
        logger = self.__getLogger(loggerName)
        logger.log(level=severity.value, msg=f"{msg}")


    def __configureLogger(self, systemLogPath: str, debugLogPath: str):
        '''
        Sets up the logging module.

        Parameters:
            systemLogPath (str): The path of the System.log file to be created by the logger. Contains >= INFO logs.
            debugLogPath (str): The path of the debug.log file to be created by the logger. Contains >= DEBUG logs.

        FROM LOGGING DOCUMENTATION:
        Does basic configuration for the logging system by creating a StreamHandler with a default Formatter and adding it to the root logger. 
        The functions debug(), info(), warning(), error() and critical() will call basicConfig() automatically if no handlers are defined for the root logger.
        This function does nothing if the root logger already has handlers configured, unless the keyword argument force is set to True.
        NOTE: This function should be called from the main thread before other threads are started. 
        '''

        # Handlers to be added to the base logger
        systemLogFileHandler = logging.FileHandler(systemLogPath)
        systemLogFileHandler.setLevel(logging.INFO)        # Log anything to the file >= INFO

        debugLogFileHandler = logging.FileHandler(debugLogPath)
        debugLogFileHandler.setLevel(logging.DEBUG)        # Log anything to the file >= DEBUG

        streamHandler = logging.StreamHandler()            
        streamHandler.setLevel(logging.INFO)              # Log anything to the console >= DEBUG

        # Write to the logging config
        logging.basicConfig(
            level=logging.INFO,     # Logs anything with a level above INFO
            format=self.LOG_FORMAT, 
            handlers=[
                systemLogFileHandler,
                debugLogFileHandler,
                streamHandler
            ],
            force=True
            )
        

    def __getFormattedTime(self, timestamp: float = None) -> str:
        """
        Returns a formatted time string. If a timestamp is provided, it formats that time.
        Otherwise, it formats the current local time.
        """
        if timestamp is None:
            timestamp = time.time()  # Use the current time if no timestamp is given
        return strftime("%Y-%m-%d--%H-%M-%S", localtime(timestamp))


    def __createCSVFile(self, fileName: str):
        '''
        Create a csv file with a specified fileName & write the header row to it.
        Header row: `["Time", "Device", "Parameter", "Value", "Units"]`

        Parameters:
            fileName (str): The name of the file to be created.
        '''

        filePath = os.path.join(self.childDirectoryPath, fileName)

        with open(filePath, "w") as file:
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
            
    
    def __make_directory(self, directoryName: str) -> str:
        '''
        Creates a directory within the base log directory.
        Used to make the path of the directory which will contain the .log & .csv file.

        Parameters:
            directoryName (str): The name of the directory being made.
        
        Returns:
            directoryPath (str): The string of the made directory path.
        '''

        # Make the path to the directory
        current_time = self.__getFormattedTime()
        directoryPath = os.path.join(self.parentDirectoryPath, f"{current_time}-{directoryName}")

        # Make the directory (if it doesn't already exist)
        print(f'making dir {directoryPath}')
        if not os.path.exists(directoryPath):
            os.makedirs(directoryPath)

        # Return the path
        return directoryPath




# Example Usage of DataLogger
if __name__ == '__main__':

    # Initialize the DataLogger with a valid file name
    data_logger = DataLogger("example_log")


    print(data_logger.telemetryPath)
    print(data_logger.systemLogPath)

    # Simulate writing telemetry data
    data_logger.writeTelemetry(device_name="EngineSensor", param_name="RPM", value=3500, units="RPM")
    data_logger.writeTelemetry(device_name="BatteryMonitor", param_name="Voltage", value=12.7, units="V")
    data_logger.writeTelemetry(device_name="TemperatureSensor", param_name="Temp", value=95.3, units="°C")

    # Simulate writing system log messages
    data_logger.writeLog(
        loggerName="SystemLogger",
        msg="System initialization complete.",
        severity=DataLogger.LogSeverity.INFO
    )
    data_logger.writeLog(
        loggerName="EngineSensor",
        msg="RPM exceeds safe limit!",
        severity=DataLogger.LogSeverity.WARNING
    )
    data_logger.writeLog(
        loggerName="SystemLogger",
        msg="System initialization complete.",  # Duplicate message, should not log again within 10 seconds.
        severity=DataLogger.LogSeverity.INFO
    )
    data_logger.writeLog(
        loggerName="lmao",
        msg="test",  # Duplicate message, should not log again within 10 seconds.
        severity=DataLogger.LogSeverity.DEBUG
    )

    # Simulate retrieving telemetry data
    print("\nTelemetry Data Logged:")
    for row in data_logger.getTelemetry():
        print(row)

    # Log an error message after a delay (to avoid duplicate filtering)
    time.sleep(6)
    data_logger.writeLog(
        loggerName="BatteryMonitor",
        msg="Battery voltage dropped below threshold!",
        severity=DataLogger.LogSeverity.ERROR
    )
    
    time.sleep(5)
    data_logger.writeLog(
        loggerName="BatteryMonitor",
        msg="Battery voltage dropped below threshold!",
        severity=DataLogger.LogSeverity.ERROR
    )
