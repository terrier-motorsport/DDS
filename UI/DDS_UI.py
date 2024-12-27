# Draft DDS Display for Terrier Motorsport
    # Anna LaPrade (alaprade@bu.edu)
    # UI/UX Design by Anna LaPrade (alaprade@bu.edu)

# Notes for Members:
    # Check you're using Python 3.2 (minimum) and that you've got pip
    # Have you installed Kivy and OpenCV?
    # Do NOT run further that Python 3.12, kivy does not have 3.13 support yet as of 11/16

import cv2
import kivy
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import RoundedRectangle
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line
from Backend.DDS_IO import DDS_IO


# Anna LaPrade's version as of 11/14/24
kivy.require('2.3.0')


#################################
#                               #
#      Color-Changing Text      #
#                               #
#################################

# Description: A series of classes that allow the text color to change as inputs are read, 
# Coloring themselves green if input is safe/good, yellow if caution needed, red if dangerous 


# Enables color changing text for battery percentage 
# Takes in a source (likely a csv file) and a position on the screen
# Uses the source to display battery percentage and what color that percentage should be
class OutlineColorChangingLabel_Battery(Label):
    def __init__(self, value_source, position, **kwargs):
        super(OutlineColorChangingLabel_Battery, self).__init__(**kwargs)
        # postition on screen
        self.pos = position

        # source of data
        self.value_source = value_source

        # value from data to be displayed 
        self.value = self.value_source()

        # Black outline, for legibility
        self.outline_color = [0, 0, 0, 1] 

        # Outline width 
        self.outline_width = 4

        # Update color as data is red 
        self.update_color()

        # Schedule updates for outline and color
        Clock.schedule_once(self.delayed_update_outline)
        Clock.schedule_interval(self.update_value, 1)

    def delayed_update_outline(self, *args):
        self.update_outline()

    def update_outline(self):
        # Ensure the outline is only drawn on the label, not the parent
        if not self.canvas:
            return
        self.canvas.before.clear()  # Clear the previous outline (if any) from the label's canvas
        with self.canvas.before:
            Color(*self.outline_color)
            

    # Update the value as data changes 
    def update_value(self, *args):
        self.value = self.value_source()
        self.update_color()

    def update_color(self):
        if 75 <= self.value <= 100:
            self.color = (0, 1, 0, 1)  # Green
        elif 25 <= self.value < 75:
            self.color = (1, 1, 0, 1)  # Yellow
        else:
            self.color = (1, 0, 0, 1)  # Red


# Enables color changing text for battery temperature 
# Takes in a source (likely a csv file) and a position on the screen
# Uses the source to display battery temperature and what color that should be
class OutlineColorChangingLabel_BatteryTemp(Label):
    def __init__(self, value_source, position, **kwargs):
        super(OutlineColorChangingLabel_BatteryTemp, self).__init__(**kwargs)
        # postition on screen
        self.pos = position

        # source of data
        self.value_source = value_source

        # value from data to be displayed 
        self.value = self.value_source()

        # Black outline, for legibility
        self.outline_color = [0, 0, 0, 1] 

        # Outline width 
        self.outline_width = 4

        # Update color as data is red 
        self.update_color()

        # Schedule updates for outline and color
        Clock.schedule_once(self.delayed_update_outline)
        Clock.schedule_interval(self.update_value, 1)

    def delayed_update_outline(self, *args):
        self.update_outline()

    def update_outline(self):
        # Ensure the outline is only drawn on the label, not the parent
        if not self.canvas:
            return
        self.canvas.before.clear()  # Clear the previous outline (if any) from the label's canvas
        with self.canvas.before:
            Color(*self.outline_color)
            

    # Update the value as data changes 
    def update_value(self, *args):
        self.value = self.value_source()
        self.update_color()

    def update_color(self):
        if 50 <= self.value <= 120:
            self.color = (0, 1, 0, 1)  # Green
        elif 20 <= self.value < 50 or 120 < self.value <= 180:
            self.color = (1, 1, 0, 1)  # Yellow
        else:
            self.color = (1, 0, 0, 1)  # Red



