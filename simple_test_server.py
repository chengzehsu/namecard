#!/usr/bin/env python3
"""
簡單的測試服務器，用於驗證 ngrok 連接
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """處理 GET 請求"""
        logger.info(f"GET {self.path}")
        
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {"status": "healthy", "message": "Simple test server running"}
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == '/callback':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {"message": "Callback endpoint ready for POST"}
            self.wfile.write(json.dumps(response).encode())
            
        else:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {"message": "Test server", "path": self.path}
            self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        """處理 POST 請求"""
        logger.info(f"POST {self.path}")
        
        if self.path == '/callback':
            # 讀取請求體
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b''
            
            logger.info(f"Headers: {dict(self.headers)}")
            logger.info(f"Body length: {content_length}")
            logger.info(f"Body: {post_data.decode('utf-8')[:200]}...")
            
            # 返回成功回應
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'OK')
            
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        """自定義日誌格式"""
        logger.info(f"{self.client_address[0]} - {format % args}")

def main():
    """啟動測試服務器"""
    port = 6000
    server_address = ('', port)
    
    httpd = HTTPServer(server_address, TestHandler)
    
    logger.info(f"🚀 簡單測試服務器啟動在 port {port}")
    logger.info(f"📋 測試 URL: http://localhost:{port}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("🛑 服務器停止")
        httpd.server_close()

if __name__ == "__main__":
    main()