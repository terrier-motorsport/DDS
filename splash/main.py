# DDS Display for Terrier Motorsport's SPLASH 2024 Table
    # Code by Mike Waetzman (mwae@bu.edu), Anna LaPrade (alaprade@bu.edu)
    # UI/UX Design by Anna LaPrade (alaprade@bu.edu)

# Notes for Members:
    # Check you're using Python 3.2 (minimum) and that you've got pip
    # Have you installed Kivy and OpenCV?

# BUTM Code: PS-CRY-002a1
import cv2

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
from kivy.uix.popup import Popup

# Mike's version as of 08/17/24, we'll probably stay around 2.3
kivy.require('2.3.0')

# ================================================================================================

#* DDS Screen: https://a.co/d/dNE2Vug
_screen_res = (1024, 600) #desired fix size
Window.size = _screen_res
Config.set('graphics', 'resizable', False)

# ================================================================================================

class DDSApp(App):

    def build(self):
        self.window = GridLayout()
        self.window.cols = 1
        tm_cherry = "splash\\img\\SPLASH_screen.png"

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
    
    #* Callback for Button Widget -- like onClick()
    def callback(self, event):
        print("Button Pushed")

        # Get size of QR code img, display as pop-up
            # Kivy Popup: https://kivy.org/doc/stable/api-kivy.uix.popup.html
        _QRcode = "splash\\img\\fake_qr.jpg"
        _popup_title_text = "Scan to join the mailing list!"
        im = cv2.imread(_QRcode)
        h, w, _ = im.shape

        qr_img = Image(source=_QRcode)

        popup = Popup(title=_popup_title_text,
                      size_hint=(None, None),
                      size=(h,w),
                      content=qr_img
                      )
        popup.open()


#* Check if screen re-sized, if so reset
def reSize(*args):
   # Dirty solution from Peter A. (https://stackoverflow.com/questions/37164410/fixed-window-size-for-kivy-programs)
   Window.size = _screen_res
   return True    

Window.bind(on_resize = reSize)

# ================================================================================================

#* Run App
if __name__ == '__main__':
    DDSApp().run()