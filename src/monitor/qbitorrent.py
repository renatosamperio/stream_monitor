#!/usr/bin/env python
# -*- coding: latin-1 -*-

LOG_NAME = 'QBitorrent'

import os
import logging
import utilities
import signal
import requests
import time

from runner import Runner
from optparse import OptionParser, OptionGroup
from qbittorrent import Client
from pprint import pprint
from datetime import timedelta

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
      self.pause_old   = False
      self.failed      = False
      self.preferences = None
      self.torrents    = None
      self.tries       = 3
      self.trackers    = None
      self.timeout_days   = 30
      self.torrents_state = {}
      self.new_trackers_available = True
      self.trackers_last = 0
      self.upd_trackers_period = 24*60*60
      self.turn_off_time = 3600*24*self.timeout_days
      
      self.printed = [True, True, True, True, True, True, True, True, True, True]
      
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
        elif key == "pause_old":
          self.pause_old = kwargs[key]
        elif key == "timeout_days":
          self.timeout_days = kwargs[key]

      self.download_trackers(first_time = True)
      ok = self.connect()
      if ok: 
        self.logger.debug("Created main object")
      

      # Initialising runner function
      kwargs.update({"app_func" : self.update})
      Runner.__init__(self, **kwargs)

    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def connect(self):
    sucess = True
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
      sucess = False
    finally:
      return sucess

  def find_file(self, torrent):
    try:
      progress = torrent['progress']
      if progress < 1:
        name = torrent['name']
        # self.logger.debug("  + Looking for [%s]"%name)
        if 'download_path' in torrent and os.path.exists(torrent['download_path']):
          
          # get to know if file is already downloaded
          file_path =  torrent['download_path'] + '/' + name
          
          # sometimes is a file or a path with more files
          if os.path.isfile(file_path) or os.path.exists(file_path):
            state = torrent['state']
            infohash = torrent["hash"]
            
            # here we might be double checking if torrent is paused
            if 'progress' in torrent and state.startswith("paused"):
              suffix = "%3.2f%%"%(torrent['progress']*100)+ ' left'
            # self.logger.debug("  +   [%s] torrent file found %s %s"%
            #                   (state, name, suffix))
          
            # there is already a torrent with the same name, let's try check it
            # not working: disappears torrent: 
            self.qb.recheck([infohash])
            self.logger.debug("  +   [%s] torrent has been rechecked [%s]"%
                              (state, name))
          
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def update(self):
    shown = False
    try:
      if not self.qb:
        # take a quick break
        self.logger.info("Take a quick break before retrying [%d]"%self.tries)
        time.sleep(5)
        
        self.tries -= 1
        self.logger.info("Retrying to connect [%d]"%self.tries)
        is_ok = self.connect()
        
        if self.tries < 1:
          self.logger.error("Exiting, not connected")
          self.signal_handler(signal.SIGTERM)
          self.failed = True
          return
      
      # updating trackers if required
      self.download_trackers()

      try:
        if not self.qb:
          is_ok = False
          return
        self.logger.debug("Collecting torrents info")
        self.preferences = self.qb.preferences()
        # filter: 'all' | 'downloading' | 'seeding'  | 'completed' |
        #      'paused' | 'active'      | 'inactive' | 'resumed'   | 
        #     'stalled' | 'stalled_uploading' | 'stalled_downloading' | 'errored';
        self.torrents = self.qb.torrents()

      # stop here if something had failed in connection
      except requests.exceptions.HTTPErr as inst:
        self.qb.logout()
        self.qb = None
        is_ok = False
        self.logger.warning("Error: Cannot get preferences, restting client")
        return 
      except Exception as inst:
        self.qb.logout()
        self.qb = None
        is_ok = False
        utilities.ParseException(inst, logger=self.logger)
        return 
        
      has_set_trackers = False
      for torrent in self.torrents:
        
        # if not shown:
        #   pprint(torrent.keys())
        #   shown = True

        progress   = torrent["progress"]
        downloaded = torrent["downloaded"]
        size       = torrent["size"]
        state      = torrent["state"]
        name       = torrent["name"]
        num_leechs = torrent["num_leechs"]
        num_seeds  = torrent["num_seeds"]
        infohash   = torrent["hash"]
        dlspeed    = torrent["dlspeed"]
        last_activity = torrent["last_activity"]
        
        # if 'magnet_uri' in torrent:
        #   del torrent['magnet_uri']
        # pprint(torrent)
        # print("* "*50)
        
        # if not state.startswith("paused"):
        #   if self.printed[0]:
        #     print("+ "*50)
        #     pprint(torrent)
        #     print("+ "*50)
        #     self.printed[0] = False
     
        # get to find paused files
        if state.startswith("paused"):
          self.find_file(torrent)
        
        # pause on going ones
        if not state.startswith("paused"):
            
          missing = utilities.human_readable_data(size - downloaded)
          hDwldSpeed = utilities.human_readable_data(int(dlspeed))
          is_downloading = "   " if dlspeed == 0 else " * "
          progress_str = "%3.2f%%"%(progress*100)
          
          # should we turn off some of the torrents? Only if it is not downloading,
          # if it would not have seeds nor leeches and hasn't been active for more
          # than a week
          now = time.time() 
          time_since_last_activity = now - last_activity
          
          if self.pause_old:
            has_not_been_around = dlspeed == 0 and \
                                  num_seeds == 0 and num_leechs == 0 and \
                                  time_since_last_activity >= self.turn_off_time

            # turn of torrents that hasn't been available 
            # for more than a week
            if has_not_been_around:
              elapsed_datetime = str(timedelta(seconds=time_since_last_activity))
              self.logger.info("  = = = Turning off torrent [%s] off since %s"%(name, elapsed_datetime))
              self.pause_torrent(name, infohash)
            
          # send state to the logs
          self.logger.info("%18s|%s|%7s|%9s/s|%9s| %3d/%3d | %s"%
                           (state, is_downloading, progress_str, hDwldSpeed, 
                            str(missing), num_seeds, num_leechs, name))
          
          # setting trackers if it would be time
          if self.new_trackers_available and progress < 1:
            has_set_trackers = self.set_trackers(name, infohash, self.trackers)
            if infohash in self.torrents_state:
              self.torrent_state.update({infohash: time.time()})

          # pausing if it is finished
          elif progress == 1 and not state.startswith("moving"):
            self.logger.info("  = = = Pausing finished torrent [%s]"%(name))
            self.pause_torrent(name, infohash)
        
      # allow all trackers to be defined and avoid updating on next call
      if has_set_trackers:
        self.new_trackers_available = False
      
      # return status
      is_ok = True
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)
      is_ok = False
    finally:
      return is_ok

  def pause_torrent(self, name, infohash):
    try:
      self.logger.debug("Pausing torrent %s"%name)
      self.qb.pause(infohash)
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def download_trackers(self, first_time = False):
    try:
      elapsed_time = time.time() - self.trackers_last
      cond = first_time or elapsed_time < self.upd_trackers_period
      if first_time or elapsed_time < self.upd_trackers_period:
        self.logger.info("    Remaining time to download tracker: %.2f"%elapsed_time)
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
  run_time.add_option('--time_out',
                type="int",
                action='store',
                default=os.environ.get('QBIT_SLEEP'),
                help='Input iterative timer')
  run_time.add_option('--pause_old',
                type="int",
                action='store',
                default=os.environ.get('QBIT_PAUSE'),
                help='Pause old torrents')
  run_time.add_option('--timeout_days',
                type="int",
                action='store',
                default=os.environ.get('QBIT_EXPIRE'),
                help='Pause old torrents')

  parser.add_option_group(app_opts)
  parser.add_option_group(run_time)
  (options, args) = parser.parse_args()
  option_dict = vars(options)

  if not options.host:
    parser.error("host name is required")
  #print(options)
  call_task(option_dict)