# Enables color changing text for battery discharge rate
# Takes in a source (likely a csv file) and a position on the screen
# Uses the source to display battery temperature and what color that should be
class OutlineColorChangingLabel_BatteryDischarge(Label):
    def __init__(self, value_source, position, **kwargs):
        super(OutlineColorChangingLabel_BatteryDischarge, self).__init__(**kwargs)
        # postition on screen
        self.pos = position

        # source of data
        self.value_source = value_source

        # value from data to be displayed 
        self.value = self.value_source()

        # Black outline, for legibility
        self.outline_color = [0, 0, 0, 1] 

        # Outline width 
        self.outline_width = 4

        # Update color as data is red 
        self.update_color()

        # Schedule updates for outline and color
        Clock.schedule_once(self.delayed_update_outline)
        Clock.schedule_interval(self.update_value, 1)

    def delayed_update_outline(self, *args):
        self.update_outline()

    def update_outline(self):
        # Ensure the outline is only drawn on the label, not the parent
        if not self.canvas:
            return
        self.canvas.before.clear()  # Clear the previous outline (if any) from the label's canvas
        with self.canvas.before:
            Color(*self.outline_color)
            

    # Update the value as data changes 
    def update_value(self, *args):
        self.value = self.value_source()
        self.update_color()

    def update_color(self):
        if 7 <= self.value:
            self.color = (1, 0, 0, 1)  # Red
            
        elif 2 <= self.value < 7:
            self.color = (1, 1, 0, 1)  # Yellow
        else:
            self.color = (0, 1, 0, 1)  # Green




#################################
#                               #
#        Battery Widget         #
#                               #
#################################


