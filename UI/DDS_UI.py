# Draft DDS Display for Terrier Motorsport
    # Anna LaPrade (alaprade@bu.edu)
    # UI/UX Design by Anna LaPrade (alaprade@bu.edu)

# Notes for Members:
    # Check you're using Python 3.2 (minimum) and that you've got pip
    # Have you installed Kivy and OpenCV?
    # Do NOT run further that Python 3.12, kivy does not have 3.13 support yet as of 11/16

# This disables kivy logs (interferes with Backend logs)
import os
os.environ["KIVY_NO_CONSOLELOG"] = "0"
os.environ["KIVY_LOG_MODE"] = "PYTHON"


from typing import List
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
        self.text = f"{self.value:.2f}%"
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
        self.text = f"{self.value:.2f}°F"
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
        self.text = f"{self.value:.2f} Amps"
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
    def __init__(self, io: DDS_IO, **kwargs):
        super().__init__(**kwargs)

        self.io = io

        # rectangle dimensions
        rect_height = 700
        rect_width = 550
    
        # Rectangle color (light blue)
        rect_color = (237 / 255, 243 / 255, 251 / 255, 1)

        # How rounded corners are
        corner_radius = 20

        # Example value source function for demonstration
        def get_pack_state_of_charge():
            soc = self.io.get_device_data('canInterface','Pack_SOC')
            if soc is not None:
                return soc
            else:
                return -1
        
        # Example value source function for demonstration
        def get_cell_high_temperature():
            highTemp = self.io.get_device_data('canInterface','High_Temperature')  
            if highTemp is not None:
                return highTemp
            else:
                return -1
        
        # Example value source function for demonstration
        def get_pack_current():
            current = self.io.get_device_data('canInterface','Pack_Current')
            if current is not None:
                return current
            else:
                return -1

        
        # Creates a float layout within the box
        self.left_rect = FloatLayout(size_hint=(None, None), size=(rect_width, rect_height))
        self.left_rect.pos = (30, (Window.height - rect_height) / 2)  # 5px from left, vertically centered
        with self.left_rect.canvas.before:
            RoundedRectangle(size=self.left_rect.size, pos=self.left_rect.pos, radius=[corner_radius], color=rect_color)
        self.add_widget(self.left_rect)

        # Add content to the battery
        # Percentage label
        self.battery_label = OutlineColorChangingLabel_Battery(value_source=get_pack_state_of_charge, text=f"{get_pack_state_of_charge():.2f}%", font_size='40sp', position=((30), (rect_height/2)+130))
        
        # Percentage icon (TO BE CHANGED)
        self.battery_icon = OutlineColorChangingLabel_Battery(value_source=get_pack_state_of_charge, text="*ICON*", font_size='70sp', position=((30), (rect_height/2)-30))
        
        # Temperature
        self.battery_temp = OutlineColorChangingLabel_BatteryTemp(value_source=get_cell_high_temperature, text=f"{get_cell_high_temperature():.2f} ºF", font_size='30sp', position=((130), (rect_height/2)-200))
        
        # Discharge rate 
        self.battery_discharge = OutlineColorChangingLabel_BatteryDischarge(value_source=get_pack_current, text=f"{get_cell_high_temperature():.2f} Amps", font_size='30sp', position=((170), (rect_height/2)-350))
        
        
        # Adds widgets to the battery rectangle 
        self.left_rect.add_widget(self.battery_label)
        self.left_rect.add_widget(self.battery_icon)
        self.left_rect.add_widget(self.battery_temp)
        self.left_rect.add_widget(self.battery_discharge)
        



#################################
#                               #
#        Warning Widget         #
#                               #
#################################

from Backend.value_monitor import ParameterMonitor, ParameterWarning

# Creates widget with warnings 
class Warnings (FloatLayout):
    def __init__(self, io: DDS_IO, **kwargs):
        super().__init__(**kwargs)

        self.io = io

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
        def get_warnings() -> List[ParameterWarning]:
            return io.get_warnings()
            

        # If warning flag set to true, display a warning! 
        warnings = get_warnings()
        startPosY = 500
        for warning in warnings:
            self.warningLabel = Label(
                text=warning,
                font_size='20sp',
                pos=(1550, startPosY), 
                color=(1, 0, 0, 1) 
            )
            self.right_rect.add_widget(self.warningLabel)
            startPosY += 100

            

#################################
#                               #
#         Center Widget         #
#                               #
#################################

# Creates widget in center of display with speed and RPM 
class Center(FloatLayout):
    def __init__(self, io: DDS_IO, **kwargs):
        super().__init__(**kwargs)

        self.io = io

        def get_speed():
            erpm = self.io.get_device_data('canInterface','ERPM') * 50
            if erpm is not None:
                return erpm/10
            else:
                return -1
        
        def get_rpm():
            erpm = self.io.get_device_data('canInterface','ERPM') * 50
            if erpm is not None:
                return erpm/3
            else:
                return -1

        # Use FloatLayout for layout behavior
        self.center_block = FloatLayout(size_hint=(None, None), size=(Window.width - 210, Window.height))
        self.center_block.pos = (100, 0)
        self.add_widget(self.center_block)

        # Create a label to display the speed value
        self.speed_label = Label(
            text=f"{get_speed():.2f}",
            font_size='140sp',
            pos_hint={'center_x': 0.675, 'center_y': 0.60}
        )
        self.center_block.add_widget(self.speed_label)


         # Create a label to display the rpm value
        self.rpm_label = Label(
            text=f"{get_rpm():.2f} RPM",
            font_size='70sp',
            pos_hint={'center_x': 0.675, 'center_y': 0.25}
        )
        self.center_block.add_widget(self.rpm_label)






#################################
#                               #
#          Main Layout          #
#                               #
#################################


class MainLayout (FloatLayout):

    def __init__(self, io: DDS_IO, **kwargs):
        super().__init__(**kwargs)
        
        # Set the orientation of layout
        self.orientation = 'horizontal'

        # Create an instance of the Battery class and add it to the layout
        self.left_instance = Battery(io)
        self.add_widget(self.left_instance)

        # Create an instance of the Center class and add it to the layout
        self.center_instance = Center(io)
        self.add_widget(self.center_instance)

        # Create an instance of the Warnings class and add it to the layout
        self.right_instance = Warnings(io)
        self.add_widget(self.right_instance)


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

        Clock.schedule_interval(self.update_io, IO_UPDATE_INTERVAL)


        self.layout = MainLayout(self.io)
        
        return self.layout
    
    def update_io(self, dt):
        self.io.update()
        # print(dt)



# Runs the app
if __name__ == "__main__":
    MyApp().run()
