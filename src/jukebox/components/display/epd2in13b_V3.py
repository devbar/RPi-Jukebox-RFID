"""
Simple LCD display implementation.

Replace this with your actual display driver, e.g. RPLCD for HD44780 displays,
or luma.oled for SSD1306 / SH1106 OLED displays.
"""

import logging
import os
import time

from .waveshare_epd import epd2in9d
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger('jb.Display.Lcd')


class Epd2in13bV3Display:
    """
    Placeholder LCD display driver.

    The interface is intentionally minimal: show() and clear().
    Swap this class with a real driver without changing the plugin logic.
    """

    def __init__(self):
        # Example for a real HD44780 via RPLCD:
        # from RPLCD import CharLCD
        # self.lcd = CharLCD(cols=16, rows=2, pin_rs=..., pin_e=..., pins_data=[...])
        pass

    def show(self, title: str, artist: str, album: str = None, paused: bool = False):
        """
        Show title and artist on the display.
        """

        logger.debug('LCD: show')
        logger.debug(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'display/Font.ttc'))

        line1 = (title or 'Unknown title')[:19]
        line2 = (title or 'Unknown title')[19:]
        line3 = (artist or 'Unknown artist')[:20]
        line4 = (artist or 'Unknown artist')[20:]

        if paused:
            line3 = '[PAUSE] ' + line3

        # self.lcd.clear()
        # self.lcd.write_string(line1 + '\r\n' + line2)
        logger.debug(f'LCD: {line1} | {line2}')

        epd = epd2in9d.EPD()
        epd.init()

        font32 = ImageFont.truetype(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'display/Font.ttc'), 32)
        font24 = ImageFont.truetype(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'display/Font.ttc'), 24)

        logger.debug(f'Fonts loaded')


        HImage = Image.new('1', (epd.height, epd.width), 0)  # 298*126
        draw = ImageDraw.Draw(HImage)
        draw.text((10, 0), line1, font = font32, fill = 255)
        draw.text((10, 27), line2, font = font32, fill = 255)
        draw.text((10, 57), line3, font = font24, fill = 255)
        draw.text((10, 84), line4, font = font24, fill = 255)


        epd.DisplayPartial(epd.getbuffer(HImage))
        epd.init()
        epd.sleep()

    def clear(self):
        """
        Clear the display.
        """
        # self.lcd.clear()
#        logger.debug('LCD: clear')
