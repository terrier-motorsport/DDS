# Device Abstract Base Class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from abc import ABC, abstractmethod

class Device(ABC):
    '''
    This class provides standard methods which each Device
    object that the DDS uses should override.
    '''


    @abstractmethod
    def initialize(self):
        # Initialize
        pass

    @abstractmethod
    def testMethod(self):
        pass

# class testThing(Device):
#     pass

# if __name__ == "__main__":
#     thing = testThing()
#     # thing.testMethod()
