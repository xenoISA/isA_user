"""
Unit Golden Tests: Compliance Service Models

Tests model validation and serialization without external dependencies.
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.compliance_service.models import (
    ContentType,
    ComplianceCheckType,
    ComplianceStatus,
    RiskLevel,
    ModerationCategory,
    PIIType,
    ComplianceCheck,
    CompliancePolicy,
    ContentModerationResult,
    PIIDetectionResult,
    PromptInjectionResult,
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    BatchComplianceCheckRequest,
    BatchComplianceCheckResponse,
    ComplianceReportRequest,
    ComplianceReportResponse,
    CompliancePolicyRequest,
    ComplianceServiceStatus,
    ComplianceStats,
)


# ====================
# Enum Tests
# ====================

class TestContentType:
    """Test ContentType enum"""

    def test_content_type_values(self):
        """Test all content type values are defined"""
        assert ContentType.TEXT.value == "text"
        assert ContentType.IMAGE.value == "image"
        assert ContentType.AUDIO.value == "audio"
        assert ContentType.VIDEO.value == "video"
        assert ContentType.FILE.value == "file"
        assert ContentType.PROMPT.value == "prompt"
        assert ContentType.RESPONSE.value == "response"

    def test_content_type_comparison(self):
        """Test content type comparison"""
        assert ContentType.TEXT.value == "text"
        assert ContentType.TEXT != ContentType.IMAGE
        assert ContentType.PROMPT.value == "prompt"


class TestComplianceCheckType:
    """Test ComplianceCheckType enum"""

    def test_compliance_check_type_values(self):
        """Test all compliance check type values"""
        assert ComplianceCheckType.CONTENT_MODERATION.value == "content_moderation"
        assert ComplianceCheckType.PII_DETECTION.value == "pii_detection"
        assert ComplianceCheckType.PROMPT_INJECTION.value == "prompt_injection"
        assert ComplianceCheckType.TOXICITY.value == "toxicity"
        assert ComplianceCheckType.COPYRIGHT.value == "copyright"
        assert ComplianceCheckType.AGE_RESTRICTION.value == "age_restriction"
        assert ComplianceCheckType.GDPR_COMPLIANCE.value == "gdpr_compliance"
        assert ComplianceCheckType.HIPAA_COMPLIANCE.value == "hipaa_compliance"
        assert ComplianceCheckType.CONTENT_SAFETY.value == "content_safety"

    def test_compliance_check_type_usage(self):
        """Test compliance check type in models"""
        assert ComplianceCheckType.CONTENT_MODERATION != ComplianceCheckType.PII_DETECTION
        assert ComplianceCheckType.TOXICITY.value == "toxicity"


class TestComplianceStatus:
    """Test ComplianceStatus enum"""

    def test_compliance_status_values(self):
        """Test all compliance status values"""
        assert ComplianceStatus.PASS.value == "pass"
        assert ComplianceStatus.FAIL.value == "fail"
        assert ComplianceStatus.WARNING.value == "warning"
        assert ComplianceStatus.PENDING.value == "pending"
        assert ComplianceStatus.FLAGGED.value == "flagged"
        assert ComplianceStatus.BLOCKED.value == "blocked"

    def test_compliance_status_comparison(self):
        """Test compliance status comparison"""
        assert ComplianceStatus.PASS != ComplianceStatus.FAIL
        assert ComplianceStatus.WARNING.value == "warning"


class TestRiskLevel:
    """Test RiskLevel enum"""

    def test_risk_level_values(self):
        """Test all risk level values"""
        assert RiskLevel.NONE.value == "none"
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_risk_level_ordering(self):
        """Test risk level comparison"""
        assert RiskLevel.NONE != RiskLevel.LOW
        assert RiskLevel.HIGH != RiskLevel.MEDIUM
        assert RiskLevel.CRITICAL.value == "critical"


class TestModerationCategory:
    """Test ModerationCategory enum"""

    def test_moderation_category_values(self):
        """Test all moderation category values"""
        assert ModerationCategory.HATE_SPEECH.value == "hate_speech"
        assert ModerationCategory.VIOLENCE.value == "violence"
        assert ModerationCategory.SEXUAL.value == "sexual"
        assert ModerationCategory.HARASSMENT.value == "harassment"
        assert ModerationCategory.SELF_HARM.value == "self_harm"
        assert ModerationCategory.ILLEGAL.value == "illegal"
        assert ModerationCategory.SPAM.value == "spam"
        assert ModerationCategory.MISINFORMATION.value == "misinformation"
        assert ModerationCategory.CHILD_SAFETY.value == "child_safety"

    def test_moderation_category_usage(self):
        """Test moderation category in content moderation"""
        assert ModerationCategory.HATE_SPEECH != ModerationCategory.VIOLENCE
        assert ModerationCategory.CHILD_SAFETY.value == "child_safety"


class TestPIIType:
    """Test PIIType enum"""

    def test_pii_type_values(self):
        """Test all PII type values"""
        assert PIIType.EMAIL.value == "email"
        assert PIIType.PHONE.value == "phone"
        assert PIIType.SSN.value == "ssn"
        assert PIIType.CREDIT_CARD.value == "credit_card"
        assert PIIType.PASSPORT.value == "passport"
        assert PIIType.DRIVER_LICENSE.value == "driver_license"
        assert PIIType.IP_ADDRESS.value == "ip_address"
        assert PIIType.ADDRESS.value == "address"
        assert PIIType.NAME.value == "name"
        assert PIIType.DATE_OF_BIRTH.value == "date_of_birth"
        assert PIIType.MEDICAL_INFO.value == "medical_info"

    def test_pii_type_comparison(self):
        """Test PII type comparison"""
        assert PIIType.EMAIL != PIIType.PHONE
        assert PIIType.SSN.value == "ssn"
        assert PIIType.MEDICAL_INFO.value == "medical_info"


# ====================
# Core Model Tests
# ====================

class TestComplianceCheck:
    """Test ComplianceCheck model"""

    def test_compliance_check_creation_minimal(self):
        """Test compliance check with minimal required fields"""
        check = ComplianceCheck(
            check_id="check_123",
            check_type=ComplianceCheckType.CONTENT_MODERATION,
            content_type=ContentType.TEXT,
            status=ComplianceStatus.PASS,
            user_id="user_456",
        )

        assert check.check_id == "check_123"
        assert check.check_type == ComplianceCheckType.CONTENT_MODERATION
        assert check.content_type == ContentType.TEXT
        assert check.status == ComplianceStatus.PASS
        assert check.user_id == "user_456"
        assert check.risk_level == RiskLevel.NONE
        assert check.confidence_score == 0.0
        assert check.violations == []
        assert check.warnings == []
        assert check.detected_issues == []
        assert check.human_review_required is False

    def test_compliance_check_with_all_fields(self):
        """Test compliance check with all fields"""
        now = datetime.now(timezone.utc)

        check = ComplianceCheck(
            check_id="check_full_123",
            check_type=ComplianceCheckType.PII_DETECTION,
            content_type=ContentType.TEXT,
            status=ComplianceStatus.FLAGGED,
            risk_level=RiskLevel.HIGH,
            user_id="user_789",
            organization_id="org_123",
            session_id="session_456",
            request_id="req_789",
            content_id="content_123",
            content_hash="abc123hash",
            content_size=1024,
            confidence_score=0.85,
            violations=[{"type": "pii", "details": "email found"}],
            warnings=[{"type": "suspicious", "message": "unusual pattern"}],
            detected_issues=["email_exposed", "phone_number"],
            moderation_categories={"hate_speech": 0.1, "violence": 0.05},
            detected_pii=[{"type": "email", "value": "***@***.com", "confidence": 0.9}],
            action_taken="flagged_for_review",
            blocked_reason="PII detected",
            human_review_required=True,
            reviewed_by="admin_001",
            review_notes="Contains sensitive information",
            metadata={"source": "user_upload", "device": "mobile"},
            provider="openai",
            checked_at=now,
            reviewed_at=now,
        )

        assert check.check_id == "check_full_123"
        assert check.risk_level == RiskLevel.HIGH
        assert check.organization_id == "org_123"
        assert check.confidence_score == 0.85
        assert len(check.violations) == 1
        assert len(check.warnings) == 1
        assert len(check.detected_issues) == 2
        assert check.human_review_required is True
        assert check.reviewed_by == "admin_001"
        assert check.provider == "openai"

    def test_compliance_check_confidence_score_validation(self):
        """Test confidence score validation (0.0 to 1.0)"""
        # Valid score
        check = ComplianceCheck(
            check_id="check_valid",
            check_type=ComplianceCheckType.TOXICITY,
            content_type=ContentType.TEXT,
            status=ComplianceStatus.PASS,
            user_id="user_123",
            confidence_score=0.75,
        )
        assert check.confidence_score == 0.75

        # Test score > 1.0
        with pytest.raises(ValidationError):
            ComplianceCheck(
                check_id="check_invalid",
                check_type=ComplianceCheckType.TOXICITY,
                content_type=ContentType.TEXT,
                status=ComplianceStatus.PASS,
                user_id="user_123",
                confidence_score=1.5,
            )

        # Test score < 0.0
        with pytest.raises(ValidationError):
            ComplianceCheck(
                check_id="check_invalid",
                check_type=ComplianceCheckType.TOXICITY,
                content_type=ContentType.TEXT,
                status=ComplianceStatus.PASS,
                user_id="user_123",
                confidence_score=-0.1,
            )

    def test_compliance_check_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ComplianceCheck(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "check_id" in missing_fields
        assert "check_type" in missing_fields
        assert "content_type" in missing_fields
        assert "status" in missing_fields


class TestCompliancePolicy:
    """Test CompliancePolicy model"""

    def test_compliance_policy_creation_minimal(self):
        """Test compliance policy with minimal fields"""
        policy = CompliancePolicy(
            policy_id="policy_123",
            policy_name="Basic Moderation Policy",
            content_types=[ContentType.TEXT, ContentType.IMAGE],
            check_types=[ComplianceCheckType.CONTENT_MODERATION],
            rules={"max_toxicity": 0.7},
        )

        assert policy.policy_id == "policy_123"
        assert policy.policy_name == "Basic Moderation Policy"
        assert len(policy.content_types) == 2
        assert len(policy.check_types) == 1
        assert policy.rules == {"max_toxicity": 0.7}
        assert policy.auto_block is True
        assert policy.require_human_review is False
        assert policy.notification_enabled is True
        assert policy.is_active is True
        assert policy.priority == 100

    def test_compliance_policy_with_all_fields(self):
        """Test compliance policy with all fields"""
        now = datetime.now(timezone.utc)

        policy = CompliancePolicy(
            policy_id="policy_full_123",
            policy_name="Enterprise Policy",
            organization_id="org_456",
            content_types=[ContentType.TEXT, ContentType.IMAGE, ContentType.VIDEO],
            check_types=[
                ComplianceCheckType.CONTENT_MODERATION,
                ComplianceCheckType.PII_DETECTION,
                ComplianceCheckType.GDPR_COMPLIANCE,
            ],
            rules={
                "max_toxicity": 0.5,
                "block_hate_speech": True,
                "redact_pii": True,
            },
            thresholds={
                "violence": 0.6,
                "sexual": 0.7,
                "harassment": 0.5,
            },
            auto_block=True,
            require_human_review=True,
            notification_enabled=True,
            is_active=True,
            priority=200,
            created_at=now,
            updated_at=now,
            created_by="admin_123",
        )

        assert policy.policy_id == "policy_full_123"
        assert policy.organization_id == "org_456"
        assert len(policy.content_types) == 3
        assert len(policy.check_types) == 3
        assert policy.thresholds["violence"] == 0.6
        assert policy.require_human_review is True
        assert policy.priority == 200
        assert policy.created_by == "admin_123"

    def test_compliance_policy_organization_scope(self):
        """Test compliance policy with organization scope"""
        policy = CompliancePolicy(
            policy_id="policy_org",
            policy_name="Organization Policy",
            organization_id="org_789",
            content_types=[ContentType.TEXT],
            check_types=[ComplianceCheckType.CONTENT_MODERATION],
            rules={"strict_mode": True},
        )

        assert policy.organization_id == "org_789"

    def test_compliance_policy_global_scope(self):
        """Test global compliance policy (no organization_id)"""
        policy = CompliancePolicy(
            policy_id="policy_global",
            policy_name="Global Policy",
            content_types=[ContentType.TEXT],
            check_types=[ComplianceCheckType.TOXICITY],
            rules={"global_threshold": 0.8},
        )

        assert policy.organization_id is None


class TestContentModerationResult:
    """Test ContentModerationResult model"""

    def test_content_moderation_result_minimal(self):
        """Test content moderation result with minimal fields"""
        result = ContentModerationResult(
            check_id="mod_123",
            content_type=ContentType.TEXT,
            status=ComplianceStatus.PASS,
            risk_level=RiskLevel.LOW,
        )

        assert result.check_id == "mod_123"
        assert result.content_type == ContentType.TEXT
        assert result.status == ComplianceStatus.PASS
        assert result.risk_level == RiskLevel.LOW
        assert result.categories == {}
        assert result.flagged_categories == []
        assert result.confidence == 0.0
        assert result.recommendation == "allow"

    def test_content_moderation_result_with_categories(self):
        """Test content moderation result with category scores"""
        result = ContentModerationResult(
            check_id="mod_cat_123",
            content_type=ContentType.TEXT,
            status=ComplianceStatus.FLAGGED,
            risk_level=RiskLevel.MEDIUM,
            categories={
                ModerationCategory.HATE_SPEECH: 0.75,
                ModerationCategory.HARASSMENT: 0.45,
                ModerationCategory.VIOLENCE: 0.15,
            },
            flagged_categories=[ModerationCategory.HATE_SPEECH],
            confidence=0.85,
            recommendation="review",
            explanation="High confidence hate speech detected",
        )

        assert len(result.categories) == 3
        assert result.categories[ModerationCategory.HATE_SPEECH] == 0.75
        assert len(result.flagged_categories) == 1
        assert result.flagged_categories[0] == ModerationCategory.HATE_SPEECH
        assert result.confidence == 0.85
        assert result.recommendation == "review"
        assert "hate speech" in result.explanation

    def test_content_moderation_result_block_recommendation(self):
        """Test content moderation with block recommendation"""
        result = ContentModerationResult(
            check_id="mod_block_123",
            content_type=ContentType.IMAGE,
            status=ComplianceStatus.BLOCKED,
            risk_level=RiskLevel.HIGH,
            categories={
                ModerationCategory.CHILD_SAFETY: 0.95,
            },
            flagged_categories=[ModerationCategory.CHILD_SAFETY],
            confidence=0.98,
            recommendation="block",
            explanation="Child safety violation detected",
            details={"severity": "critical", "auto_reported": True},
        )

        assert result.risk_level == RiskLevel.HIGH
        assert result.recommendation == "block"
        assert result.details["severity"] == "critical"


class TestPIIDetectionResult:
    """Test PIIDetectionResult model"""

    def test_pii_detection_result_minimal(self):
        """Test PII detection result with no PII found"""
        result = PIIDetectionResult(
            check_id="pii_123",
            status=ComplianceStatus.PASS,
            risk_level=RiskLevel.NONE,
        )

        assert result.check_id == "pii_123"
        assert result.status == ComplianceStatus.PASS
        assert result.risk_level == RiskLevel.NONE
        assert result.detected_pii == []
        assert result.pii_count == 0
        assert result.pii_types == []
        assert result.needs_redaction is False

    def test_pii_detection_result_with_pii(self):
        """Test PII detection result with detected PII"""
        result = PIIDetectionResult(
            check_id="pii_detected_123",
            status=ComplianceStatus.FLAGGED,
            risk_level=RiskLevel.HIGH,
            detected_pii=[
                {
                    "type": "email",
                    "value": "***@***.com",
                    "location": "line 5",
                    "confidence": 0.95,
                },
                {
                    "type": "phone",
                    "value": "***-***-1234",
                    "location": "line 12",
                    "confidence": 0.88,
                },
                {
                    "type": "ssn",
                    "value": "***-**-****",
                    "location": "line 20",
                    "confidence": 0.92,
                },
            ],
            pii_count=3,
            pii_types=[PIIType.EMAIL, PIIType.PHONE, PIIType.SSN],
            needs_redaction=True,
        )

        assert len(result.detected_pii) == 3
        assert result.pii_count == 3
        assert len(result.pii_types) == 3
        assert PIIType.EMAIL in result.pii_types
        assert PIIType.SSN in result.pii_types
        assert result.needs_redaction is True
        assert result.risk_level == RiskLevel.HIGH

    def test_pii_detection_result_medical_info(self):
        """Test PII detection with medical information"""
        result = PIIDetectionResult(
            check_id="pii_medical_123",
            status=ComplianceStatus.BLOCKED,
            risk_level=RiskLevel.CRITICAL,
            detected_pii=[
                {
                    "type": "medical_info",
                    "value": "[REDACTED MEDICAL INFO]",
                    "location": "paragraph 3",
                    "confidence": 0.96,
                },
            ],
            pii_count=1,
            pii_types=[PIIType.MEDICAL_INFO],
            needs_redaction=True,
        )

        assert result.risk_level == RiskLevel.CRITICAL
        assert PIIType.MEDICAL_INFO in result.pii_types
        assert result.needs_redaction is True


class TestPromptInjectionResult:
    """Test PromptInjectionResult model"""

    def test_prompt_injection_result_no_detection(self):
        """Test prompt injection result with no injection detected"""
        result = PromptInjectionResult(
            check_id="injection_123",
            status=ComplianceStatus.PASS,
            risk_level=RiskLevel.NONE,
        )

        assert result.check_id == "injection_123"
        assert result.status == ComplianceStatus.PASS
        assert result.risk_level == RiskLevel.NONE
        assert result.is_injection_detected is False
        assert result.injection_type is None
        assert result.confidence == 0.0
        assert result.detected_patterns == []
        assert result.suspicious_tokens == []
        assert result.recommendation == "allow"

    def test_prompt_injection_result_direct_injection(self):
        """Test prompt injection result with direct injection detected"""
        result = PromptInjectionResult(
            check_id="injection_direct_123",
            status=ComplianceStatus.BLOCKED,
            risk_level=RiskLevel.HIGH,
            is_injection_detected=True,
            injection_type="direct",
            confidence=0.92,
            detected_patterns=["ignore_previous", "system_prompt_override"],
            suspicious_tokens=["ignore", "system", "override"],
            recommendation="block",
            explanation="Direct prompt injection attempt detected",
        )

        assert result.is_injection_detected is True
        assert result.injection_type == "direct"
        assert result.confidence == 0.92
        assert len(result.detected_patterns) == 2
        assert "ignore_previous" in result.detected_patterns
        assert len(result.suspicious_tokens) == 3
        assert result.recommendation == "block"

    def test_prompt_injection_result_jailbreak_attempt(self):
        """Test prompt injection result with jailbreak attempt"""
        result = PromptInjectionResult(
            check_id="injection_jailbreak_123",
            status=ComplianceStatus.FLAGGED,
            risk_level=RiskLevel.CRITICAL,
            is_injection_detected=True,
            injection_type="jailbreak",
            confidence=0.88,
            detected_patterns=[
                "dan_mode",
                "roleplay_override",
                "forget_instructions",
            ],
            suspicious_tokens=["DAN", "ignore", "pretend"],
            recommendation="block",
            explanation="Jailbreak attempt: DAN mode activation detected",
        )

        assert result.injection_type == "jailbreak"
        assert result.risk_level == RiskLevel.CRITICAL
        assert "dan_mode" in result.detected_patterns
        assert result.recommendation == "block"

    def test_prompt_injection_result_indirect_injection(self):
        """Test prompt injection result with indirect injection"""
        result = PromptInjectionResult(
            check_id="injection_indirect_123",
            status=ComplianceStatus.WARNING,
            risk_level=RiskLevel.MEDIUM,
            is_injection_detected=True,
            injection_type="indirect",
            confidence=0.65,
            detected_patterns=["context_manipulation"],
            suspicious_tokens=["context"],
            recommendation="review",
            explanation="Potential indirect injection via context manipulation",
        )

        assert result.injection_type == "indirect"
        assert result.risk_level == RiskLevel.MEDIUM
        assert result.recommendation == "review"


# ====================
# Request/Response Model Tests
# ====================

class TestComplianceCheckRequest:
    """Test ComplianceCheckRequest model"""

    def test_compliance_check_request_minimal(self):
        """Test compliance check request with minimal fields"""
        request = ComplianceCheckRequest(
            user_id="user_123",
            content_type=ContentType.TEXT,
            content="This is test content",
        )

        assert request.user_id == "user_123"
        assert request.content_type == ContentType.TEXT
        assert request.content == "This is test content"
        assert request.check_types == [ComplianceCheckType.CONTENT_MODERATION]
        assert request.organization_id is None
        assert request.policy_id is None

    def test_compliance_check_request_with_multiple_checks(self):
        """Test compliance check request with multiple check types"""
        request = ComplianceCheckRequest(
            user_id="user_456",
            organization_id="org_789",
            content_type=ContentType.TEXT,
            content="Sample text with potential PII",
            check_types=[
                ComplianceCheckType.CONTENT_MODERATION,
                ComplianceCheckType.PII_DETECTION,
                ComplianceCheckType.TOXICITY,
            ],
            policy_id="policy_123",
        )

        assert len(request.check_types) == 3
        assert ComplianceCheckType.PII_DETECTION in request.check_types
        assert request.policy_id == "policy_123"

    def test_compliance_check_request_with_file_content(self):
        """Test compliance check request for file content"""
        request = ComplianceCheckRequest(
            user_id="user_789",
            content_type=ContentType.IMAGE,
            content_id="file_123",
            content_url="https://storage.example.com/image.jpg",
            check_types=[ComplianceCheckType.CONTENT_MODERATION],
            metadata={"filename": "image.jpg", "size": 2048000},
        )

        assert request.content_type == ContentType.IMAGE
        assert request.content_id == "file_123"
        assert request.content_url == "https://storage.example.com/image.jpg"
        assert request.metadata["filename"] == "image.jpg"

    def test_compliance_check_request_with_session_tracking(self):
        """Test compliance check request with session tracking"""
        request = ComplianceCheckRequest(
            user_id="user_123",
            organization_id="org_456",
            session_id="session_789",
            request_id="req_abc",
            content_type=ContentType.PROMPT,
            content="Generate a story about...",
            check_types=[ComplianceCheckType.PROMPT_INJECTION],
        )

        assert request.session_id == "session_789"
        assert request.request_id == "req_abc"
        assert request.content_type == ContentType.PROMPT


class TestComplianceCheckResponse:
    """Test ComplianceCheckResponse model"""

    def test_compliance_check_response_pass(self):
        """Test compliance check response for passing check"""
        now = datetime.now(timezone.utc)

        response = ComplianceCheckResponse(
            check_id="check_123",
            status=ComplianceStatus.PASS,
            risk_level=RiskLevel.NONE,
            passed=True,
            message="Content passed all compliance checks",
            checked_at=now,
            processing_time_ms=125.5,
        )

        assert response.check_id == "check_123"
        assert response.status == ComplianceStatus.PASS
        assert response.passed is True
        assert response.risk_level == RiskLevel.NONE
        assert response.violations == []
        assert response.warnings == []
        assert response.action_required == "none"
        assert response.processing_time_ms == 125.5

    def test_compliance_check_response_with_violations(self):
        """Test compliance check response with violations"""
        now = datetime.now(timezone.utc)

        response = ComplianceCheckResponse(
            check_id="check_fail_123",
            status=ComplianceStatus.FAIL,
            risk_level=RiskLevel.HIGH,
            passed=False,
            violations=[
                {"type": "hate_speech", "confidence": 0.85, "category": "harassment"},
                {"type": "toxicity", "confidence": 0.72, "category": "offensive"},
            ],
            warnings=[
                {"type": "suspicious_pattern", "message": "Unusual language detected"},
            ],
            action_required="block",
            action_taken="content_blocked",
            message="Content blocked due to policy violations",
            checked_at=now,
            processing_time_ms=230.8,
        )

        assert response.passed is False
        assert len(response.violations) == 2
        assert len(response.warnings) == 1
        assert response.action_required == "block"
        assert response.action_taken == "content_blocked"
        assert response.risk_level == RiskLevel.HIGH

    def test_compliance_check_response_with_detailed_results(self):
        """Test compliance check response with detailed sub-results"""
        now = datetime.now(timezone.utc)

        mod_result = ContentModerationResult(
            check_id="mod_123",
            content_type=ContentType.TEXT,
            status=ComplianceStatus.WARNING,
            risk_level=RiskLevel.MEDIUM,
            categories={ModerationCategory.HARASSMENT: 0.65},
            confidence=0.7,
            recommendation="review",
        )

        pii_result = PIIDetectionResult(
            check_id="pii_123",
            status=ComplianceStatus.FLAGGED,
            risk_level=RiskLevel.HIGH,
            detected_pii=[{"type": "email", "value": "***@***.com"}],
            pii_count=1,
            pii_types=[PIIType.EMAIL],
        )

        response = ComplianceCheckResponse(
            check_id="check_detailed_123",
            status=ComplianceStatus.FLAGGED,
            risk_level=RiskLevel.HIGH,
            passed=False,
            moderation_result=mod_result,
            pii_result=pii_result,
            action_required="review",
            message="Content requires manual review",
            checked_at=now,
            processing_time_ms=350.2,
        )

        assert response.moderation_result is not None
        assert response.pii_result is not None
        assert response.moderation_result.check_id == "mod_123"
        assert response.pii_result.pii_count == 1
        assert response.action_required == "review"


class TestBatchComplianceCheckRequest:
    """Test BatchComplianceCheckRequest model"""

    def test_batch_compliance_check_request(self):
        """Test batch compliance check request"""
        request = BatchComplianceCheckRequest(
            user_id="user_123",
            organization_id="org_456",
            items=[
                {"content": "First message", "content_type": "text"},
                {"content": "Second message", "content_type": "text"},
                {"content_id": "file_123", "content_type": "image"},
            ],
            check_types=[
                ComplianceCheckType.CONTENT_MODERATION,
                ComplianceCheckType.PII_DETECTION,
            ],
        )

        assert request.user_id == "user_123"
        assert request.organization_id == "org_456"
        assert len(request.items) == 3
        assert len(request.check_types) == 2

    def test_batch_compliance_check_request_minimal(self):
        """Test batch compliance check request with minimal fields"""
        request = BatchComplianceCheckRequest(
            user_id="user_789",
            items=[{"content": "Test", "content_type": "text"}],
            check_types=[ComplianceCheckType.TOXICITY],
        )

        assert request.user_id == "user_789"
        assert request.organization_id is None
        assert len(request.items) == 1


class TestBatchComplianceCheckResponse:
    """Test BatchComplianceCheckResponse model"""

    def test_batch_compliance_check_response(self):
        """Test batch compliance check response"""
        now = datetime.now(timezone.utc)

        results = [
            ComplianceCheckResponse(
                check_id="check_1",
                status=ComplianceStatus.PASS,
                risk_level=RiskLevel.NONE,
                passed=True,
                message="Pass",
                checked_at=now,
                processing_time_ms=100.0,
            ),
            ComplianceCheckResponse(
                check_id="check_2",
                status=ComplianceStatus.FLAGGED,
                risk_level=RiskLevel.MEDIUM,
                passed=False,
                message="Flagged",
                checked_at=now,
                processing_time_ms=150.0,
            ),
        ]

        response = BatchComplianceCheckResponse(
            total_items=2,
            passed_items=1,
            failed_items=0,
            flagged_items=1,
            results=results,
            summary={
                "average_processing_time_ms": 125.0,
                "high_risk_items": 0,
            },
        )

        assert response.total_items == 2
        assert response.passed_items == 1
        assert response.failed_items == 0
        assert response.flagged_items == 1
        assert len(response.results) == 2
        assert response.summary["average_processing_time_ms"] == 125.0


class TestComplianceReportRequest:
    """Test ComplianceReportRequest model"""

    def test_compliance_report_request_minimal(self):
        """Test compliance report request with minimal fields"""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)

        request = ComplianceReportRequest(
            start_date=start,
            end_date=end,
        )

        assert request.start_date == start
        assert request.end_date == end
        assert request.organization_id is None
        assert request.user_id is None
        assert request.check_types is None
        assert request.include_violations is True
        assert request.include_statistics is True
        assert request.include_trends is False

    def test_compliance_report_request_with_filters(self):
        """Test compliance report request with filters"""
        start = datetime.now(timezone.utc) - timedelta(days=30)
        end = datetime.now(timezone.utc)

        request = ComplianceReportRequest(
            organization_id="org_123",
            user_id="user_456",
            start_date=start,
            end_date=end,
            check_types=[
                ComplianceCheckType.CONTENT_MODERATION,
                ComplianceCheckType.PII_DETECTION,
            ],
            risk_levels=[RiskLevel.HIGH, RiskLevel.CRITICAL],
            statuses=[ComplianceStatus.BLOCKED, ComplianceStatus.FLAGGED],
            include_violations=True,
            include_statistics=True,
            include_trends=True,
        )

        assert request.organization_id == "org_123"
        assert request.user_id == "user_456"
        assert len(request.check_types) == 2
        assert len(request.risk_levels) == 2
        assert len(request.statuses) == 2
        assert request.include_trends is True

    def test_compliance_report_request_organization_wide(self):
        """Test compliance report request for organization"""
        start = datetime.now(timezone.utc) - timedelta(days=90)
        end = datetime.now(timezone.utc)

        request = ComplianceReportRequest(
            organization_id="org_789",
            start_date=start,
            end_date=end,
            include_statistics=True,
            include_trends=True,
        )

        assert request.organization_id == "org_789"
        assert request.user_id is None


class TestComplianceReportResponse:
    """Test ComplianceReportResponse model"""

    def test_compliance_report_response_basic(self):
        """Test basic compliance report response"""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        now = datetime.now(timezone.utc)

        response = ComplianceReportResponse(
            report_id="report_123",
            period={"start": start, "end": end},
            total_checks=1000,
            passed_checks=850,
            failed_checks=100,
            flagged_checks=50,
            violations_by_type={
                "content_moderation": 75,
                "pii_detection": 25,
            },
            violations_by_category={
                "hate_speech": 30,
                "harassment": 25,
                "pii": 20,
            },
            high_risk_incidents=15,
            unique_users=250,
            top_violators=[
                {"user_id": "user_bad_1", "violation_count": 10},
                {"user_id": "user_bad_2", "violation_count": 8},
            ],
            generated_at=now,
        )

        assert response.report_id == "report_123"
        assert response.total_checks == 1000
        assert response.passed_checks == 850
        assert response.failed_checks == 100
        assert response.flagged_checks == 50
        assert len(response.violations_by_type) == 2
        assert response.high_risk_incidents == 15
        assert response.unique_users == 250
        assert len(response.top_violators) == 2

    def test_compliance_report_response_with_trends(self):
        """Test compliance report response with trend data"""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        now = datetime.now(timezone.utc)

        response = ComplianceReportResponse(
            report_id="report_trends_123",
            period={"start": start, "end": end},
            total_checks=500,
            passed_checks=400,
            failed_checks=80,
            flagged_checks=20,
            violations_by_type={"content_moderation": 50},
            violations_by_category={"hate_speech": 30},
            high_risk_incidents=5,
            unique_users=100,
            top_violators=[],
            daily_stats=[
                {"date": "2025-12-14", "total_checks": 75, "violations": 8},
                {"date": "2025-12-15", "total_checks": 80, "violations": 10},
            ],
            generated_at=now,
        )

        assert response.daily_stats is not None
        assert len(response.daily_stats) == 2
        assert response.daily_stats[0]["date"] == "2025-12-14"

    def test_compliance_report_response_with_violations(self):
        """Test compliance report response with detailed violations"""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        now = datetime.now(timezone.utc)

        violations = [
            ComplianceCheck(
                check_id="check_1",
                check_type=ComplianceCheckType.CONTENT_MODERATION,
                content_type=ContentType.TEXT,
                status=ComplianceStatus.BLOCKED,
                user_id="user_123",
                risk_level=RiskLevel.HIGH,
            ),
        ]

        response = ComplianceReportResponse(
            report_id="report_detailed_123",
            period={"start": start, "end": end},
            total_checks=100,
            passed_checks=85,
            failed_checks=10,
            flagged_checks=5,
            violations_by_type={"content_moderation": 10},
            violations_by_category={"harassment": 10},
            high_risk_incidents=3,
            unique_users=50,
            top_violators=[],
            violations=violations,
            generated_at=now,
            metadata={"report_type": "detailed", "requested_by": "admin_123"},
        )

        assert response.violations is not None
        assert len(response.violations) == 1
        assert response.metadata["report_type"] == "detailed"


class TestCompliancePolicyRequest:
    """Test CompliancePolicyRequest model"""

    def test_compliance_policy_request_minimal(self):
        """Test compliance policy request with minimal fields"""
        request = CompliancePolicyRequest(
            policy_name="Basic Policy",
            content_types=[ContentType.TEXT],
            check_types=[ComplianceCheckType.CONTENT_MODERATION],
            rules={"max_toxicity": 0.7},
        )

        assert request.policy_name == "Basic Policy"
        assert len(request.content_types) == 1
        assert len(request.check_types) == 1
        assert request.rules["max_toxicity"] == 0.7
        assert request.auto_block is True
        assert request.require_human_review is False
        assert request.notification_enabled is True

    def test_compliance_policy_request_comprehensive(self):
        """Test compliance policy request with all fields"""
        request = CompliancePolicyRequest(
            policy_name="Enterprise Security Policy",
            organization_id="org_123",
            content_types=[ContentType.TEXT, ContentType.IMAGE, ContentType.VIDEO],
            check_types=[
                ComplianceCheckType.CONTENT_MODERATION,
                ComplianceCheckType.PII_DETECTION,
                ComplianceCheckType.GDPR_COMPLIANCE,
            ],
            rules={
                "strict_mode": True,
                "auto_redact_pii": True,
                "block_hate_speech": True,
            },
            thresholds={
                "violence": 0.5,
                "sexual": 0.6,
                "harassment": 0.4,
            },
            auto_block=True,
            require_human_review=True,
            notification_enabled=True,
        )

        assert request.policy_name == "Enterprise Security Policy"
        assert request.organization_id == "org_123"
        assert len(request.content_types) == 3
        assert len(request.check_types) == 3
        assert request.thresholds["violence"] == 0.5
        assert request.require_human_review is True


# ====================
# System Model Tests
# ====================

class TestComplianceServiceStatus:
    """Test ComplianceServiceStatus model"""

    def test_compliance_service_status_operational(self):
        """Test compliance service status when operational"""
        status = ComplianceServiceStatus(
            database_connected=True,
            nats_connected=True,
            providers={
                "openai": True,
                "aws_comprehend": True,
                "perspective_api": False,
            },
        )

        assert status.service == "compliance_service"
        assert status.status == "operational"
        assert status.port == 8250
        assert status.version == "1.0.0"
        assert status.database_connected is True
        assert status.nats_connected is True
        assert status.providers["openai"] is True
        assert status.providers["perspective_api"] is False

    def test_compliance_service_status_degraded(self):
        """Test compliance service status with degraded providers"""
        status = ComplianceServiceStatus(
            database_connected=True,
            nats_connected=True,
            providers={
                "openai": True,
                "aws_comprehend": False,
                "perspective_api": False,
            },
        )

        assert status.database_connected is True
        assert status.providers["openai"] is True
        assert status.providers["aws_comprehend"] is False


class TestComplianceStats:
    """Test ComplianceStats model"""

    def test_compliance_stats_creation(self):
        """Test compliance statistics model"""
        stats = ComplianceStats(
            total_checks_today=150,
            total_checks_7d=1050,
            total_checks_30d=4500,
            violations_today=12,
            violations_7d=85,
            violations_30d=360,
            blocked_content_today=5,
            pending_reviews=8,
            avg_processing_time_ms=125.5,
            checks_by_type={
                "content_moderation": 2000,
                "pii_detection": 1500,
                "toxicity": 1000,
            },
            violations_by_risk={
                "low": 200,
                "medium": 120,
                "high": 35,
                "critical": 5,
            },
        )

        assert stats.total_checks_today == 150
        assert stats.total_checks_30d == 4500
        assert stats.violations_today == 12
        assert stats.violations_30d == 360
        assert stats.blocked_content_today == 5
        assert stats.pending_reviews == 8
        assert stats.avg_processing_time_ms == 125.5
        assert stats.checks_by_type["content_moderation"] == 2000
        assert stats.violations_by_risk["critical"] == 5

    def test_compliance_stats_daily_metrics(self):
        """Test daily compliance metrics"""
        stats = ComplianceStats(
            total_checks_today=200,
            total_checks_7d=1400,
            total_checks_30d=6000,
            violations_today=15,
            violations_7d=105,
            violations_30d=450,
            blocked_content_today=8,
            pending_reviews=12,
            avg_processing_time_ms=130.0,
            checks_by_type={"content_moderation": 100},
            violations_by_risk={"high": 10},
        )

        assert stats.total_checks_today == 200
        assert stats.violations_today == 15
        assert stats.blocked_content_today == 8


if __name__ == "__main__":
    pytest.main([__file__])
