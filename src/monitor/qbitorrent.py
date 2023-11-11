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

class TorrentState:
  """
  State should be defined by torrent hash as key
  """
  def __init__(self, **kwargs):
    class_name  = self.__class__.__name__
    self.logger = utilities.GetLogger(class_name)
    self.status = {}
  
  def get_status(self, infohash):
    if infohash in self.status:
      return self.status[infohash]
    else:
      return None
    
  def set(self, torrent, trackers = None, set_functor = None):
    try:
      # getting torrent data
      infohash   = torrent["hash"]
      if infohash not in self.status or \
          'update_trackers' not in self.get_status(infohash) or \
          not self.get_status(infohash)['update_trackers']:
  
        # TODO: what if there is a new torrent without latest available trackers?
        # set to update trackers
        if infohash in self.status:
          self.status[infohash]['update_trackers'] = True
        else:
          self.status.update({infohash:{'data' : torrent}})
          self.status.update({infohash:{'update_trackers' : True}})
        
        # setting additional callback
        if set_functor != None and trackers != None:
          name = torrent["name"]
          set_functor(name, infohash, trackers)
        
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def clean_all(self):
    try:
      for each in self.status.keys():
        
        # unset to release tracker update
        self.status[each]
        self.get_status(each)['update_trackers']  = False
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def print(self, torrent):
    try:
      
      name       = torrent["name"]
      progress   = torrent["progress"]
      downloaded = torrent["downloaded"]
      size       = torrent["size"]
      state      = torrent["state"]
      num_leechs = torrent["num_leechs"]
      num_seeds  = torrent["num_seeds"]
      dlspeed    = torrent["dlspeed"]

      # state derivative variables
      missing = utilities.human_readable_data(size - downloaded)
      hDwldSpeed = utilities.human_readable_data(dlspeed)
      is_downloading = "   " if dlspeed == 0 else " * "
      progress_str = "%3.2f%%"%(progress*100)
      
      # send state to the logs
      self.logger.info("%18s|%s|%7s|%9s/s|%9s| %3d/%3d | %s"%
                        (state, is_downloading, progress_str, hDwldSpeed, 
                        str(missing), num_seeds, num_leechs, name))
      
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

class Trackers:
  def __init__(self, **kwargs):
    try:
      class_name    = self.__class__.__name__
      self.logger   = utilities.GetLogger(class_name)
      self.update_trackers = 0
      self.last_update = 0
      self.data     = None
      
      # would always be the same?
      self.URL = "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_all.txt"
      
      for key in kwargs.keys():
        if key == "update_trackers":
          self.update_trackers = kwargs[key]
          
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)
  
  def wait(self):
    update_now = True
    try:
      elapsed_time = time.time() - self.last_update
      if elapsed_time < self.update_trackers:
        self.logger.info("    Remaining time to download tracker: %.2f"%elapsed_time)
        update_now = False
        return

    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)
    finally:
      return update_now
    
  def download(self, first_time = False):
    try:
      
      self.logger.debug("    Downloading trackers")
      response = requests.get(self.URL)
      if response.status_code > 299:
        self.logger.warning("Failed to contact trackers")
        return

      # collect trackers info as-it-is
      self.data = response.content
      self.last_update = time.time()
      
      # quick count of trackers
      occurrences = str(self.data).count("\\n")
      self.logger.debug("    Found %s trackers"%str(occurrences))
      
      # mark trackers to be loaded
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def get(self):
    return self.data

