# Draft DDS Display for Terrier Motorsport
    # Anna LaPrade (alaprade@bu.edu)
    # UI/UX Design by Anna LaPrade (alaprade@bu.edu)     

# Notes for Members:
    # Check you're using Python 3.2 (minimum) and that you've got pip
    # Have you installed requirements.txt? (run pip install -r requirements.txt)
    # Do NOT run further that Python 3.12, kivy does not have 3.13 support yet as of 11/16

# This configures kivy logs (interferes with Backend logs without this)
import os
os.environ["KIVY_NO_CONSOLELOG"] = "0"
os.environ["KIVY_LOG_MODE"] = "PYTHON"

# Run in fullscreen
from kivy.core.window import Window


from typing import List
import kivy
import random
import logging
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import RoundedRectangle
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.loader import Loader


from UI.diagnostic_screen import DiagnosticScreen
from Backend.DDS_IO import DDS_IO


# Anna LaPrade's version as of 11/14/24
kivy.require('2.3.0')

# Colors used in UI
custom_red = (1, (73/255), (60/255), 1) 
error_red = (1, 0, 0, 1)
yellow = (1, 1, 0, 1)
green = (0, 1, 0, 1)
widget_white = (237 / 255, 243 / 255, 251 / 255, 1)
background_blue = (33/255, 33/255, 48/255, 1)

# Image Preloading 
preloaded_images = {
    "discharge_logo": Loader.image("UI/discharge_logo.png"),
    "temp_logo": Loader.image("UI/temp_logo.png"),
    "battery_icon": Loader.image("UI/battery_icon.png"),
    "battery_icon_25": Loader.image("UI/battery_icon_75.png"),
    "battery_icon_50": Loader.image("UI/battery_icon_50.png"),
    "battery_icon_25": Loader.image("UI/battery_icon_25.png"),
    "battery_icon_0": Loader.image("UI/battery_icon_0.png"),
}


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
    def __init__(self, value_source, **kwargs):
        super(OutlineColorChangingLabel_Battery, self).__init__(**kwargs)
        
        # Source of data
        self.value_source = value_source

        # Value from data to be displayed
        self.value = self.value_source()

        # Black outline, for legibility
        self.outline_color = [0, 0, 0, 1]

        # Outline width
        self.outline_width = 4

        # Update color as data is read
        self.update_color()

        # Schedule updates for outline and color
        Clock.schedule_once(self.delayed_update_outline)
        Clock.schedule_interval(self.update_value, 0.01)

    def delayed_update_outline(self, *args):
        self.update_outline()

    def update_outline(self):
        if not self.canvas:
            return
        self.canvas.before.clear()  # Clear the previous outline (if any)
        with self.canvas.before:
            Color(*self.outline_color)

    def update_value(self, *args):
        self.value = self.value_source()
        self.text = f"{self.value:.2f}%"
        self.update_color()

    def update_color(self):
        if 75 <= self.value <= 100:
            self.color = green  # Green
        elif 25 <= self.value < 75:
            self.color = yellow  # Yellow
        else:
            self.color = custom_red  # Red


# Enables color changing text for battery temperature 
# Takes in a source (likely a csv file) and a position on the screen
# Uses the source to display battery temperature and what color that should be
class OutlineColorChangingLabel_BatteryTemp(Label):
    def __init__(self, value_source, position=None, **kwargs):
        super(OutlineColorChangingLabel_BatteryTemp, self).__init__(**kwargs)
        
        

        # Source of data
        self.value_source = value_source

        # Value from data to be displayed 
        self.value = self.value_source()

        # Black outline, for legibility
        self.outline_color = [0, 0, 0, 1] 

        # Outline width 
        self.outline_width = 4

        # Update color as data is read 
        # self.update_color()

        # Schedule updates for outline and color
        Clock.schedule_once(self.delayed_update_outline)
        Clock.schedule_interval(self.update_value, 0.01)

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

        # Check if value is a string (indicating an error)
        if isinstance(self.value, str):
            self.text = self.value
            self.color = error_red  # Red for errors
            return

        # If value is valid, display it
        try:
            self.value = float(self.value)
            self.text = f"{self.value:.2f}°F"
            self.update_color()
        except (ValueError, TypeError):
            self.text = "N/A"
            self.color = error_red  # Red for invalid values
            return

    def update_color(self):
        if 50 <= self.value <= 120:
            self.color = green  # Green
        elif 20 <= self.value < 50 or 120 < self.value <= 180:
            self.color = yellow  # Yellow
        else:
            self.color = custom_red  # Red




