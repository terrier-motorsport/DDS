from kivy.app import App
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.config import Config


# Set the window size 
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '600')


class CenteredImage(App):
    def build(self):
        # Use FloatLayout to position the image at the center
        layout = FloatLayout()

        # Create an Image widget
        image = Image(source='gook.jpg', size_hint=(None, None), size=(400, 400))  # Adjust size if needed

        # Center the image
        image.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

        # Add the image to the layout
        layout.add_widget(image)

        return layout
    

class CenteredImageWithCorners(App):
    def build(self):
        # Use FloatLayout to position the image at the center
        layout = FloatLayout()

        # Create an Image widget
        gook = Image(source='gook.jpg', size_hint=(None, None), size=(400, 400))  # Adjust size if needed

        # Center the image
        gook.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

        # Add the image to the layout
        layout.add_widget(gook)

        #Now the corners

        gook_Top_Left = Image(source='gook_Top_Left.png', size_hint=(None, None), size=(400, 400), pos=(0, 600-400))
        layout.add_widget(gook_Top_Left)

        gook_Top_Right = Image(source='gook_Top_Right.png', size_hint=(None, None), size=(400, 400), pos=(1024-400, 600-400))
        layout.add_widget(gook_Top_Right)

        gook_Bottom_Left = Image(source='gook_Bottom_Left.png', size_hint=(None, None), size=(400, 400), pos=(0, 0))
        layout.add_widget(gook_Bottom_Left)

        gook_Bottom_Right = Image(source='gook_Bottom_Right.png', size_hint=(None, None), size=(400, 400), pos=(1024-400, 0))
        layout.add_widget(gook_Bottom_Right)

        return layout
    

if __name__ == '__main__':
    # Running the app does not strictly require a virtual environment, but using one is recommended
    # to manage dependencies and avoid conflicts.
    CenteredImageWithCorners().run()