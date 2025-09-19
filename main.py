#!/home/venkat/pyenv/notes/bin/python
from kivy.app import App
from kivy.lang import Builder
from kivy.factory import Factory
from kivy.uix.popup import Popup
from kivy.core.window import Window

from rag_ui import RagAppUI
from notes import MeetingForm
#from newtab import NewTabUI

from kivy.core.window import Window
Window.size = (800, 600)  # Width x Height in pixels

        
class RagApp(App):
    def build(self):
        #Builder.load_file("rag.kv")
        Window.bind(on_resize=self.on_resize)
        self.on_resize(Window, Window.width, Window.height)
        return Factory.RootTabs()
    def on_resize(self, window, width, height):
        """
        This function is called automatically whenever the window is resized.
        """
        new_size = f"Window resized to: {width}x{height}"
        print(new_size)
        
if __name__ == "__main__":
    RagApp().run()

