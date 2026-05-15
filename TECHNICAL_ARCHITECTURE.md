# AI CLI Orchestrator - Technical Architecture

## 🏛️ System Architecture Overview

This document provides detailed technical specifications for the AI CLI Orchestrator system.

## 🔄 System Flow Diagrams

### 1. Request Flow

```
User Request
    ↓
React UI (TypeScript)
    ↓
WebSocket/REST API
    ↓
FastAPI Backend
    ↓
Orchestration Engine
    ↓
┌─────────────────────────────────────┐
│   Routing Decision Algorithm        │
│                                     │
│  1. Check current CLI status        │
│  2. Analyze task type               │
│  3. Check rate limits               │
│  4. Select optimal CLI              │
│  5. Load context if needed          │
└─────────────────────────────────────┘
    ↓
CLI Wrapper (Selected)
    ↓
Actual CLI Process
    ↓
Output Stream
    ↓
WebSocket → React UI
```

### 2. Rate Limit Detection Flow

```
CLI Execution
    ↓
Monitor Service (Continuous)
    ↓
┌─────────────────────────────────────┐
│   Detection Strategies              │
│                                     │
│  ✓ Response time analysis           │
│  ✓ Error message parsing            │
│  ✓ HTTP status codes                │
│  ✓ Token usage tracking             │
│  ✓ Request count monitoring         │
└─────────────────────────────────────┘
    ↓
Rate Limit Detected?
    ↓ YES
┌─────────────────────────────────────┐
│   Failover Process                  │
│                                     │
│  1. Pause current CLI               │
│  2. Save current state              │
│  3. Select next available CLI       │
│  4. Sync context                    │
│  5. Resume task                     │
└─────────────────────────────────────┘
    ↓
Continue Execution
```

### 3. Context Synchronization Flow

```
Task Start/CLI Switch
    ↓
Context Manager
    ↓
┌─────────────────────────────────────┐
│   Context Components                │
│                                     │
│  • skill.md (capabilities)          │
│  • plan.md (project plan)           │
│  • session.yaml (state)             │
│  • task_history (previous work)     │
└─────────────────────────────────────┘
    ↓
Calculate Context Diff
    ↓
┌─────────────────────────────────────┐
│   Optimization                      │
│                                     │
│  • Send only changes                │
│  • Compress large contexts          │
│  • Cache frequently used data       │
│  • Incremental updates              │
└─────────────────────────────────────┘
    ↓
Send to Target CLI
    ↓
Verify Sync Success
```

### 4. Session Management Flow

```
Session Start
    ↓
Load/Create Session YAML
    ↓
┌─────────────────────────────────────┐
│   Session Data                      │
│                                     │
│  • session_id                       │
│  • project_name                     │
│  • current_cli                      │
│  • context_hashes                   │
│  • cli_usage_stats                  │
│  • task_history                     │
└─────────────────────────────────────┘
    ↓
During Execution
    ↓
┌─────────────────────────────────────┐
│   Continuous Updates                │
│                                     │
│  • After each task                  │
│  • On CLI switch                    │
│  • On context change                │
│  • Every 5 minutes (checkpoint)     │
└─────────────────────────────────────┘
    ↓
Save to YAML
    ↓
Session End/Recovery
```

## 🧩 Component Details

### 1. CLI Wrapper Base Class

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncIterator
from dataclasses import dataclass
from enum import Enum

class CLIStatus(Enum):
    AVAILABLE = "available"
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    OFFLINE = "offline"

@dataclass
class CLIResponse:
    success: bool
    output: str
    error: Optional[str]
    execution_time: float
    tokens_used: Optional[int]
    rate_limit_hit: bool

