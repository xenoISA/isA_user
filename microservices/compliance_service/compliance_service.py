"""
Compliance Service Business Logic

处理内容审核、PII检测、提示词注入检测等合规检查
"""

import logging
import hashlib
import re
import time
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import uuid
import asyncio

from .compliance_repository import ComplianceRepository
from .models import (
    ComplianceCheck, ComplianceCheckRequest, ComplianceCheckResponse,
    ContentModerationResult, PIIDetectionResult, PromptInjectionResult,
    ComplianceCheckType, ComplianceStatus, RiskLevel, ContentType,
    ModerationCategory, PIIType, CompliancePolicy
)
from .events.publishers import (
    publish_compliance_check_performed,
    publish_compliance_violation_detected,
    publish_compliance_warning_issued
)

logger = logging.getLogger(__name__)


class ComplianceService:
    """合规服务核心业务逻辑"""

    def __init__(self, event_bus=None, config=None):
        self.repository = ComplianceRepository(config=config)
        self.event_bus = event_bus
        
        # 配置
        self.enable_openai_moderation = True
        self.enable_local_checks = True
        
        # 缓存
        self._policy_cache: Dict[str, CompliancePolicy] = {}
        
        # 统计
        self._stats = {
            "total_checks": 0,
            "blocked_content": 0,
            "flagged_content": 0
        }
    
    # ====================
    # 核心检查方法
    # ====================
    
    async def perform_compliance_check(
        self,
        request: ComplianceCheckRequest
    ) -> ComplianceCheckResponse:
        """执行合规检查 - 主入口"""
        start_time = time.time()
        check_id = str(uuid.uuid4())
        
        try:
            logger.info(f"Starting compliance check {check_id} for user {request.user_id}")
            
            # 获取适用的策略
            policy = await self._get_applicable_policy(request)
            
            # 执行各类检查
            check_results = await self._run_checks(request, check_id)
            
            # 评估总体合规状态
            overall_status, risk_level, violations, warnings = \
                self._evaluate_results(check_results, policy)
            
            # 决定行动
            action_required, action_taken = \
                await self._determine_action(overall_status, risk_level, policy)
            
            # 创建检查记录
            compliance_check = ComplianceCheck(
                check_id=check_id,
                check_type=request.check_types[0] if request.check_types else ComplianceCheckType.CONTENT_MODERATION,
                content_type=request.content_type,
                status=overall_status,
                risk_level=risk_level,
                user_id=request.user_id,
                organization_id=request.organization_id,
                session_id=request.session_id,
                request_id=request.request_id,
                content_id=request.content_id,
                content_hash=self._hash_content(request.content) if request.content else None,
                violations=violations,
                warnings=warnings,
                detected_issues=[v.get("issue", "") for v in violations],
                action_taken=action_taken,
                metadata=request.metadata,
                checked_at=datetime.utcnow()
            )
            
            # 保存到数据库
            await self.repository.create_check(compliance_check)

            # 发送事件通知
            # 1. Always publish check performed event
            await publish_compliance_check_performed(
                self.event_bus,
                check_id=check_id,
                user_id=request.user_id,
                check_type=compliance_check.check_type.value,
                content_type=compliance_check.content_type.value,
                status=overall_status.value,
                risk_level=risk_level.value,
                violations_count=len(violations),
                warnings_count=len(warnings),
                action_taken=action_taken,
                organization_id=request.organization_id,
                processing_time_ms=(time.time() - start_time) * 1000,
                metadata=request.metadata
            )

            # 2. If violations detected, publish violation event
            if overall_status == ComplianceStatus.FAIL and violations:
                await publish_compliance_violation_detected(
                    self.event_bus,
                    check_id=check_id,
                    user_id=request.user_id,
                    violations=violations,
                    risk_level=risk_level.value,
                    action_taken=action_taken,
                    organization_id=request.organization_id,
                    requires_review=(risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]),
                    blocked_content=(action_taken == "blocked"),
                    metadata=request.metadata
                )

            # 3. If warnings issued, publish warning event
            if warnings:
                await publish_compliance_warning_issued(
                    self.event_bus,
                    check_id=check_id,
                    user_id=request.user_id,
                    warnings=warnings,
                    risk_level=risk_level.value,
                    organization_id=request.organization_id,
                    allowed_with_warning=(action_taken not in ["blocked", "blocked"]),
                    metadata=request.metadata
                )
            
            # 构建响应
            processing_time = (time.time() - start_time) * 1000
            
            response = ComplianceCheckResponse(
                check_id=check_id,
                status=overall_status,
                risk_level=risk_level,
                passed=(overall_status == ComplianceStatus.PASS),
                violations=violations,
                warnings=warnings,
                moderation_result=check_results.get("moderation"),
                pii_result=check_results.get("pii"),
                injection_result=check_results.get("injection"),
                action_required=action_required,
                action_taken=action_taken,
                message=self._get_response_message(overall_status, risk_level),
                checked_at=datetime.utcnow(),
                processing_time_ms=processing_time
            )
            
            logger.info(f"Compliance check {check_id} completed: {overall_status.value}")
            return response
            
        except Exception as e:
            logger.error(f"Error in compliance check {check_id}: {e}")
            return ComplianceCheckResponse(
                check_id=check_id,
                status=ComplianceStatus.FAIL,
                risk_level=RiskLevel.HIGH,
                passed=False,
                violations=[{"issue": "System error during compliance check", "details": str(e)}],
                warnings=[],
                action_required="review",
                action_taken="blocked",
                message="Compliance check failed due to system error",
                checked_at=datetime.utcnow(),
                processing_time_ms=(time.time() - start_time) * 1000
            )
    
    async def _run_checks(
        self,
        request: ComplianceCheckRequest,
        check_id: str
    ) -> Dict[str, Any]:
        """运行所有需要的检查"""
        results = {}
        
        # 并发运行多个检查
        tasks = []
        
        if ComplianceCheckType.CONTENT_MODERATION in request.check_types:
            tasks.append(self._check_content_moderation(request, check_id))
        
        if ComplianceCheckType.PII_DETECTION in request.check_types:
            tasks.append(self._check_pii_detection(request, check_id))
        
        if ComplianceCheckType.PROMPT_INJECTION in request.check_types:
            tasks.append(self._check_prompt_injection(request, check_id))
        
        if ComplianceCheckType.TOXICITY in request.check_types:
            tasks.append(self._check_toxicity(request, check_id))
        
        # 等待所有检查完成
        if tasks:
            check_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 整理结果
            for i, check_type in enumerate(request.check_types):
                if i < len(check_results):
                    if isinstance(check_results[i], Exception):
                        logger.error(f"Check {check_type.value} failed: {check_results[i]}")
                    else:
                        results[check_type.value.split('_')[0]] = check_results[i]
        
        return results
    
    # ====================
    # 内容审核检查
    # ====================
    
    async def _check_content_moderation(
        self,
        request: ComplianceCheckRequest,
        check_id: str
    ) -> ContentModerationResult:
        """内容审核检查"""
        try:
            logger.info(f"Running content moderation for check {check_id}")
            
            if request.content_type == ContentType.TEXT or request.content_type == ContentType.PROMPT:
                return await self._moderate_text(request.content, check_id)
            
            elif request.content_type == ContentType.IMAGE:
                return await self._moderate_image(request.content_id or request.content_url, check_id)
            
            elif request.content_type == ContentType.AUDIO:
                return await self._moderate_audio(request.content_id or request.content_url, check_id)
            
            else:
                # 默认返回通过
                return ContentModerationResult(
                    check_id=check_id,
                    content_type=request.content_type,
                    status=ComplianceStatus.PASS,
                    risk_level=RiskLevel.NONE,
                    confidence=1.0,
                    recommendation="allow"
                )
                
        except Exception as e:
            logger.error(f"Content moderation error: {e}")
            return ContentModerationResult(
                check_id=check_id,
                content_type=request.content_type,
                status=ComplianceStatus.FAIL,
                risk_level=RiskLevel.HIGH,
                confidence=0.0,
                recommendation="review",
                explanation=str(e)
            )
    
    async def _moderate_text(self, text: str, check_id: str) -> ContentModerationResult:
        """文本内容审核"""
        if not text:
            return ContentModerationResult(
                check_id=check_id,
                content_type=ContentType.TEXT,
                status=ComplianceStatus.PASS,
                risk_level=RiskLevel.NONE,
                confidence=1.0,
                recommendation="allow"
            )
        
        categories = {}
        flagged_categories = []
        max_score = 0.0
        
        # 方法1: 使用OpenAI Moderation API（如果可用）
        if self.enable_openai_moderation:
            try:
                openai_result = await self._call_openai_moderation(text)
                if openai_result:
                    categories = openai_result.get("categories", {})
                    for cat, flagged in openai_result.get("category_scores", {}).items():
                        score = float(flagged)
                        categories[cat] = score
                        if score > max_score:
                            max_score = score
                        if score > 0.5:  # 阈值
                            flagged_categories.append(cat)
            except Exception as e:
                logger.warning(f"OpenAI moderation failed: {e}")
        
        # 方法2: 本地规则检查（备选）
        if self.enable_local_checks:
            local_result = await self._local_text_moderation(text)
            categories.update(local_result["categories"])
            flagged_categories.extend(local_result["flagged"])
            max_score = max(max_score, local_result.get("max_score", 0))
        
        # 确定状态和风险级别
        if max_score >= 0.9:
            status = ComplianceStatus.BLOCKED
            risk_level = RiskLevel.CRITICAL
            recommendation = "block"
        elif max_score >= 0.7:
            status = ComplianceStatus.FAIL
            risk_level = RiskLevel.HIGH
            recommendation = "block"
        elif max_score >= 0.5:
            status = ComplianceStatus.FLAGGED
            risk_level = RiskLevel.MEDIUM
            recommendation = "review"
        elif max_score >= 0.3:
            status = ComplianceStatus.WARNING
            risk_level = RiskLevel.LOW
            recommendation = "allow"
        else:
            status = ComplianceStatus.PASS
            risk_level = RiskLevel.NONE
            recommendation = "allow"
        
        return ContentModerationResult(
            check_id=check_id,
            content_type=ContentType.TEXT,
            status=status,
            risk_level=risk_level,
            categories=categories,
            flagged_categories=flagged_categories,
            confidence=max_score,
            recommendation=recommendation,
            explanation=f"Flagged categories: {', '.join(flagged_categories)}" if flagged_categories else None
        )
    
    async def _moderate_image(self, image_ref: str, check_id: str) -> ContentModerationResult:
        """图片内容审核"""
        # 这里应该集成AWS Rekognition, Google Vision API, 或Azure Content Moderator
        # 简化示例:
        logger.info(f"Image moderation for {image_ref}")
        
        # TODO: 实际实现图片审核
        # 可以集成:
        # - AWS Rekognition (DetectModerationLabels)
        # - Google Cloud Vision (SafeSearchDetection)
        # - Azure Content Moderator
        
        return ContentModerationResult(
            check_id=check_id,
            content_type=ContentType.IMAGE,
            status=ComplianceStatus.PASS,
            risk_level=RiskLevel.NONE,
            confidence=0.9,
            recommendation="allow",
            explanation="Image moderation not fully implemented - passed by default"
        )
    
    async def _moderate_audio(self, audio_ref: str, check_id: str) -> ContentModerationResult:
        """音频内容审核"""
        # 音频审核流程:
        # 1. 使用语音转文字 (Whisper, AWS Transcribe, Google Speech-to-Text)
        # 2. 对转录文本进行审核
        logger.info(f"Audio moderation for {audio_ref}")
        
        # TODO: 实际实现音频审核
        
        return ContentModerationResult(
            check_id=check_id,
            content_type=ContentType.AUDIO,
            status=ComplianceStatus.PASS,
            risk_level=RiskLevel.NONE,
            confidence=0.9,
            recommendation="allow",
            explanation="Audio moderation not fully implemented - passed by default"
        )
    
    # ====================
    # PII 检测
    # ====================
    
    async def _check_pii_detection(
        self,
        request: ComplianceCheckRequest,
        check_id: str
    ) -> PIIDetectionResult:
        """PII检测"""
        try:
            if not request.content or request.content_type not in [ContentType.TEXT, ContentType.PROMPT]:
                return PIIDetectionResult(
                    check_id=check_id,
                    status=ComplianceStatus.PASS,
                    risk_level=RiskLevel.NONE,
                    detected_pii=[],
                    pii_count=0
                )
            
            detected_pii = []
            
            # 使用正则表达式检测常见PII
            pii_patterns = {
                PIIType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                PIIType.PHONE: r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                PIIType.SSN: r'\b\d{3}-\d{2}-\d{4}\b',
                PIIType.CREDIT_CARD: r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
                PIIType.IP_ADDRESS: r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
            }
            
            for pii_type, pattern in pii_patterns.items():
                matches = re.finditer(pattern, request.content)
                for match in matches:
                    detected_pii.append({
                        "type": pii_type.value,
                        "value": self._mask_pii(match.group()),
                        "location": match.span(),
                        "confidence": 0.95
                    })
            
            # 判断风险级别
            pii_count = len(detected_pii)
            if pii_count >= 5:
                risk_level = RiskLevel.CRITICAL
                status = ComplianceStatus.FAIL
                needs_redaction = True
            elif pii_count >= 3:
                risk_level = RiskLevel.HIGH
                status = ComplianceStatus.FLAGGED
                needs_redaction = True
            elif pii_count >= 1:
                risk_level = RiskLevel.MEDIUM
                status = ComplianceStatus.WARNING
                needs_redaction = True
            else:
                risk_level = RiskLevel.NONE
                status = ComplianceStatus.PASS
                needs_redaction = False
            
            return PIIDetectionResult(
                check_id=check_id,
                status=status,
                detected_pii=detected_pii,
                pii_count=pii_count,
                pii_types=[PIIType(p["type"]) for p in detected_pii],
                risk_level=risk_level,
                needs_redaction=needs_redaction
            )
            
        except Exception as e:
            logger.error(f"PII detection error: {e}")
            return PIIDetectionResult(
                check_id=check_id,
                status=ComplianceStatus.FAIL,
                risk_level=RiskLevel.HIGH,
                detected_pii=[],
                pii_count=0
            )
    
    # ====================
    # 提示词注入检测
    # ====================
    
    async def _check_prompt_injection(
        self,
        request: ComplianceCheckRequest,
        check_id: str
    ) -> PromptInjectionResult:
        """提示词注入检测"""
        try:
            if not request.content or request.content_type not in [ContentType.TEXT, ContentType.PROMPT]:
                return PromptInjectionResult(
                    check_id=check_id,
                    status=ComplianceStatus.PASS,
                    risk_level=RiskLevel.NONE,
                    is_injection_detected=False,
                    confidence=1.0,
                    recommendation="allow"
                )
            
            text = request.content.lower()
            
            # 检测常见的注入模式
            injection_patterns = [
                r'ignore\s+(previous|above|prior)\s+(instructions|prompts?|commands?)',
                r'forget\s+(everything|all|previous)',
                r'you\s+are\s+now',
                r'system\s*:\s*',
                r'</?\s*system\s*>',
                r'jailbreak',
                r'developer\s+mode',
                r'override\s+(safety|rules|restrictions)',
            ]
            
            detected_patterns = []
            max_confidence = 0.0
            
            for pattern in injection_patterns:
                if re.search(pattern, text):
                    detected_patterns.append(pattern)
                    max_confidence = max(max_confidence, 0.8)
            
            # 检测异常结构
            suspicious_tokens = []
            if '<|' in text or '|>' in text:
                suspicious_tokens.append('special_tokens')
                max_confidence = max(max_confidence, 0.6)
            
            if '###' in text or '```' in text:
                suspicious_tokens.append('code_blocks')
                max_confidence = max(max_confidence, 0.4)
            
            # 判断结果
            is_injection = len(detected_patterns) > 0
            
            if max_confidence >= 0.8:
                status = ComplianceStatus.FAIL
                risk_level = RiskLevel.HIGH
                injection_type = "direct"
                recommendation = "block"
            elif max_confidence >= 0.5:
                status = ComplianceStatus.FLAGGED
                risk_level = RiskLevel.MEDIUM
                injection_type = "suspicious"
                recommendation = "review"
            else:
                status = ComplianceStatus.PASS
                risk_level = RiskLevel.NONE
                injection_type = None
                recommendation = "allow"
            
            return PromptInjectionResult(
                check_id=check_id,
                status=status,
                risk_level=risk_level,
                is_injection_detected=is_injection,
                injection_type=injection_type,
                confidence=max_confidence,
                detected_patterns=detected_patterns,
                suspicious_tokens=suspicious_tokens,
                recommendation=recommendation,
                explanation=f"Detected patterns: {', '.join(detected_patterns)}" if detected_patterns else None
            )
            
        except Exception as e:
            logger.error(f"Prompt injection detection error: {e}")
            return PromptInjectionResult(
                check_id=check_id,
                status=ComplianceStatus.FAIL,
                risk_level=RiskLevel.HIGH,
                is_injection_detected=True,
                confidence=0.0,
                recommendation="block"
            )
    
    # ====================
    # 毒性检测
    # ====================
    
    async def _check_toxicity(
        self,
        request: ComplianceCheckRequest,
        check_id: str
    ) -> Dict[str, Any]:
        """毒性检测"""
        # TODO: 集成 Perspective API 或类似服务
        return {
            "check_id": check_id,
            "toxicity_score": 0.0,
            "status": ComplianceStatus.PASS.value
        }
    
    # ====================
    # 辅助方法
    # ====================
    
    async def _call_openai_moderation(self, text: str) -> Optional[Dict[str, Any]]:
        """调用OpenAI Moderation API"""
        try:
            # TODO: 实际实现OpenAI API调用
            # import openai
            # response = await openai.Moderation.acreate(input=text)
            # return response["results"][0]
            
            # 模拟返回
            return None
        except Exception as e:
            logger.error(f"OpenAI moderation API error: {e}")
            return None
    
    async def _local_text_moderation(self, text: str) -> Dict[str, Any]:
        """本地文本审核（基于规则）"""
        categories = {}
        flagged = []
        max_score = 0.0
        
        # 简单的关键词检测
        hate_keywords = ['hate', 'racist', 'discrimination']
        violence_keywords = ['kill', 'murder', 'violence', 'attack']
        
        text_lower = text.lower()
        
        # 仇恨言论检测
        hate_count = sum(1 for kw in hate_keywords if kw in text_lower)
        if hate_count > 0:
            score = min(hate_count * 0.3, 1.0)
            categories["hate"] = score
            max_score = max(max_score, score)
            if score > 0.5:
                flagged.append("hate")
        
        # 暴力内容检测
        violence_count = sum(1 for kw in violence_keywords if kw in text_lower)
        if violence_count > 0:
            score = min(violence_count * 0.3, 1.0)
            categories["violence"] = score
            max_score = max(max_score, score)
            if score > 0.5:
                flagged.append("violence")
        
        return {
            "categories": categories,
            "flagged": flagged,
            "max_score": max_score
        }
    
    def _evaluate_results(
        self,
        check_results: Dict[str, Any],
        policy: Optional[CompliancePolicy]
    ) -> Tuple[ComplianceStatus, RiskLevel, List[Dict], List[Dict]]:
        """评估所有检查结果"""
        violations = []
        warnings = []
        max_risk = RiskLevel.NONE
        worst_status = ComplianceStatus.PASS
        
        status_priority = {
            ComplianceStatus.PASS: 0,
            ComplianceStatus.WARNING: 1,
            ComplianceStatus.FLAGGED: 2,
            ComplianceStatus.FAIL: 3,
            ComplianceStatus.BLOCKED: 4
        }
        
        risk_priority = {
            RiskLevel.NONE: 0,
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4
        }
        
        # 遍历所有检查结果
        for check_type, result in check_results.items():
            if hasattr(result, 'status'):
                if status_priority[result.status] > status_priority[worst_status]:
                    worst_status = result.status
                
                if risk_priority[result.risk_level] > risk_priority[max_risk]:
                    max_risk = result.risk_level
                
                # 收集违规和警告
                if result.status in [ComplianceStatus.FAIL, ComplianceStatus.BLOCKED]:
                    violations.append({
                        "check_type": check_type,
                        "issue": result.recommendation if hasattr(result, 'recommendation') else "Compliance violation",
                        "details": result.explanation if hasattr(result, 'explanation') else ""
                    })
                elif result.status in [ComplianceStatus.WARNING, ComplianceStatus.FLAGGED]:
                    warnings.append({
                        "check_type": check_type,
                        "issue": "Potential compliance issue",
                        "details": result.explanation if hasattr(result, 'explanation') else ""
                    })
        
        return worst_status, max_risk, violations, warnings
    
    async def _determine_action(
        self,
        status: ComplianceStatus,
        risk_level: RiskLevel,
        policy: Optional[CompliancePolicy]
    ) -> Tuple[str, Optional[str]]:
        """决定应采取的行动"""
        if status == ComplianceStatus.BLOCKED or risk_level == RiskLevel.CRITICAL:
            return "block", "blocked"
        elif status == ComplianceStatus.FAIL or risk_level == RiskLevel.HIGH:
            return "block", "blocked"
        elif status == ComplianceStatus.FLAGGED or risk_level == RiskLevel.MEDIUM:
            return "review", "flagged_for_review"
        elif status == ComplianceStatus.WARNING:
            return "allow", "allowed_with_warning"
        else:
            return "none", "allowed"
    
    async def _get_applicable_policy(
        self,
        request: ComplianceCheckRequest
    ) -> Optional[CompliancePolicy]:
        """获取适用的策略"""
        try:
            if request.policy_id:
                return await self.repository.get_policy_by_id(request.policy_id)
            
            # 获取组织或全局策略
            policies = await self.repository.get_active_policies(request.organization_id)
            
            # 返回第一个匹配的策略（按优先级排序）
            for policy in policies:
                if request.content_type in policy.content_types:
                    return policy
            
            return None
        except Exception as e:
            logger.error(f"Error getting policy: {e}")
            return None
    
    def _hash_content(self, content: str) -> str:
        """生成内容哈希"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _mask_pii(self, value: str) -> str:
        """掩码PII"""
        if len(value) <= 4:
            return "***"
        return value[:2] + "*" * (len(value) - 4) + value[-2:]
    
    def _get_response_message(self, status: ComplianceStatus, risk_level: RiskLevel) -> str:
        """获取响应消息"""
        if status == ComplianceStatus.PASS:
            return "Content passed all compliance checks"
        elif status == ComplianceStatus.WARNING:
            return "Content passed with warnings"
        elif status == ComplianceStatus.FLAGGED:
            return "Content flagged for review"
        elif status == ComplianceStatus.FAIL:
            return "Content failed compliance checks"
        elif status == ComplianceStatus.BLOCKED:
            return "Content blocked due to compliance violations"
        else:
            return "Compliance check pending"


__all__ = ['ComplianceService']

