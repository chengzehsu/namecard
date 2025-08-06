"""
AI 處理效能監控器 - AI Engineer 實作
監控和分析 AI 處理管線的效能指標
"""

import asyncio
import json
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiofiles

from simple_config import Config


@dataclass
class ProcessingMetrics:
    """單次處理指標"""

    request_id: str
    start_time: float
    end_time: float
    processing_time: float
    api_key_used: str
    image_size_bytes: int
    result_quality: str  # good/partial/poor
    card_count: int
    success: bool
    error_message: Optional[str] = None
    cache_hit: bool = False
    retry_count: int = 0

    @property
    def processing_time_ms(self) -> float:
        return self.processing_time * 1000


@dataclass
class SystemHealth:
    """系統健康狀態"""

    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    active_connections: int
    queue_size: int
    avg_response_time: float
    error_rate: float
    throughput: float  # requests per second


class PerformanceMonitor:
    """AI 處理效能監控器"""

    def __init__(self, max_history_size: int = 10000):
        """
        初始化效能監控器

        Args:
            max_history_size: 最大歷史記錄數量
        """
        self.max_history_size = max_history_size

        # 歷史記錄
        self.processing_history: deque = deque(maxlen=max_history_size)
        self.health_history: deque = deque(maxlen=1000)  # 保留最近1000個健康檢查

        # 實時統計
        self.real_time_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_processing_time": 0.0,
            "cache_hits": 0,
            "current_hour_requests": 0,
            "current_minute_requests": 0,
        }

        # 分時統計
        self.hourly_stats = defaultdict(
            lambda: {"requests": 0, "avg_time": 0.0, "error_rate": 0.0}
        )
        self.minute_stats = deque(maxlen=60)  # 最近60分鐘

        # 效能閾值
        self.performance_thresholds = {
            "max_response_time_ms": 15000,  # 15秒
            "max_error_rate": 0.05,  # 5%
            "max_queue_size": 100,
            "min_success_rate": 0.95,  # 95%
        }

        # 異常檢測
        self.anomaly_detection = {
            "response_time_window": deque(maxlen=100),
            "error_rate_window": deque(maxlen=100),
            "throughput_window": deque(maxlen=60),
        }

        # 啟動背景任務
        self._start_background_monitoring()

        print("✅ AI 效能監控器初始化完成")

    async def record_processing(
        self,
        request_id: str,
        start_time: float,
        end_time: float,
        api_key_used: str,
        image_size_bytes: int,
        result: Dict[str, Any],
        cache_hit: bool = False,
        retry_count: int = 0,
    ):
        """
        記錄處理指標

        Args:
            request_id: 請求 ID
            start_time: 開始時間戳
            end_time: 結束時間戳
            api_key_used: 使用的 API Key
            image_size_bytes: 圖片大小
            result: 處理結果
            cache_hit: 是否命中快取
            retry_count: 重試次數
        """
        processing_time = end_time - start_time
        success = "error" not in result

        metrics = ProcessingMetrics(
            request_id=request_id,
            start_time=start_time,
            end_time=end_time,
            processing_time=processing_time,
            api_key_used=api_key_used,
            image_size_bytes=image_size_bytes,
            result_quality=result.get("overall_quality", "unknown"),
            card_count=result.get("card_count", 0),
            success=success,
            error_message=result.get("error"),
            cache_hit=cache_hit,
            retry_count=retry_count,
        )

        # 加入歷史記錄
        self.processing_history.append(metrics)

        # 更新實時統計
        self._update_real_time_stats(metrics)

        # 異常檢測
        await self._detect_anomalies(metrics)

        # 記錄到檔案（非阻塞）
        asyncio.create_task(self._persist_metrics(metrics))

    def _update_real_time_stats(self, metrics: ProcessingMetrics):
        """更新實時統計"""
        self.real_time_stats["total_requests"] += 1

        if metrics.success:
            self.real_time_stats["successful_requests"] += 1
        else:
            self.real_time_stats["failed_requests"] += 1

        self.real_time_stats["total_processing_time"] += metrics.processing_time

        if metrics.cache_hit:
            self.real_time_stats["cache_hits"] += 1

        # 分時統計
        current_hour = datetime.now().hour
        self.hourly_stats[current_hour]["requests"] += 1

        # 更新每小時平均時間
        hour_stats = self.hourly_stats[current_hour]
        total_requests = hour_stats["requests"]
        current_avg = hour_stats["avg_time"]
        hour_stats["avg_time"] = (
            current_avg * (total_requests - 1) + metrics.processing_time
        ) / total_requests

    async def _detect_anomalies(self, metrics: ProcessingMetrics):
        """檢測異常情況"""
        # 回應時間異常
        self.anomaly_detection["response_time_window"].append(metrics.processing_time)
        if len(self.anomaly_detection["response_time_window"]) >= 10:
            recent_times = list(self.anomaly_detection["response_time_window"])
            avg_time = statistics.mean(recent_times)
            std_dev = statistics.stdev(recent_times) if len(recent_times) > 1 else 0

            # 檢測是否超過 2 個標準差
            if metrics.processing_time > avg_time + (2 * std_dev):
                await self._log_anomaly(
                    "response_time_spike",
                    f"處理時間異常: {metrics.processing_time:.2f}s (平均: {avg_time:.2f}s)",
                )

        # 錯誤率異常
        error_rate = self._calculate_recent_error_rate()
        if error_rate > self.performance_thresholds["max_error_rate"]:
            await self._log_anomaly("high_error_rate", f"錯誤率過高: {error_rate:.2%}")

    async def _log_anomaly(self, anomaly_type: str, message: str):
        """記錄異常"""
        anomaly = {
            "type": anomaly_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "recent_metrics": self._get_recent_summary(),
        }

        print(f"🚨 效能異常檢測: {message}")

        # 可以在這裡添加警報通知邏輯
        # await self._send_alert(anomaly)

    def get_performance_summary(self, time_range_minutes: int = 60) -> Dict[str, Any]:
        """
        獲取效能摘要

        Args:
            time_range_minutes: 時間範圍（分鐘）

        Returns:
            效能摘要
        """
        cutoff_time = time.time() - (time_range_minutes * 60)
        recent_metrics = [
            m for m in self.processing_history if m.start_time > cutoff_time
        ]

        if not recent_metrics:
            return {"message": "No data in specified time range"}

        # 基本統計
        total_requests = len(recent_metrics)
        successful_requests = sum(1 for m in recent_metrics if m.success)
        failed_requests = total_requests - successful_requests

        # 時間統計
        processing_times = [m.processing_time for m in recent_metrics]
        avg_processing_time = statistics.mean(processing_times)
        p95_processing_time = (
            statistics.quantiles(processing_times, n=20)[18]  # 95th percentile
            if len(processing_times) > 10
            else avg_processing_time
        )
        p99_processing_time = (
            statistics.quantiles(processing_times, n=100)[98]  # 99th percentile
            if len(processing_times) > 100
            else avg_processing_time
        )

        # 品質統計
        quality_distribution = defaultdict(int)
        for m in recent_metrics:
            quality_distribution[m.result_quality] += 1

        # 快取統計
        cache_hits = sum(1 for m in recent_metrics if m.cache_hit)
        cache_hit_rate = cache_hits / total_requests if total_requests > 0 else 0

        # API Key 使用分佈
        api_key_usage = defaultdict(int)
        for m in recent_metrics:
            api_key_usage[m.api_key_used] += 1

        # 吞吐量計算
        time_span_hours = time_range_minutes / 60
        throughput_per_hour = (
            total_requests / time_span_hours if time_span_hours > 0 else 0
        )

        return {
            "time_range_minutes": time_range_minutes,
            "summary": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": (
                    successful_requests / total_requests if total_requests > 0 else 0
                ),
                "throughput_per_hour": round(throughput_per_hour, 2),
            },
            "performance": {
                "avg_processing_time_ms": round(avg_processing_time * 1000, 2),
                "p95_processing_time_ms": round(p95_processing_time * 1000, 2),
                "p99_processing_time_ms": round(p99_processing_time * 1000, 2),
                "min_processing_time_ms": round(min(processing_times) * 1000, 2),
                "max_processing_time_ms": round(max(processing_times) * 1000, 2),
            },
            "quality_distribution": dict(quality_distribution),
            "cache_performance": {
                "cache_hits": cache_hits,
                "cache_hit_rate": round(cache_hit_rate, 4),
                "cache_miss_rate": round(1 - cache_hit_rate, 4),
            },
            "api_key_usage": dict(api_key_usage),
            "health_status": self._assess_health_status(recent_metrics),
        }

    def _assess_health_status(
        self, recent_metrics: List[ProcessingMetrics]
    ) -> Dict[str, Any]:
        """評估系統健康狀態"""
        if not recent_metrics:
            return {"status": "unknown", "reason": "No recent data"}

        total_requests = len(recent_metrics)
        successful_requests = sum(1 for m in recent_metrics if m.success)
        success_rate = successful_requests / total_requests

        avg_response_time = statistics.mean(m.processing_time for m in recent_metrics)

        # 健康狀態判斷
        issues = []

        if success_rate < self.performance_thresholds["min_success_rate"]:
            issues.append(f"成功率低: {success_rate:.2%}")

        if avg_response_time > (
            self.performance_thresholds["max_response_time_ms"] / 1000
        ):
            issues.append(f"回應時間過長: {avg_response_time:.2f}s")

        error_rate = 1 - success_rate
        if error_rate > self.performance_thresholds["max_error_rate"]:
            issues.append(f"錯誤率過高: {error_rate:.2%}")

        if not issues:
            return {
                "status": "healthy",
                "success_rate": round(success_rate, 4),
                "avg_response_time_ms": round(avg_response_time * 1000, 2),
            }
        else:
            return {
                "status": "degraded" if len(issues) < 3 else "unhealthy",
                "issues": issues,
                "success_rate": round(success_rate, 4),
                "avg_response_time_ms": round(avg_response_time * 1000, 2),
            }

    def _calculate_recent_error_rate(self, window_size: int = 50) -> float:
        """計算最近的錯誤率"""
        if len(self.processing_history) < window_size:
            recent_metrics = list(self.processing_history)
        else:
            recent_metrics = list(self.processing_history)[-window_size:]

        if not recent_metrics:
            return 0.0

        failed_count = sum(1 for m in recent_metrics if not m.success)
        return failed_count / len(recent_metrics)

    def _get_recent_summary(self, count: int = 10) -> Dict[str, Any]:
        """獲取最近處理的摘要"""
        recent = (
            list(self.processing_history)[-count:] if self.processing_history else []
        )

        return {
            "count": len(recent),
            "avg_time_ms": (
                round(statistics.mean(m.processing_time for m in recent) * 1000, 2)
                if recent
                else 0
            ),
            "success_rate": (
                sum(1 for m in recent if m.success) / len(recent) if recent else 0
            ),
            "cache_hit_rate": (
                sum(1 for m in recent if m.cache_hit) / len(recent) if recent else 0
            ),
        }

    async def generate_performance_report(
        self, hours: int = 24, include_raw_data: bool = False
    ) -> Dict[str, Any]:
        """
        生成詳細效能報告

        Args:
            hours: 報告時間範圍（小時）
            include_raw_data: 是否包含原始資料

        Returns:
            詳細效能報告
        """
        cutoff_time = time.time() - (hours * 3600)
        relevant_metrics = [
            m for m in self.processing_history if m.start_time > cutoff_time
        ]

        if not relevant_metrics:
            return {"error": "No data available for the specified time range"}

        # 按小時分組統計
        hourly_breakdown = defaultdict(
            lambda: {"requests": 0, "success_count": 0, "total_time": 0, "errors": []}
        )

        for metric in relevant_metrics:
            hour_key = datetime.fromtimestamp(metric.start_time).strftime(
                "%Y-%m-%d %H:00"
            )
            hour_data = hourly_breakdown[hour_key]

            hour_data["requests"] += 1
            hour_data["total_time"] += metric.processing_time

            if metric.success:
                hour_data["success_count"] += 1
            else:
                hour_data["errors"].append(metric.error_message)

        # 計算每小時統計
        hourly_stats = {}
        for hour, data in hourly_breakdown.items():
            hourly_stats[hour] = {
                "requests": data["requests"],
                "success_rate": data["success_count"] / data["requests"],
                "avg_response_time_ms": round(
                    (data["total_time"] / data["requests"]) * 1000, 2
                ),
                "error_count": len(data["errors"]),
                "unique_errors": len(set(data["errors"])),
            }

        # 頂層統計
        total_requests = len(relevant_metrics)
        total_success = sum(1 for m in relevant_metrics if m.success)

        # 效能趨勢分析
        processing_times = [m.processing_time for m in relevant_metrics]

        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "time_range_hours": hours,
                "total_requests_analyzed": total_requests,
            },
            "executive_summary": {
                "overall_success_rate": round(total_success / total_requests, 4),
                "avg_processing_time_ms": round(
                    statistics.mean(processing_times) * 1000, 2
                ),
                "total_processing_hours": round(sum(processing_times) / 3600, 2),
                "peak_hour": max(hourly_stats.items(), key=lambda x: x[1]["requests"]),
                "slowest_hour": max(
                    hourly_stats.items(), key=lambda x: x[1]["avg_response_time_ms"]
                ),
            },
            "performance_breakdown": {
                "response_time_percentiles": {
                    "p50": round(statistics.median(processing_times) * 1000, 2),
                    "p90": (
                        round(statistics.quantiles(processing_times, n=10)[8] * 1000, 2)
                        if len(processing_times) > 10
                        else 0
                    ),
                    "p95": (
                        round(
                            statistics.quantiles(processing_times, n=20)[18] * 1000, 2
                        )
                        if len(processing_times) > 20
                        else 0
                    ),
                    "p99": (
                        round(
                            statistics.quantiles(processing_times, n=100)[98] * 1000, 2
                        )
                        if len(processing_times) > 100
                        else 0
                    ),
                },
                "quality_metrics": {
                    quality: sum(
                        1 for m in relevant_metrics if m.result_quality == quality
                    )
                    for quality in set(m.result_quality for m in relevant_metrics)
                },
                "cache_efficiency": {
                    "total_cache_hits": sum(1 for m in relevant_metrics if m.cache_hit),
                    "cache_hit_rate": round(
                        sum(1 for m in relevant_metrics if m.cache_hit)
                        / total_requests,
                        4,
                    ),
                },
            },
            "hourly_breakdown": hourly_stats,
            "recommendations": self._generate_recommendations(relevant_metrics),
        }

        if include_raw_data:
            report["raw_metrics"] = [
                {
                    "request_id": m.request_id,
                    "timestamp": datetime.fromtimestamp(m.start_time).isoformat(),
                    "processing_time_ms": m.processing_time_ms,
                    "result_quality": m.result_quality,
                    "success": m.success,
                    "cache_hit": m.cache_hit,
                    "retry_count": m.retry_count,
                }
                for m in relevant_metrics
            ]

        return report

    def _generate_recommendations(self, metrics: List[ProcessingMetrics]) -> List[str]:
        """基於效能資料生成建議"""
        recommendations = []

        if not metrics:
            return recommendations

        # 分析處理時間
        processing_times = [m.processing_time for m in metrics]
        avg_time = statistics.mean(processing_times)
        p95_time = (
            statistics.quantiles(processing_times, n=20)[18]
            if len(processing_times) > 20
            else avg_time
        )

        if avg_time > 10:  # 超過10秒
            recommendations.append(
                f"平均處理時間 {avg_time:.1f}s 偏高，建議優化 API 呼叫或增加快取"
            )

        if p95_time > 20:  # P95超過20秒
            recommendations.append(
                f"P95 處理時間 {p95_time:.1f}s 過長，建議檢查異常請求並設定超時"
            )

        # 分析錯誤率
        error_rate = sum(1 for m in metrics if not m.success) / len(metrics)
        if error_rate > 0.05:  # 錯誤率超過5%
            recommendations.append(
                f"錯誤率 {error_rate:.1%} 過高，建議檢查 API 配額和網路穩定性"
            )

        # 分析快取效果
        cache_hit_rate = sum(1 for m in metrics if m.cache_hit) / len(metrics)
        if cache_hit_rate < 0.3:  # 快取命中率低於30%
            recommendations.append(
                f"快取命中率 {cache_hit_rate:.1%} 偏低，建議調整快取策略或增加快取容量"
            )

        # 分析重試情況
        avg_retries = statistics.mean(m.retry_count for m in metrics)
        if avg_retries > 0.5:
            recommendations.append(
                f"平均重試次數 {avg_retries:.1f} 偏高，建議檢查 API 穩定性"
            )

        return recommendations

    async def _persist_metrics(self, metrics: ProcessingMetrics):
        """持久化指標資料"""
        try:
            # 簡單的日誌記錄
            log_entry = {
                "timestamp": datetime.fromtimestamp(metrics.start_time).isoformat(),
                "request_id": metrics.request_id,
                "processing_time_ms": metrics.processing_time_ms,
                "success": metrics.success,
                "result_quality": metrics.result_quality,
                "cache_hit": metrics.cache_hit,
                "image_size_kb": round(metrics.image_size_bytes / 1024, 2),
            }

            # 寫入日誌檔案
            log_file = f"performance_log_{datetime.now().strftime('%Y%m%d')}.jsonl"
            async with aiofiles.open(log_file, "a", encoding="utf-8") as f:
                await f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        except Exception as e:
            print(f"⚠️ 效能指標持久化失敗: {e}")

    def _start_background_monitoring(self):
        """啟動背景監控任務"""

        async def health_check_task():
            while True:
                try:
                    await asyncio.sleep(60)  # 每分鐘檢查一次
                    await self._collect_system_health()
                except Exception as e:
                    print(f"⚠️ 健康檢查任務錯誤: {e}")

        # 不直接啟動，讓主應用決定
        self._background_task = health_check_task

    async def start_monitoring(self):
        """啟動背景監控"""
        return asyncio.create_task(self._background_task())

    async def _collect_system_health(self):
        """收集系統健康資料"""
        try:
            import psutil

            health = SystemHealth(
                timestamp=datetime.now(),
                cpu_usage=psutil.cpu_percent(interval=1),
                memory_usage=psutil.virtual_memory().percent,
                active_connections=len(psutil.net_connections()),
                queue_size=0,  # 需要從實際佇列獲取
                avg_response_time=self._get_recent_avg_response_time(),
                error_rate=self._calculate_recent_error_rate(),
                throughput=self._calculate_current_throughput(),
            )

            self.health_history.append(health)

        except ImportError:
            # psutil 未安裝，跳過系統健康檢查
            pass
        except Exception as e:
            print(f"⚠️ 系統健康檢查錯誤: {e}")

    def _get_recent_avg_response_time(self, minutes: int = 5) -> float:
        """獲取最近平均回應時間"""
        cutoff = time.time() - (minutes * 60)
        recent = [m for m in self.processing_history if m.start_time > cutoff]
        return statistics.mean(m.processing_time for m in recent) if recent else 0.0

    def _calculate_current_throughput(self, minutes: int = 5) -> float:
        """計算當前吞吐量"""
        cutoff = time.time() - (minutes * 60)
        recent_count = sum(1 for m in self.processing_history if m.start_time > cutoff)
        return recent_count / minutes  # 每分鐘請求數
