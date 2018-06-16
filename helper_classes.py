#!/usr/bin/python

"""
    16-06-2018
    Author: Naman Jain

"""
import os
import random
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
    background_color = [255, 0, 255, 0.5]


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

        self.title = 'Title'
        self.artist = 'Artist'
        self.album = 'Album'
        self.albumartist = 'Album Artists'
        self.date = 'Year'
        self.genre = 'Genre'
        self.tracknumber = 'Track Number'

        self.window_title = "Musical - Music Tag Editor"

        tag_covers = ['default_music_one.png', 'default_music_two.png']
        self.default_tag_cover = os.path.join('extras', 'images', random.choice(tag_covers))

        self.switch_icon = os.path.join("extras", "switch_icon.png")

        # File renaming options
        self.rename = {"no-rename": "Don't Rename", "album-title": "{Album} - {Title}",
                       "album-artist-title": "{Album} - {Artist} - {Title}",
                       "artist-album-title": "{Artist} - {Album} - {Title}",
                       "title-album": "{Title} - {Album}"}

    def __getitem__(self, item) -> AnyStr:
        return self.__dict__[item]

    # noinspection SpellCheckingInspection
    def __iter__(self) -> Iterator[str]:
        yield from ['title', 'artist', 'album', 'albumartist', 'date', 'genre', 'tracknumber']


class FileInfoLabel(Label):
    """
        File Info Label
    """

    def __init__(self, text: str, **kwargs) -> None:
        kwargs['text'] = f"[b][i][size=15][color=000000]{text}[/color][/font]f[/i][/b]"
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
                    f"[/i][/b]"