# Enables color changing text for battery discharge rate
# Takes in a source (likely a csv file) and a position on the screen
# Uses the source to display battery temperature and what color that should be
class OutlineColorChangingLabel_BatteryDischarge(Label):
    def __init__(self, value_source, **kwargs):
        super(OutlineColorChangingLabel_BatteryDischarge, self).__init__(**kwargs)
        

        # source of data
        self.value_source = value_source

        # value from data to be displayed 
        self.value = self.value_source()

        # Black outline, for legibility
        self.outline_color = [0, 0, 0, 1] 

        # Outline width 
        self.outline_width = 4

        # Update color as data is read 
        # self.update_color()

        # Schedule updates for outline and color
        Clock.schedule_once(self.delayed_update_outline)
        Clock.schedule_interval(self.update_value, 0.01)

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

        # Check if value is a string (indicating an error)
        if isinstance(self.value, str):
            self.text = self.value
            self.color = error_red  # Red for errors
            return

        # If value is valid, display it
        try:
            self.value = float(self.value)
            self.text = f"{self.value:.2f} Amps"
            self.update_color()
        except (ValueError, TypeError):
            self.text = "N/A"
            self.color = error_red  # Red for invalid values
            return

    def update_color(self):
        if 7 <= self.value:
            self.color = custom_red  # Red
            
        elif 2 <= self.value < 7:
            self.color = yellow  # Yellow
        else:
            self.color = green  # Green

