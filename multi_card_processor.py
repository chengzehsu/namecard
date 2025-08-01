"""
多名片處理器 - 專門處理多張名片的工作流程和用戶交互
"""

import json
from typing import Dict, List, Any, Tuple
from name_card_processor import NameCardProcessor


class MultiCardProcessor:
    """多名片處理器，負責協調多名片識別、品質評估和用戶交互"""
    
    def __init__(self):
        """初始化多名片處理器"""
        self.card_processor = NameCardProcessor()
        
    def process_image_with_quality_check(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        處理圖片並進行品質檢查
        
        Returns:
            Dict包含:
            - card_count: 名片數量
            - cards: 名片資料列表  
            - overall_quality: good/partial/poor
            - processing_suggestions: 處理建議
            - action_required: 是否需要用戶交互
            - user_options: 用戶可選的操作
        """
        try:
            # 使用增強的名片處理器進行識別
            result = self.card_processor.extract_multi_card_info(image_bytes)
            
            # 檢查是否有錯誤
            if "error" in result:
                return result
                
            # 分析處理結果並決定下一步行動
            return self._analyze_and_recommend_action(result)
            
        except Exception as e:
            return {"error": f"多名片處理失敗: {str(e)}"}
    
    def _analyze_and_recommend_action(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析識別結果並推薦用戶行動"""
        try:
            card_count = card_data.get("card_count", 0)
            overall_quality = card_data.get("overall_quality", "poor")
            cards = card_data.get("cards", [])
            
            # 基本資料檢查
            if card_count == 0:
                return {
                    **card_data,
                    "action_required": True,
                    "user_options": ["重新拍攝"],
                    "recommendation": "未檢測到名片，請重新拍攝"
                }
            
            # 單張名片處理
            if card_count == 1:
                return self._handle_single_card_decision(card_data, cards[0])
            
            # 多張名片處理
            else:
                return self._handle_multi_card_decision(card_data, cards)
                
        except Exception as e:
            return {
                **card_data,
                "error": f"分析處理結果時發生錯誤: {str(e)}",
                "action_required": True,
                "user_options": ["重新拍攝"]
            }
    
    def _handle_single_card_decision(self, card_data: Dict[str, Any], card: Dict[str, Any]) -> Dict[str, Any]:
        """處理單張名片的決策邏輯"""
        confidence_score = card.get("confidence_score", 0.5)
        overall_quality = card_data.get("overall_quality", "poor")
        
        if overall_quality == "good" and confidence_score >= 0.8:
            # 品質良好，直接處理
            return {
                **card_data,
                "action_required": False,
                "recommendation": "名片識別品質良好，將自動處理",
                "auto_process": True
            }
        
        elif overall_quality in ["partial", "good"] and confidence_score >= 0.6:
            # 品質中等，詢問用戶
            issues = []
            if not card.get("name"):
                issues.append("缺少姓名")
            if not card.get("company"):
                issues.append("缺少公司名稱")
            if card.get("clarity_issues"):
                issues.extend(card["clarity_issues"])
                
            return {
                **card_data,
                "action_required": True,
                "user_options": ["繼續處理", "重新拍攝"],
                "recommendation": f"識別結果可能有問題: {', '.join(issues)}。您可以選擇繼續處理或重新拍攝",
                "quality_issues": issues
            }
        
        else:
            # 品質差，建議重拍
            return {
                **card_data,
                "action_required": True,
                "user_options": ["重新拍攝"],
                "recommendation": "名片識別品質較差，強烈建議重新拍攝以獲得更好的結果",
                "force_retake": True
            }
    
    def _handle_multi_card_decision(self, card_data: Dict[str, Any], cards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """處理多張名片的決策邏輯"""
        card_count = len(cards)
        overall_quality = card_data.get("overall_quality", "poor")
        
        # 分析每張名片的品質
        good_cards = []
        poor_cards = []
        
        for i, card in enumerate(cards):
            confidence = card.get("confidence_score", 0.5)
            has_required_fields = card.get("name") and card.get("company")
            
            if confidence >= 0.7 and has_required_fields:
                good_cards.append(i + 1)
            else:
                poor_cards.append(i + 1)
        
        # 根據品質分佈決定行動
        if len(good_cards) == card_count:
            # 所有名片品質良好
            return {
                **card_data,
                "action_required": True,
                "user_options": ["分別處理所有名片", "重新拍攝單張名片"],
                "recommendation": f"檢測到 {card_count} 張名片，品質都不錯。建議分別處理",
                "good_cards": good_cards,
                "poor_cards": []
            }
        
        elif len(good_cards) > 0:
            # 部分名片品質良好
            return {
                **card_data,
                "action_required": True,
                "user_options": [
                    f"只處理品質良好的 {len(good_cards)} 張名片",
                    "分別處理所有名片",
                    f"重新拍攝第 {', '.join(map(str, poor_cards))} 張名片"
                ],
                "recommendation": f"檢測到 {card_count} 張名片，其中 {len(good_cards)} 張品質良好，{len(poor_cards)} 張需要改善",
                "good_cards": good_cards,
                "poor_cards": poor_cards
            }
        
        else:
            # 所有名片品質都差
            return {
                **card_data,
                "action_required": True,
                "user_options": ["重新拍攝"],
                "recommendation": f"檢測到 {card_count} 張名片，但識別品質都不理想，建議重新拍攝",
                "good_cards": [],
                "poor_cards": poor_cards,
                "suggest_single_shot": True
            }
    
    def get_cards_for_processing(self, card_data: Dict[str, Any], user_choice: str) -> List[Dict[str, Any]]:
        """根據用戶選擇獲取需要處理的名片"""
        try:
            cards = card_data.get("cards", [])
            good_cards = card_data.get("good_cards", [])
            
            if user_choice == "分別處理所有名片":
                return cards
            
            elif user_choice.startswith("只處理品質良好"):
                return [cards[i-1] for i in good_cards if i <= len(cards)]
            
            elif user_choice == "繼續處理":
                return cards
            
            else:
                # 其他情況返回空列表，表示需要重新拍攝
                return []
                
        except Exception as e:
            print(f"獲取處理名片時出錯: {e}")
            return []
    
    def generate_user_friendly_message(self, analysis_result: Dict[str, Any]) -> str:
        """生成用戶友好的訊息"""
        try:
            card_count = analysis_result.get("card_count", 0)
            recommendation = analysis_result.get("recommendation", "")
            user_options = analysis_result.get("user_options", [])
            
            message = f"📸 **名片識別結果**\n\n"
            message += f"🔍 檢測到 {card_count} 張名片\n"
            message += f"💡 {recommendation}\n\n"
            
            if user_options:
                message += "請選擇您要執行的操作：\n"
                for i, option in enumerate(user_options, 1):
                    message += f"{i}. {option}\n"
            
            # 如果有品質問題的詳細資訊
            if analysis_result.get("good_cards") and analysis_result.get("poor_cards"):
                good_cards = analysis_result["good_cards"]
                poor_cards = analysis_result["poor_cards"]
                message += f"\n✅ 品質良好：第 {', '.join(map(str, good_cards))} 張\n"
                message += f"⚠️ 需要改善：第 {', '.join(map(str, poor_cards))} 張\n"
            
            return message
            
        except Exception as e:
            return f"❌ 產生訊息時發生錯誤: {str(e)}"
    
    def get_processing_suggestions(self, analysis_result: Dict[str, Any]) -> List[str]:
        """獲取處理建議"""
        suggestions = analysis_result.get("processing_suggestions", [])
        
        # 添加拍攝建議
        if analysis_result.get("suggest_single_shot"):
            suggestions.append("💡 建議：一次只拍一張名片可以獲得更好的識別效果")
        
        if analysis_result.get("card_count", 0) > 2:
            suggestions.append("💡 建議：如果名片較多，可以分批處理以確保品質")
        
        return suggestions