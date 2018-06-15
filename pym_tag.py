#!/usr/bin/python3

"""
    Python: Created by Naman Jain on 12-01-2018
    File: music_file_tag_editor

    GUI Tag editor for MP3 file.
    It supports Tag editing using mutagen library, renaming the file based on its ID3 attributes,
    changing album art using local file system or using Internet search or removing it completely.

    It also supports changing cover art of all MP3 files with same album and album artist as the
    opened file.

"""

# ## PyLint custom options: ## #
# pylint: disable=too-many-instance-attributes
# pylint: disable=c-extension-no-member
# pylint: disable=no-name-in-module

import os.path
import tempfile
from collections import OrderedDict
from contextlib import suppress
from glob import glob
from typing import AnyStr, Tuple, Iterable

import shutil
import win32con
# noinspection PyProtectedMember
from kivy import Config
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from mutagen import id3, File
from mutagen.easyid3 import EasyID3
# noinspection PyProtectedMember
from mutagen.id3 import APIC, ID3
from mutagen.mp3 import MP3

from win10toast import ToastNotifier

import win32api
import win32gui
from win32ui import CreateFileDialog
import winxpgui


class TagEditor(App, BoxLayout):
    """
        Class for tag editor
    """

    # class attributes
    FILE_OPENED = False  # to store state of the opened file
    # File renaming options
    rename = {"no-rename": "Don't Rename", "album-title": "{Album} - {Title}",
              "album-artist-title": "{Album} - {Artist} - {Title}",
              "artist-album-title": "{Artist} - {Album} - {Title}",
              "title-album": "{Title} - {Album}"}

    class Constants(OrderedDict):
        """
            This class is for providing constants
        """

        def __init__(self) -> None:
            super().__init__()
            self.title = 'Title'
            self.artist = 'Artist'
            self.album = 'Album'
            self.albumartist = 'Album Artists'
            self.date = 'Year'
            self.genre = 'Genre'

            self.default_tag_cover = r'extras/default_music.png'
            self.escape_button = r'extras/escape_label.png'

        def __getitem__(self, item):
            return self.__dict__[item]

        def __dir__(self) -> Iterable[str]:
            return ['1title', '2artist', '3album', '4albumartist', '5date', '6genre']

    constants = Constants()

    class FileInfoLabel(Label):
        """
            File Info Label
        """

        def __init__(self, text: str, **kwargs) -> None:
            kwargs['text'] = f'[b][i][size=15][color=000000]{text}[/color][/font][/i][/b]'
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
            self.text = f"[b][i][size=15][color=000000]{os.path.basename(value)}[/color][/font]" \
                        f"[/i][/b]"

    @staticmethod
    def _return_popup(title: AnyStr, content: Widget, size: Tuple, size_hint=(None, None)) -> Popup:
        """
            This method is for creating a unified Popup which will have a similar design
            throughout the application

        :param title: Title of the popup
        :type title: str
        :param content: content to be put in the popup
        :type content: Widget
        :param size: size of the Popup
        :type size: tuple
        :param size_hint: size hint of the Popup wrt to the parent
        :type size_hint: tuple; default=(None, None)
        :return: the generated Popup
        :rtype: Popup
        """
        popup = Popup(title=title, content=content, size=size, size_hint=size_hint,
                      title_align='center')
        return popup

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
        self.music_file_info_layout = BoxLayout(orientation='vertical', size_hint=(0.5, 1),
                                                pos_hint={'top': True, 'center_x': True})
        self.music_file_tag_layout = BoxLayout(orientation='vertical', size_hint=(0.5, 1))

        self.image_cover_art = Image(source=TagEditor.constants.default_tag_cover)
        self.label_file_name = TagEditor.FileInfoLabel('Open A File')
        self.button_album_art_change = Button(text="Options", size_hint=(0.25, 0.1),
                                              pos_hint={'center_x': 0.5},
                                              background_color=(255, 0, 0, 0.4),
                                              background_normal='')

        for widget in (self.image_cover_art, self.button_album_art_change, self.label_file_name,
                       Image(source=TagEditor.constants.escape_button, size_hint=(None, None),
                             size=(600, 200), pos_hint={'center_x': 0.725, 'bottom': True})):
            self.music_file_info_layout.add_widget(widget)

        self.text_input_dict = dict()

        for key in dir(TagEditor.constants):
            self.text_input_dict[key[1:]] = TextInput(hint_text_color=[26, 12, 232, 1],
                                                      hint_text=TagEditor.constants[key[1:]],
                                                      multiline=False,
                                                      font_size='20sp',
                                                      background_color=(0, 255, 255, 0.8))

        self.checkbox_layout = BoxLayout(orientation='horizontal')
        self.checkbox_all_albums_art = CheckBox(active=True, color=[0, 0, 0, 1])

        for widget in (TagEditor.FileInfoLabel(text="Apply this album art to all songs in the "
                                                    "album"), self.checkbox_all_albums_art):
            self.checkbox_layout.add_widget(widget)

        self.button_open = Button(text='Open', background_color=(255, 0, 0, 1),
                                  background_normal='')
        self.button_save = Button(text='Save', background_color=(255, 0, 0, 1),
                                  background_normal='')
        self.button_reset = Button(text='Reset', background_color=(255, 0, 0, 1),
                                   background_normal='')

        self.main_layout.add_widget(self.music_file_info_layout)
        self.main_layout.add_widget(self.music_file_tag_layout)

        self.naming_opt = "no-rename"

        def _naming_option_selector(_, selected_text):
            """
            binding function for the spinner, which assign the selected text to
            'self.naming_option'
            :param _:
            :type _:
            :param selected_text: the option selected by the user in the Spinner
            :type selected_text: str
            """
            self.naming_opt = selected_text

        self.naming_option_spinner = Spinner(text=TagEditor.rename[self.naming_opt],
                                             values=[TagEditor.rename[key]
                                                     for key in TagEditor.rename])

        self.naming_option_spinner.bind(text=_naming_option_selector)

        # Button's Layout
        self.layout_button = BoxLayout(orientation='horizontal')

        for widget in self.button_open, self.button_save, self.button_reset:
            self.layout_button.add_widget(widget)

        # button bindings
        for button, binding in zip((self.button_open, self.button_save, self.button_reset,
                                    self.button_album_art_change),
                                   (self.file_open, self.save_file, self.reset_widgets,
                                    self.album_art_manager)):
            button.bind(on_press=binding)

        self.file_name, self.file_path, self.file_extension = str(), list(), str()
        self.to_delete = tempfile.TemporaryDirectory()

    def build(self):
        """
            building the App
        :return:
        :rtype:
        """
        self.icon = TagEditor.constants.default_tag_cover

        # window background color
        Window.clearcolor = (255, 215, 0, 1)

        self.add_widget(self.main_layout)
        for key in self.text_input_dict:
            self.music_file_tag_layout.add_widget(widget=self.text_input_dict[key])

        for widget in [self.naming_option_spinner, self.checkbox_layout,
                       self.layout_button]:
            self.music_file_tag_layout.add_widget(widget)

        return self

    def reset_widgets(self, _):
        """
            Reset all field to original state
        """
        self.label_file_name.pretty_text = 'Open A File'
        self.title = "Musical - Music Tag Editor"

        for key in self.text_input_dict:
            self.text_input_dict[key].text = ''
        if os.path.exists(os.path.join(os.getcwd(), TagEditor.constants.default_tag_cover)):
            self.image_cover_art.source = TagEditor.constants.default_tag_cover
            self.image_cover_art.reload()
        else:
            self.image_cover_art.clear_widgets()

        TagEditor.FILE_OPENED = False

        self.to_delete.cleanup()
        self.to_delete = tempfile.TemporaryDirectory()

    def file_open(self, _: Button):
        """
            Opens a Windows file open dialog.
            It will use '.mp3' extension for file types

        :param _:
        :type _:
        :return:
        :rtype:
        """
        # True, None for fileopen and False, File_Name for filesave dialog
        self.reset_widgets(None)
        file_dialog = CreateFileDialog(True, ".mp3", None, 0, "MP3 Files (*.mp3)|*.mp3", None)
        file_dialog.DoModal()

        # String, List, String
        self.file_name, self.file_path, self.file_extension = \
            file_dialog.GetFileName(), file_dialog.GetPathNames(), file_dialog.GetFileExt()

        if any([self.file_name == '', self.file_path == [], self.file_extension == '']):
            # if file open operation is cancelled, show a notification
            win_notification = ToastNotifier()
            win_notification.show_toast(self.title, "File open operation cancelled",
                                        icon_path=TagEditor.constants.default_tag_cover,
                                        duration=5)
            return

        try:
            audio_file, mp3_file = EasyID3(self.file_path[0]), MP3(self.file_path[0])

        except id3.ID3NoHeaderError:
            # adding tags if the file has none
            file = File(self.file_path[0], easy=True)
            file.add_tags()
            file.save()
            audio_file, mp3_file = EasyID3(self.file_path[0]), MP3(self.file_path[0])

        if any(['APIC:Cover' in mp3_file, 'APIC:' in mp3_file]):
            with open(os.path.join(self.to_delete.name, 'image.jpeg'), 'wb') as img:
                if 'APIC:' in mp3_file:
                    img.write(mp3_file['APIC:'].data)
                else:
                    img.write(mp3_file['APIC:Cover'].data)

            self.image_cover_art.source = os.path.join(self.to_delete.name, 'image.jpeg')
            print(os.path.exists(os.path.join(self.to_delete.name, 'image.jpeg')),
                  file=open("log.txt", 'w+'))
            self.image_cover_art.reload()

        self.title += f" -> {self.file_name}"
        self.label_file_name.pretty_text = self.file_name

        # filling the text field with the metadata of the song
        with suppress(KeyError):
            for key in self.text_input_dict:
                if not audio_file.get(key, self.text_input_dict[key].text) == "":
                    self.text_input_dict[key].text = \
                        audio_file.get(key, self.text_input_dict[key].text)[0]

        TagEditor.FILE_OPENED = True

    def save_file(self, _: Button):
        """
        Save file and rename it according to the option selected by the user.

        :param _:
        :type _:
        :return:
        :rtype:
        :return:
        :rtype:
        """

        if not TagEditor.FILE_OPENED:
            self._return_popup(title='No file opened', content=Label(text="Please open a file..."),
                               size_hint=(None, None), size=(500, 100)).open()
            return

        file = None
        to_return = False
        try:
            file = MP3(self.file_path[0], ID3=ID3)
        except IndexError:
            self._return_popup(title="Error", content=Label(text='Please Open a file'),
                               size_hint=(None, None), size=(200, 200)).open()
            to_return = True

        if to_return:
            return
        with suppress(id3.error):
            file.delete()
            file.add_tags()

        if not self.image_cover_art.source == TagEditor.constants.default_tag_cover:
            with open(self.image_cover_art.source, 'rb') as alb_art:
                file.tags.add(APIC(encoding=1, mime='image/png', type=3, desc=u'Cover',
                                   data=alb_art.read()))

        else:
            with suppress(KeyError):
                if 'APIC:' in file:
                    file.tags.pop('APIC:')
                else:
                    file.tags.pop('APIC:Cover')

            self.checkbox_all_albums_art.active = False

        file.save()

        music_file = EasyID3(self.file_path[0])

        # adding tags to the file
        for tag in self.text_input_dict:
            music_file[tag] = self.text_input_dict[tag].text
        music_file.save()

        self.file_name = self.file_path[0]

        # if the option is "no-rename": "Don't Rename"
        if self.naming_opt != list(TagEditor.rename.keys())[0]:
            artist = music_file[TagEditor.constants.artist][0]
            album = music_file[TagEditor.constants.album][0]
            title = music_file[TagEditor.constants.title][0]

            self.file_name = self.naming_opt.format(Artist=artist, Album=album, Title=title)
            self.file_name = rf"{os.path.dirname(self.file_path[0])}\{self.file_name}.mp3"
            os.rename(self.file_path[0], self.file_name)
            self.file_path[0] = self.file_name

        self._return_popup(title='MP3 File Saved', content=Label(text=f'{self.file_name} Saved'),
                           size=(800, 200)).open()

        self.label_file_name.pretty_text = os.path.basename(self.file_name)

        TagEditor.FILE_OPENED = True

        if self.checkbox_all_albums_art.active:
            self.album_art_all_songs(self.text_input_dict[TagEditor.constants.album].text,
                                     self.text_input_dict[TagEditor.constants.albumartist].text)

        # resetting the widgets after saving the file
        self.reset_widgets(None)

    def album_art_manager(self, _: Button):
        """
            Function to grab the album art;
            it will offer three choice,
            Download from Internet or Pick from local filesystem or Remove the cover art
        """

        if not TagEditor.FILE_OPENED:
            self._return_popup(title='No file opened', content=Label(text="Please open a file..."),
                               size=(500, 100)).open()
            return

        button_local_picker = Button(text='Local Filesystem')
        button_google_search = Button(text='Search With Google')
        button_art_remove = Button(text='Remove Album Art')
        button_extract_art = Button(text='Extract The Album Art')

        art_button_layout = BoxLayout(orientation='vertical')

        # binding function to buttons in the popup
        for widget, func in zip((button_google_search, button_local_picker, button_art_remove,
                                 button_extract_art),
                                (self.album_art_google, self.album_art_local,
                                 self.album_art_remove, self.album_art_extract)):
            widget.bind(on_press=func)
            art_button_layout.add_widget(widget)

        art_picker = self._return_popup(title='Select Album Art', content=art_button_layout,
                                        size=(200, 200))

        art_picker.open()

    def album_art_local(self, _: Button, downloaded=False):
        """
        Allows to selected the album art from the local file system.
        Opens the file dialog for selecting jpeg or png or jpg file

        It will open user's default Downloads folder in case the file is downloaded from the
        internet

        :param _:
        :type _:
        :param downloaded:
        :type downloaded:
        """
        # True for fileopen and False for filesave dialog
        file_types = "JPEG File (*.jpeg), jpg File (*.jpg) | *.jpg; *.jpeg; | PNG File (*.png) | " \
                     "*.png ||"

        if not downloaded:
            file_dialog = CreateFileDialog(True, None, None, 0, file_types, None)
        else:
            # noinspection SpellCheckingInspection
            file_dialog = CreateFileDialog(True, os.path.join(os.getenv('USERPROFILE',
                                                                        'Downloads')), None,
                                           0, file_types, None)

        file_dialog.DoModal()

        # assigning the mp3 cover art widget's source to selected image path
        if not file_dialog.GetPathNames()[0] == "":
            self.image_cover_art.source = file_dialog.GetPathNames()[0]
            self.image_cover_art.reload()

    def album_art_google(self, _: Button):
        """
        this method will open the browser (default Google Chrome) and search for the album art...

        :param _:
        :type _:
        """
        if self.text_input_dict["album"].text == "":
            self._return_popup(title='Empty Fields',
                               content=Label(text="Please fill Album and Artist field to perform "
                                                  "an auto search of album art"),
                               size=(500, 100)).open()
            return

        # Google advance search query; tbm=isch -> image search; image size = 500*500
        search_url = "https://www.google.co.in/search?tbm=isch&tbs=isz:ex,iszw:500,iszh:500&" \
                     f"as_q={self.text_input_dict['albumartist'].text}+" \
                     f" {self.text_input_dict['album'].text} album art"

        # open the default web browser to let the user download the image manually
        import webbrowser
        webbrowser.open(search_url)

        self.album_art_local(_, downloaded=True)

    def album_art_remove(self, _: Button):
        """

        :param _:
        :type _:
        """
        file = MP3(self.file_path[0], ID3=ID3)
        self.image_cover_art.source = TagEditor.Constants().default_tag_cover

        try:
            file.pop('APIC:Cover')

        except KeyError:
            with suppress(KeyError):
                file.pop('APIC:')

        finally:
            self.image_cover_art.reload()

    def album_art_extract(self, _: Button):
        """
            Extracting Album art and saving to disc
        :param _:
        :type _:
        """
        file_dialog = CreateFileDialog(False, None, "album_art.png", 0, "*.png| PNG File", None)
        file_dialog.DoModal()

        file_path = file_dialog.GetPathNames()

        shutil.copy(self.image_cover_art.source, file_path[0])

    def album_art_all_songs(self, album: AnyStr, album_artist: AnyStr):
        """
            Apply album art to all songs of the same album and artist
        """
        for file_name in glob(f"{os.path.dirname(self.file_path[0])}/*.mp3"):
            music_file = EasyID3(file_name)

            if music_file[TagEditor.constants.album][0] == album and \
                    music_file[TagEditor.constants.albumartist][0] == album_artist:
                music_file.save()
                mp3_file = MP3(file_name)
                with open(self.image_cover_art.source, 'rb') as alb_art:
                    mp3_file.tags.add(APIC(encoding=1, mime='image/png', type=3, desc=u'Cover',
                                           data=alb_art.read()))
                    mp3_file.save()

    def on_start(self):
        """
            this will be called when the app will start
            and it will do perform necessary modification
        """
        # Window Custom Configuration
        # making window non-resizable and borderless
        Config.set('graphics', 'resizable', False)
        Config.set('graphics', 'borderless', True)

        # window style values
        gwl_style_dlgframe = 0x00400000
        gwl_style_sysmenu = 0x00080000
        gwl_style_thickframe = 0x00040000

        gwl_style_minimizebox = 0x00020000
        gwl_style_maximizebox = 0x00010000

        gwl_style_caption = gwl_style_dlgframe

        # Retrieves a handle to the top - level window whose class name and window name match the
        # specified strings.
        window_handler = win32gui.FindWindow(None, self.title)

        style = win32gui.GetWindowLong(window_handler, win32con.GWL_STYLE)
        style = style & (gwl_style_caption | gwl_style_thickframe |
                         gwl_style_minimizebox | gwl_style_maximizebox | gwl_style_sysmenu)
        win32gui.SetWindowLong(window_handler, win32con.GWL_STYLE, style)

        # making window transparent
        win32gui.SetWindowLong(window_handler, win32con.GWL_EXSTYLE,
                               win32gui.GetWindowLong(window_handler, win32con.GWL_EXSTYLE) |
                               win32con.WS_EX_LAYERED)

        # Set the opacity and transparency color key of the windows
        winxpgui.SetLayeredWindowAttributes(window_handler, win32api.RGB(0, 0, 0), 220,
                                            win32con.LWA_ALPHA)

        # opening window in maximized mode
        win32gui.ShowWindow(window_handler, win32con.SW_MAXIMIZE)

    def on_stop(self):
        """
            this will be called when the app will exit
            and it will delete any temporary directory created
        """
        if self.to_delete is not None:
            self.to_delete.cleanup()
        super().on_stop()


def main():
    """
        Main Function
    """

    tag_editor = TagEditor()
    tag_editor.run()


if __name__ == '__main__':
    main()