# Enables battery logo with changing battery levels, yippee! 
class Battery_Logo(Image):
    def __init__(self, value_source, position, **kwargs):
        super(Battery_Logo, self).__init__(**kwargs)
        # postition on screen
        self.pos = position

        # source of data
        self.value_source = value_source

        self.size_hint = (None, None)
        self.source = preloaded_images["battery_icon"].filename

        # size of image
        self.size = (200, 200) 

        # Updates value 
        Clock.schedule_interval(self.update_value, 0.01)

    def update_value(self, *args):
        self.value = self.value_source()
        self.update_image()

    # brackets for what battery level should be visible 
    def update_image(self):
        if 80 <= self.value <= 100:
            self.source = preloaded_images["battery_icon"].filename   # full
        elif 65 <= self.value < 80:
            self.source = preloaded_images["battery_icon_75"].filename  # 3/4
        elif 35 <= self.value < 65:
            self.source = preloaded_images["battery_icon_50"].filename # 1/2
        elif 15 <= self.value < 35:
            self.source = preloaded_images["battery_icon_25"].filename # 1/4
        else:
            self.source = preloaded_images["battery_icon_0"].filename  # empty 




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
        rect_height = 450
        rect_width = 285  
    
        # Rectangle color (light blue)
        rect_color = widget_white

        # How rounded corners are
        corner_radius = 20

        # Example value source function for demonstration
        def get_pack_state_of_charge() -> str:
            soc = self.io.get_device_data('canInterface', 'Pack_SOC', "BatteryWidget")
            # print(soc)
            if soc is str:
                # This will happen if there is an error.
                return soc
            elif soc is None:
                return ""
            else:
                try:
                    return float(soc) if soc is not None else -1
                except ValueError:
                    return -1
        
        # Example value source function for demonstration
        def get_cell_high_temperature():
            highTemp = self.io.get_device_data('canInterface', 'High_Temperature', "BatteryWidget")
            # print(highTemp)  # Debugging print
            if isinstance(highTemp, str):
                # If an error string is returned, use it directly
                return highTemp
            elif highTemp is None:
                return ""
            else:
                try:
                    return float(highTemp)
                except ValueError:
                    return -1

        # Example value source function for demonstration
        def get_pack_current():
            current = self.io.get_device_data('canInterface', 'Pack_Current', "BatteryWidget")
            # print(current)  # Debugging print
            if isinstance(current, str):
                # If an error string is returned, use it directly
                return current
            elif current is None:
                return ""
            else:
                try:
                    return float(current)
                except ValueError:
                    return -1

        
        # Creates a float layout within the box
        self.left_rect = FloatLayout(size_hint=(0.25, 0.6))  # 40% width, 80% height of parent
        self.left_rect.pos_hint = {"x": 0.05, "center_y": 0.5}  # 5% from left, vertically centered

        # Draw the white rectangle around the left_rect
        self.left_rect = FloatLayout(size_hint=(None, None), size=(rect_width, rect_height))
        self.left_rect.pos = (0+20, (600 - rect_height) // 2)  # Left-aligned, vertically centered (600 is the screen height)
        with self.left_rect.canvas.before:
            RoundedRectangle(size=self.left_rect.size, pos=self.left_rect.pos, radius=[corner_radius], color=rect_color)
        self.add_widget(self.left_rect)

        # Dummy values:
        def temp_source():
            return random.randint(0,100)
        def temp_source1():
            return random.randint(0,100)
        def temp_source2():
            return random.randint(0,100)
        def temp_source3():
            return random.randint(0,100)


        # Add content to the battery
        # Percentage label
        battery_label = OutlineColorChangingLabel_Battery(value_source=temp_source, text=f"{temp_source()}%", font_size='35sp', pos=(20, (rect_height/2)+10))
        
        # Percentage icon 
        battery_icon = Battery_Logo(value_source= temp_source, position =(65, (rect_height/2)+ 30))
        
        # Temperature
        battery_temp = OutlineColorChangingLabel_BatteryTemp(value_source=temp_source2, text=f"{temp_source2()} ºF", font_size='25sp', pos=(100, (rect_height/2)-200))
        
        # Discharge rate 
        battery_discharge = OutlineColorChangingLabel_BatteryDischarge(value_source=temp_source3, text=f"{temp_source2()} Units", font_size='25sp', pos=(80, (rect_height/2)-300))

        # Temperature Logo
        temp_logo = Image(source = preloaded_images["temp_logo"].filename, size=(125, 125), size_hint=(None, None), pos=(50, (rect_height/2-40)))

        # Discharge Logo
        discharge_logo = Image(source = preloaded_images["discharge_logo"].filename, size=(100, 100), size_hint=(None, None), pos=(40, (rect_height/2-120)))


        
        
        # Adds widgets to the battery rectangle 
        self.left_rect.add_widget(battery_label)  
        self.left_rect.add_widget(battery_icon)
        self.left_rect.add_widget(battery_temp)
        self.left_rect.add_widget(battery_discharge)
        self.left_rect.add_widget(temp_logo)
        self.left_rect.add_widget(discharge_logo)
        
     
        



#################################
#                               #
#        Warning Widget         #
#                               #
#################################

from Backend.value_monitor import ParameterMonitor, ParameterWarning
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window

class Warnings(FloatLayout):
    def __init__(self, io: DDS_IO, **kwargs):
        super().__init__(**kwargs)

        self.io = io

        # Rectangle dimensions
        rect_height = 450
        rect_width = 285

        # Rectangle color
        rect_color = widget_white

        # Rounded corners
        corner_radius = 20

        # Establish rectangle
        self.right_rect = Widget(size_hint=(None, None), size=(rect_width, rect_height))
        self.right_rect.pos = ((1024 - rect_width) - 20, (600 - rect_height) // 2)  # Right-aligned
        with self.right_rect.canvas.before:
            RoundedRectangle(pos=self.right_rect.pos, size=self.right_rect.size, radius=[corner_radius], color=rect_color)
        self.add_widget(self.right_rect)

        # Scrolling layout to contain warnings
        self.layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.layout.bind(minimum_height=self.layout.setter('height'))

        # Create the ScrollView
        self.scrollView = ScrollView(
            size_hint=(None, None),
            size=(self.right_rect.size[0], self.right_rect.size[1] - 20),
            pos=(self.right_rect.pos[0] + 10, self.right_rect.pos[1] + 10)
        )
        self.scrollView.add_widget(self.layout)

        # Add ScrollView to the widget
        self.add_widget(self.scrollView)

        # Update warnings initially
        self.update_warnings()

        # Schedule updates every second
        Clock.schedule_interval(self.update_warnings, 0.01)

    def update_warnings(self, *args):
        """
        Updates the list of warnings dynamically by fetching new warnings
        from the DDS_IO instance and repopulating the UI.
        """
        # Clear existing widgets
        self.layout.clear_widgets()

        # Get the latest warnings from the io object
        warnings = self.io.get_warnings()

        # Repopulate the warning labels
        for warning in warnings:
            label = Label(
                text=warning,
                font_size="20sp",
                size_hint=(1, None),  # Fixed width, dynamic height
                halign="left",  # Align text to the left
                valign="middle",  # Align text vertically to the middle
                color=(0.8, 0, 0, 1),  # Red text for warnings
                bold=True
            )
            label.text_size = (self.right_rect.size[0] - 20, None)

            # Dynamically adjust height based on content
            label.bind(
                texture_size=lambda instance, value: setattr(
                    instance, 'height', value[1] + 10  # Add padding
                )
            )
            self.layout.add_widget(label)


            

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
        self.speed = -1
        self.rpm = -1

        # Use FloatLayout for layout behavior
        self.center_block = FloatLayout(size_hint=(None, None), size=(804, 600))  # Fixed size: (Window.width - 210, Window.height)
        # Absolute positioning: center the block manually on a 600x1024 screen
        self.center_block.pos = (212, 0)  # Absolute position for center block

        self.add_widget(self.center_block)

                # Create a label to display the speed value
        self.speed_label = Label(
            text=f"{self.get_speed()}",
            font_size='100sp',
            pos=(106, 80)
        )
        self.center_block.add_widget(self.speed_label)

        self.speed_label_mph = Label(
            text="MPH",
            font_size='50sp',
            pos=(106, 0)
        )
        self.center_block.add_widget(self.speed_label_mph)
    
    
        # Create a label to display the rpm value
        self.rpm_label = Label(
            text=f"{self.get_rpm()} RPM",
            font_size='50sp',
            pos=(106, -90)
        )
        self.center_block.add_widget(self.rpm_label)
    
        # Schedule updates every second
        Clock.schedule_interval(self.update_value, 0.01)

    # Define getter functions
    def get_speed(self):
        erpm = self.io.get_device_data('canInterface', 'ERPM', "CenterWidget")
        if isinstance(erpm, str):
        # If it's a string (e.g., error message), return it directly
            return erpm
        elif erpm is None:
        # If no data is available, return a fallback value
            return -1
        else:
            try:
            # Convert to float and calculate speed
                return float(erpm) * 5
            except (ValueError, TypeError):
            # Handle invalid data gracefully
                return -1
    
    def get_rpm(self):
        erpm = self.io.get_device_data('canInterface', 'ERPM', "CenterWidget")
        if isinstance(erpm, str):
        # If it's a string (e.g., error message), return it directly
            return erpm
        elif erpm is None:
        # If no data is available, return a fallback value
            return -1
        else:
            try:
            # Convert to float and calculate RPM
                return float(erpm) * 10
            except (ValueError, TypeError):
            # Handle invalid data gracefully
                return -1

    def update_value(self, dt=None):
        self.speed = self.get_speed()
        self.rpm = self.get_rpm()

        if isinstance(self.speed, str):
            self.speed_label.text = self.speed
        else:
            self.speed_label.text = f"Speed: {self.speed:.2f} mph" if self.speed != -1 else "Speed: -- mph"

        if isinstance(self.rpm, str):
            self.rpm_label.text = self.rpm
        else:
            self.rpm_label.text = f"RPM: {self.rpm:.2f}" if self.rpm != -1 else "RPM: --"

        # print(f"Updated values - Speed: {self.speed}, RPM: {self.rpm}")





        



#################################
#                               #
#          Main Layout          #
#                               #
#################################


class MainLayout(FloatLayout):

    def __init__(self, io: DDS_IO, **kwargs):
        super().__init__(**kwargs)
        self.io = io

        self.racingScreen = FloatLayout()
        
        # Set the orientation of layout
        self.racingScreen.orientation = 'horizontal'

        # Create an instance of the Battery class and add it to the layout
        left_instance = Battery(io)
        self.racingScreen.add_widget(left_instance)

        # Create an instance of the Center class and add it to the layout
        center_instance = Center(io)
        self.racingScreen.add_widget(center_instance)

        # Create an instance of the Warnings class and add it to the layout
        right_instance = Warnings(io)
        self.racingScreen.add_widget(right_instance)

        # Create a button to enable the diagnostic screen
        diagnostic_button = Button(
            text="Diagnostics",
            size_hint=(None, None),
            size=(250, 70),
            pos_hint={'right': 1, 'top': 1},  # Top-right corner
        )
        # Bind the button to the method to enable the diagnostic screen
        diagnostic_button.bind(on_release=self.show_diagnostic_screen)
        self.racingScreen.add_widget(diagnostic_button)

        # Add racing screen to layout
        self.add_widget(self.racingScreen)


    def show_diagnostic_screen(self, instance):
        """
        This method is triggered when the diagnostic button is pressed.
        """
        self.clear_widgets()
        self.add_widget(DiagnosticScreen(io=self.io, navigate_to_racing=self.show_racing_screen))
        print("Diagnostics screen enabled")  # Placeholder action

    def show_racing_screen(self, instance):
        """
        This method is triggered when the racing button is pressed.
        """

        self.clear_widgets()
        self.add_widget(self.racingScreen)

# full app 
class MyApp(App):

    def __init__(self, io: DDS_IO, demoMode=False, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Terrier Motorsport DDS'
        self.io = io
        self.demoMode = demoMode
        
        
    def build(self):
        # Set the window size to 1024x600
        Window.fullscreen = True
        Window.size = (1024, 600)

        # Set background color 
        Window.clearcolor = background_blue  # dark blue 

        # Set update intervals
        IO_UPDATE_INTERVAL = 0.0001

        Clock.schedule_interval(self.update_io, IO_UPDATE_INTERVAL)


        self.layout = MainLayout(self.io)
        
        return self.layout
    
    def update_io(self, dt):
        # Update io
        self.io.update()

        self.track_delta_time(dt)


    def track_delta_time(self, dt):

        # Initialize attributes for tracking elapsed time and dt values
        if not hasattr(self, '_elapsed_time'):
            self._elapsed_time = 0
            self._dt_sum = 0
            self._dt_count = 0
            self.log = logging.getLogger('DDS_UI')

        # Accumulate the elapsed time
        self._elapsed_time += dt

        # Update the sum of dt values and count
        self._dt_sum += dt
        self._dt_count += 1

        # Every second, calculate and print the average dt
        if self._elapsed_time >= 1.0:
            # Calculate the average delta time
            average_dt = self._dt_sum / self._dt_count if self._dt_count > 0 else 0

            # Print the average dt for the past second
            self.log.info(f"Average delta time (dt): {average_dt:.6f} seconds")

            # Reset the counters for the next second
            self._elapsed_time = 0
            self._dt_sum = 0
            self._dt_count = 0




# Runs the app
if __name__ == "__main__":
    MyApp(io=DDS_IO(debug=False, demo_mode=True)).run()
