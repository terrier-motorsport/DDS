


from Backend.resources.analog_in import Analog_In, ValueMapper, ExponentialValueMapper
from Backend.resources.ads_1015 import ADS_1015


# ===== M3200 Constants =====
M3200_value_mapper = ValueMapper(
    voltage_range=[0.5, 4.5], 
    output_range=[0, 17])

# ===== NTC M12 Constants =====
resistance_values = [
    45313, 26114, 15462, 9397, 5896, 3792, 2500,
    1707, 1175, 834, 596, 436, 323, 243, 187, 144, 113, 89
]
temperature_values = [
    -40, -30, -20, -10, 0, 10, 20, 30, 40, 50,
    60, 70, 80, 90, 100, 110, 120, 130
]
# Refer to the voltage divider circuit for the NTC_M12s
supply_voltage = 5
fixed_resistor = 1000
NTC_M12_value_mapper = ExponentialValueMapper(
    resistance_values=resistance_values,
    output_values=temperature_values,
    supply_voltage=supply_voltage,
    fixed_resistor=fixed_resistor
)


def define_ADC1(logger) -> ADS_1015:
        '''
        ADC1 according to https://www.notion.so/butm/ADC1-ADS-1015-25fb3d884d454a82a2305ffa6699438e?pvs=4
        '''

        deviceName = 'coolingLoopSensors1'

        device = ADS_1015(deviceName, logger=logger, inputs = [
            Analog_In('hotPressure', 'bar', mapper=M3200_value_mapper, tolerance=0.1),           #ADC1(A0)
            Analog_In('hotTemperature', '°C', mapper=NTC_M12_value_mapper, tolerance=0.1),       #ADC1(A1)
            Analog_In('coldPressure', 'bar', mapper=M3200_value_mapper, tolerance=0.1),          #ADC1(A2)
            Analog_In('coldTemperature', '°C', mapper=NTC_M12_value_mapper, tolerance=0.1)       #ADC1(A3)
        ])

        return device


def define_ADC2(logger) -> ADS_1015:
        '''
        ADC2 according to https://www.notion.so/butm/ADC2-ADS-1115-29fd3d4279e84104aa3ee4d67bb5d22f?pvs=4
        '''

        deviceName = 'coolingLoopSensors2'

        device = ADS_1015(deviceName, logger=logger, inputs = [
            Analog_In('TBDPressure', 'bar', mapper=M3200_value_mapper, tolerance=0.1),           #ADC2(A0)
            Analog_In('TBDTemperature', '°C', mapper=NTC_M12_value_mapper, tolerance=0.1),       #ADC2(A1)
        ])

        return device


def define_wheel_MPU_6050(logger) -> None:
    # TODO: IMPLEMENT
    pass


def define_chassis_MPU_6050(logger) -> None:
    # TODO: IMPLEMENT
    pass


def define_top_MPU_6050(logger) -> None:
    # TODO: IMPLEMENT
    pass


def define_GPS(logger) -> None:
    # TODO: IMPLEMENT
    pass