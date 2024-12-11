# Abstract Analog In class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)
    # NOTE: To be used by the ADS classes.

from typing import Union
from scipy.interpolate import interp1d

class ValueMapper:
    """
    Helper class to handle voltage-to-output conversions.
    """
    def __init__(self, voltage_range: tuple, output_range: tuple):
        self.min_voltage, self.max_voltage = voltage_range
        self.min_output, self.max_output = output_range
        self.voltage_range = self.max_voltage - self.min_voltage
        self.output_range = self.max_output - self.min_output

    def voltage_to_value(self, voltage: float):
        """
        Converts an input voltage to the corresponding output value.

        Parameters:
        voltage (float): The input voltage.

        Returns:
        float: The converted output value, or None if the voltage is out of range.
        """
        # if not (self.min_voltage <= voltage <= self.max_voltage):
        #     raise ValueError("Voltage ({voltage}v) out of range [{self.min_voltage}, {self.max_voltage}].")

        # Perform the conversion
        # Normalize the voltage to a 0-1 range
        normalized_voltage = (voltage - self.min_voltage) / (self.max_voltage - self.min_voltage)

        # Scale the normalized voltage to the output range
        scaled_output = normalized_voltage * (self.max_output - self.min_output)

        # Add the minimum output to get the final value
        output = scaled_output + self.min_output

        return output
    

    @staticmethod
    def voltage_to_resistance(adc_voltage: float, supply_voltage: float, fixed_resistor: float) -> float:
        """
        Converts an ADC voltage reading to resistance using a voltage divider.

        Parameters:
        adc_voltage (float): The measured voltage at the ADC pin.
        supply_voltage (float): The supply voltage of the circuit.
        fixed_resistor (float): The resistance of the fixed resistor in the voltage divider (in Ohms).

        Returns:
        float: The calculated resistance of the sensor (in Ohms).
        """
        # if adc_voltage <= 0 or adc_voltage >= supply_voltage:
        #     raise ValueError(f"ADC voltage ({adc_voltage}v) must be within the range of the supply voltage ({supply_voltage}v).")

        # Use the voltage divider formula to calculate the sensor resistance
        sensor_resistance = (adc_voltage * fixed_resistor) / (supply_voltage - adc_voltage)
        return sensor_resistance
    
    
    



class ExponentialValueMapper:
    """
    A class to map ADC voltage readings to output values (e.g., temperature or pressure)
    for sensors with resistance-based non-linear characteristics.
    """
    def __init__(self, resistance_values: list, output_values: list, supply_voltage: float, fixed_resistor: float):
        """
        Initialize the mapper with resistance-to-output data and circuit parameters.

        Parameters:
        resistance_values (list): List of sensor resistances (Ohms).
        output_values (list): List of corresponding output values (e.g., temperature in °C).
        """
        # Assign simple variables
        self.supply_voltage = supply_voltage
        self.fixed_resistor = fixed_resistor


        # Input Validation for resistance and output values
        if len(resistance_values) != len(output_values):
            raise ValueError("Resistance and output value lists must have the same length.")


        # Ensure resistance and output values are sorted
        sorted_data = sorted(zip(resistance_values, output_values))
        self.resistance_values, self.output_values = zip(*sorted_data)

        # Create the interpolation function for resistance-to-output mapping
        self.interpolator = interp1d(self.resistance_values, self.output_values, fill_value="extrapolate")

        # Calc min and max voltage
        self.min_voltage, self.max_voltage = self.__calculate_min_max_voltage()

    def voltage_to_value(self, adc_voltage: float) -> float:
        """
        Converts an ADC voltage reading to the corresponding output value.

        Parameters:
        adc_voltage (float): The measured ADC voltage.

        Returns:
        float: The interpolated output value (e.g., temperature in °C).
        """
        # Step 1: Convert ADC voltage to resistance
        sensor_resistance = ValueMapper.voltage_to_resistance(adc_voltage, self.supply_voltage, self.fixed_resistor)

        # Step 2: Convert resistance to output value using interpolation
        return float(self.interpolator(sensor_resistance))
    

    def resistance_to_value(self, resistance : float):
        '''Converts a resistance to an interpolated output'''
        return float(self.interpolator(resistance))
    

    def __calculate_min_max_voltage(self):
        """
        Calculate the minimum and maximum output voltages based on resistance values.

        Returns:
        tuple: (min_voltage, max_voltage)
        """
        # Ensure resistance values are sorted
        min_resistance = min(self.resistance_values)
        max_resistance = max(self.resistance_values)

        # Voltage divider formula
        min_voltage = self.supply_voltage * (min_resistance / (min_resistance + self.fixed_resistor))
        max_voltage = self.supply_voltage * (max_resistance / (max_resistance + self.fixed_resistor))

        return min_voltage, max_voltage