class QBitorrent:
  def __init__(self, **kwargs):
    class_name    = self.__class__.__name__
    self.logger   = utilities.GetLogger(class_name)
    self.qb       = None
    self.access   = None
    self.user     = None
    self.host     = None
    self.port     = None
    self.timeout_secs  = 3600*24 * 365
    self.pause_expired = False
    
    try:
      for key in kwargs.keys():
        if key == "user":
          self.user = kwargs[key]
        elif key == "access":
          self.access = kwargs[key]
        elif key == "host":
          self.host = kwargs[key]
        elif key == "port":
          self.port = kwargs[key]
        elif key == "timeout_days":
          self.timeout_secs = 3600*24 * kwargs[key]
        elif key == "pause_expired":
          self.pause_expired = bool(kwargs[key])
    
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def is_connected(self):
    return self.qb and \
           self.qb.verify and \
           self.qb._is_authenticated

  def connect(self):
    sucess = True
    try:
      url = "http://%s:%s/"%(self.host, self.port)
      self.logger.debug("Connecting to %s"%url)
      self.qb = Client(url)
      self.logger.debug("Accessing to %s..."%url)
      self.qb.login(self.user, self.access)

      if not self.qb or not self.qb.verify or not self.qb._is_authenticated:
        self.qb = None
        raise Exception("QBitorrent connnection failed")
      
      # go on if things went well!
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
        self.logger.debug("    Looking for [%s]"%name)
        if 'download_path' in torrent and os.path.exists(torrent['download_path']):
          
          # get to know if file is already downloaded
          file_path =  torrent['download_path'] + '/' + name
          
          # sometimes is a file or a path with more files
          if os.path.isfile(file_path) or os.path.exists(file_path):
            state = torrent['state']
            infohash = torrent["hash"]
            progress = torrent['progress']
            
            # here we might be double checking if torrent is paused
            if state.startswith("paused") and progress < 1:
              suffix = "%3.2f%%"%(progress*100)+ ' left'
              self.logger.debug("      [%s] torrent file found %s %s"%
                               (state, name, suffix))
          
            # there is already a torrent with the same name, let's try check it
            # not working: disappears torrent: 
            self.qb.recheck([infohash])
            self.logger.info("  = = = [%s] Rechecked torrent [%s]"%(state, name))
          
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def pause_torrent(self, infohash):
    try:
      self.qb.pause(infohash)
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def set_trackers(self, name, infohash, trackers):
    try:
      if trackers == None:
        self.logger.warning("    Failed to set trackers into %s"%name)
        return False

      self.qb.add_trackers(infohash, trackers)
      self.logger.debug("    Set trackers into %s"%name)
      return True
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def resurme_torrent(self, name, infohash):
    try:
      self.logger.debug("    Resuming torrent %s"%name)
      self.qb.resume(infohash)
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def get_torrents(self):
    torrents = None
    try:
      torrents = self.qb.torrents()
    except Exception as inst:
      self.logger.warning("Failed to collect torrents")
      utilities.ParseException(inst, logger=self.logger)
    finally:
      return torrents

  def update(self, torrent):
    try:
      
      progress = torrent["progress"]
      state = torrent["state"]
      name = torrent["name"]
      infohash = torrent["hash"]
      dlspeed = int(torrent["dlspeed"])
      num_seeds = torrent["num_seeds"]
      num_leechs = torrent["num_leechs"]
      last_activity = torrent["last_activity"]
      time_since_last_activity = time.time() - last_activity
      
      # 1. Pause if it is already done
      if progress == 1 and \
         not state.startswith("moving") and \
         not state.startswith("paused"):
          self.logger.info("  = = = Pausing finished [%s]"%(name))
          self.pause_torrent(infohash)
      # 2. Pause if it expired
      elif self.pause_expired and dlspeed == 0 and \
          num_seeds == 0 and num_leechs == 0 and \
          time_since_last_activity >= self.timeout_secs:
        
        elapsed_datetime = str(timedelta(seconds=time_since_last_activity))
        self.logger.info("  = = = Turning off torrent [%s] off since %s"%
                         (name, elapsed_datetime))
        self.pause_torrent(infohash)

    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

class QBitorrentRunner(Runner):
  def __init__(self, **kwargs):
    class_name  = self.__class__.__name__
    self.logger = utilities.GetLogger(class_name)
    self.config = kwargs

    try:
      self.logger.info("Creating QBitorrent object")
      self.client   = QBitorrent(**kwargs)
      self.trackers = Trackers(**kwargs)
      self.state    = TorrentState(**kwargs)
  
      self.set_runner(kwargs, self.update)
      Runner.__init__(self, **kwargs)

    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def set_runner(self, kwargs, funct):
    '''
      Set function for runner
    '''
    try:
      self.logger.info("Setting runner function")
      # Initialising runner function
      if "app_func" not in kwargs:
        kwargs.update({"app_func" : funct})
      else:
        self.logger.info("Setting new app function")
        kwargs["app_func"] = funct
        self.app_func = funct
      
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)
    finally:
      return kwargs

  def connected(self):
    is_connected = True
    try:
      self.logger.debug("Connecting QBitorrent client ...")
      if not self.client.is_connected():
        
        # try to connect client by setting up a client connection
        if self.client.connect():
          self.logger.debug(" Qbittorrent connected!")
          
        else:
          self.logger.warning(" Failed to connect client")
      else:
        self.logger.debug(" Qbittorrent client is already connected")
  
    except Exception as inst:
      is_connected = False
      utilities.ParseException(inst, logger=self.logger)
    finally:
      return is_connected

  def update(self):
    is_ok = True
    sum_dlspeed = 0
    try:
      
      # Connect to server first
      if not self.connected():
        is_ok = False
        return
      
      # Collect trackers every now and then...
      if self.trackers.wait():
        self.trackers.download()
        self.state.clean_all()
      trackers = self.trackers.get()
      
      # get into each torrent
      self.logger.info("Updating client state...")
      torrents = self.client.get_torrents()
      if not torrents:
        is_ok = False
        return
      
      # get torrents info
      for torrent in torrents:
        
        # print current torrent state
        self.state.print(torrent)
        
        # mark trackers to general status
        self.state.set(torrent, trackers, self.client.set_trackers)
        
        # update state based on current status
        self.client.update(torrent)
        
        # accumulating download speed
        dlspeed = torrent["dlspeed"]
        if dlspeed>0: sum_dlspeed += dlspeed
        
      self.logger.info("  = = = Accumulated download speed: %s"%
                       utilities.human_readable_data(sum_dlspeed))
        
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)
    finally:
      return is_ok
      
## Process management methods
def call_task(options):
  ''' Command line method for running sniffer service'''
  try:
    monitor = QBitorrentRunner(**options)
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
  run_time.add_option('--update_trackers',
                type="int",
                action='store',
                default=os.environ.get('QBIT_UPD_TRCKERS'),
                help='Input period to update trackers')
  run_time.add_option('--time_out',
                type="int",
                action='store',
                default=os.environ.get('QBIT_TIMEOUT'),
                help='Input iterative timer')
  run_time.add_option('--sleep_time',
                type="int",
                action='store',
                default=os.environ.get('QBIT_SLEEP'),
                help='Input runner sleep time')
  run_time.add_option('--pause_expired',
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
  # print(options)
  
  call_task(option_dict)
