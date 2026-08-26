"""
Display plugin for showing the current player status on an external display.

This plugin subscribes to the internal Jukebox publisher and updates the display
whenever the player status changes.
"""

import zmq
import threading
import json
import logging

import jukebox.plugs as plugs
from .simple_lcd import SimpleLcdDisplay

logger = logging.getLogger('jb.Display')


def _format_status(status):
    """
    Extract display-relevant fields from the player status.
    """
    if not isinstance(status, dict):
        return None, None, 'stop'

    state = status.get('state', 'stop')
    title = status.get('title', '')
    artist = status.get('artist', '')
    return title, artist, state


class DisplaySubscriber:
    """
    Subscriber that listens to playerstatus updates and refreshes the display.
    """

    def __init__(self):
        self.ctx = zmq.Context.instance()
        self.sub = self.ctx.socket(zmq.SUB)
        self.sub.connect('inproc://PublisherToProxy')
        self.sub.setsockopt(zmq.SUBSCRIBE, b'playerstatus')

        self.display = SimpleLcdDisplay()
        self.running = True
        self.thread = threading.Thread(target=self._event_loop, daemon=True, name='DisplaySubscriber')

    def start(self):
        """Start the subscriber thread."""
        self.thread.start()
        logger.info('Display subscriber started')

    def stop(self):
        """Stop the subscriber thread and clear the display."""
        self.running = False
        self.sub.close()
        self.thread.join(timeout=2.0)
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

    def _update_display(self, status):
        title, artist, state = _format_status(status)

        if state == 'play':
            self.display.show(title, artist)
        elif state == 'pause':
            self.display.show(title, artist, paused=True)
        else:
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
