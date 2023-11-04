#!/usr/bin/env python
# -*- coding: latin-1 -*-

TIMEOUT = 300  # maximum seconds
SLEEP_TIME = 5

import multiprocessing
import utilities
import time
import sys

from pprint import pprint
from signal import signal
from signal import SIGTERM, SIGINT
  
class Runner(multiprocessing.Process):
  def __init__(self, **kwargs):
    try:

      self.logger.debug("Starting runner")
      
      # Initialising class variables
      self.component    = self.__class__.__name__
      self.logger       = utilities.GetLogger("Runner")
      self.app_func     = None
      self.time_out     = None
      self.sleep_time   = SLEEP_TIME
      self.stop_running = False

      multiprocessing.Process.__init__(self)
      self.logger.debug("  Started runner process")

      # handle sigterm
      signal(SIGTERM,self.signal_handler)
      signal(SIGINT, self.signal_handler)

      for key in kwargs.keys():
        # print("--- key: %s"%key)
        if key == "app_func":
          self.app_func   = kwargs[key]
        elif key == "time_out":
          self.time_out = kwargs[key]
          self.logger.debug("  Set timeout to %ds"%self.time_out)
        elif key == "sleep_time":
          self.sleep_time = kwargs[key]
          self.logger.debug("  Set sleep time to %ds"%self.sleep_time)

      self.start()
      self.logger.debug("  Created runner object")
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def timeout(self, wakeup):
    try:
      while time.time() - self.start_time < self.time_out and \
            not self.stop_running:
        time.sleep(self.sleep_time)
      self.logger.debug("  Executed runner's time out")
    
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def signal_handler(self, signum, frame):
    # self.logger.debug("Signal Number:", signum, " Frame: ", frame) 
    self.logger.info("  Handling runner signal")
    self.logger.debug("  Stop running app")
    self.stop_running = True

  def run(self):
    '''
      Required to implement this method 
      manager.Manager (multiprocessing.Process)
      
    '''
    try:
      self.logger.debug("  Running process")
      while not self.stop_running:
        self.logger.debug("  Looping process: [stop_running=%s]"%str(self.stop_running))
       
        # configured method from app
        self.start_time = time.time()
        ok = self.app_func()

        if not ok:
          self.logger.debug("  App function failed to execute, sleeping %d"%self.sleep_time)
          time.sleep(self.sleep_time)
        else:
          # sleep process for some time
          # self.logger.debug("  Timing out app function...")
          self.timeout(self.wakeup)

      self.logger.info("Runner has been ended")
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)
    finally:
      sys.exit(1)

  def wakeup(self):
    try:
      if self.stop_running:
        self.stop_running = True
        self.logger.info("  Stopping runner")
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)
      