#!/usr/bin/env python
# -*- coding: latin-1 -*-

TIMEOUT = 300  # maximum seconds
SLEEP_TIME = 5

import multiprocessing
import utilities
import time

from pprint import pprint
from signal import signal
from signal import SIGTERM, SIGINT

class Runner(multiprocessing.Process):
  def __init__(self, **kwargs):
    try:

      # Initialising class variables
      self.component    = self.__class__.__name__
      self.logger       = utilities.GetLogger(self.component)
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
        #print("--- sleep_time: %s"%key)
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
    t = 0
    try:
      while time.time() - self.start_time < self.time_out and not self.stop_running:
        time.sleep(self.sleep_time)
      
      # self.wakeup()
      self.logger.debug("  Executed runner timer")
    
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def signal_handler(self, sig):
    self.logger.info("  Handling runner signal")
    self.stop_running = True

    # just kill the process
    #import sys
    #sys.exit(0)

  def run(self):
    '''
      Required to implement this method 
      manager.Manager (multiprocessing.Process)
      
    '''
    try:
      self.logger.debug("  Running process")
      while not self.stop_running:
        self.logger.debug("  Looping process")
        # configured method from app
        self.start_time = time.time()
        self.app_func()

        # sleep process for some time
        self.timeout(self.wakeup)

      self.logger.info("Runner has been ended")
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)

  def wakeup(self):
    try:
      if self.stop_running:
        self.stop_running = True
        self.logger.info("  Stopping runner")
    except Exception as inst:
      utilities.ParseException(inst, logger=self.logger)




