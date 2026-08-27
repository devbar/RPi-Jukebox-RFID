"""
Display plugin for showing the current player status on an external display.

This plugin subscribes to the internal Jukebox publisher and updates the display
whenever the player status changes meaningfully.
"""

import zmq
import threading
import json
import logging
import time

import jukebox.plugs as plugs
from .simple_lcd import SimpleLcdDisplay
from .epd2in13b_V3 import Epd2in13bV3Display

logger = logging.getLogger('jb.Display')

# Time to wait before clearing the display after a stop event.
# This avoids flickering during track/folder changes where MPD briefly reports stop.
CLEAR_DELAY_SECONDS = 2.0
DISPLAY_TYPE = 'epd2in13b_V3'

def _format_status(status):
    """
    Extract display-relevant fields from the player status.
    """
    if not isinstance(status, dict):
        return None, None, 'stop', ''

    state = status.get('state', 'stop')
    title = status.get('title', '')
    artist = status.get('artist', '')
    album = status.get('album', '')
    file_path = status.get('file', '')
    return title, artist, state, album, file_path


class DisplaySubscriber:
    """
    Subscriber that listens to playerstatus updates and refreshes the display.
    """

    def __init__(self):
        self.ctx = zmq.Context.instance()
        self.sub = self.ctx.socket(zmq.SUB)
        self.sub.connect('inproc://PublisherToProxy')
        self.sub.setsockopt(zmq.SUBSCRIBE, b'playerstatus')

        self.display = self._createDisplay()
        self.running = True
        self.thread = threading.Thread(target=self._event_loop, daemon=True, name='DisplaySubscriber')

        self._last_key = None
        self._clear_timer = None
        self._lock = threading.Lock()
        
    def _createDisplay(self):
        if DISPLAY_TYPE == 'epd2in13b_V3':
            return Epd2in13bV3Display()
        else:
            return SimpleLcdDisplay()

    def start(self):
        """Start the subscriber thread."""
        self.thread.start()
        logger.info('Display subscriber started')

    def stop(self):
        """Stop the subscriber thread and clear the display."""
        self.running = False
        self.sub.close()
        self.thread.join(timeout=2.0)
        self._cancel_clear_timer()
        self.display.clear()
        logger.info('Display subscriber stopped')

    def _event_loop(self):
        while self.running:
            try:
                topic, message = self.sub.recv_multipart()
            except zmq.ZMQError:
                break
            except Exception as e:
                logger.error(f'Error receiving display message: {e}')
                continue

            if not self.running:
                break

            try:
                status = json.loads(message)
            except json.JSONDecodeError as e:
                logger.error(f'Error decoding playerstatus JSON: {e}')
                continue

            self._update_display(status)

    def _cancel_clear_timer(self):
        with self._lock:
            if self._clear_timer is not None:
                self._clear_timer.cancel()
                self._clear_timer = None

    def _schedule_clear(self):
        self._cancel_clear_timer()
        with self._lock:
            self._clear_timer = threading.Timer(CLEAR_DELAY_SECONDS, self._do_clear)
            self._clear_timer.start()

    def _do_clear(self):
        with self._lock:
            self._clear_timer = None
        self.display.clear()

    def _update_display(self, status):
        title, artist, state, album, file_path = _format_status(status)

        # Create a key that represents the meaningful displayed content.
        # Include title and artist to catch delayed metadata updates from streams.
        # Ignore elapsed/duration changes that do not affect the display.
        key = (file_path, state, title, artist, album)
        
        logger.debug(f'Display update: {key}')

        if key == self._last_key:
            return
        self._last_key = key

        if state == 'play':
            self._cancel_clear_timer()
            self.display.show(title, artist, album=status.get('album'))
        elif state == 'pause':
            self._cancel_clear_timer()
            self.display.show(title, artist, album=status.get('album'), paused=True)
        elif state == 'stop':
            # Delay clear to avoid flicker during track/folder changes.
            self._schedule_clear()
        else:
            self._cancel_clear_timer()
            self.display.clear()


subscriber = None


@plugs.initialize
def initialize():
    logger.info('Initializing display plugin')
    global subscriber
    subscriber = DisplaySubscriber()
    subscriber.start()


@plugs.atexit
def atexit(**ignored_kwargs):
    global subscriber
    if subscriber is not None:
        subscriber.stop()
