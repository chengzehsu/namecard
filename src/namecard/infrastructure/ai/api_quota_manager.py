"""
智能 API 配額管理器 - AI Engineer 實作
管理多個 API Keys 的配額、速率限制和負載均衡
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
import aiofiles

from config import Config


class ApiKeyStatus(Enum):
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class ApiKeyMetrics:
    """API Key 使用指標"""
    key_id: str
    key_masked: str  # 遮罩後的 Key (前6後4字元)
    status: ApiKeyStatus = ApiKeyStatus.ACTIVE
    
    # 配額管理
    daily_quota: int = 1000
    used_today: int = 0
    quota_reset_time: Optional[datetime] = None
    
    # 速率限制
    requests_per_minute: int = 60
    requests_this_minute: int = 0
    minute_reset_time: Optional[datetime] = None
    
    # 效能指標
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_used: Optional[datetime] = None
    
    # 錯誤追蹤
    consecutive_errors: int = 0
    last_error: Optional[str] = None
    error_history: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.quota_reset_time is None:
            # 設定為明日午夜重置
            tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            self.quota_reset_time = tomorrow + timedelta(days=1)
        
        if self.minute_reset_time is None:
            # 設定為下一分鐘重置
            next_minute = datetime.now().replace(second=0, microsecond=0)
            self.minute_reset_time = next_minute + timedelta(minutes=1)


class ApiQuotaManager:
    """API 配額智能管理器"""

    def __init__(self, persistence_file: str = "api_quota_stats.json"):
        """
        初始化配額管理器
        
        Args:
            persistence_file: 統計資料持久化檔案
        """
        self.persistence_file = persistence_file
        self.api_keys = []
        self.metrics: Dict[str, ApiKeyMetrics] = {}
        
        # 初始化 API Keys
        self._initialize_api_keys()
        
        # 背景任務
        self._background_tasks = []
        self._start_background_tasks()
        
        print(f"✅ API 配額管理器初始化完成")
        print(f"   - 管理 API Keys: {len(self.api_keys)}")
        print(f"   - 持久化檔案: {persistence_file}")

    def _initialize_api_keys(self):
        """初始化 API Keys 和指標"""
        keys = [Config.GOOGLE_API_KEY, Config.GOOGLE_API_KEY_FALLBACK]
        keys = [key for key in keys if key and key.strip()]
        
        for i, key in enumerate(keys):
            key_id = f"key_{i}"
            masked_key = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else "***masked***"
            
            self.api_keys.append(key)
            self.metrics[key_id] = ApiKeyMetrics(
                key_id=key_id,
                key_masked=masked_key
            )
        
        # 載入持久化資料
        asyncio.create_task(self._load_persisted_metrics())

    async def get_best_api_key(self) -> Tuple[Optional[str], Optional[str]]:
        """
        獲取當前最佳的 API Key
        
        Returns:
            Tuple[api_key, key_id] 或 (None, None) 如果沒有可用的
        """
        now = datetime.now()
        best_key_id = None
        best_score = -1
        
        for key_id, metrics in self.metrics.items():
            # 跳過停用或有問題的 Keys
            if metrics.status in [ApiKeyStatus.DISABLED, ApiKeyStatus.ERROR]:
                continue
            
            # 檢查配額重置
            if metrics.quota_reset_time and now >= metrics.quota_reset_time:
                metrics.used_today = 0
                metrics.quota_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                if metrics.status == ApiKeyStatus.QUOTA_EXCEEDED:
                    metrics.status = ApiKeyStatus.ACTIVE
            
            # 檢查速率限制重置
            if metrics.minute_reset_time and now >= metrics.minute_reset_time:
                metrics.requests_this_minute = 0
                metrics.minute_reset_time = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
                if metrics.status == ApiKeyStatus.RATE_LIMITED:
                    metrics.status = ApiKeyStatus.ACTIVE
            
            # 檢查是否可用
            if metrics.status != ApiKeyStatus.ACTIVE:
                continue
            
            if metrics.used_today >= metrics.daily_quota:
                metrics.status = ApiKeyStatus.QUOTA_EXCEEDED
                continue
            
            if metrics.requests_this_minute >= metrics.requests_per_minute:
                metrics.status = ApiKeyStatus.RATE_LIMITED
                continue
            
            # 計算評分（考慮效能和使用量）
            quota_ratio = metrics.used_today / metrics.daily_quota
            success_rate = (
                metrics.successful_requests / max(metrics.total_requests, 1)
                if metrics.total_requests > 0 else 1.0
            )
            
            # 評分公式：成功率權重最高，然後是剩餘配額
            score = (success_rate * 0.7) + ((1 - quota_ratio) * 0.3)
            
            # 懲罰連續錯誤
            if metrics.consecutive_errors > 0:
                score *= (0.9 ** metrics.consecutive_errors)
            
            if score > best_score:
                best_score = score
                best_key_id = key_id
        
        if best_key_id is None:
            return None, None
        
        key_index = int(best_key_id.split('_')[1])
        return self.api_keys[key_index], best_key_id

    async def record_api_usage(
        self, 
        key_id: str, 
        success: bool, 
        response_time: float, 
        error_message: Optional[str] = None
    ):
        """
        記錄 API 使用情況
        
        Args:
            key_id: API Key ID
            success: 是否成功
            response_time: 回應時間（秒）
            error_message: 錯誤訊息（如果有）
        """
        if key_id not in self.metrics:
            return
        
        metrics = self.metrics[key_id]
        now = datetime.now()
        
        # 更新使用統計
        metrics.total_requests += 1
        metrics.used_today += 1
        metrics.requests_this_minute += 1
        metrics.last_used = now
        
        if success:
            metrics.successful_requests += 1
            metrics.consecutive_errors = 0
            
            # 更新平均回應時間
            total_successful = metrics.successful_requests
            current_avg = metrics.average_response_time
            metrics.average_response_time = (
                (current_avg * (total_successful - 1) + response_time) / total_successful
            )
        else:
            metrics.failed_requests += 1
            metrics.consecutive_errors += 1
            metrics.last_error = error_message or "Unknown error"
            
            # 記錄錯誤歷史（保留最近10個）
            metrics.error_history.append(f"{now.isoformat()}: {error_message}")
            if len(metrics.error_history) > 10:
                metrics.error_history.pop(0)
            
            # 根據錯誤類型更新狀態
            if error_message:
                error_lower = error_message.lower()
                if any(keyword in error_lower for keyword in [
                    'quota', 'limit exceeded', 'resource exhausted', 'billing'
                ]):
                    metrics.status = ApiKeyStatus.QUOTA_EXCEEDED
                elif 'rate limit' in error_lower or '429' in error_lower:
                    metrics.status = ApiKeyStatus.RATE_LIMITED
                elif metrics.consecutive_errors >= 3:
                    metrics.status = ApiKeyStatus.ERROR
        
        # 持久化更新
        await self._save_metrics()

    async def get_quota_status(self) -> Dict[str, any]:
        """獲取所有 API Keys 的配額狀態"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'total_api_keys': len(self.api_keys),
            'keys': {}
        }
        
        available_keys = 0
        total_quota_used = 0
        total_requests = 0
        
        for key_id, metrics in self.metrics.items():
            key_status = {
                'key_masked': metrics.key_masked,
                'status': metrics.status.value,
                'quota': {
                    'daily_limit': metrics.daily_quota,
                    'used_today': metrics.used_today,
                    'remaining': metrics.daily_quota - metrics.used_today,
                    'usage_percentage': (metrics.used_today / metrics.daily_quota) * 100,
                    'reset_time': metrics.quota_reset_time.isoformat() if metrics.quota_reset_time else None
                },
                'rate_limit': {
                    'requests_per_minute': metrics.requests_per_minute,
                    'used_this_minute': metrics.requests_this_minute,
                    'remaining_this_minute': metrics.requests_per_minute - metrics.requests_this_minute
                },
                'performance': {
                    'total_requests': metrics.total_requests,
                    'success_rate': (
                        (metrics.successful_requests / metrics.total_requests * 100)
                        if metrics.total_requests > 0 else 0
                    ),
                    'average_response_time': metrics.average_response_time,
                    'consecutive_errors': metrics.consecutive_errors,
                    'last_used': metrics.last_used.isoformat() if metrics.last_used else None
                }
            }
            
            status['keys'][key_id] = key_status
            
            if metrics.status == ApiKeyStatus.ACTIVE:
                available_keys += 1
            
            total_quota_used += metrics.used_today
            total_requests += metrics.total_requests
        
        status['summary'] = {
            'available_keys': available_keys,
            'total_quota_used': total_quota_used,
            'total_requests': total_requests,
            'system_health': 'healthy' if available_keys > 0 else 'degraded'
        }
        
        return status

    async def predict_quota_exhaustion(self) -> Dict[str, any]:
        """預測配額耗盡時間"""
        predictions = {}
        
        for key_id, metrics in self.metrics.items():
            if metrics.total_requests == 0:
                continue
            
            # 計算使用率趨勢
            hours_since_midnight = (datetime.now() - datetime.now().replace(hour=0, minute=0, second=0)).total_seconds() / 3600
            
            if hours_since_midnight > 0:
                hourly_usage_rate = metrics.used_today / hours_since_midnight
                remaining_quota = metrics.daily_quota - metrics.used_today
                
                if hourly_usage_rate > 0:
                    hours_until_exhaustion = remaining_quota / hourly_usage_rate
                    exhaustion_time = datetime.now() + timedelta(hours=hours_until_exhaustion)
                    
                    predictions[key_id] = {
                        'key_masked': metrics.key_masked,
                        'hourly_usage_rate': round(hourly_usage_rate, 2),
                        'remaining_quota': remaining_quota,
                        'predicted_exhaustion': exhaustion_time.isoformat(),
                        'hours_until_exhaustion': round(hours_until_exhaustion, 2),
                        'risk_level': self._calculate_risk_level(hours_until_exhaustion)
                    }
        
        return predictions

    def _calculate_risk_level(self, hours_until_exhaustion: float) -> str:
        """計算風險等級"""
        if hours_until_exhaustion < 2:
            return 'critical'
        elif hours_until_exhaustion < 6:
            return 'high'
        elif hours_until_exhaustion < 12:
            return 'medium'
        else:
            return 'low'

    async def _save_metrics(self):
        """持久化指標資料"""
        try:
            data = {}
            for key_id, metrics in self.metrics.items():
                data[key_id] = {
                    'key_masked': metrics.key_masked,
                    'status': metrics.status.value,
                    'daily_quota': metrics.daily_quota,
                    'used_today': metrics.used_today,
                    'total_requests': metrics.total_requests,
                    'successful_requests': metrics.successful_requests,
                    'failed_requests': metrics.failed_requests,
                    'average_response_time': metrics.average_response_time,
                    'consecutive_errors': metrics.consecutive_errors,
                    'last_error': metrics.last_error,
                    'error_history': metrics.error_history[-5:],  # 只儲存最近5個錯誤
                    'last_used': metrics.last_used.isoformat() if metrics.last_used else None,
                    'quota_reset_time': metrics.quota_reset_time.isoformat() if metrics.quota_reset_time else None
                }
            
            async with aiofiles.open(self.persistence_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))
                
        except Exception as e:
            print(f"⚠️ 儲存指標資料失敗: {e}")

    async def _load_persisted_metrics(self):
        """載入持久化的指標資料"""
        try:
            async with aiofiles.open(self.persistence_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
            
            for key_id, saved_data in data.items():
                if key_id in self.metrics:
                    metrics = self.metrics[key_id]
                    
                    # 恢復資料（只恢復累計統計，狀態重新計算）
                    metrics.daily_quota = saved_data.get('daily_quota', 1000)
                    metrics.used_today = saved_data.get('used_today', 0)
                    metrics.total_requests = saved_data.get('total_requests', 0)
                    metrics.successful_requests = saved_data.get('successful_requests', 0)
                    metrics.failed_requests = saved_data.get('failed_requests', 0)
                    metrics.average_response_time = saved_data.get('average_response_time', 0.0)
                    metrics.consecutive_errors = saved_data.get('consecutive_errors', 0)
                    metrics.last_error = saved_data.get('last_error')
                    metrics.error_history = saved_data.get('error_history', [])
                    
                    # 恢復時間資料
                    if saved_data.get('last_used'):
                        metrics.last_used = datetime.fromisoformat(saved_data['last_used'])
                    if saved_data.get('quota_reset_time'):
                        metrics.quota_reset_time = datetime.fromisoformat(saved_data['quota_reset_time'])
            
            print(f"✅ 載入持久化指標資料成功")
            
        except FileNotFoundError:
            print(f"📝 首次執行，建立新的指標追蹤")
        except Exception as e:
            print(f"⚠️ 載入持久化資料失敗: {e}")

    def _start_background_tasks(self):
        """啟動背景任務"""
        # 定期清理和重置任務
        async def cleanup_task():
            while True:
                try:
                    await asyncio.sleep(300)  # 每5分鐘執行一次
                    await self._cleanup_and_reset()
                except Exception as e:
                    print(f"⚠️ 背景清理任務錯誤: {e}")
        
        # 定期儲存任務
        async def save_task():
            while True:
                try:
                    await asyncio.sleep(60)  # 每分鐘儲存一次
                    await self._save_metrics()
                except Exception as e:
                    print(f"⚠️ 背景儲存任務錯誤: {e}")
        
        # 不直接啟動，讓呼叫者決定
        self._background_tasks = [cleanup_task, save_task]

    async def start_background_monitoring(self):
        """啟動背景監控任務"""
        tasks = [asyncio.create_task(task()) for task in self._background_tasks]
        return tasks

    async def _cleanup_and_reset(self):
        """清理和重置過期資料"""
        now = datetime.now()
        
        for metrics in self.metrics.values():
            # 重置每日配額
            if metrics.quota_reset_time and now >= metrics.quota_reset_time:
                metrics.used_today = 0
                metrics.quota_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                if metrics.status == ApiKeyStatus.QUOTA_EXCEEDED:
                    metrics.status = ApiKeyStatus.ACTIVE
                    print(f"🔄 {metrics.key_masked} 每日配額已重置")
            
            # 重置每分鐘速率限制
            if metrics.minute_reset_time and now >= metrics.minute_reset_time:
                metrics.requests_this_minute = 0
                metrics.minute_reset_time = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
                if metrics.status == ApiKeyStatus.RATE_LIMITED:
                    metrics.status = ApiKeyStatus.ACTIVE
            
            # 重置連續錯誤狀態（超過1小時未使用）
            if (metrics.last_used and 
                now - metrics.last_used > timedelta(hours=1) and 
                metrics.status == ApiKeyStatus.ERROR):
                metrics.status = ApiKeyStatus.ACTIVE
                metrics.consecutive_errors = 0
                print(f"🔄 {metrics.key_masked} 錯誤狀態已重置")