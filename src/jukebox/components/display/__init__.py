"""
Display plugin for showing the current player status on an external display.

This plugin subscribes to the internal Jukebox publisher and updates the display
whenever the player status changes meaningfully.

Display updates are processed serially by a single worker thread. If multiple
updates arrive while a refresh is in progress, only the latest update is applied.
This is required for EPD/e-paper displays which cannot handle concurrent refreshes.
"""

import zmq
import threading
import json
import logging

import jukebox.plugs as plugs
from .simple_lcd import SimpleLcdDisplay
from .epd2in13b_V3 import Epd2in13bV3Display
from .epd2in9b_V4 import Epd2in9bV4Display

logger = logging.getLogger('jb.Display')

# Select the display driver to use.
# 'simple_lcd' is a placeholder console logger for development.
# 'epd2in13b_V3' is the Waveshare 2.13inch e-Paper display.
DISPLAY_TYPE = 'epd2in9b_V4'

# Time to wait before clearing the display after a stop event.
# This avoids flickering during track/folder changes where MPD briefly reports stop.
CLEAR_DELAY_SECONDS = 2.0


def _format_status(status):
    """
    Extract display-relevant fields from the player status.
    """
    if not isinstance(status, dict):
        return None, None, 'stop', '', ''

    state = status.get('state', 'stop')
    title = status.get('title', '')
    artist = status.get('artist', '')
    album = status.get('album', '')
    file_path = status.get('file', '')
    repeat_info = _format_repeat(status)
    return title, artist, state, file_path, repeat_info


def _format_repeat(status):
    """
    Build a short repeat indicator from MPD repeat/single fields.
    """
    repeat = status.get('repeat')
    single = status.get('single')

    if repeat in (1, '1', True):
        if single in (1, '1', True):
            return 'repeat_one'
        return 'repeat_all'
    return ''


def _create_display():
    """
    Factory for creating the configured display driver.
    """
    if DISPLAY_TYPE == 'epd2in13b_V3':
        return Epd2in13bV3Display()
    
    if DISPLAY_TYPE == 'epd2in9b_V4':
        return Epd2in9bV4Display()
    
    return SimpleLcdDisplay()


class DisplaySubscriber:
    """
    Subscriber that listens to playerstatus updates and refreshes the display.

    Display updates are processed serially by a single worker thread. If multiple
    updates arrive while a refresh is in progress, only the latest update is applied.
    This is required for EPD/e-paper displays which cannot handle concurrent refreshes.
    """

    def __init__(self):
        self.ctx = zmq.Context.instance()
        self.sub = self.ctx.socket(zmq.SUB)
        self.sub.connect('inproc://PublisherToProxy')
        self.sub.setsockopt(zmq.SUBSCRIBE, b'playerstatus')

        self.display = _create_display()
        self.running = True

        self._pending_status = None
        self._pending_lock = threading.Lock()
        self._update_event = threading.Event()

        self._last_key = None
        self._clear_timer = None
        self._timer_lock = threading.Lock()

        self._receiver_thread = threading.Thread(target=self._event_loop, daemon=True, name='DisplayReceiver')
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name='DisplayWorker')

    def start(self):
        """Start the receiver and worker threads."""
        self._receiver_thread.start()
        self._worker_thread.start()
        logger.info('Display subscriber started')

    def stop(self):
        """Stop the subscriber threads and clear the display."""
        self.running = False
        self.sub.close()
        self._update_event.set()
        self._receiver_thread.join(timeout=2.0)
        self._worker_thread.join(timeout=2.0)
        self._cancel_clear_timer()
        self.display.clear()
        logger.info('Display subscriber stopped')

    def _event_loop(self):
        """
        Receive playerstatus messages and schedule the latest update.
        """
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

            with self._pending_lock:
                self._pending_status = status
            self._update_event.set()

    def _worker_loop(self):
        """
        Process display updates one at a time, always using the latest pending status.
        """
        while self.running:
            self._update_event.wait()
            if not self.running:
                break

            with self._pending_lock:
                status = self._pending_status
                self._pending_status = None
                self._update_event.clear()

            if status is not None:
                try:
                    self._update_display(status)
                except Exception as e:
                    logger.error(f'Error updating display: {e}')

    def _cancel_clear_timer(self):
        with self._timer_lock:
            if self._clear_timer is not None:
                self._clear_timer.cancel()
                self._clear_timer = None

    def _schedule_clear(self):
        self._cancel_clear_timer()
        with self._timer_lock:
            self._clear_timer = threading.Timer(CLEAR_DELAY_SECONDS, self._do_clear)
            self._clear_timer.start()

    def _do_clear(self):
        with self._timer_lock:
            self._clear_timer = None
        self.display.clear()

    def _update_display(self, status):
        title, artist, state, file_path, repeat_info = _format_status(status)

        # Create a key that represents the meaningful displayed content.
        # Include title, artist and repeat_info to catch delayed metadata updates
        # and repeat mode changes. Ignore elapsed/duration changes.
        key = (file_path, state, title, artist, repeat_info)

        if key == self._last_key:
            return
        self._last_key = key

        if state == 'play':
            self._cancel_clear_timer()
            self.display.show(title, artist, album=status.get('album'), repeat_info=repeat_info)
        elif state == 'pause':
            self._cancel_clear_timer()
            self.display.show(title, artist, album=status.get('album'), paused=True, repeat_info=repeat_info)
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
