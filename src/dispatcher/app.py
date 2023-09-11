import asyncio
from flask import Flask, request, jsonify

app = Flask(__name__)

class MonitorEndpoint:
    def __init__(self):
        pass

    async def async_function(self, data):
        # Simulate an asynchronous task (e.g., fetching data from a database)
        print("---")
        print(data)
        # await asyncio.sleep(2)
        return f"status: ok"

    @app.route('/series', methods=['POST'])
    async def series():
        try:
            data = request.json
            if not data:
                return jsonify({'error': 'Data parameter is required for series'}), 400
            
            async_task = MonitorEndpoint().async_function(data)
            result = await async_task
            return jsonify({'series': result})

        except Exception as e:
            return jsonify({'error': str(e)}), 500
        
    @app.route('/movies', methods=['POST'])
    async def movies():
        try:
            data = request.json
            if not data:
                return jsonify({'error': 'Data parameter is required for movies'}), 400
            
            async_task = MonitorEndpoint().async_function(data)
            result = await async_task
            return jsonify({'movies': result})

        except Exception as e:
            return jsonify({'error': str(e)}), 500
        
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555)