"""
Simple LCD display implementation.

Replace this with your actual display driver, e.g. RPLCD for HD44780 displays,
or luma.oled for SSD1306 / SH1106 OLED displays.
"""

import logging
import os
import time
import textwrap

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
        epd = epd2in9d.EPD()
        epd.init()
        epd.Clear()

    def show(self, title: str, artist: str, album: str = None, paused: bool = False, repeat_info: str = None):
        """
        Show title and artist on the display.
        """
        logger.debug('LCD: show')
        
        epd = epd2in9d.EPD()
        epd.init()
        
        line0 = artist if artist else 'Unknown artist'
        
        lines_album = textwrap.wrap(album or '', width=35)
        
        line1 = lines_album[0] if len(lines_album) > 0 else 'Unknown album'
        line2 = lines_album[1] if len(lines_album) > 1 else ''
        
        lines_title = textwrap.wrap(title or '', width=35)
        
        line3 = lines_title[0] if len(lines_title) > 0 else 'Unknown title'
        line4 = lines_title[1][25:] if len(lines_title) > 1 else ''

        font24 = ImageFont.truetype(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'display/Font.ttc'), 24)
        font18 = ImageFont.truetype(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'display/Font.ttc'), 18)

        HImage = Image.new('1', (epd.height, epd.width), 0)  # 298*126
        draw = ImageDraw.Draw(HImage)
        draw.text((10, 0), line0, font = font24, fill = 255)
        draw.text((10, 29), line1, font = font18, fill = 255)
        draw.text((10, 49), line2, font = font18, fill = 255)
        
        draw.text((10, 75), line3, font = font18, fill = 255)
        draw.text((10, 99), line4, font = font18, fill = 255)
        
        if repeat_info == 'repeat_one':
            draw.text((240, 99), "[R1]", font = font18, fill = 255)
        elif repeat_info == 'repeat_all':
            draw.text((240, 99), "[RA]", font = font18, fill = 255)
        else:
            draw.text((240, 99), "   ", font = font18, fill = 255)
            
        if paused:
            draw.text((270, 99), "[P]", font = font18, fill = 255)
        elif repeat_info == 'repeat_all':
            draw.text((270, 99), "   ", font = font18, fill = 255)

        epd.DisplayPartial(epd.getbuffer(HImage))
        epd.init()
        epd.sleep()

    def clear(self):
        """
        Clear the display.
        """
        # self.lcd.clear()
#        logger.debug('LCD: clear')
