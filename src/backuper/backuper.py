import subprocess
import utilities
import logging
import pathlib
import shutil
from optparse import OptionParser, OptionGroup
from pprint import pprint

LOG_NAME = "Backup"

class Backuper:
    def __init__(self) -> None:
        class_name  = self.__class__.__name__
        self.logger = utilities.GetLogger(class_name)
        self.patterns = {
            'size': 'files to consider',
            'copying': [
                'sending incremental file list',
                'created directory'
            ],
            'parsing': False,
            'ignore': [
                './',
                'bytes/sec',
                'sending incremental file list'
            ],
            'next': ['to-check', 'to-chk'],
            'previous':None,
            'counter': 1,
            'end': 'total size is'
        }
        
        self.backup = []
        
    def parse_outout(self, stdout_line):
        try:
            line_size = len(stdout_line)
            if line_size <1:
                return stdout_line
            
            # print(f'====[{line_size}] {stdout_line}')
            list_start = [True if token in stdout_line else False 
                            for token in self.patterns['copying']]
                
            if self.patterns['parsing']:
                # find tokens that should be ignored 
                list_ignore = [True if token in stdout_line else False 
                               for token in self.patterns['ignore']]
                # print('0**** list_ignore: %s'%str(list_ignore))
                # print('0**** ignore? %s'%str(any(list_ignore)))
                if any(list_ignore):
                    # print("1**** ignore: %s"%stdout_line)
                    pass
                elif self.patterns['end'] in stdout_line:
                    self.patterns['previous'] = None
                    self.patterns['parsing'] = False
                    # print('2**** ending')
                    pass
                # the directory structure is shown in a nested way until it gets a file
                elif self.patterns['previous'] is None or self.patterns['previous'] in stdout_line:
                    self.patterns['previous'] = stdout_line
                    # print("3**** keep: %s"%self.patterns['previous'])
                else:
                    # this line has the progress percentage and transmission rat
                    progress = stdout_line.split()
                    
                    # after this line another file will start copying
                    # print("4**** previous: %s"%self.patterns['previous'])
                    # print("4**** progress: %s"%progress)
                    # print('4**** counter: %s'%self.patterns['counter'])
                    # print('4**** previous: %s'%self.patterns['previous'])
                    # print('4**** progress: %s'%str(progress))
                    self.logger.info('[%d] %s: %s'%(self.patterns['counter'], 
                                                    self.patterns['previous'], 
                                                    progress[1]))
                    
                    # find tokens that should say we are going next file
                    list_next = [True if token in stdout_line else False 
                                 for token in self.patterns['next']]
                    if any(list_next):
                        # Store path to copied file
                        self.backup.append(self.patterns['previous'])
                        
                        # Keep score of copied file
                        self.patterns['previous'] = None
                        self.patterns['counter'] += 1
                        
            elif self.patterns['size'] in stdout_line:
                file_count= stdout_line[0:stdout_line.index(self.patterns['size'])].split()[0]
                self.logger.debug(f"* Found {file_count} files")
            elif any(list_start): #self.patterns['copying'] in stdout_line:
                self.patterns['parsing'] = True
                self.logger.debug(f"* Parsing output...")
            else:
                print(f"=> {stdout_line}".strip())
        except Exception as inst:
            utilities.ParseException(inst)
            
    def execute(self, cmd):
        stdout_line = None
        try:
            popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
            for stdout_line in iter(popen.stdout.readline, ""):
                self.parse_outout(stdout_line.strip())
            popen.stdout.close()
            return_code = popen.wait()
            if return_code:
                raise subprocess.CalledProcessError(return_code, cmd)
        except Exception as inst:
            utilities.ParseException(inst)
        finally:
            return stdout_line

    def copy_files(self, source, destination):
        command = ["rsync", "-rP", "--remove-source-files", source, destination]
        try:
            for path in self.execute(command):
                # print(path, end="")
                pass
        except Exception as inst:
            utilities.ParseException(inst)
   
    def remove_source(self, source, dry_run = True):
        
        # check of files are still in source path
        source_path = pathlib.Path(source)
        files_in_source = [item for item in source_path.rglob("*") if item.is_file()]
        count_files  = len(files_in_source)
        if count_files > 0:
            self.logger.warning(f"There are {count_files} in {source}")
            self.logger.warning("%s"%str(files_in_source))
            return False
        
        # remove directory
        self.logger.info(f"Removing path and contents of {source}")
        if dry_run: shutil.rmtree(source)
        
    def move_files(self, source, destination, dry_run = True):
        # start by copying files to destination
        self.copy_files(source, destination)
        
        # confirm files are copied
        self.remove_source(source, dry_run)
        
if __name__ == '__main__':
    # create logger
    logFormatter="'%(asctime)s|%(levelname)7s|%(name)25s|%(message)s'"
    logging.basicConfig(format=logFormatter, level=logging.DEBUG)
    logger = utilities.GetLogger(LOG_NAME)
    logger.debug('Logger created.')
    
    usage       = "usage: %prog source=string dest=bool"
    parser      = OptionParser(usage=usage)
    app_opts = OptionGroup(parser, "Runtime options")
    app_opts.add_option('--source',
                    type="string",
                    action='store')
    app_opts.add_option('--dest',
                    type="string",
                    action='store')
    app_opts.add_option("--dry_run", 
                        action="store_true", 
                        default=False,
                        help="Dry run option")
    
    parser.add_option_group(app_opts)
    (options, args) = parser.parse_args()
    # print(options)
# if False:
    if not options.source:
        parser.error("source path is required")
        
    if not options.dest:
        parser.error("dest path is required")
    
    backuper = Backuper()
    backuper.move_files(options.source, 
                        options.dest, 
                        dry_run = options.dry_run)

# /series/cartoons/drive2/original_files
# /series/cartoons/drive3/original_files

# curl -X POST \
#      -H "Content-Type: application/json" \
#      -d '{"source": "/series/cartoons/drive3/original_files", "dest": "/series/cartoons/drive2", "dry_run": "Fale"}' \
#          http://127.0.0.1:5001/stream_monitor/backuper

# rm -rf /series/cartoons/drive3/original_files; python backuper.py --source /series/cartoons/drive2/original_files --dest /series/cartoons/drive3
# rm -rf /series/cartoons/drive3/original_files; rsync -rP --remove-source-files /series/cartoons/drive2/original_files /series/cartoons/drive3

# rm -rf /series/cartoons/drive2/original_files; python backuper.py --source /series/cartoons/drive3/original_files --dest /series/cartoons/drive2