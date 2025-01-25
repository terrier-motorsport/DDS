# Value Monitor for Terrier Motorsport's DDS
    # Code & Design by Jackson Justus (jackjust@bu.edu)

from Backend.DDS_IO import DDS_IO
from typing import Callable, List, Optional, Union
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.clock import Clock


# Constants for default text and layout configurations
DEFAULT_DEVICE_TEXT = "Select Device"
DEFAULT_OPTION_TEXT = "Select Option"
NO_DEVICES_TEXT = "NO DEVICES AVAIL"
NO_PARAMETERS_TEXT = "NO PARAMS AVAIL"
NO_DATA_TEXT = "NO DATA AVAIL"
BUTTON_HEIGHT = 150
GRID_SPACING = 20
GRID_PADDING = 20


class DynamicDropdown(DropDown):
    """Custom dropdown to dynamically update items and bind behavior to a button."""

    def __init__(self, dropdown_button: Button, get_dropdown_items_callback: Callable[[], List[str]], **kwargs):
        super().__init__(**kwargs)
        self.dropdown_button = dropdown_button
        self.get_dropdown_items = get_dropdown_items_callback
        self.bind_to_dropdown_button(self.update_and_display_dropdown_items) # Update items before opening
        self.bind_to_dropdown_button(self.open)                              # Open dropdown

        # Bind the 'on_select' event of the dropdown to update the button's text
        self.bind(
            on_select=lambda instance, selected_value: self.select_dropdown_item(selected_value)
        )


    def bind_to_dropdown_button(self, callable_to_bind: Callable):
        """
        Bind an event to when the button for the dropdown is released

        Parameters:
            callable_to_bind (Callable): The function to call when the event happens.
        """

        self.dropdown_button.bind(on_release=callable_to_bind)
    
    
    def bind_to_dropdown_selection(self, callable_to_bind: Callable):
        """
        Bind an event to when an option in the dropdown is released

        Parameters:
            callable_to_bind (Callable): The function to call when the event happens.
        """
        # self.bind(on_select=lambda instance, selection: setattr(mainbutton, 'text', selection))

        self.bind(on_select=callable_to_bind)


    def select_dropdown_item(self, selected_value: str):
        """
        Is called when an item in the dropdown menu is selected.
        Updates the text of the associated button when a dropdown item is selected.
        
        Args:
            selected_value (str): The text of the selected dropdown item.
        """
        # Set the button's text to the selected value
        self.dropdown_button.text = selected_value


    def update_and_display_dropdown_items(self, instance):
        """
        This function clears any existing dropdown options,
        and refreshes the list of options by calling self.get_dropdown_items.
        It then displays the options with a list of buttons.
        """

        # Clear all existing dropdown options
        self.clear_widgets()

        # Get the updated list of available dropdown items
        items = self.get_dropdown_items()

        # For each avaliable selection item,
        for item in items:
            # Create the selection button.
            btn = Button(text=item, size_hint_y=None, height=44)

            # Bind the built-in "select" function of the parent DropDown to each button in the dropdown.
            btn.bind(on_release=lambda btn: self.select(btn.text))

            # Bind any user-specified functions to the selection of an option.
            # for callable in self.on_dropdown_selection_made:
            #     btn.bind(on_release=callable)

            # Add the selection option to the dropdown.
            self.add_widget(btn)


    def get_selected_option(self) -> Optional[str]:
        """
        Retrieve the currently selected option.

        Returns:
            Optional[str]: The text of the selected option, or None if no selection is made.
        """
        return self.dropdown_button.text if self.dropdown_button.text != DEFAULT_OPTION_TEXT else None


    def reset(self):
        """Reset the dropdown to the default state."""
        self.dropdown_button.text = DEFAULT_OPTION_TEXT


