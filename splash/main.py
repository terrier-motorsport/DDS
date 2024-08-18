# DDS Display for Terrier Motorsport's SPLASH 2024 Table
    # Code by Mike Waetzman (mwae@bu.edu), Anna LaPrade (alaprade@bu.edu)
    # UI/UX Design by Anna LaPrade (alaprade@bu.edu)

# BUTM Code: PS-CRY-002a1

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
from kivy.clock import Clock

from kivy.uix.modalview import ModalView    # Like the Popup widget


# Mike's version as of 08/17/24, we'll probably stay around 2.3
kivy.require('2.3.0')

#* DDS Screen: https://a.co/d/dNE2Vug
_screen_res = (1024, 600) #desired fix size
Window.size = _screen_res
Config.set('graphics', 'resizable', False)



class DDSApp(App):

    def build(self):
        self.window = GridLayout()
        self.window.cols = 1
        tm_cherry = "img\SPLASH_screen.png"

        # car_img = Image(source = "img\SPLASH screen.png")
        # self.window.add_widget(car_img)

        img_button = Button(text = "",
                            size = _screen_res,
                            background_normal = tm_cherry,
                            background_down = tm_cherry
                            )
        self.window.add_widget(img_button)

        img_button.bind(on_press=self.callback)

        # car_img.bind(on_press = bonk())
        # # input stuff
        # self.val = TextInput(multiline=False)
        # self.window.add_widget(self.val)

        return self.window
    
    #* Callback for Button Widget -- part of the main DDSApp() class
        #! Test code in here, parse later :)
    def callback(self, event):
        print("Button Pushed")

        view = ModalView()
        view.add_widget(Image(source="img\\fake_qr.jpg"))
        view.open()
        
        


#* Check if screen re-sized, if so reset
    # Dirty solution from Peter A. (https://stackoverflow.com/questions/37164410/fixed-window-size-for-kivy-programs)
def reSize(*args):
   Window.size = _screen_res
   return True    
Window.bind(on_resize = reSize)


#* Run App
if __name__ == '__main__':
    DDSApp().run()