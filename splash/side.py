# DDS Display for Terrier Motorsport's SPLASH 2024 Table
    # Code by Mike Waetzman (mwae@bu.edu), Anna LaPrade (alaprade@bu.edu)
    # UI/UX Design by Anna LaPrade (alaprade@bu.edu)

# BUTM Code: PS-CRY-002b1

import kivy
from kivy.app import App
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.config import Config              # May not be needed later
from kivy.core.window import Window


kivy.require('2.3.0')

class sideApp(App):
    def build(self):
        self.window = GridLayout()
        return self.window


if __name__ == "__main__":
    print("Side Open")
    sideApp().run()