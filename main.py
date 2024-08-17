# DDS Display for Terrier Motorsport's SPLASH 2024 Table
    # Code by Mike Waetzman (mwae@bu.edu), Anna LaPrade (alaprade@bu.edu)
    # UI/UX Design by Anna LaPrade (alaprade@bu.edu)

# BUTM Code: PS-CRY-002

import kivy
from kivy.app import App
from kivy.core.window import Window

# Mike's version as of 08/17/24, we'll probably stay around 2.3
kivy.require('2.3.0')

# DDS Screen: https://a.co/d/dNE2Vug
Window.size = (1024, 600)

class DDSApp(App):
    def build(FloatLayout):
        pass

if __name__ == '__main__':
    DDSApp().run()