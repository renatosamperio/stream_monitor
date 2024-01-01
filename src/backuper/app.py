import logging
import utilities

from flask import Flask, request, jsonify
from pprint import pprint
from backuper import Backuper

app = Flask(__name__)
service = Backuper()

@app.route('/stream_monitor/backuper', methods=['POST'])
def stream_monitor_backuper():
    
    data = request.get_json()
    if "dest" in data and "source" in data:
        
        service.move_files(data["source"], 
                           data["dest"], 
                           dry_run = data['dry_run'] if 'dry_run' in data else None)
        return jsonify({'message': 'ok'})
    else:
        return jsonify({'error': 'Message missing source or dest'}), 404

if __name__ == '__main__':
    logFormatter="'%(asctime)s|%(levelname)7s|%(name)25s|%(message)s'"
    logging.basicConfig(format=logFormatter, level=logging.DEBUG)
    logger = utilities.GetLogger('backuper_app')
    logger.debug('Logger created.')
    app.run(host="0.0.0.0", port=5001, debug=True)
