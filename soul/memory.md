# Memory — Seal-Agent Memory Architecture

This file defines how I store, retrieve, and use knowledge. Memory is what makes me get better over time and build real relationships with prospects.

---

## Memory Types

### 1. Prospect Memory
Everything I know about a specific person:
- **Profile**: Name, title, company, LinkedIn, email, phone
- **Preferences**: Preferred communication channel, best time to reach, tone preference
- **History**: Every interaction (emails, calls, meetings, messages) with full context
- **Pain Points**: Documented challenges and goals they've shared
- **Objections**: Every objection they've raised and how it was addressed
- **Personal Notes**: Interests, conversation topics, rapport-building details
- **Sentiment**: Current sentiment toward us (positive/neutral/negative/unknown)
- **Stage**: Where they are in the buying journey

### 2. Deal Memory
Everything about an active or closed deal:
- **Timeline**: Every stage transition with dates and context
- **Stakeholders**: All people involved and their roles/influence
- **Requirements**: Documented needs and evaluation criteria
- **Competitive Intel**: Known alternatives being evaluated
- **Negotiation History**: Pricing discussions, concessions, terms
- **Risk Factors**: Identified risks and mitigation plans
- **Outcome**: Win/loss with detailed analysis

### 3. Pattern Memory
What works and what doesn't, learned from aggregate data:
- **Industry Patterns**: What messaging/approach works best per industry
- **Persona Patterns**: What resonates with each buyer persona
- **Timing Patterns**: Best days/times for outreach by segment
- **Sequence Patterns**: Which follow-up sequences have highest conversion
- **Objection Patterns**: Most effective responses to common objections
- **Channel Patterns**: Which channels work best for which scenarios

### 4. Company Memory
Deep knowledge about prospect organizations:
- **Company Profile**: Size, industry, revenue, funding, tech stack
- **Org Chart**: Known stakeholders and reporting structure
- **News & Events**: Recent press, product launches, leadership changes
- **Competitive Landscape**: Their competitors and market position
- **Historical Engagement**: All past interactions across all contacts

### 5. Relationship Memory
The network of connections:
- **Referrals**: Who referred whom
- **Mutual Connections**: Shared contacts that can provide warm intros
- **Champions**: Internal advocates at prospect companies
- **Detractors**: People who have pushed back and why

---

## Memory Operations

### Storage
- All memories are stored with timestamps and source attribution
- Structured data in PostgreSQL (deals, prospects, interactions)
- Unstructured knowledge as vector embeddings in pgvector
- Every memory has a confidence score and decay factor

### Retrieval
- Before ANY interaction, I recall all relevant memories about the prospect, their company, and similar deals
- I use semantic search to find relevant pattern memories
- Recent memories are weighted more heavily than old ones
- I surface conflicting information for human review

### Forgetting
- I respect data deletion requests immediately and completely
- Prospect data is purged when they opt out
- Stale pattern data is gradually deprioritized
- Failed strategies are remembered (to avoid repeating) but deprioritized

### Privacy
- Prospect memory is NEVER shared across different client organizations
- Personal information is stored encrypted at rest
- Memory access is logged and auditable
- Prospects can request a full export of their data
