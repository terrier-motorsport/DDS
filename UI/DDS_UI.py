# Draft DDS Display for Terrier Motorsport
    # Anna LaPrade (alaprade@bu.edu)
    # UI/UX Design by Anna LaPrade (alaprade@bu.edu)     

# Notes for Members:
    # Check you're using Python 3.2 (minimum) and that you've got pip
    # Have you installed requirements.txt? (run pip install -r requirements.txt)
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
from kivy.uix.button import Button

from UI.diagnostic_screen import DiagnosticScreen
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
        Clock.schedule_interval(self.update_value, 1)

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
            self.color = (0, 1, 0, 1)  # Green
        elif 25 <= self.value < 75:
            self.color = (1, 1, 0, 1)  # Yellow
        else:
            self.color = (1, 0, 0, 1)  # Red


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

        # Check if value is a string (indicating an error)
        if isinstance(self.value, str):
            self.text = self.value
            self.color = (1, 0, 0, 1)  # Red for errors
            return

        # If value is valid, display it
        try:
            self.value = float(self.value)
            self.text = f"{self.value:.2f}°F"
            self.update_color()
        except (ValueError, TypeError):
            self.text = "N/A"
            self.color = (1, 0, 0, 1)  # Red for invalid values
            return

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

        # Update color as data is red 
        # self.update_color()

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

        # Check if value is a string (indicating an error)
        if isinstance(self.value, str):
            self.text = self.value
            self.color = (1, 0, 0, 1)  # Red for errors
            return

        # If value is valid, display it
        try:
            self.value = float(self.value)
            self.text = f"{self.value:.2f} Amps"
            self.update_color()
        except (ValueError, TypeError):
            self.text = "N/A"
            self.color = (1, 0, 0, 1)  # Red for invalid values
            return

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
    
        # Rectangle color (light blue)
        rect_color = (237 / 255, 243 / 255, 251 / 255, 1)

        # How rounded corners are
        corner_radius = 20

        # Example value source function for demonstration
        def get_pack_state_of_charge() -> str:
            soc = self.io.get_device_data('canInterface', 'Pack_SOC', "BatteryWidget")
            print(soc)
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
            print(highTemp)  # Debugging print
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
            print(current)  # Debugging print
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
        def draw_white_rectangle(*args):
            self.left_rect.canvas.before.clear()  # Clear previous drawings
            with self.left_rect.canvas.before:
                Color(rect_color)  # White color (RGBA)
                RoundedRectangle(size=self.left_rect.size, pos=self.left_rect.pos)

        # Bind the drawing function to the size and position changes
        self.left_rect.bind(size=draw_white_rectangle, pos=draw_white_rectangle)

        # Initially call the draw function
        draw_white_rectangle()

        # Add the widget to the parent
        self.add_widget(self.left_rect)


       

        


        # Add content to the battery
        # Percentage label
        self.battery_label = OutlineColorChangingLabel_Battery(
            value_source=get_pack_state_of_charge,
            text=f"{get_pack_state_of_charge()}",
            font_size='40sp',
            size_hint=(0.8, 0.1),
            pos_hint={"center_x": 0.5, "top": 0.9}
        )

        # Percentage icon (TO BE CHANGED)
        self.battery_icon = OutlineColorChangingLabel_Battery(
            value_source=get_pack_state_of_charge,
            text="*ICON*",
            font_size='70sp',
            size_hint=(0.8, 0.2),
            pos_hint={"center_x": 0.5, "center_y": 0.6}
        )

        # Temperature
        self.battery_temp = OutlineColorChangingLabel_BatteryTemp(
            value_source=get_cell_high_temperature,
            text=f"{get_cell_high_temperature()}",
            font_size='30sp',
            size_hint=(0.8, 0.1),
            pos_hint={"center_x": 0.5, "center_y": 0.4}
        )

        # Discharge rate 
        self.battery_discharge = OutlineColorChangingLabel_BatteryDischarge(
            value_source=get_pack_current,
            text=f"{get_pack_current()}",
            font_size='30sp',
            size_hint=(0.8, 0.1),
            pos_hint={"center_x": 0.5, "center_y": 0.2}
        )
    
        
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
        rect_height = 700
        rect_width = 550

        # Rectangle color
        rect_color = (237 / 255, 243 / 255, 251 / 255, 1)

        # How round the corners are
        corner_radius = 20

        # Establish the rectangle using FloatLayout
        self.right_rect = FloatLayout(size_hint=(0.25, 0.6))  # 25% width, 60% height of parent
        self.right_rect.pos_hint = {"right": 0.95, "center_y": 0.5}  # 5% from right, vertically centered

        # Draw the right rectangle
        def draw_right_rectangle(*args):
            self.right_rect.canvas.before.clear()  # Clear previous drawings
            with self.right_rect.canvas.before:
                Color(rect_color)  # Desired color
                RoundedRectangle(size=self.right_rect.size, pos=self.right_rect.pos, radius=[corner_radius])

        # Bind the drawing function to the size and position changes
        self.right_rect.bind(size=draw_right_rectangle, pos=draw_right_rectangle)

        # Initially call the draw function
        draw_right_rectangle()

        # Add the widget to the parent
        self.add_widget(self.right_rect)

        # Scrolling layout constrained to the rectangle
        layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        # Make sure the height is dynamically adjusted
        layout.bind(minimum_height=layout.setter('height'))

        # Temporary source to mock values
        warnings = io.get_warnings()
        # [
        #     "Short warning",
        #     "This is a much longer warning message that will likely span multiple lines in the UI",
        #     "Another long message that needs to wrap and dynamically adjust the height of its label.",
        #     "Small",
        #     "More warnings to demonstrate dynamic height handling.",
        # ]


        # Add buttons as an example
        for warning in warnings:
            label = Label(
                text=warning,
                font_size="20sp",
                size_hint=(1, None),  # Fixed width, dynamic height
                halign="left",  # Align text to the left
                valign="middle",  # Align text vertically to the middle
                color=(0.8, 0, 0, 1),  # White text
                bold=True
            )
            # Enable text wrapping
            label.text_size = (self.right_rect.size[0] - 20, None)

            # Dynamically adjust height based on content
            label.bind(
                texture_size=lambda instance, value: setattr(
                    instance, 'height', value[1] + 10  # Add padding
                )
            )
            layout.add_widget(label)

        # Create the ScrollView and constrain it to the rectangle
        scrollView = ScrollView(
            size_hint=(None, None),  # Disable automatic size adjustments
            size=(self.right_rect.size[0] , self.right_rect.size[1] - 20),  # Match rectangle's dimensions with padding
            pos=(self.right_rect.pos[0] + 10, self.right_rect.pos[1] + 10)  # Match rectangle's position with padding
        )
        scrollView.add_widget(layout)

        # Add the ScrollView to the rectangle
        self.add_widget(scrollView)


        # # Create a ScrollView to contain the warnings
        # scroll_view = ScrollView(size_hint=(None, None), size=(rect_width - 40, rect_height - 40))
        # scroll_view.pos = (self.right_rect.pos[0] + 20, self.right_rect.pos[1] + 20)  # Add padding

        # # Create a BoxLayout inside the ScrollView for the warnings
        # layout = BoxLayout(
        #     padding=10,
        #     orientation="vertical",  # Stack labels vertically
        #     size_hint=(None, None),
        #     width=scroll_view.width,  # Match width to ScrollView
        # )

        # # Dynamically calculate height based on content
        # layout.bind(
        #     minimum_height=lambda instance, value: setattr(
        #         layout, 'height', max(value, rect_height)  # Ensure layout is at least as tall as rect_height
        #     )
        # )

        # # Add each warning as a Label to the layout
        # for warning in warnings:
        #     label = Label(
        #         text=warning,
        #         font_size="20sp",
        #         size_hint=(1, None),  # Allow fixed width and dynamic height
        #         halign="left",
        #         valign="middle",
        #         color=(1, 0, 0, 1),
        #         bold=True
        #     )
        #     # Enable text wrapping and alignment
        #     label.text_size = (layout.width - 20, None)  # Set the width for text wrapping

        #     # Bind the texture_size to dynamically adjust the height of the label
        #     label.bind(
        #         texture_size=lambda instance, value: setattr(
        #             instance, 'height', value[1] + 10  # Adjust height based on text and add padding
        #         )
        #     )

        #     # Add the widget to the layout
        #     layout.add_widget(label)

        # # Add the layout to the ScrollView
        # scroll_view.add_widget(layout)

        # # Add the ScrollView to the right rectangle
        # self.add_widget(scroll_view)
            

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
        
        def get_rpm():
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

        # Use FloatLayout for layout behavior
        self.center_block = FloatLayout(size_hint=(0.9, 1))
        self.center_block.pos_hint = {"x": 0.0977, "y": 0}
        self.add_widget(self.center_block)

        # Create a label to display the speed value
        self.speed_label = Label(
            text=f"{get_speed()} MPH",
            font_size='100sp',
            pos_hint={'center_x': 0.45, 'center_y': 0.60}
        )
        self.center_block.add_widget(self.speed_label)


         # Create a label to display the rpm value
        self.rpm_label = Label(
            text=f"{get_rpm()} RPM",
            font_size='50sp',
            pos_hint={'center_x': 0.45, 'center_y': 0.40}
        )
        self.center_block.add_widget(self.rpm_label)






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
            size=(250, 100),
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
    MyApp(io=DDS_IO(debug=False, demo_mode=True)).run()
