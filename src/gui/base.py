# -*- coding:utf-8 -*-
#
# Copyright (C) 2018 sthoo <sth201807@gmail.com>
#
# Support: Report an issue at https://github.com/sth2018/FastWordQuery/issues
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version; http://www.gnu.org/copyleft/gpl.html.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys

from anki.utils import is_mac
from aqt.qt import *


__all__ = ['APP_ICON', 'Dialog', 'WIDGET_SIZE', 'get_icon']

from aqt.theme import theme_manager


def process_icon_colors_for_dark_theme(
    png_path: str,
    dark_threshold: int = 60,
    boost_factor: float = 1.35,
    min_value: int = 40,
) -> QIcon:
    """Loads a PNG, inverts very dark pixels to light colors, and brightens

    remaining colored pixels using HSV scaling with a minimum floor.

    :param png_path: Path to the source PNG image.
    :param dark_threshold: HSV Value (0-255) at or below which pixels are
      inverted.
    :param boost_factor: Multiplier for brightness on pixels above threshold.
    :param min_value: Minimum HSV brightness floor for boosted non-dark
      pixels.
    """
    image = QImage(png_path)
    if image.isNull():
        raise FileNotFoundError(f"Could not load image at {png_path}")

    image = image.convertToFormat(QImage.Format.Format_ARGB32)

    width = image.width()
    height = image.height()

    for y in range(height):
        for x in range(width):
            pixel_color = QColor.fromRgba(image.pixel(x, y))

            # Skip fully transparent pixels
            if pixel_color.alpha() == 0:
                continue

            v = pixel_color.value()

            # 1. Invert dark pixels (e.g. RGB(0,0,0) -> RGB(255,255,255))
            if v <= dark_threshold:
                r = 255 - pixel_color.red()
                g = 255 - pixel_color.green()
                b = 255 - pixel_color.blue()

                inverted = QColor(r, g, b, pixel_color.alpha())
                image.setPixel(x, y, inverted.rgba())

            # 2. Brighten non-dark colors
            else:
                h, s, _, a = pixel_color.getHsv()

                # Scale brightness and apply minimum floor (clamped to 255 max)
                new_v = max(min_value, min(255, int(v * boost_factor)))

                brightened = QColor.fromHsv(h, s, new_v, a)
                image.setPixel(x, y, brightened.rgba())

    return QIcon(QPixmap.fromImage(image))

def get_icon(filename):
    curdir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(curdir, os.pardir, 'res', filename)

    if theme_manager.night_mode:
        return process_icon_colors_for_dark_theme(path)
    
    return QIcon(path)


APP_ICON = get_icon('wqicon.png')  # Addon Icon


class Dialog(QDialog):
    '''
    Base used for all dialog windows.
    '''

    def __init__(self, parent, title):
        '''
        Set the modal status for the dialog, sets its layout to the
        return value of the _ui() method, and sets a default title.
        '''

        self._title = title if "FastWQ" in title else "FastWQ - " + title
        self._parent = parent
        super().__init__(parent)

        self.setModal(True)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setWindowIcon(APP_ICON)
        self.setWindowTitle(self._title)
        # 2 & 3 & mac compatible
        if is_mac and sys.hexversion >= 0x03000000:
            QApplication.setStyle('Fusion')


class WidgetSize(object):
    '''
    constant values
    '''
    dialog_width = 950
    dialog_height_margin = 166 if is_mac and sys.hexversion < 0x03000000 else 166
    map_min_height = 0
    map_max_height = 30
    map_fld_width = 100
    map_dictname_width = 250
    map_dict_width = 160
    map_field_width = 200


WIDGET_SIZE = WidgetSize()
