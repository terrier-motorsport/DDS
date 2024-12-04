from resources.input import CANDevice
import time



motorspd = CANDevice('DTI HV 500 (MC)', can_interface='can0', database_path='splash/candatabase/CANDatabaseDTI500.dbc')

mode = input("tx or rx1 or rx2?")

if (mode == 'tx'):
    while True:
        motorspd.old_send_can() 
        time.sleep(0.001)
elif mode == 'rx1':
    while True:
        print(motorspd.__fetch_can_data().get("ERPM"))

elif mode == 'rx2':
    motorspd.get_data_raw()

# print(motorspd.get_protocol())

motorspd.close_connection()