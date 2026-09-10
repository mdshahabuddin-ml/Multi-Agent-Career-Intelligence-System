# Hermes Architecture

## Overview

Hermes is the multi-agent framework for the Career Intelligence System. It provides the infrastructure for building, orchestrating, and managing AI agents that perform career-related tasks.

## Module Structure

```
backend/hermes/
├── core/           # Base classes for agents, state, and tasks
├── memory/         # Agent memory storage and retrieval
├── skills/         # Skill registration, discovery, and execution
├── agents/         # Specialized agent implementations
├── automation/     # Task scheduling and execution
├── browser/        # Web browsing capabilities
├── gateway/        # API gateway and external integrations
├── mcp/            # Model Context Protocol client
├── approval/       # Human-in-the-loop approval workflows
└── learning/       # Feedback collection and improvement tracking
```

## Core Concepts

### Agent
An autonomous unit that processes tasks. Agents have:
- A unique ID and configuration
- Mutable state for tracking context
- A history of executed tasks
- Event callbacks for lifecycle hooks

### Task
A unit of work with a defined lifecycle:
- `pending` → `in_progress` → `completed` | `failed` | `cancelled`
- Tasks carry input data, metadata, and tags
- Results are captured in `TaskResult` objects

### State
Thread-safe state management for agents:
- `AgentState`: per-agent state with context and history
- `StateManager`: centralized registry for multi-agent scenarios

## Memory System

### Storage
File-system based persistence for agent memories:
- Organized by agent ID and category
- JSON-based storage with index for fast lookups
- CRUD operations with search capabilities

### Retrieval
Relevance-based memory retrieval:
- Text matching for query relevance
- Recency weighting for temporal context
- Configurable scoring weights

## Skills

### Registry
Thread-safe catalog of available skills:
- Registration with metadata (description, parameters, tags)
- Search by name, description, or tags
- Execution statistics tracking

### Execution
Safe skill execution with:
- Timeout enforcement
- Error handling and statistics
- Async support

## Agent Types

### PlannerAgent
Decomposes high-level goals into structured task plans:
- Analyzes goals and constraints
- Identifies dependencies between subtasks
- Supports plan revision based on failures

### SupervisorAgent
Coordinates sub-agent execution:
- Manages a pool of sub-agents
- Parallel task execution
- Progress monitoring and aggregation

### SubAgent
Lightweight worker agents:
- Execute specific task types
- Configurable handlers
- Factory method for quick creation

## Automation

### TaskScheduler
Manages timed and recurring tasks:
- One-time and recurring scheduling
- Delay-based scheduling
- Async execution loop

### TaskRunner
Controlled task execution:
- Concurrency limits via semaphores
- Handler registration by task type
- Batch execution support

## External Integrations

### BrowserManager
Web browsing capabilities for agents:
- Navigation and content extraction
- Form interaction
- Screenshot capture

### GatewayRouter
Request routing between agents and services:
- Route registration and management
- Middleware pipeline
- Method-based routing

### MCPClient
Model Context Protocol integration:
- Tool discovery and invocation
- Resource access
- Server connection management

## Safety & Governance

### ApprovalManager
Human-in-the-loop workflows:
- Request approval for sensitive actions
- Approve/reject with notes
- Timeout handling

### Learning
Continuous improvement:
- `FeedbackCollector`: gather performance feedback
- `ImprovementTracker`: analyze and suggest improvements

## Data Storage

```
data/hermes/
├── memory/     # Agent memory files (JSON)
├── skills/     # Skill definitions
└── tasks/      # Task execution history
```

## Testing

```
tests/hermes/
├── test_agent.py       # Core agent tests
├── test_memory.py      # Memory system tests
├── test_skills.py      # Skill system tests
└── test_automation.py  # Automation tests
```

## Design Principles

1. **Modularity**: Each module has a single responsibility
2. **Thread Safety**: Shared resources use proper synchronization
3. **Extensibility**: Easy to add new agent types and skills
4. **Safety**: Timeouts, approval workflows, and error handling
5. **Observability**: Comprehensive logging and statistics
