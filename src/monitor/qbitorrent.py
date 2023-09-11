#!/usr/bin/env python
# -*- coding: latin-1 -*-

LOG_NAME = 'QBitorrent'

import os, sys
import logging
import utilities
import signal
import requests
import time

from runner import Runner
from optparse import OptionParser, OptionGroup
from qbittorrent import Client
from pprint import pprint

logging.getLogger("urllib3").setLevel(logging.WARNING)

class QBitorrent(Runner):

  def __init__(self, **kwargs):
    try:
      # Initialising class variables
      class_name       = self.__class__.__name__
      self.logger      = utilities.GetLogger(class_name)
      self.access      = None
      self.user        = None
      self.host        = None
      self.port        = None
      self.qb          = None
      self.preferences = None
      self.torrents    = None
      self.tries       = 3
      self.trackers    = None
      self.torrents_state = {}
      self.new_trackers_available = True
      self.trackers_last = 0
      self.upd_trackers_period = 24*60*60
      for key in kwargs.keys():
        #print("---- key: %s"%key)
        if key == "user":
          self.user = kwargs[key]
        elif key == "access":
          self.access = kwargs[key]
        elif key == "host":
          self.host = kwargs[key]
        elif key == "port":
          self.port = kwargs[key]

      self.update_trackers(first_time = True)
      self.connect()
      self.logger.debug("Created main object")

      # Initialising runner function
      kwargs.update({"app_func" : self.update})
      Runner.__init__(self, **kwargs)

    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def connect(self):
    try:
      url = "http://%s:%s/"%(self.host, self.port)
      self.logger.debug("Connecting to %s"%url)
      self.qb = Client(url)
      self.logger.debug("Accessing to %s..."%url)
      self.qb.login(self.user, self.access)

      if not self.qb or not self.qb.verify or not self.qb._is_authenticated:
        raise Exception("QBitorrent connnection failed")
      api_version = self.qb.api_version
      qbittorrent_version = self.qb.qbittorrent_version
      self.logger.info("Session established (%s, %s)."
        %(api_version, qbittorrent_version))
      
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def update(self):
    try:
      if not self.qb:
        self.tries -= 1
        self.logger.warning("Retrying to connect [%d]"%self.tries)
        self.connect()
      if self.tries < 1:
        self.logger.error("Exiting, not connected")
        self.signal_handler(signal.SIGTERM)
      
      # updating trackers if required
      self.update_trackers()

      self.logger.debug("Collecting torrents info")
      self.preferences = self.qb.preferences()

      # filter: 'all' | 'downloading' | 'seeding' | 'completed' | 'paused' | 'active' | 'inactive' | 'resumed' | 'stalled' | 'stalled_uploading' | 'stalled_downloading' | 'errored';
      self.torrents = self.qb.torrents()

      has_set_trackers = False
      for torrent in self.torrents:
        progress   = torrent["progress"]
        downloaded = torrent["downloaded"]
        size       = torrent["size"]
        state      = torrent["state"]
        progress   = torrent["progress"]
        name       = torrent["name"]
        completed  = torrent["completed"]
        num_leechs = torrent["num_leechs"]
        num_seeds  = torrent["num_seeds"]
        category   = torrent["category"]
        infohash   = torrent["hash"]

        # pause on going ones
        if not state.startswith("paused"):
          missing = utilities.human_readable_data(size - downloaded)
          self.logger.info("%s | [%s] at %3.2f%% - %s"%
                           (state, name, progress*100, str(missing)))

          # setting trackers if it would be time
          if self.new_trackers_available and progress < 1:
            has_set_trackers = self.set_trackers(name, infohash, self.trackers)
            if infohash in self.torrents_state:
              self.torrent_state.update({infohash: time.time()})

          # pausing if it is finished
          elif progress == 1 and not state.startswith("moving"):
            self.logger.info("  = Pausing torrent [%s]"%(name))
            self.pause_torrent(name, infohash)
             
      # allow all trackers to be defined and avoid updating on next call
      if has_set_trackers:
        self.new_trackers_available = False
      
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def pause_torrent(self, name, infohash):
    try:
      self.logger.debug("Pausing torrent %s"%name)
      self.qb.pause(infohash)
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def update_trackers(self, first_time = False):
    try:
      elapsed_time = time.time() - self.trackers_last
      cond = first_time or elapsed_time < self.upd_trackers_period
      if first_time or elapsed_time < self.upd_trackers_period:
        self.logger.info("    Remaining time to update tracker: %.2f"%elapsed_time)
        return

      self.logger.debug("    Downloading trackers")
      URL = "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_all.txt"
      response = requests.get(URL)
      if response.status_code > 299:
        self.logger.warning("Failed to contact trackers")
        return

      self.trackers = response.content
      self.new_trackers_available = True
      self.trackers_last = time.time()
      occurrences = str(self.trackers).count("\\n")
      self.logger.debug("    Found %s trackers"%str(occurrences))
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def set_trackers(self, name, infohash, trackers):
    try:
      if self.trackers == None:
        self.logger.warning("    Trackers not found to set")
        return False

      self.logger.debug("    Setting trackers to %s"%name)
      self.qb.add_trackers(infohash, trackers)
      return True
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

## Process management methods
def call_task(options):
  ''' Command line method for running sniffer service'''
  try:

    monitor = QBitorrent(**options)

  except Exception as inst:
      utilities.ParseException(inst, logger=logger)

if __name__ == '__main__':
  logFormatter="'%(asctime)s|%(levelname)7s|%(name)25s|%(message)s'"
  logging.basicConfig(format=logFormatter, level=logging.DEBUG)
  logger = utilities.GetLogger(LOG_NAME)
  logger.debug('Logger created.')
  
  usage       = "usage: %prog option1=string option2=bool"
  parser      = OptionParser(usage=usage)

  app_opts = OptionGroup(parser, "Runtime options")
  app_opts.add_option('--user',
                type="string",
                action='store',
                default=os.environ.get('QBIT_USR'),
                help='Input qbitorrent login user')
  app_opts.add_option('--access',
                type="string",
                action='store',
                default=os.environ.get('QBIT_ACC'),
                help='Input qbitorrent login access')
  app_opts.add_option('--host',
                type="string",
                action='store',
                default=os.environ.get('QBIT_HOST'),
                help='Input qbitorrent host')
  app_opts.add_option('--port',
                type="string",
                action='store',
                default=os.environ.get('QBIT_PORT'),
                help='Input qbitorrent port')

  run_time = OptionGroup(parser, "Runtime options")
  run_time.add_option('--time_out',"-t",
                type="int",
                action='store',
                default=os.environ.get('QBIT_SLEEP'),
                help='Input iterative timer')

  parser.add_option_group(app_opts)
  parser.add_option_group(run_time)
  (options, args) = parser.parse_args()
  option_dict = vars(options)

  if not options.host:
    parser.error("host name is required")
  #print(options)
  call_task(option_dict)