class BaseCLIWrapper(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.name = config['name']
        self.slug = config['slug']
        self.command = config['command']
        self.rate_limits = config['rate_limits']
        self.specialties = config['specialties']
        self.status = CLIStatus.AVAILABLE
        self.usage_stats = {
            'requests_today': 0,
            'requests_hour': 0,
            'last_request': None
        }
    
    @abstractmethod
    async def execute(self, prompt: str, context: Dict[str, Any]) -> CLIResponse:
        """Execute command with given prompt and context"""
        pass
    
    @abstractmethod
    async def stream_execute(self, prompt: str, context: Dict[str, Any]) -> AsyncIterator[str]:
        """Stream execution output in real-time"""
        pass
    
    @abstractmethod
    def check_rate_limit(self) -> bool:
        """Check if rate limit is approaching or hit"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize CLI connection and verify authentication"""
        pass
    
    def update_usage(self, tokens: Optional[int] = None):
        """Update usage statistics"""
        self.usage_stats['requests_today'] += 1
        self.usage_stats['requests_hour'] += 1
        self.usage_stats['last_request'] = datetime.now()
    
    def can_handle_task(self, task_type: str) -> bool:
        """Check if this CLI can handle the given task type"""
        return task_type in self.specialties or 'general' in self.specialties
```

### 2. Orchestration Engine

```python
from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime

class OrchestrationEngine:
    def __init__(self, cli_wrappers: List[BaseCLIWrapper]):
        self.cli_wrappers = {cli.slug: cli for cli in cli_wrappers}
        self.current_cli: Optional[str] = None
        self.router = TaskRouter(self.cli_wrappers)
        self.monitor = MonitorService(self.cli_wrappers)
        self.session_manager = SessionManager()
        self.context_manager = ContextManager()
    
    async def execute_task(self, task: Dict[str, Any]) -> CLIResponse:
        """Main task execution with automatic failover"""
        
        # 1. Classify task and select CLI
        selected_cli = await self.router.select_cli(task)
        
        # 2. Check and sync context
        context = await self.context_manager.get_context(selected_cli)
        
        # 3. Execute with monitoring
        try:
            response = await self._execute_with_monitoring(
                selected_cli, 
                task['prompt'], 
                context
            )
            
            # 4. Update session
            await self.session_manager.update_task_history(task, response)
            
            return response
            
        except RateLimitException:
            # 5. Automatic failover
            return await self._handle_failover(task, selected_cli)
    
    async def _execute_with_monitoring(
        self, 
        cli_slug: str, 
        prompt: str, 
        context: Dict[str, Any]
    ) -> CLIResponse:
        """Execute with real-time monitoring"""
        
        cli = self.cli_wrappers[cli_slug]
        
        # Start monitoring
        monitor_task = asyncio.create_task(
            self.monitor.watch_execution(cli_slug)
        )
        
        try:
            # Execute
            response = await cli.execute(prompt, context)
            
            # Check for rate limit indicators
            if response.rate_limit_hit or cli.check_rate_limit():
                raise RateLimitException(cli_slug)
            
            return response
            
        finally:
            monitor_task.cancel()
    
    async def _handle_failover(
        self, 
        task: Dict[str, Any], 
        failed_cli: str
    ) -> CLIResponse:
        """Handle automatic failover to another CLI"""
        
        # 1. Mark current CLI as rate limited
        self.cli_wrappers[failed_cli].status = CLIStatus.RATE_LIMITED
        
        # 2. Select alternative CLI
        alternative_cli = await self.router.select_cli(
            task, 
            exclude=[failed_cli]
        )
        
        if not alternative_cli:
            raise NoAvailableCLIException("All CLIs are rate limited")
        
        # 3. Sync context to new CLI
        await self.context_manager.sync_to_cli(alternative_cli)
        
        # 4. Retry execution
        context = await self.context_manager.get_context(alternative_cli)
        return await self._execute_with_monitoring(
            alternative_cli, 
            task['prompt'], 
            context
        )
```

### 3. Task Router

```python
from typing import List, Optional, Dict, Any
import re

class TaskRouter:
    def __init__(self, cli_wrappers: Dict[str, BaseCLIWrapper]):
        self.cli_wrappers = cli_wrappers
        self.task_patterns = {
            'frontend': [
                r'\b(react|vue|angular|component|ui|css|html|frontend)\b',
                r'\b(styling|layout|responsive|design)\b'
            ],
            'backend': [
                r'\b(api|endpoint|server|database|backend)\b',
                r'\b(authentication|authorization|middleware)\b'
            ],
            'algorithm': [
                r'\b(algorithm|optimize|performance|complexity)\b',
                r'\b(sort|search|tree|graph)\b'
            ]
        }
    
    async def select_cli(
        self, 
        task: Dict[str, Any], 
        exclude: List[str] = None
    ) -> str:
        """Select optimal CLI for task"""
        
        exclude = exclude or []
        
        # 1. Classify task type
        task_type = self._classify_task(task['prompt'])
        
        # 2. Get available CLIs
        available_clis = [
            cli for slug, cli in self.cli_wrappers.items()
            if slug not in exclude and cli.status == CLIStatus.AVAILABLE
        ]
        
        if not available_clis:
            raise NoAvailableCLIException()
        
        # 3. Score CLIs based on specialty match
        scored_clis = []
        for cli in available_clis:
            score = self._calculate_score(cli, task_type)
            scored_clis.append((score, cli))
        
        # 4. Sort by score and select best
        scored_clis.sort(reverse=True, key=lambda x: x[0])
        
        return scored_clis[0][1].slug
    
    def _classify_task(self, prompt: str) -> str:
        """Classify task based on prompt content"""
        
        prompt_lower = prompt.lower()
        
        for task_type, patterns in self.task_patterns.items():
            for pattern in patterns:
                if re.search(pattern, prompt_lower):
                    return task_type
        
        return 'general'
    
    def _calculate_score(self, cli: BaseCLIWrapper, task_type: str) -> float:
        """Calculate CLI suitability score"""
        
        score = 0.0
        
        # Specialty match
        if task_type in cli.specialties:
            score += 10.0
        elif 'general' in cli.specialties:
            score += 5.0
        
        # Rate limit headroom
        daily_limit = cli.rate_limits.get('daily', float('inf'))
        usage = cli.usage_stats['requests_today']
        headroom = (daily_limit - usage) / daily_limit
        score += headroom * 5.0
        
        # Priority (lower is better)
        score += (10 - cli.priority) * 2.0
        
        return score
```

### 4. Context Manager

```python
import hashlib
from typing import Dict, Any
import yaml

class ContextManager:
    def __init__(self):
        self.skill_md_path = "shared/skill.md"
        self.plan_md_path = "shared/plan.md"
        self.context_cache = {}
    
    async def get_context(self, cli_slug: str) -> Dict[str, Any]:
        """Get context for specific CLI"""
        
        # Read shared files
        skill_content = await self._read_file(self.skill_md_path)
        plan_content = await self._read_file(self.plan_md_path)
        
        # Calculate hashes
        skill_hash = self._hash_content(skill_content)
        plan_hash = self._hash_content(plan_content)
        
        # Check if CLI needs update
        cached = self.context_cache.get(cli_slug, {})
        needs_update = (
            cached.get('skill_hash') != skill_hash or
            cached.get('plan_hash') != plan_hash
        )
        
        if needs_update:
            # Prepare context
            context = {
                'skill': skill_content,
                'plan': plan_content,
                'skill_hash': skill_hash,
                'plan_hash': plan_hash,
                'updated_at': datetime.now().isoformat()
            }
            
            # Update cache
            self.context_cache[cli_slug] = context
            
            return context
        
        return cached
    
    async def sync_to_cli(self, cli_slug: str) -> bool:
        """Sync context to specific CLI"""
        
        context = await self.get_context(cli_slug)
        
        # In real implementation, this would send context to CLI
        # For now, just update cache
        self.context_cache[cli_slug] = context
        
        return True
    
    def _hash_content(self, content: str) -> str:
        """Generate hash of content"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def _read_file(self, path: str) -> str:
        """Read file content"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return ""
```

### 5. Session Manager

```python
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

class SessionManager:
    def __init__(self, sessions_dir: str = "shared/sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: Optional[Dict[str, Any]] = None
    
    async def create_session(self, project_name: str) -> str:
        """Create new session"""
        
        session_id = f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = {
            'session_id': session_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'project_name': project_name,
            'current_cli': None,
            'context': {
                'skill_md_hash': None,
                'plan_md_hash': None,
                'last_sync': None
            },
            'cli_usage': {},
            'task_history': []
        }
        
        await self._save_session(session)
        self.current_session = session
        
        return session_id
    
    async def load_session(self, session_id: str) -> Dict[str, Any]:
        """Load existing session"""
        
        session_path = self.sessions_dir / f"{session_id}.yaml"
        
        with open(session_path, 'r') as f:
            session = yaml.safe_load(f)
        
        self.current_session = session
        return session
    
    async def update_task_history(
        self, 
        task: Dict[str, Any], 
        response: CLIResponse
    ):
        """Update task history in session"""
        
        if not self.current_session:
            return
        
        task_entry = {
            'task_id': f"task_{len(self.current_session['task_history']) + 1:03d}",
            'description': task.get('description', task['prompt'][:100]),
            'cli_used': task.get('cli_used'),
            'status': 'completed' if response.success else 'failed',
            'started_at': task.get('started_at'),
            'completed_at': datetime.now().isoformat(),
            'execution_time': response.execution_time
        }
        
        self.current_session['task_history'].append(task_entry)
        self.current_session['updated_at'] = datetime.now().isoformat()
        
        await self._save_session(self.current_session)
    
    async def _save_session(self, session: Dict[str, Any]):
        """Save session to YAML file"""
        
        session_path = self.sessions_dir / f"{session['session_id']}.yaml"
        
        with open(session_path, 'w') as f:
            yaml.dump(session, f, default_flow_style=False, sort_keys=False)
```

## 🔌 API Endpoints

### REST API

```python
from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="AI CLI Orchestrator API")

class TaskRequest(BaseModel):
    prompt: str
    task_type: Optional[str] = None
    preferred_cli: Optional[str] = None

class TaskResponse(BaseModel):
    task_id: str
    cli_used: str
    success: bool
    output: str
    execution_time: float

@app.post("/api/execute", response_model=TaskResponse)
async def execute_task(request: TaskRequest):
    """Execute a task using optimal CLI"""
    
    task = {
        'prompt': request.prompt,
        'task_type': request.task_type,
        'preferred_cli': request.preferred_cli
    }
    
    response = await orchestrator.execute_task(task)
    
    return TaskResponse(
        task_id=f"task_{datetime.now().timestamp()}",
        cli_used=orchestrator.current_cli,
        success=response.success,
        output=response.output,
        execution_time=response.execution_time
    )

@app.get("/api/status")
async def get_status():
    """Get system status"""
    
    return {
        'clis': [
            {
                'name': cli.name,
                'slug': cli.slug,
                'status': cli.status.value,
                'usage': cli.usage_stats
            }
            for cli in orchestrator.cli_wrappers.values()
        ],
        'current_session': orchestrator.session_manager.current_session
    }

@app.get("/api/sessions")
async def list_sessions():
    """List all sessions"""
    
    sessions_dir = Path("shared/sessions")
    sessions = []
    
    for session_file in sessions_dir.glob("*.yaml"):
        with open(session_file, 'r') as f:
            session = yaml.safe_load(f)
            sessions.append({
                'session_id': session['session_id'],
                'project_name': session['project_name'],
                'created_at': session['created_at'],
                'task_count': len(session['task_history'])
            })
    
    return sessions

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    
    await websocket.accept()
    
    try:
        while True:
            # Send status updates
            status = await get_status()
            await websocket.send_json(status)
            await asyncio.sleep(1)
    except:
        pass
```

## 🎨 Frontend Architecture

### Component Structure

```typescript
// Main App Structure
App
├── Dashboard
│   ├── StatusMonitor
│   │   ├── CLIStatusCard (x8)
│   │   └── SystemHealthIndicator
│   ├── TerminalViewer
│   │   ├── TerminalTabs
│   │   └── XTermComponent
│   ├── Analytics
│   │   ├── UsageChart
│   │   ├── RateLimitGraph
│   │   └── PerformanceMetrics
│   └── ConfigPanel
│       ├── CLIConfiguration
│       └── SessionManagement
```

### State Management (Zustand)

```typescript
interface OrchestratorState {
  clis: CLIStatus[];
  currentSession: Session | null;
  taskHistory: Task[];
  isExecuting: boolean;
  
  // Actions
  executeTask: (prompt: string) => Promise<void>;
  switchCLI: (cliSlug: string) => void;
  loadSession: (sessionId: string) => Promise<void>;
  updateCLIStatus: (cliSlug: string, status: string) => void;
}

const useOrchestratorStore = create<OrchestratorState>((set, get) => ({
  clis: [],
  currentSession: null,
  taskHistory: [],
  isExecuting: false,
  
  executeTask: async (prompt: string) => {
    set({ isExecuting: true });
    
    try {
      const response = await api.executeTask({ prompt });
      
      set(state => ({
        taskHistory: [...state.taskHistory, response],
        isExecuting: false
      }));
    } catch (error) {
      set({ isExecuting: false });
      throw error;
    }
  },
  
  // ... other actions
}));
```

## 🔒 Security Considerations

### 1. Credential Management
- Store API keys in environment variables
- Use encrypted storage for sensitive data
- Implement credential rotation
- Never log credentials

### 2. Input Validation
- Sanitize all user inputs
- Validate CLI commands before execution
- Implement rate limiting on API endpoints
- Use Pydantic for request validation

### 3. Process Isolation
- Run CLI processes in isolated environments
- Implement resource limits
- Monitor for suspicious activity
- Implement timeout mechanisms

## 📊 Performance Optimization

### 1. Caching Strategy
- Cache CLI responses for identical prompts
- Cache context hashes to avoid redundant syncs
- Implement LRU cache for frequently used data

### 2. Async Operations
- Use asyncio for concurrent CLI execution
- Implement connection pooling
- Stream large outputs instead of buffering

### 3. Resource Management
- Implement process pools
- Clean up terminated processes
- Monitor memory usage
- Implement garbage collection for old sessions

## 🧪 Testing Strategy

### Unit Tests
- Test each CLI wrapper independently
- Test routing algorithm with various scenarios
- Test context synchronization logic
- Test session management operations

### Integration Tests
- Test CLI switching scenarios
- Test failover mechanisms
- Test context sync across CLIs
- Test session recovery

### End-to-End Tests
- Test complete user workflows
- Test rate limit handling
- Test parallel execution
- Test UI interactions

## 📈 Monitoring & Observability

### Metrics to Track
- Request count per CLI
- Average response time
- Rate limit hit frequency
- Failover success rate
- Context sync time
- Session recovery time

### Logging Strategy
- Structured logging with JSON format
- Log levels: DEBUG, INFO, WARNING, ERROR
- Separate logs for each CLI
- Centralized log aggregation

## 🚀 Deployment

### Development
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Production
```bash
# Using Docker Compose
docker-compose up -d
```

This architecture provides a solid foundation for building a robust, scalable AI CLI orchestrator that can handle the complexities of managing multiple AI coding assistants efficiently.