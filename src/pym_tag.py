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

import os
import pathlib
import subprocess
import sys
import tempfile
import webbrowser
from contextlib import suppress, contextmanager
from functools import partial
from glob import glob
from typing import AnyStr, Tuple, Union
from urllib.parse import urlunparse, quote, urlencode

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from mutagen import id3, File
from mutagen.easyid3 import EasyID3
# noinspection PyProtectedMember
from mutagen.id3 import APIC, ID3, USLT
from mutagen.mp3 import MP3

from helper_classes import Constants, PymLabel, CustomSpinner


class TagEditor(App, BoxLayout):
    """
        Class for tag editor app
    """

    # class attributes
    FILE_OPENED = False  # to store state of the opened file

    def __init__(self, **kwargs):
        """

        :param kwargs:
        :type kwargs:
        """
        kwargs['orientation'] = 'vertical'
        super().__init__(**kwargs)

        self.constants = Constants()
        self.title = self.constants.window_title
        self.icon = os.path.join('../res', 'app_icon.ico')

        # layouts
        self.main_layout = BoxLayout(orientation='horizontal')
        self.music_file_info_layout = BoxLayout(orientation='vertical', size_hint=(0.5, 1),
                                                pos_hint={'top': True, 'center_x': True})
        self.music_file_tag_layout = BoxLayout(orientation='vertical', size_hint=(0.5, 1))

        self.image_cover_art = Image(source=self.constants.default_tag_cover)
        self.label_file_name = PymLabel('Open A File')
        self.button_album_art_change = Button(text="Options", size_hint=(0.25, 0.1),
                                              pos_hint={'center_x': 0.5},
                                              background_color=(255, 0, 0, 0.4),
                                              background_normal='')

        for widget in (self.image_cover_art, self.button_album_art_change, self.label_file_name):
            self.music_file_info_layout.add_widget(widget)

        self.text_input_dict = {key: TextInput(hint_text_color=[26, 12, 232, 1],
                                               hint_text=self.constants[key],
                                               font_name=os.path.join('../res', 'AlexBrush-Regular.ttf'),
                                               halign='center',
                                               multiline=(key != "lyrics"),
                                               write_tab=False,
                                               font_size='30sp',
                                               input_filter='int' if key in ("date", "tracknumber") else None,
                                               background_color=(0, 0, 255, 0.8))
                                for key in self.constants}

        # checkbox function which will be called when checkbox is selected
        def _on_checkbox_select(_widget: Widget, _):
            if not TagEditor.FILE_OPENED:
                self._return_popup(title="No File opened", content=Label(text="No File Opened"), ) \
                    .open()

        self.checkbox_layout = BoxLayout(orientation='horizontal')
        self.switch_layout = BoxLayout(orientation='horizontal')
        self.checkbox_all_albums_art = CheckBox(active=False, color=[0, 0, 0, 1])
        self.checkbox_all_albums_art.bind(active=_on_checkbox_select)
        self.checkbox_all_albums_art.disabled = True

        # switch for applying album art to all songs of the same album
        def _label_select(_widget: Widget, _):
            self.checkbox_all_albums_art.active = not self.checkbox_all_albums_art.active

        label_all = PymLabel(text="Apply this album art to all songs in the album", markup=True)
        label_all.bind(on_ref_press=_label_select)

        for widget in label_all, self.checkbox_all_albums_art:
            self.checkbox_layout.add_widget(widget)

        open_text = "Open\n\n[size=12][i]CTRL + O[/i][/size]"
        self.button_open = Button(text=open_text, background_color=(255, 0, 0, 1),
                                  background_normal='', markup=True, halign='center', valign='center')
        save_text = "Save\n\n[size=12][i]CTRL + S[/i][/size]"
        self.button_save = Button(text=save_text, background_color=(255, 0, 0, 1),
                                  background_normal='', markup=True, halign='center', valign='center')
        self.naming_format = "no-rename"

        def _naming_formation_selector(_, selected_text):
            """
            binding function for the spinner, which assign the selected text to
            'self.naming_format'
            :param _:
            :type _:
            :param selected_text: the option selected by the user in the Spinner
            :type selected_text: str
            """
            self.naming_format = selected_text

        self.naming_spinner = CustomSpinner(text=self.constants.rename[self.naming_format],
                                            values=self.constants.rename.values())

        self.naming_spinner.bind(text=_naming_formation_selector)

        # Button's Layout
        self.layout_button = BoxLayout(orientation='horizontal')

        for widget in self.button_open, self.button_save:
            self.layout_button.add_widget(widget)

        # button bindings
        for button, binding in zip((self.button_open, self.button_save, self.button_album_art_change),
                                   (self.file_open, self.save_file, self.album_art_manager)):
            button.bind(on_press=binding)

        self.file_name, self.file_path, self.file_extension = str(), str(), str()
        self.to_delete = tempfile.TemporaryDirectory()

    def __repr__(self) -> str:
        return "TagEditor Class"

    @staticmethod
    @contextmanager
    def saving(file: File):
        """
            calls save method on the object
        :param file: file to be saved
        :type file: File
        """
        yield file
        file.save()

    def _return_popup(self, title: AnyStr, content: Widget, size: Tuple = (500, 100),
                      size_hint=(None, None)) -> Popup:
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
        :type size_hint: tuple; default=(500, 100)
        :return: the generated Popup
        :rtype: Popup
        """
        popup = Popup(title=f"{self.constants.name} - {title}", content=content, size=size,
                      size_hint=size_hint, title_align='center')

        # popup_background = ModalView()
        # popup_background.add_widget(Image(source=self.constants.rocket_image))
        # popup.background = self.constants.rocket_image
        popup.background_color = [0, 255, 220, 0.9]
        popup.title_size = 18  # size in sp 255 0 120
        popup.title_color = [1, 255, 0, 1]  # rgba (pink)
        popup.separator_color = [1, 0, 255, 255]  # rgba (cyan)
        popup.separator_height = 5

        return popup

    def build(self):
        """
            building the App
        :return: the created window
        :rtype: TagEditor
        """
        self.icon = self.constants.default_tag_cover

        # window background color
        # noinspection SpellCheckingInspection
        Window.clearcolor = (255, 215, 0, 1)

        for key in self.text_input_dict:
            self.music_file_tag_layout.add_widget(widget=self.text_input_dict[key])

        for widget in self.naming_spinner, self.checkbox_layout, self.layout_button:
            self.music_file_tag_layout.add_widget(widget)

        for widget in self.music_file_info_layout, self.music_file_tag_layout:
            self.main_layout.add_widget(widget)

        self.add_widget(self.main_layout)

        self.init_app(None)

        return self

    def init_app(self, _: Union[Button, None]):
        """
        Set all field to original state
        :param _: Placeholder for button when used as a callback
        :return:
        """
        self.label_file_name.pretty_text = 'Open A File'
        self.title = self.constants.window_title

        for key in self.text_input_dict:
            self.text_input_dict[key].text = ''
            self.text_input_dict[key].readonly = True

        if os.path.exists(os.path.join(os.getcwd(), self.constants.default_tag_cover)):
            self.image_cover_art.source = self.constants.default_tag_cover
            self.image_cover_art.reload()

        else:
            self.image_cover_art.clear_widgets()

        TagEditor.FILE_OPENED = False
        self.checkbox_all_albums_art.disabled = True

        self.to_delete.cleanup()
        self.to_delete = tempfile.TemporaryDirectory()

        # binding keyboard handler
        Window.bind(on_keyboard=self.on_keyboard)

    def on_keyboard(self, _, __, ___, codepoint, modifier):
        """
        Handler for keyboard shortcuts
        :param _: Window
        :param __: Key
        :param ___: Scancode
        :param codepoint:
        :param modifier:
        :return:
        """
        if 'ctrl' in modifier and codepoint == 'o':
            self.file_open(None)

        elif'ctrl' in modifier and codepoint == 's':
            self.save_file(None)

    def file_open(self, _: Union[Button, None]) -> None:
        """
            Opens a Windows file open dialog.
            It will use '.mp3' extension for file types

        :param _:
        :type _:
        :return:
        :rtype:
        """
        self.init_app(None)
        self.checkbox_all_albums_art.disabled = False

        for text_input in self.text_input_dict.values():
            text_input.readonly = False

        # True, None for fileopen and False, File_Name for file save dialog
        try:
            self.file_path = subprocess.check_output([
                'zenity', '--file-selection', '--file-filter=MP3 files (MP3) | *.mp3 | *.MP3', '--title=Select an MP3'
            ]).decode(sys.stdout.encoding).strip()

        except subprocess.CalledProcessError:
            self.file_path = ""

        self.file_name = os.path.basename(self.file_path)
        self.file_extension = os.path.splitext(self.file_path)[-1]

        # if no file is selected or cancel button is pressed
        if self.file_path == "":
            # if file open operation is cancelled
            return

        try:
            audio_file = EasyID3(self.file_path)
            mp3_file = MP3(self.file_path)

        except id3.ID3NoHeaderError:
            # adding id3 header tags if the file has none
            with self.saving(File(self.file_path, easy=True)) as file:
                file.add_tags()

            audio_file = EasyID3(self.file_path)
            mp3_file = MP3(self.file_path)

        if any(['APIC:Cover' in mp3_file, 'APIC:' in mp3_file]):
            with open(os.path.join(self.to_delete.name, 'image.jpeg'), 'wb') as img:
                img.write(mp3_file['APIC:' if 'APIC:' in mp3_file else 'APIC:Cover'].data)

            self.image_cover_art.source = os.path.join(self.to_delete.name, 'image.jpeg')
            self.image_cover_art.reload()

        self.title += f" -> {self.file_path}"
        self.label_file_name.pretty_text = self.file_name

        # filling the text field with the metadata of the song
        with suppress(KeyError):
            for key in self.text_input_dict:
                if not audio_file.get(key, self.text_input_dict[key].text) == "":
                    self.text_input_dict[key].text = audio_file.get(key, self.text_input_dict[key].text)[0]

        TagEditor.FILE_OPENED = True

    def save_file(self, _: Union[Button, None]) -> None:
        """
        Save file and rename it according to the option selected by the user.

        :param _:
        :type _:
        :return:
        :rtype:
        """

        if not TagEditor.FILE_OPENED:
            self._return_popup(title='No file opened', content=Label(text="Please open a file...")).open()
            return

        file = None
        to_return = False
        save_file_content = f"Saving {self.text_input_dict['title']}"
        saving_file = self._return_popup(title="Saving File", content=Label(text=save_file_content))

        try:
            file = MP3(self.file_path, ID3=ID3)

        except IndexError:
            self._return_popup(title="Error", content=Label(text='Please Open a file....'),
                               size=(200, 200)).open()
            to_return = True

        with self.saving(file) as file:
            if to_return:
                return

            saving_file.open()
            with suppress(id3.error):
                file.delete()
                file.add_tags()

            if not self.image_cover_art.source == self.constants.default_tag_cover:
                with open(self.image_cover_art.source, 'rb') as album_art_file:
                    file.tags.add(APIC(
                        mime=f"image/{pathlib.Path(self.image_cover_art.source).suffix.strip('.')}",
                        type=3, desc=u'Cover', encoding=1, data=album_art_file.read()
                    ))

            else:
                with suppress(KeyError):
                    if 'APIC:' in file:
                        file.tags.pop('APIC:')
                    else:
                        file.tags.pop('APIC:Cover')

                self.checkbox_all_albums_art.active = False

            file[u"USLT::'eng'"] = (USLT(
                encoding=3, lang=u'eng', desc=u'Lyrics', text=self.text_input_dict['lyrics'].text.strip())
            )

        with self.saving(EasyID3(self.file_path)) as music_file:
            # adding tags to the file
            for tag in self.text_input_dict:
                if tag == 'lyrics':
                    continue

                music_file[tag] = self.text_input_dict[tag].text

            if not self.image_cover_art.source == self.constants.default_tag_cover:
                with open(self.image_cover_art.source, 'rb') as album_art_file:
                    file.tags.add(APIC(mime=f"image/{pathlib.Path(self.image_cover_art.source).suffix.strip('.')}",
                                       type=3, desc=u'Cover', encoding=1, data=album_art_file.read()))

            else:
                with suppress(KeyError):
                    if 'APIC:' in file:
                        file.tags.pop('APIC:')
                    else:
                        file.tags.pop('APIC:Cover')

                self.checkbox_all_albums_art.active = False

        self.file_name = self.file_path
        
        # if the option is not : "Don't Rename"
        if self.naming_format != "no-rename" and self.naming_format != "Don't Rename":
            print(self.naming_format)
            artist = music_file['artist'][0]
            albumartist = music_file['albumartist'][0]
            album = music_file['album'][0]
            title = music_file['title'][0]

            # renaming the modified file with name according to the chosen option by the user
            self.file_name = self.naming_format.format(Artist=artist, AlbumArtist=albumartist, Album=album, Title=title)
            self.file_name = os.path.join(os.path.dirname(self.file_path), f"{self.file_name}.mp3")

            try:
                os.rename(self.file_path, self.file_name)

            except FileExistsError:
                os.remove(self.file_name)
                os.rename(self.file_path, self.file_name)

            self.file_path = self.file_name

        saving_file.dismiss()
        self._return_popup(title='MP3 File Saved', content=Label(text=f'{self.file_name} Saved'),
                           size=(800, 200)).open()

        self.label_file_name.pretty_text = os.path.basename(self.file_name)

        TagEditor.FILE_OPENED = True

        if self.checkbox_all_albums_art.active:
            print(12345)
            try:
                self.album_art_all_songs(self.text_input_dict['album'].text,
                                         self.text_input_dict['albumartist'].text)
            except AssertionError:
                self._return_popup("Missing Fields", content=PymLabel(text="Album and Album Artist is Missing"))

        # resetting the widgets after saving the file
        self.init_app(None)

    def album_art_manager(self, _: Button) -> None:
        """
            Function to grab the album art;
            it will offer three choice,
            Download from Internet or Pick from local filesystem or Remove the cover art
            :param _:
            :type _:
            :return:
            :rtype:
        """

        if not TagEditor.FILE_OPENED:
            self._return_popup(title='No file opened',
                               content=Label(text="Please open a file...")).open()
            return

        # button for the popup
        button_local_picker = Button(text='Local Filesystem', background_color=(255, 0, 0, 1),
                                     background_normal='')
        button_google_search = Button(text='Search With Google', background_color=(255, 0, 0, 1),
                                      background_normal='')
        button_art_remove = Button(text='Remove Album Art', background_color=(255, 0, 0, 1),
                                   background_normal='')
        button_extract_art = Button(text='Extract The Album Art', background_color=(255, 0, 0, 1),
                                    background_normal='')

        art_button_layout = BoxLayout(orientation='vertical')
        art_picker = self._return_popup(title='Select Album Art', content=art_button_layout,
                                        size=(200, 200))

        # binding function to button in the popup
        for widget, callback in zip((button_google_search, button_local_picker, button_art_remove,
                                     button_extract_art),
                                    (self.album_art_google, self.album_art_local,
                                     self.album_art_remove, self.album_art_extract)):
            widget.bind(on_press=partial(callback, art_picker=art_picker))
            art_button_layout.add_widget(widget)

        art_picker.open()

    def album_art_local(self, _: Button, art_picker: Popup) -> None:
        """
        Allows to select the album art from the local file system.
        Opens the file dialog for selecting jpeg or png or jpg file

        It will open user's default Downloads folder in case the file is downloaded from the
        internet

        :param art_picker:
        :type art_picker: Popup
        :param _:
        :type _: Button
        """
        art_picker.dismiss()
        file_types = "JPEG File, jpg File, PNG File | *.jpg | *.jpeg | *.png;"

        with suppress(subprocess.CalledProcessError):
            # opening file dialog in Downloads folder if the image was searched online
            image_path = subprocess.check_output([
                'zenity', '--file-selection', f'--file-filter={file_types}', '--title=Select an Image file'
            ]).decode(sys.stdout.encoding).strip()

            self.image_cover_art.source = image_path
            self.image_cover_art.reload()

    def album_art_google(self, _: Button, art_picker: Popup) -> None:
        """
        this method will open the browser (default Google Chrome) and search for the album art...

        :param art_picker:
        :type art_picker: Popup
        :param _:
        :type _: Button
        """
        art_picker.dismiss()
        if self.text_input_dict["album"].text == "":
            self._return_popup(title='Empty Fields',
                               content=Label(text="Please fill Album and Artist field to perform "
                                                  "an auto search of album art")).open()
            return

        # Google as_q -> advance search query; tbm=isch -> image search; image size = 500*500
        search_url = urlunparse(('https', 'www.google.co.in', quote('search'), '',
                                 urlencode({'tbm': 'isch',
                                            'tbs': 'isz:ex,iszw:500,iszh:500',
                                            'as_q': f"{self.text_input_dict['albumartist'].text} "
                                                    f"{self.text_input_dict['album'].text} "
                                                    f"album art"}), ''))

        # open the default web browser to let the user download the image manually
        webbrowser.open(search_url)

        self.album_art_local(_, art_picker=art_picker)

    def album_art_remove(self, _: Button, art_picker: Popup) -> None:
        """
            Function for removing the album art from the MP3 File
        :param art_picker:
        :type art_picker: Popup
        :param _:
        :type _: Button
        """
        art_picker.dismiss()

        file = MP3(self.file_path, ID3=ID3)
        self.image_cover_art.source = self.constants.default_tag_cover

        try:
            file.pop('APIC:Cover')

        except KeyError:
            with suppress(KeyError):
                file.pop('APIC:')

        finally:
            self.image_cover_art.reload()

    @staticmethod
    def album_art_extract(_: Button, art_picker: Popup) -> None:
        """
            Extracting Album art and saving to disc
        :param art_picker:
        :type art_picker: Popup
        :param _:
        :type _: Button
        """
        art_picker.dismiss()

        # create name for extracted album art and name it on the basis of its album name and replace all punctuation
        # with ""
        # extract_file = f"{self.text_input_dict['album'].text}_{round(time())}.jpeg" \
        #     if self.text_input_dict['album'].text != "" else f"album_art_{round(time())}.jpeg"
        #
        # # extract_file = re.sub(r"[^\w\s]", '', extract_file).replace('_', "")
        #
        # file_dialog = CreateFileDialog(False, None, extract_file, 0, "*.jpeg| JPEG File", None)
        # file_dialog.DoModal()
        #
        # file_path = file_dialog.GetPathNames()
        #
        # shutil.copy(self.image_cover_art.source, file_path[0])

    def album_art_all_songs(self, album: AnyStr, album_artist: AnyStr) -> None:
        """
            Apply album art to all songs of the same album and artist
        :param album: the album name which album art has to be changed
        :type album: str
        :param album_artist: the album artist name which album art has to be changed
        :type album_artist: str
        """

        for file_name in glob(f"{os.path.dirname(self.file_path)}/*.mp3"):
            music_file = EasyID3(file_name)

            if music_file['album'][0] == album and music_file['albumartist'][0] == album_artist:
                with self.saving(MP3(file_name)) as mp3_file:
                    with open(self.image_cover_art.source, 'rb') as alb_art:
                        mp3_file.tags.add(APIC(mime=f'image/{pathlib.Path(self.image_cover_art.source).suffix}',
                                               type=3, desc=u'Cover', data=alb_art.read(), encoding=1))

    def on_stop(self):
        """
            this will be called when the app will exit,
            and it will delete any temporary directory created
        """
        if self.to_delete is not None:
            self.to_delete.cleanup()
        super().on_stop()


def main():
    """
        Main Function
    """
    TagEditor().run()
