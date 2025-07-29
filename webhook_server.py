#!/usr/bin/env python3
"""
簡化的 LINE Bot webhook 服務器
專門用於解決連接問題
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging
from urllib.parse import urlparse
from name_card_processor import NameCardProcessor  
from notion_manager import NotionManager
from config import Config

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化處理器
try:
    Config.validate_config()
    card_processor = NameCardProcessor()
    notion_manager = NotionManager()
    logger.info("✅ 所有處理器初始化成功")
except Exception as e:
    logger.error(f"❌ 初始化失敗: {e}")
    exit(1)

class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """處理 GET 請求"""
        path = urlparse(self.path).path
        
        if path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "healthy", "message": "LINE Bot webhook server running"}
            self.wfile.write(json.dumps(response).encode())
            
        elif path == '/callback':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers() 
            response = {"message": "Webhook endpoint ready", "method": "POST required"}
            self.wfile.write(json.dumps(response).encode())
            
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def do_POST(self):
        """處理 POST 請求"""
        path = urlparse(self.path).path
        
        if path == '/callback':
            logger.info("📥 收到 POST 請求到 /callback")
            
            # 檢查 X-Line-Signature header
            signature = self.headers.get('X-Line-Signature')
            if not signature:
                logger.warning("❌ 缺少 X-Line-Signature header")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Missing X-Line-Signature header')
                return
            
            # 讀取請求體
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            logger.info(f"📄 收到請求體長度: {content_length}")
            
            try:
                # 解析 JSON
                webhook_data = json.loads(post_data.decode())
                logger.info(f"📋 Webhook 數據: {webhook_data}")
                
                # 模擬成功處理
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'OK')
                
                logger.info("✅ Webhook 處理成功")
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON 解析錯誤: {e}")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Invalid JSON')
                
            except Exception as e:
                logger.error(f"❌ 處理錯誤: {e}")
                self.send_response(500)
                self.end_headers()  
                self.wfile.write(b'Internal Server Error')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        """自定義日誌格式"""
        logger.info(f"{self.address_string()} - {format % args}")

def main():
    """啟動服務器"""
    port = 9000
    server_address = ('', port)
    
    httpd = HTTPServer(server_address, WebhookHandler)
    
    logger.info(f"🚀 Webhook 服務器啟動在 port {port}")
    logger.info(f"📋 健康檢查: http://localhost:{port}/health")
    logger.info(f"🔗 Webhook 端點: http://localhost:{port}/callback")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("🛑 服務器停止")
        httpd.server_close()

if __name__ == "__main__":
    main()