class Analog_In:

    # Properties
    name : str
    voltage : float
    units : str
    tolerance : float   # % in decimal form (Ex: 0.20 = 20%)

    # Decoding properties
    min_voltage : float
    max_voltage : float


    def __init__(self, name: str, units: str, mapper: Union[ValueMapper, ExponentialValueMapper], tolerance=0.2):
        '''Initalizer for the Analog_in object'''
        self.name = name
        self.units = units
        self.converter = mapper
        self.tolerance = tolerance

        self.min_voltage = mapper.min_voltage
        self.max_voltage = mapper.max_voltage


    def get_output(self):
        '''Gets the output of the analog in'''
        # If no params are passed, use the voltage variable
        return self.voltage_to_output(self.voltage)


    def voltage_to_output(self, voltage: float) -> float:
        """
        Converts input voltage to the corresponding output using the embedded RangeConverter.

        Parameters:
        voltage (float): The input voltage.

        Returns:
        float: The output value in the specified units.
        """
        
        return self.converter.voltage_to_value(voltage)
    

    def voltage_in_tolerange_range(self) -> bool:
        '''Returns if the current voltage is inside the tolerance range'''
        # Tolerable Condition
        voltage_tolerance = (self.converter.voltage_range * self.tolerance) / 2
        min = self.converter.min_voltage - voltage_tolerance
        max = self.converter.max_voltage + voltage_tolerance

        if min < self.voltage < max:
            return True
        else:
            return False
        
        

    



# Example usage
DEBUG_ENABLED = False

if DEBUG_ENABLED:

    # Define resistance-to-temperature data
    resistance_values = [
        45313, 26114, 15462, 9397, 5896, 3792, 2500,
        1707, 1175, 834, 596, 436, 323, 243, 187, 144, 113, 89
    ]
    temperature_values = [
        -40, -30, -20, -10, 0, 10, 20, 30, 40, 50,
        60, 70, 80, 90, 100, 110, 120, 130
    ]

    # Initialize the exponential value mapper for non-linear sensors
    botch_NTC_M12_mapper = ExponentialValueMapper(
        resistance_values=resistance_values,
        output_values=temperature_values,
        supply_voltage=5,
        fixed_resistor=10000

    )

    # Example Analog_in for temperature reading
    botch_NTC_M12 = Analog_In(
        name="Thermistor Temperature Sensor",
        units="°C",
        mapper=botch_NTC_M12_mapper
    )

    # Example ADC voltage input
    botch_NTC_M12.voltage = 2.5 # Replace with actual ADC voltage reading
    print(botch_NTC_M12.voltage_to_output(1))

    # Example usage (Linear Mapping)
    m3200_pressure_mapper = ValueMapper(
        voltage_range=[0.5, 4.5], 
        output_range=[0, 17])
    
    m3200_pressure_sensor = Analog_In(
        name="m3200 pressure sensor",
        units='Bar',
        mapper=m3200_pressure_mapper
    )

    print(m3200_pressure_sensor.voltage_to_output(1))