class DiagnosticScreen(FloatLayout):
    """UI layout for the diagnostic screen."""

    def __init__(self, io: DDS_IO, navigate_to_racing: Callable, **kwargs):
        super().__init__(**kwargs)
        self.io = io
        self.navigate_to_racing = navigate_to_racing

        self.grid_layout = self.create_grid_layout()
        self.device_dropdown_button = self.create_device_dropdown_button()
        self.option_dropdown_button = self.create_option_dropdown_button()
        self.add_racing_button()
        self.add_value_label()

        self.add_widget(self.grid_layout)


    def create_grid_layout(self) -> GridLayout:
        """Create the base grid layout for the screen."""
        return GridLayout(
            cols=3,
            spacing=GRID_SPACING,
            padding=GRID_PADDING,
            size_hint=(None, None),
            size=(Window.width, Window.height),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )


    def create_device_dropdown_button(self) -> Button:
        """
        Create and configure the device dropdown.
        Add the button to `self.grid_layout`
        """
        if not self.io.get_device_names():
            # Show label if no devices are available
            no_devices_label = Label(
                text=NO_DEVICES_TEXT,
                font_size="20sp",
                size_hint=(1, None),
                height=BUTTON_HEIGHT,
                color=(0.8, 0, 0, 1),
                bold=True,
            )
            self.grid_layout.add_widget(no_devices_label)
            return None

        # If there is available devices...
        # Create a button and attach a dropdown
        device_dropdown_button = Button(
            text=DEFAULT_DEVICE_TEXT,
            size_hint=(1, None),
            height=BUTTON_HEIGHT,
        )
        self.device_dropdown = DynamicDropdown(device_dropdown_button, self.io.get_device_names)
        self.grid_layout.add_widget(device_dropdown_button)
        return device_dropdown_button


    def create_option_dropdown_button(self) -> Button:
        """
        Create and configure the option dropdown button for selecting parameters of a specific device.

        This function dynamically updates the dropdown options based on the selected device
        from the device dropdown. If no device is selected, the dropdown will remain empty.

        Returns:
            Button: The button that displays the dropdown for parameter selection.
        """
        # Create a button for the dropdown with default text
        option_dropdown_button = Button(
            text=DEFAULT_OPTION_TEXT,  # Default placeholder text for the dropdown
            size_hint=(1, None),      # Make the button horizontally stretchable and fixed height
            height=BUTTON_HEIGHT,     # Set the height of the button
        )

        # Create the dynamic dropdown for the button, updating based on the selected device's parameters
        self.option_dropdown = DynamicDropdown(
            option_dropdown_button,
            # Pass a lambda that fetches parameters based on the selected device
            lambda: self.get_device_parameters(self.get_selected_device())
        )

        # Update the value label when a new option is selected
        
        # self.option_dropdown.bind_to_dropdown_selection(
        #     lambda: self.set_value_label_text(self.io.get_device_data(self.get_selected_device(), self.get_selected_parameter, "DiagnosticScreen"))
        #     )

        # Add the button to the grid layout so it appears in the UI
        self.grid_layout.add_widget(option_dropdown_button)

        # Return the configured button to the caller
        return option_dropdown_button


    def add_racing_button(self):
        """Add a button to navigate to the racing screen."""
        racing_button = Button(
            text="Racing",
            size_hint=(1, None),
            height=BUTTON_HEIGHT,
        )
        racing_button.bind(on_release=self.navigate_to_racing)
        self.grid_layout.add_widget(racing_button)


    def add_value_label(self):
        """Add a label to display diagnostic values."""
        self.value_label = Label(text=NO_DATA_TEXT, size_hint=(1, None), height=BUTTON_HEIGHT)
        self.grid_layout.add_widget(self.value_label)

        # Update value on parameter selection
        def update_value(instance, selected_value):
            print(f'UPDATING VALUE: {instance}, {selected_value} || {self.get_selected_parameter()}')
            selected_device = self.get_selected_device()
            selected_parameter = selected_value
            parameter_value = self.io.get_device_data(selected_device, selected_parameter, "DiagnosticsScreen") or "No data"
            self.value_label.text = str(parameter_value)

        self.option_dropdown.bind_to_dropdown_selection(update_value)


    def add_value_label(self):
        """Add a label to display diagnostic values."""
        self.value_label = Label(text=NO_DATA_TEXT, size_hint=(1, None), height=BUTTON_HEIGHT)
        self.grid_layout.add_widget(self.value_label)

        # Function to update the value label
        def update_value_label(dt=None):
            selected_device = self.get_selected_device()
            selected_parameter = self.get_selected_parameter()
            if selected_device and selected_parameter:
                parameter_value = (
                    self.io.get_device_data(selected_device, selected_parameter, "DiagnosticsScreen")
                    or "No data"
                )
                self.value_label.text = str(parameter_value)
            else:
                self.value_label.text = NO_DATA_TEXT

        # Bind the option dropdown to update the value immediately upon selection
        def on_parameter_selected(instance, selected_value):
            print(f'UPDATING VALUE: {instance}, {selected_value}')
            update_value_label()

        self.option_dropdown.bind_to_dropdown_selection(on_parameter_selected)

        # Schedule continuous updates to the value label
        Clock.schedule_interval(update_value_label, 0.01)  # Update every second

    def set_value_label_text(self, text: str):
        print(f'SETTING VALUE TEXT: {text}')
        self.value_label = text


    def get_selected_device(self) -> Optional[str]:
        '''
        Gets the selected device from the device dropdown.

        Returns:
            (str): The selected device.
            (None): If no devices are selected.
        '''
        # Get the selected device's name if it exists and is not the default text
        return (
            self.device_dropdown_button.text
            if self.device_dropdown_button and self.device_dropdown_button.text != DEFAULT_DEVICE_TEXT
            else None
        )
    

    def get_selected_parameter(self) -> Optional[str]:
        """
        Retrieve the currently selected parameter from the option dropdown.

        This function checks the text of the option dropdown button to determine
        the selected parameter. If no parameter is selected or the text is the default,
        it returns None.

        Returns:
            Optional[str]: The text of the selected parameter, or None if no selection is made.
        """
        # Check if the option dropdown button exists and if it has a valid selection
        return (
            self.option_dropdown_button.text
            if self.option_dropdown_button and self.option_dropdown_button.text != DEFAULT_OPTION_TEXT
            else None
        )
            

    def get_device_parameters(self, device: str) -> List[str]:
        """
        Retrieve a list of parameters for the given device.

        If the given device is the, it returns an empty list. Otherwise, it fetches
        the parameters for the selected device using the I/O interface.

        Returns:
            List[str]: A list of parameters associated with the selected device,
                    or an empty list if no device is selected.
        """


        # Return the parameters for the selected device if it exists, else the no parameters text
        return self.io.get_device_parameters(device) if device else [NO_PARAMETERS_TEXT]