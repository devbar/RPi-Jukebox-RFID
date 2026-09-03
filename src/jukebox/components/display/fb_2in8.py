"""
Framebuffer display driver for a 320x240 color LCD.

Writes images directly to a Linux framebuffer device (e.g. /dev/fb0).
The default resolution is 320x240 with 24-bit RGB color.
"""

import logging
import os

from PIL import Image  # type: ignore

from .fb_2in8_image_factory import Fb2in8ImageFactory

logger = logging.getLogger('jb.Display.Fb2in8')


class Fb2in8Display:
    """
    Framebuffer display driver for a 320x240 color LCD.
    """

    def __init__(self, framebuffer: str = '/dev/fb0'):
        self._framebuffer = framebuffer
        self._width = 320
        self._height = 240
        self._bytes_per_pixel = 3
        self.image_factory = Fb2in8ImageFactory()

    def show(self, title: str, artist: str, album: str = None, paused: bool = False, repeat_info: str = None, coverart: str = None):
        """
        Render and display the current track information on the framebuffer.
        """
        try:
            image = self.image_factory.create(title, artist, album, paused, repeat_info or '', coverart)
            self._write_to_framebuffer(image)
        except Exception as e:
            logger.error(f'Error rendering framebuffer display: {e}')

    def clear(self):
        """
        Clear the framebuffer by filling it with the background color.
        """
        try:
            image = Image.new('RGB', (self._width, self._height), (0, 0, 0))
            self._write_to_framebuffer(image)
        except Exception as e:
            logger.error(f'Error clearing framebuffer display: {e}')

    def _write_to_framebuffer(self, image: Image):
        """
        Write a PIL RGB image to the Linux framebuffer device.
        """
        if not os.path.exists(self._framebuffer):
            logger.warning(f'Framebuffer device not found: {self._framebuffer}')
            return

        image = image.convert('RGB')
        image = image.resize((self._width, self._height))
        raw = image.tobytes()

        with open(self._framebuffer, 'wb') as fb:
            fb.write(raw)
            fb.flush()

        logger.debug(f'Wrote {len(raw)} bytes to {self._framebuffer}')
