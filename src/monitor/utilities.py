#!/usr/bin/env python

import os, sys
import logging
import logging.handlers

def GetLogger(filename, 
              logFormatter="'%(asctime)s|%(levelname)7s|%(name)25s|%(message)s'",
              useFile=False, useConsole=False):
  ''' Returns an instance of logger '''

  logger = logging.getLogger(filename)

  if useConsole:
    handler = logging.StreamHandler()
    #handler.setFormatter(logFormatter)
    formatter = logging.Formatter(logFormatter)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
  if useFile:
    fileHandler = GetFileLogger(filename)
    logger.addHandler(fileHandler)
  return logger
    
def GetFileLogger(filename, fileLength=1000000, numFiles=5):
  ''' Sets up file handler for logger'''
  myFormat = "%(asctime)s|%(process)6d|%(name)25s|%(message)s"
  formatter = logging.Formatter(myFormat)
  fileHandler = logging.handlers.RotatingFileHandler(
                    filename=filename, 
                    maxBytes=fileLength, 
                    backupCount=numFiles)
  fileHandler.setFormatter(formatter)
  return fileHandler

def ParseException(inst, logger=None):
  ''' Takes out useful information from incoming exceptions'''
  exc_type, exc_obj, exc_tb = sys.exc_info()
  exception_fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
  exception_line = str(exc_tb.tb_lineno) 
  exception_type = str(type(inst))
  exception_desc = str(inst)
  if logger:
    logger.debug( "  %s: %s in %s:%s"%(exception_type, 
				    exception_desc, 
				    exception_fname,  
				    exception_line ))
  else:
    print ("  %s: %s in %s:%s"%(exception_type, 
				    exception_desc, 
				    exception_fname,  
				    exception_line ))

def human_readable_data(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"