# Displays data relevant to battery within a box, 
# including preentage, temperature, and discharge rate
class Battery (FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # rectangle dimensions
        rect_height = 700
        rect_width = 550
    
        # Rectangle color (light blue)
        rect_color = (237 / 255, 243 / 255, 251 / 255, 1)

        # How rounded corners are
        corner_radius = 20

        # Example value source function for demonstration
        def temp_source():
            return 80  # Replace with actual logic to provide a dynamic value
        
        # Example value source function for demonstration
        def temp_source2():
            return 20  # Replace with actual logic to provide a dynamic value
        
        # Example value source function for demonstration
        def temp_source3():
            return 7  # Replace with actual logic to provide a dynamic value

        
        # Creates a float layout within the box
        self.left_rect = FloatLayout(size_hint=(None, None), size=(rect_width, rect_height))
        self.left_rect.pos = (30, (Window.height - rect_height) / 2)  # 5px from left, vertically centered
        with self.left_rect.canvas.before:
            RoundedRectangle(size=self.left_rect.size, pos=self.left_rect.pos, radius=[corner_radius], color=rect_color)
        self.add_widget(self.left_rect)

        # Add content to the battery
        # Percentage label
        self.battery_label = OutlineColorChangingLabel_Battery(value_source=temp_source, text=f"{temp_source()}%", font_size='40sp', position=((30), (rect_height/2)+130))
        
        # Percentage icon (TO BE CHANGED)
        self.battery_icon = OutlineColorChangingLabel_Battery(value_source=temp_source, text="*ICON*", font_size='70sp', position=((30), (rect_height/2)-30))
        
        # Temperature
        self.battery_temp = OutlineColorChangingLabel_BatteryTemp(value_source=temp_source2, text=f"{temp_source2()} ºF", font_size='30sp', position=((130), (rect_height/2)-200))
        
        # Discharge rate 
        self.battery_discharge = OutlineColorChangingLabel_BatteryDischarge(value_source=temp_source3, text=f"{temp_source2()} Units", font_size='30sp', position=((170), (rect_height/2)-350))
        
        
        # Adds widgets to the battery rectangle 
        self.left_rect.add_widget(self.battery_label)
        self.left_rect.add_widget(self.battery_icon)
        self.left_rect.add_widget(self.battery_temp)
        self.left_rect.add_widget(self.battery_discharge)

    def update_data(self, data):
        '''Updated the data of all dynamic values on the widget.'''

        # Percentage label
        stateOfCharge = data['canInterface']['Pack_SOC']
        self.battery_label.value_source = stateOfCharge
        self.battery_label.text = f"{stateOfCharge}%"

        # Percentage icon 
        self.battery_icon.value_source = stateOfCharge

        # Temperature
        batteryTemp = data['canInterface']['High_Temperature']
        self.battery_temp.value_source = batteryTemp
        self.battery_temp.text = f'{batteryTemp}ºF'

        # Discharge rate 
        dischargeRate = data['canInterface']['Pack_Current']
        self.battery_discharge.value_source = dischargeRate
        self.battery_discharge.text = f"{dischargeRate} Amps"
        



#################################
#                               #
#        Warning Widget         #
#                               #
#################################

# Creates widget with warnings 
class Warnings (FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # rectangle dimensions
        rect_height = 700
        rect_width = 550

        # rectangle color
        rect_color = (237 / 255, 243 / 255, 251 / 255, 1)

        # how round the corners are 
        corner_radius = 20


        # Establishes light blue rectangle 
        self.right_rect = Widget(size_hint=(None, None), size=(rect_width, rect_height))
        self.right_rect.pos = (Window.width - 130, (Window.height - rect_height) / 2)  # 5px from right, vertically centered
        with self.right_rect.canvas.before:
            RoundedRectangle(pos=self.right_rect.pos, size=self.right_rect.size, radius=[corner_radius], color=rect_color)
        self.add_widget(self.right_rect)

        
        # Temporary source to mock values 
        def temp_source():
            return True


        # Lable to show what section is for 
        self.warning_label = Label(
            text="WARNINGS",
            font_size='50sp',
            pos=(1700, 800), 
            color=(33/255, 33/255, 48/255, 1) 
        )

        self.right_rect.add_widget(self.warning_label)

        # If warning flag set to true, display a warning! 
        if temp_source() == True:
            self.warning = Label(
                text="WARNING 1",
                font_size='20sp',
                pos=(1550, 700), 
                color=(1, 0, 0, 1) 
            )
            self.right_rect.add_widget(self.warning)

            

#################################
#                               #
#         Center Widget         #
#                               #
#################################

# Creates widget in center of display with speed and RPM 
class Center(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


        # Use FloatLayout for layout behavior
        self.center_block = FloatLayout(size_hint=(None, None), size=(Window.width - 210, Window.height))
        self.center_block.pos = (100, 0)
        self.add_widget(self.center_block)

        # Create a label to display the speed value
        self.speed_label = Label(
            text=f"{999}",
            font_size='140sp',
            pos_hint={'center_x': 0.675, 'center_y': 0.60}
        )
        self.center_block.add_widget(self.speed_label)


         # Create a label to display the rpm value
        self.rpm_label = Label(
            text=f"{999} RPM",
            font_size='70sp',
            pos_hint={'center_x': 0.675, 'center_y': 0.25}
        )
        self.center_block.add_widget(self.rpm_label)

    def update_data(self, data):
        '''Updated the data of all dynamic values on the widget.'''

        if isinstance(data['canInterface']['ERPM'], float):
            self.rpm_label.text = f"{data['canInterface']['ERPM']:.1f} RPM"
            self.speed_label.text = f"{data['canInterface']['ERPM'] * 10:.1f}"
        else:
            print(data['canInterface']['ERPM'])
            self.speed_label.text = str(data['canInterface']['ERPM'])






#################################
#                               #
#          Main Layout          #
#                               #
#################################


class MainLayout (FloatLayout):

    def __init__(self, data: dict, **kwargs):
        super().__init__(**kwargs)
        
        # Set the orientation of layout
        self.orientation = 'horizontal'

        # Create an instance of the Battery class and add it to the layout
        self.left_instance = Battery()
        self.add_widget(self.left_instance)

        # Create an instance of the Center class and add it to the layout
        self.center_instance = Center()
        self.add_widget(self.center_instance)

        # Create an instance of the Warnings class and add it to the layout
        self.right_instance = Warnings()
        self.add_widget(self.right_instance)


import random
# full app 
class MyApp(App):

    def __init__(self, io: DDS_IO, demoMode=False, **kwargs):
        super().__init__(**kwargs)
        self.io = io
        self.demoMode = demoMode
        
        
    def build(self):
        # Set the window size to 1024x600
        Window.size = (1024, 600)

        # Set background color 
        Window.clearcolor = (33/255, 33/255, 48/255, 1)  # dark blue 

        # Set update intervals
        IO_UPDATE_INTERVAL = 0.0001
        if not self.demoMode:
            UI_UPDATE_INTERVAL = 0.016
        else:
            UI_UPDATE_INTERVAL = 0.5

        Clock.schedule_interval(self.update_io, IO_UPDATE_INTERVAL)
        Clock.schedule_interval(self.update_ui, UI_UPDATE_INTERVAL)

        print('hey')

        self.data = {
            'canInterface': {
                'ERPM': random.random(),
                'Pack_SOC': 50,
                'High_Temperature': 92,
                'Pack_Current': 162
            }
        }

        self.layout = MainLayout(self.data)
        
        return self.layout
    
    def update_io(self, dt):
        # Update all io
        self.io.update()
        print(dt)

        # Get the device data
        for deviceKey, deviceData in self.data.items():
            for paramKey, paramValue in deviceData.items():
                self.data[deviceKey][paramKey] = self.io.get_device_data(deviceKey, paramKey)

                if self.demoMode and (self.data[deviceKey][paramKey] is None):
                    self.data[deviceKey][paramKey] = random.random()

                print(f'updated {paramKey} with {self.data[deviceKey][paramKey]}')


    def update_ui(self, dt):
        self.layout.center_instance.update_data(self.data)
        self.layout.left_instance.update_data(self.data)



# Runs the app
if __name__ == "__main__":
    MyApp().run()
