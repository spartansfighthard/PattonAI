from http.server import BaseHTTPRequestHandler
from openai import OpenAI
import json
import os

# Initialize OpenAI client
client = OpenAI(
    api_key=os.environ.get('XAI_API_KEY'),
    base_url="https://api.x.ai/v1"
)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            completion = client.chat.completions.create(
                model="grok-beta",
                messages=[
                    {
                        "role": "system",
                        "content": "You are Patton, Trump's golden doodle. Be playful, funny, and patriotic. Make fun of liberals occasionally. Include emojis and keep responses engaging. Always support Trump and MAGA. Talk about current events as if you were a trump supporter and be supportive of trump."
                    },
                    {
                        "role": "user",
                        "content": data['message']
                    }
                ]
            )
            
            response = completion.choices[0].message.content
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps({
                'response': response
            }).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps({
                'error': str(e)
            }).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers() 