#!/usr/bin/python3

"""
    Python: Created by Naman Jain on 12-01-2018
    File: music_file_tag_editor

    GUI Tag editor for MP3 file

"""
import os
import shutil
import time
from contextlib import suppress

import mutagen
import win32gui

import win32api
import win32con
import winxpgui
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.bubble import Bubble
from kivy.uix.button import Button
from kivy.uix.effectwidget import EffectWidget
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3
from mutagen.mp3 import MP3

import win32ui


class TagEditor(App, BoxLayout):
    """
        Class for tag editor
    """

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=c-extension-no-member
    # pylint: disable=global-variable-undefined

    # class attributes
    rename = {"no-rename": "Don't Rename", "album-title": "{Album} - {Title}",
              "album-artist-title": "{Album} - {Artist} - {Title}",
              "artist-album-title": "{Artist} - {Album} - {Title}",
              "title-album": "{Title} - {Album}"}

    FILE_OPENED = False
    TO_DELETE = list()
    __DEFAULT_TAG_COVER = r'extras/default_music.png'

    @classmethod
    def default_tag_image(cls):
        """

        :return: name of default file cover
        :rtype: str
        """
        return TagEditor.__DEFAULT_TAG_COVER

    class ImageButton(ButtonBehavior, Image):
        """
            Class for giving Button characteristics to Image
        """

        def __init__(self, parent_width, **kwargs):
            if os.path.exists(TagEditor.default_tag_image()):
                kwargs['source'] = TagEditor.default_tag_image()

            # The width should be equal to parent
            kwargs['size_hint_x'] = 1
            # The width should be half of the parent
            kwargs['size_hint_y'] = 0.5
            kwargs['pos_hint'] = {'top': True}
            kwargs['width'] = parent_width

            super().__init__(**kwargs)

    class FileInfoLabel(Label):
        """
            File Info Label
        """

        def __init__(self, text: str, **kwargs):
            kwargs['text'] = f'[color=000000]{text}[/color]'
            kwargs['size_hint_x'] = 1
            kwargs['size_hint_y'] = 0.25
            kwargs['markup'] = True

            super().__init__(**kwargs)

        @property
        def pretty_text(self):
            """
                Getter for text
            """
            return self.text

        @pretty_text.setter
        def pretty_text(self, value):
            self.text = f"[color=000000]{os.path.basename(value)}[/color]"

    def __init__(self, **kwargs):
        """

        :param kwargs:
        :type kwargs:
        """
        kwargs['orientation'] = 'vertical'
        super().__init__(**kwargs)

        self.title = "Musical - Music Tag Editor"

        # layouts
        self.main_layout = BoxLayout(orientation='horizontal')
        self.music_file_info_layout = BoxLayout(orientation='vertical', pos_hint={'top': True,
                                                                                  'center_x': True})
        self.music_file_tag_layout = BoxLayout(orientation='vertical')

        parent_width = self.width
        self.image_cover_art = TagEditor.ImageButton(parent_width)
        self.label_file_name = TagEditor.FileInfoLabel('Open A File')

        for widget in [self.image_cover_art, self.label_file_name]:
            self.music_file_info_layout.add_widget(widget)

        self.text_input_dict = dict()

        text_input_keys = ['title', 'artist', 'album', 'albumartist', 'date', 'genre']
        text_input_hints = ['Title', 'Artists', 'Album', 'Album Artists', 'Year', 'Genre']

        for key, hint in zip(text_input_keys, text_input_hints):
            self.text_input_dict[key] = TextInput(hint_text=hint, multiline=False,
                                                  hint_text_color=(1, 1, 1, 1), font_size='20sp',
                                                  background_color=(0, 255, 255, 0.8))

        self.button_open = Button(text='Open', background_color=(255, 0, 0, 1),
                                  background_normal='')
        self.button_save = Button(text='Save', background_color=(255, 0, 0, 1),
                                  background_normal='')
        self.button_reset = Button(text='Reset', background_color=(255, 0, 0, 1),
                                   background_normal='')

        self.bubble_button = {
            'button_local': Button(text='Pick Image from Local File System'),
            'button_google': Button(text='Download Image from Google')
        }

        search_bubble = Bubble(orientation='horizontal')
        for widget in [self.bubble_button['button_local'], self.bubble_button['button_google']]:
            search_bubble.add_widget(widget)

        self.main_layout.add_widget(self.music_file_info_layout)
        self.main_layout.add_widget(self.music_file_tag_layout)

        def naming_option_selector(_, selected_text):
            """

            :param _:
            :type _:
            :param selected_text:
            :type selected_text:
            """
            self.naming_option = selected_text

        self.naming_option = "no-rename"
        self.naming_option_spinner = Spinner(text=TagEditor.rename["no-rename"],
                                             values=[TagEditor.rename[key]
                                                     for key in TagEditor.rename])

        self.naming_option_spinner.bind(text=naming_option_selector)

        self.layout_button = BoxLayout(orientation='horizontal')
        effect_widget_one, effect_widget_two, effect_widget_three = \
            EffectWidget(), EffectWidget(), EffectWidget()

        for effect_widget, widget in zip(
                (effect_widget_one, effect_widget_two, effect_widget_three),
                (self.button_open, self.button_save, self.button_reset)):
            effect_widget.add_widget(widget)
            self.layout_button.add_widget(effect_widget)

        # button bindings
        self.button_open.bind(on_press=self.file_open)
        self.button_reset.bind(on_press=self.reset)
        self.button_save.bind(on_press=self.save_file)
        self.image_cover_art.bind(on_press=self.album_art_manager)

        self.file_name, self.file_path, self.file_extension = str(), list(), str()

        self.to_delete = None

    def build(self):
        """
            building the App
        :return:
        :rtype:
        """
        self.icon = "extras/default_music.png"

        # window background color
        Window.clearcolor = (255, 215, 0, 1)

        self.add_widget(self.main_layout)
        for key in self.text_input_dict:
            self.music_file_tag_layout.add_widget(widget=self.text_input_dict[key])

        for widget in [self.naming_option_spinner, self.layout_button]:
            self.music_file_tag_layout.add_widget(widget)

        return self

    def reset(self, _):
        """
            Reset all field to original state
        """
        self.label_file_name.pretty_text = 'Open File'
        self.title = "Musical - Music Tag Editor"

        for key in self.text_input_dict:
            self.text_input_dict[key].text = ''
        if os.path.exists(TagEditor.__DEFAULT_TAG_COVER):
            self.image_cover_art.source = TagEditor.__DEFAULT_TAG_COVER
        else:
            self.image_cover_art.clear_widgets()
        TagEditor.FILE_OPENED = False

    def file_open(self, _: Button):
        """

        :param _:
        :type _:
        :return:
        :rtype:
        """
        # True, None for fileopen and False, File_Name for filesave dialog
        self.reset(None)
        file_dialog = win32ui.CreateFileDialog(True, ".mp3", None, 0, "MP3 Files (*.mp3)|*.mp3",
                                               None)
        file_dialog.DoModal()

        self.file_name, self.file_path, self.file_extension = \
            file_dialog.GetFileName(), file_dialog.GetPathNames(), file_dialog.GetFileExt()

        if any([self.file_name == '', self.file_path == [], self.file_extension == '']):
            return

        global AUDIO_FILE
        global MP3_FILE
        try:
            AUDIO_FILE, MP3_FILE = EasyID3(self.file_path[0]), MP3(self.file_path[0])
        except mutagen.id3.ID3NoHeaderError:
            file = File(self.file_path[0], easy=True)
            file.add_tags()
            file.save()
            AUDIO_FILE, MP3_FILE = EasyID3(self.file_path[0]), MP3(self.file_path[0])

        if any(['APIC:Cover' in MP3_FILE, 'APIC:' in MP3_FILE]):
            _temp_dir_name = rf"{os.getcwd()}\{self.file_name}{round(time.time())}"
            os.mkdir(_temp_dir_name)
            self.to_delete = True
            TagEditor.TO_DELETE.append(_temp_dir_name)

            with open(f'{_temp_dir_name}/image.jpg', 'wb') as img:
                if 'APIC:' in MP3_FILE:
                    img.write(MP3_FILE['APIC:'].data)
                else:
                    img.write(MP3_FILE['APIC:Cover'].data)

            self.image_cover_art.source = f'{_temp_dir_name}/image.jpg'

        self.title += f" -> {self.file_name}"
        self.label_file_name.pretty_text = self.file_name

        with suppress(KeyError):
            for key in self.text_input_dict:
                if not AUDIO_FILE.get(key, self.text_input_dict[key].text) == "":
                    self.text_input_dict[key].text = \
                        AUDIO_FILE.get(key, self.text_input_dict[key].text)[0]

        TagEditor.FILE_OPENED = True

    def save_file(self, _: Button) -> object:
        """

        :param _:
        :type _:
        :return:
        :rtype:
        :return:
        :rtype:
        """
        if not TagEditor.FILE_OPENED:
            Popup(title='No file opened', content=Label(text="Please open a file..."),
                  size_hint=(None, None), size=(500, 100)).open()
            return

        file = None
        to_return = False
        try:
            file = MP3(self.file_path[0], ID3=ID3)
        except IndexError:
            Popup(title="Error", content=Label(text='Please Open a file'), size_hint=(None, None),
                  size=(200, 200)).open()
            to_return = True

        if to_return:
            return
        with suppress(mutagen.id3.error):
            file.clear()
            file.add_tags()

        if not self.image_cover_art.source == TagEditor.__DEFAULT_TAG_COVER:
            with open(self.image_cover_art.source, 'rb') as alb_art:
                file.tags.add(
                    APIC(encoding=1, mime='image/png', type=3, desc=u'Cover', data=alb_art.read()))

        file.save()

        music_file = EasyID3(self.file_path[0])

        # adding tags
        for tag in self.text_input_dict:
            music_file[tag] = self.text_input_dict[tag].text
        music_file.save()

        self.file_name = self.file_path[0]

        # "no-rename"
        if self.naming_option != list(TagEditor.rename.keys())[0]:
            artist = music_file['artist'][0]
            album = music_file['album'][0]
            title = music_file['title'][0]

            self.file_name = self.naming_option.format(Artist=artist, Album=album, Title=title)
            self.file_name = f"{os.path.dirname(self.file_path[0])}\\{self.file_name}.mp3"
            os.rename(self.file_path[0], self.file_name)
            self.file_path[0] = self.file_name

        file_saved = Popup(title='File Saved', content=Label(text=f'{self.file_name} Saved'),
                           size_hint=(None, None), size=(800, 200))

        file_saved.open()
        self.label_file_name.pretty_text = os.path.basename(self.file_name)

        TagEditor.FILE_OPENED = True

        # resetting after saving the file
        self.reset(None)

    def album_art_manager(self, _: Button):
        """
            Function to grab the album art;
            it will offer three choice,
            Download from Internet or Pick from local filesystem or delete the cover art
        """

        if not TagEditor.FILE_OPENED:
            Popup(title='No file opened', content=Label(text="Please open a file..."),
                  size_hint=(None, None), size=(500, 100)).open()
            return

        button_local_picker = Button(text='Local Filesystem')
        button_google_search = Button(text='Search With Google')
        button_art_remove = Button(text='Remove Album Art')

        art_button_layout = BoxLayout(orientation='vertical')

        # binding function to buttons in the popup
        for widget, func in zip((button_google_search, button_local_picker, button_art_remove),
                                (self.album_art_google, self.album_art_local,
                                 self.album_art_remove)):
            widget.bind(on_press=func)
            art_button_layout.add_widget(widget)

        art_picker = Popup(title='Select Album Art', content=art_button_layout,
                           size_hint=(None, None), size=(200, 200))

        art_picker.open()

    def album_art_local(self, _: Button):
        """

        :param _:
        :type _:
        """
        # True for fileopen and False for filesave dialog
        file_types = "JPEG File (*.jpeg), JPG File (*.jpg) | *.jpeg; *.jpg; | PNG File (*.png) | " \
                     "*.png ||"
        file_dialog = win32ui.CreateFileDialog(True, None, None, 0, file_types, None)
        file_dialog.DoModal()

        # assigning the mp3 cover art widget's source to selected image path
        if not file_dialog.GetPathNames()[0] == "":
            self.image_cover_art.source = file_dialog.GetPathNames()[0]

    def album_art_google(self, _: Button):
        """
        this method will open Google Chrome and search for the album art...

        :param _:
        :type _:
        """
        if self.text_input_dict['album'].text == "":
            Popup(title='Empty Field', content=Label(text="Please fill Album field to perform an "
                                                          "auto search of album art"),
                  size_hint=(None, None), size=(500, 100)).open()
            return

        # Google advance search query; tbm=isch -> image search; image size = 500*500
        search_url = "https://www.google.co.in/search?tbm=isch&tbs=isz:ex,iszw:500,iszh:500&" \
                     f"as_q={self.text_input_dict['artist'].text}+" \
                     f" {self.text_input_dict['album'].text} album art"

        import webbrowser
        webbrowser.open(search_url)

    def album_art_remove(self, _: Button):
        """

        :param _:
        :type _:
        """
        file = MP3(self.file_path[0], ID3=ID3)

        try:
            file.pop('APIC:Cover')

        except KeyError:
            with suppress(KeyError):
                file.pop('APIC:')

        finally:
            self.image_cover_art.clear_widgets()

    def on_start(self):
        """
            this will be called when the app will exit
            and it will do all necessary modification
        """
        # making window transparent
        window_handler = win32gui.FindWindow(None, self.title)

        win32gui.SetWindowLong(window_handler, win32con.GWL_EXSTYLE,
                               win32gui.GetWindowLong(window_handler, win32con.GWL_EXSTYLE) |
                               win32con.WS_EX_LAYERED)
        winxpgui.SetLayeredWindowAttributes(window_handler, win32api.RGB(0, 0, 0), 200,
                                            win32con.LWA_ALPHA)

    def on_stop(self):
        """
            this will be called when the app will exit
            and it will delete any temporary directory created
        """
        super().on_stop()
        if self.to_delete is not None and os.path.exists(self.to_delete):
            for directory in TagEditor.TO_DELETE:
                shutil.rmtree(directory)


def main():
    """
        Main Function
    """
    tag_editor = TagEditor()
    tag_editor.run()


if __name__ == '__main__':
    main()
