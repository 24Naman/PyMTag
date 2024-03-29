#!/usr/bin/python

"""
    16-06-2018
    Author: Naman Jain

"""
import os
from collections import OrderedDict
from typing import AnyStr, Iterator

from kivy.properties import ObjectProperty
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import SpinnerOption, Spinner


class CustomSpinnerOption(SpinnerOption):
    """
        Class for custom spinner
    """
    background_color = [255, 0, 255, 0.8]


class CustomSpinner(Spinner, Button):
    """
        Class for custom spinner
    """
    background_color = [255, 0, 255, 0.5]

    option_cls = ObjectProperty(CustomSpinnerOption)


# noinspection SpellCheckingInspection
class Constants(OrderedDict):
    """
        This class is for providing constants
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.app_icon = 'app_icon.ico'

        self.title = 'Title'
        self.artist = 'Artist'
        self.album = 'Album'
        self.albumartist = 'Album Artists'
        self.date = 'Year'
        self.genre = 'Genre'
        self.tracknumber = 'Track Number'
        self.lyrics = 'Lyrics'

        self.name = "PyMTag"
        self.window_title = f"{self.name} - MP3 Tag Editor"

        self.default_tag_cover = os.path.join('../res', 'default_music.jpg')

        self.rocket_image = os.path.join('../res', 'rocket.png')
        self.switch_icon = os.path.join("../res", "switch_icon.png")

        # File renaming options
        self.rename = {"no-rename": "Don't Rename", "title-album": "{Title} - {Album}",
                       "album-title": "{Album} - {Title}", "artist-title": "{Artist} - {Title}",
                       "album-artist-title": "{Album} - {Artist} - {Title}",
                       "artist-album-title": "{Artist} - {Album} - {Title}",
                       "album-albumartist-title": "{Album} - {AlbumArtist} - {Title}",
                       "albumartist-album-title": "{AlbumArtist} - {Album} - {Title}"
                       }

    def __getitem__(self, item) -> AnyStr:
        return self.__dict__[item]

    # noinspection SpellCheckingInspection
    def __iter__(self) -> Iterator[str]:
        """
        Creating iterator to use in UI creation

        :yield: [description]
        :rtype: Iterator[str]
        """
        yield from ['title', 'artist', 'album', 'albumartist', 'date', 'genre', 'tracknumber', 'lyrics']


class PymLabel(Label):
    """
        File Info Label
    """

    def __init__(self, text: str, **kwargs) -> None:
        self.text = f"[b][i][size=15][color=000000]{text}[/color][/font][/i][/b]"

        kwargs['text'] = self.text
        kwargs['size_hint_x'] = 1
        kwargs['size_hint_y'] = 0.25
        kwargs['markup'] = True

        super().__init__(**kwargs)

    @property
    def pretty_text(self) -> str:
        """
            Getter for text
        """
        return self.text

    @pretty_text.setter
    def pretty_text(self, value: str) -> None:
        self.text = f"[b][i][size=15][color=000000]{os.path.basename(value)}[/color][/font]" \
                    "[/i][/b]"
