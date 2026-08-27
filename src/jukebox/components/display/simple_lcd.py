"""
Simple LCD display implementation.

Replace this with your actual display driver, e.g. RPLCD for HD44780 displays,
or luma.oled for SSD1306 / SH1106 OLED displays.
"""

import logging

logger = logging.getLogger('jb.Display.Lcd')


class SimpleLcdDisplay:
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

    def show(self, title: str, artist: str, album: str = None, paused: bool = False, repeat_info: str = ''):
        """
        Show title and artist on the display.
        """
        line1 = (title or 'Unknown title')[:16]
        line2 = (artist or 'Unknown artist')[:16]

        if paused:
            line2 = '[PAUSE] ' + line2[:8]
        elif repeat_info:
            line2 = f'{line2[:12]} {repeat_info[:3]}'

        # self.lcd.clear()
        # self.lcd.write_string(line1 + '\r\n' + line2)
        logger.debug(f'LCD: {line1} | {line2}')

    def clear(self):
        """
        Clear the display.
        """
        # self.lcd.clear()
        logger.debug('LCD: clear')
