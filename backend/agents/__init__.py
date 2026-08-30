"""
Agents Package for CareerIntel AI.

This package contains all agent implementations, orchestration,
communication, memory, and human-in-the-loop systems.
"""

from backend.agents.registry import (
    AgentRegistry,
    AgentConfig,
    AgentStatus,
    AgentRole,
    AgentCapability,
    BaseAgent,
    agent_registry,
    create_agent_config,
)

from backend.agents.communication.protocol import (
    AgentMessage,
    MessageType,
    MessagePriority,
    MessageBus,
    CommunicationChannel,
    message_bus,
    create_request,
    create_response,
    create_notification,
    create_handoff,
)

from backend.agents.memory.shared_memory import (
    SharedMemory,
    MemoryEntry,
    MemoryScope,
    MemoryType,
    ConversationContext,
    shared_memory,
    remember,
    recall,
    search_memory,
    start_conversation,
    get_conversation,
)

from backend.agents.orchestration.workflow_orchestrator import (
    BaseOrchestrator,
    SequentialOrchestrator,
    ParallelOrchestrator,
    HumanInTheLoopOrchestrator,
    Workflow,
    WorkflowStep,
    WorkflowExecution,
    OrchestrationState,
    AgentRole,
    create_research_workflow,
    create_job_matching_workflow,
)

from backend.agents.human_loop.intervention import (
    HumanLoopManager,
    HumanIntervention,
    HumanFeedback,
    InterventionType,
    InterventionPriority,
    InterventionStatus,
    HumanInterface,
    ConsoleHumanInterface,
    WebHumanInterface,
    console_interface,
    web_interface,
    human_loop_manager,
)

# Existing agent modules (backward compatibility)
from backend.agents.jobs import (
    JobSearchAgent,
    JobNormalizer,
    DuplicateDetector,
    RequirementExtractor,
    JobMatchingAgent,
    OpportunityRanker,
    RawJob,
    NormalizedJob,
    MockJobProvider,
)

from backend.agents.candidate import (
    ProfileAgent,
    ResumeParserAgent,
    SkillExtractionAgent,
    ProjectAnalyzerAgent,
    ExperienceAnalyzerAgent,
)

from backend.agents.research import (
    ResearchSupervisor,
    ResearchPlanner,
    WebResearcher,
    NewsResearcher,
    JobMarketResearcher,
    CompanyResearcher,
    AcademicResearcher,
    EvidenceAgent,
    VerificationAgent,
    AnalysisAgent,
    SynthesisAgent,
    ReportAgent,
)

from backend.agents.career import (
    SkillGapAgent,
    CareerPathAgent,
    LearningAgent,
    CareerAdvisor,
)

from backend.agents.application import (
    ATSResumeAgent,
    ResumeReviewerAgent,
    CoverLetterAgent,
    ApplicationAnswerAgent,
    ApplicationAgent,
)

__all__ = [
    # Registry
    "AgentRegistry",
    "AgentConfig",
    "AgentStatus",
    "AgentRole",
    "AgentCapability",
    "BaseAgent",
    "agent_registry",
    "create_agent_config",
    # Communication
    "AgentMessage",
    "MessageType",
    "MessagePriority",
    "MessageBus",
    "CommunicationChannel",
    "message_bus",
    "create_request",
    "create_response",
    "create_notification",
    "create_handoff",
    # Memory
    "SharedMemory",
    "MemoryEntry",
    "MemoryScope",
    "MemoryType",
    "ConversationContext",
    "shared_memory",
    "remember",
    "recall",
    "search_memory",
    "start_conversation",
    "get_conversation",
    # Orchestration
    "BaseOrchestrator",
    "SequentialOrchestrator",
    "ParallelOrchestrator",
    "HumanInTheLoopOrchestrator",
    "Workflow",
    "WorkflowStep",
    "WorkflowExecution",
    "OrchestrationState",
    "create_research_workflow",
    "create_job_matching_workflow",
    # Human Loop
    "HumanLoopManager",
    "HumanIntervention",
    "HumanFeedback",
    "InterventionType",
    "InterventionPriority",
    "InterventionStatus",
    "HumanInterface",
    "ConsoleHumanInterface",
    "WebHumanInterface",
    "console_interface",
    "web_interface",
    "human_loop_manager",
    # Existing agents
    "JobSearchAgent",
    "JobNormalizer",
    "DuplicateDetector",
    "RequirementExtractor",
    "JobMatchingAgent",
    "OpportunityRanker",
    "RawJob",
    "NormalizedJob",
    "MockJobProvider",
    "ProfileAgent",
    "ResumeParserAgent",
    "SkillExtractionAgent",
    "ProjectAnalyzerAgent",
    "ExperienceAnalyzerAgent",
    "ResearchSupervisor",
    "ResearchPlanner",
    "WebResearcher",
    "NewsResearcher",
    "JobMarketResearcher",
    "CompanyResearcher",
    "AcademicResearcher",
    "EvidenceAgent",
    "VerificationAgent",
    "AnalysisAgent",
    "SynthesisAgent",
    "ReportAgent",
    "SkillGapAgent",
    "CareerPathAgent",
    "LearningAgent",
    "CareerAdvisor",
    "ATSResumeAgent",
    "ResumeReviewerAgent",
    "CoverLetterAgent",
    "ApplicationAnswerAgent",
    "ApplicationAgent",
]