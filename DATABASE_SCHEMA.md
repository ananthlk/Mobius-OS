# Database Schema Visualization

This document provides a visual representation of the Mobius OS database schema, organized by logical domains.

## Overview

The database schema consists of 32+ tables organized into the following domains:
- User Management & Authentication
- Workflow & Session Management
- LLM & AI Infrastructure
- Tools & Task Catalog
- Workflow Planning & Execution
- Memory & Events
- Audit & Logging
- Core Tables

## Entity Relationship Diagram

```mermaid
erDiagram
    %% Core Tables
    interactions {
        UUID id PK
        VARCHAR user_id
        VARCHAR role
        TEXT content
        JSONB metadata
        TIMESTAMP created_at
    }
    
    agent_recipes {
        SERIAL id PK
        TEXT name
        TEXT goal
        JSONB steps
        TEXT start_step_id
        INTEGER version
        TEXT status
        INTEGER problem_id FK
        TEXT channel
        JSONB metadata
        TEXT created_by
        TEXT user_id
        BOOLEAN is_active
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    problem_definitions {
        SERIAL id PK
        TEXT name
        TEXT domain
        TEXT description
        TEXT user_id
        TIMESTAMP created_at
    }
    
    schema_version {
        INTEGER version PK
        TIMESTAMP applied_at
    }
    
    %% Workflow & Session Management
    shaping_sessions {
        SERIAL id PK
        TEXT user_id
        TEXT status
        TEXT consultant_strategy
        JSONB rag_citations
        JSONB draft_plan
        JSONB final_recipe
        JSONB transcript
        JSONB gate_state
        TEXT active_agent
        TEXT planning_phase_decision
        BOOLEAN planning_phase_approved
        TIMESTAMP planning_phase_approved_at
        INTEGER consultant_iteration_count
        INTEGER max_iterations
        JSONB bounded_plan_state
        JSONB bound_plan_spec
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    workflow_problem_identification {
        SERIAL id PK
        TEXT user_id
        TEXT status
        JSONB transcript
        JSONB draft_plan
        INTEGER mapped_problem_id FK
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    workflow_executions {
        SERIAL id PK
        INTEGER recipe_id FK
        TEXT user_id
        TEXT status
        INTEGER duration_ms
        INTEGER shaping_session_id FK
        TIMESTAMP started_at
        TIMESTAMP ended_at
    }
    
    journey_state {
        INTEGER session_id PK_FK
        TEXT domain
        TEXT strategy
        TEXT current_step
        NUMERIC percent_complete
        TEXT status
        JSONB step_details
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    session_state {
        INTEGER session_id PK_FK
        TEXT state_key PK
        JSONB state_data
        TIMESTAMP updated_at
    }
    
    user_activity {
        SERIAL id PK
        TEXT user_id
        TEXT module
        TEXT resource_id
        JSONB resource_metadata
        TIMESTAMP last_accessed
    }
    
    %% LLM & AI Infrastructure
    llm_providers {
        SERIAL id PK
        VARCHAR name
        VARCHAR provider_type
        VARCHAR base_url
        BOOLEAN is_active
        TEXT user_id
        TEXT created_by
        TEXT updated_by
        TIMESTAMP deleted_at
        TIMESTAMP created_at
    }
    
    llm_config {
        SERIAL id PK
        INTEGER provider_id FK
        VARCHAR config_key
        TEXT encrypted_value
        BOOLEAN is_secret
        TIMESTAMP updated_at
    }
    
    llm_models {
        SERIAL id PK
        INTEGER provider_id FK
        VARCHAR model_id
        VARCHAR display_name
        INTEGER context_window
        NUMERIC input_cost_per_1k
        NUMERIC output_cost_per_1k
        BOOLEAN is_active
        TEXT description
        VARCHAR latency_tier
        JSONB capabilities
        INTEGER last_latency_ms
        TIMESTAMP last_verified_at
        BOOLEAN is_recommended
        TEXT user_id
    }
    
    llm_system_rules {
        SERIAL id PK
        VARCHAR rule_type
        VARCHAR module_id
        INTEGER model_id FK
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    user_llm_preferences {
        SERIAL id PK
        VARCHAR user_id
        VARCHAR module_id
        INTEGER model_id FK
        TIMESTAMP updated_at
    }
    
    llm_trace_logs {
        SERIAL id PK
        INTEGER session_id FK
        TEXT module
        TEXT operation
        JSONB model_config
        TEXT system_prompt
        TEXT user_prompt
        TEXT llm_response
        JSONB token_usage
        INTEGER latency_ms
        TEXT user_id
        TIMESTAMP created_at
    }
    
    prompt_templates {
        SERIAL id PK
        VARCHAR prompt_key
        VARCHAR module_name
        VARCHAR strategy
        VARCHAR sub_level
        VARCHAR domain
        VARCHAR mode
        VARCHAR step
        INTEGER version
        BOOLEAN is_active
        JSONB prompt_config
        TEXT description
        VARCHAR created_by
        TEXT user_id
        TIMESTAMP created_at
        TIMESTAMP updated_at
        VARCHAR updated_by
    }
    
    prompt_history {
        SERIAL id PK
        INTEGER prompt_template_id FK
        VARCHAR prompt_key
        INTEGER version
        JSONB prompt_config
        VARCHAR changed_by
        TEXT change_reason
        TEXT user_id
        TIMESTAMP created_at
    }
    
    prompt_usage {
        SERIAL id PK
        VARCHAR prompt_key
        INTEGER session_id FK
        VARCHAR user_id
        TIMESTAMP invoked_at
        NUMERIC response_quality_score
        JSONB metadata
    }
    
    %% Tools & Task Catalog
    tools {
        SERIAL id PK
        VARCHAR name
        VARCHAR display_name
        TEXT description
        VARCHAR category
        VARCHAR version
        JSONB schema_definition
        BOOLEAN requires_human_review
        BOOLEAN is_batch_processable
        INTEGER estimated_execution_time_ms
        INTEGER timeout_ms
        BOOLEAN is_deterministic
        BOOLEAN is_stateless
        BOOLEAN supports_async
        BOOLEAN supports_conditional_execution
        VARCHAR default_condition_type
        JSONB conditional_execution_examples
        VARCHAR implementation_type
        VARCHAR implementation_path
        JSONB implementation_config
        VARCHAR author
        TEXT[] tags
        TEXT documentation_url
        TEXT example_usage
        VARCHAR status
        BOOLEAN is_public
        INTEGER created_by
        TIMESTAMP created_at
        TIMESTAMP updated_at
        TIMESTAMP deprecated_at
    }
    
    tool_parameters {
        SERIAL id PK
        INTEGER tool_id FK
        VARCHAR parameter_name
        VARCHAR parameter_type
        TEXT description
        BOOLEAN is_required
        TEXT default_value
        JSONB validation_rules
        INTEGER order_index
    }
    
    tool_execution_conditions {
        SERIAL id PK
        INTEGER tool_id FK
        VARCHAR condition_type
        JSONB condition_expression
        VARCHAR action_type
        INTEGER action_target_tool_id FK
        VARCHAR action_target_tool_name
        TEXT condition_description
        VARCHAR icon_name
        VARCHAR icon_color
        INTEGER execution_order
        BOOLEAN is_active
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    tool_usage_logs {
        SERIAL id PK
        INTEGER tool_id FK
        INTEGER session_id FK
        INTEGER workflow_execution_id
        TIMESTAMP executed_at
        INTEGER execution_time_ms
        VARCHAR status
        TEXT error_message
        JSONB input_params
        JSONB output_result
    }
    
    task_catalog {
        SERIAL id PK
        UUID task_id
        VARCHAR task_key
        VARCHAR name
        TEXT description
        JSONB classification
        JSONB contract
        JSONB automation
        JSONB tool_binding_defaults
        JSONB information
        JSONB policy
        JSONB temporal
        JSONB escalation
        JSONB dependencies
        JSONB failure
        JSONB ui
        JSONB governance
        VARCHAR status
        INTEGER version
        VARCHAR schema_version
        TIMESTAMP created_at_utc
        TIMESTAMP updated_at_utc
        TIMESTAMP deprecated_at_utc
        VARCHAR created_by
        VARCHAR updated_by
    }
    
    task_groups {
        SERIAL id PK
        VARCHAR group_key
        VARCHAR name
        TEXT description
        VARCHAR parent_group_key FK
        JSONB metadata
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    task_group_memberships {
        SERIAL id PK
        VARCHAR task_key FK
        VARCHAR group_key FK
        INTEGER display_order
        TIMESTAMP created_at
    }
    
    task_catalog_history {
        SERIAL id PK
        VARCHAR task_key FK
        INTEGER version
        JSONB task_data
        VARCHAR changed_by
        TEXT change_notes
        TIMESTAMP created_at
    }
    
    %% Workflow Planning
    workflow_plans {
        SERIAL id PK
        INTEGER session_id FK
        VARCHAR plan_name
        TEXT problem_statement
        TEXT goal
        JSONB plan_structure
        JSONB metadata
        VARCHAR parent_template_key
        VARCHAR status
        INTEGER version
        TIMESTAMP created_at
        TIMESTAMP approved_at
        TIMESTAMP execution_started_at
        TIMESTAMP execution_completed_at
        TIMESTAMP updated_at
        VARCHAR created_by
        VARCHAR approved_by
        VARCHAR last_modified_by
    }
    
    workflow_plan_phases {
        SERIAL id PK
        INTEGER plan_id FK
        VARCHAR phase_id
        VARCHAR phase_name
        TEXT description
        JSONB phase_structure
        JSONB metadata
        VARCHAR status
        INTEGER execution_order
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    workflow_plan_steps {
        SERIAL id PK
        INTEGER plan_id FK
        INTEGER phase_id FK
        VARCHAR step_id
        TEXT description
        JSONB tool_definition
        JSONB metadata
        VARCHAR status
        INTEGER execution_order
        TEXT[] depends_on_step_ids
        JSONB execution_result
        TEXT execution_error
        INTEGER execution_duration_ms
        TIMESTAMP created_at
        TIMESTAMP updated_at
        TIMESTAMP execution_started_at
        TIMESTAMP execution_completed_at
    }
    
    workflow_plan_enhancements {
        SERIAL id PK
        INTEGER plan_id FK
        INTEGER step_id FK
        VARCHAR enhancement_type
        JSONB enhancement_data
        VARCHAR enhanced_by
        VARCHAR enhanced_by_type
        TEXT enhancement_reason
        TIMESTAMP created_at
    }
    
    eligibility_plan_templates {
        SERIAL id PK
        VARCHAR template_key
        VARCHAR module_name
        VARCHAR domain
        VARCHAR strategy
        VARCHAR step
        VARCHAR name
        TEXT description
        JSONB template_config
        JSONB match_pattern
        INTEGER version
        BOOLEAN is_active
        VARCHAR created_by
        TIMESTAMP created_at
        TIMESTAMP updated_at
        VARCHAR updated_by
    }
    
    %% Memory & Events
    memory_events {
        SERIAL id PK
        INTEGER session_id FK
        VARCHAR bucket_type
        JSONB payload
        TIMESTAMP created_at
    }
    
    message_feedback {
        SERIAL id PK
        INTEGER memory_event_id FK
        TEXT user_id
        TEXT rating
        TEXT comment
        TIMESTAMP created_at
    }
    
    %% Audit & Logging
    audit_logs {
        SERIAL id PK
        VARCHAR user_id
        VARCHAR session_id
        VARCHAR action
        VARCHAR resource_type
        VARCHAR resource_id
        JSONB details
        VARCHAR ip_address
        TEXT user_agent
        TIMESTAMP created_at
    }
    
    %% User Management Domain
    users {
        SERIAL id PK
        VARCHAR auth_id
        VARCHAR email
        VARCHAR name
        VARCHAR role
        BOOLEAN is_active
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    %% User Profiles (Patient Data)
    user_profiles {
        VARCHAR patient_id PK
        JSONB emr_data
        JSONB system_data
        JSONB health_plan_data
        JSONB availability_flags
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    %% User Account Profiles
    user_account_profiles {
        INTEGER user_id PK_FK
        JSONB preferences
        JSONB settings
        JSONB metadata
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    user_basic_profiles {
        INTEGER user_id PK_FK
        VARCHAR preferred_name
        VARCHAR phone
        VARCHAR mobile
        VARCHAR alternate_email
        VARCHAR timezone
        VARCHAR locale
        TEXT avatar_url
        TEXT bio
        JSONB metadata
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    user_professional_profiles {
        INTEGER user_id PK_FK
        VARCHAR job_title
        VARCHAR department
        VARCHAR organization
        INTEGER manager_id FK
        VARCHAR team_name
        VARCHAR employee_id
        VARCHAR office_location
        DATE start_date
        JSONB metadata
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    user_communication_profiles {
        INTEGER user_id PK_FK
        VARCHAR communication_style
        VARCHAR tone_preference
        INTEGER prompt_style_id
        VARCHAR preferred_language
        VARCHAR response_format_preference
        JSONB notification_preferences
        VARCHAR engagement_level
        JSONB metadata
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    user_use_case_profiles {
        INTEGER user_id PK_FK
        JSONB primary_workflows
        JSONB workflow_frequency
        JSONB module_preferences
        JSONB task_patterns
        JSONB domain_expertise
        JSONB metadata
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    user_ai_preference_profiles {
        INTEGER user_id PK_FK
        JSONB escalation_rules
        VARCHAR autonomy_level
        DECIMAL confidence_threshold
        JSONB require_confirmation_for
        JSONB preferred_model_preferences
        JSONB feedback_preferences
        VARCHAR preferred_strategy
        JSONB strategy_preferences
        JSONB task_category_preferences
        JSONB task_domain_preferences
        JSONB metadata
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    user_query_history_profiles {
        INTEGER user_id PK_FK
        JSONB most_common_queries
        JSONB query_categories
        JSONB search_patterns
        JSONB question_templates
        JSONB interaction_stats
        JSONB metadata
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    user_communication_preferences {
        VARCHAR user_id PK
        VARCHAR tone
        VARCHAR style
        VARCHAR engagement_level
        TIMESTAMP updated_at
    }
    
    user_query_session_links {
        SERIAL id PK
        INTEGER user_id FK
        INTEGER session_id FK
        UUID interaction_id FK
        TEXT query_text
        VARCHAR query_category
        VARCHAR module
        VARCHAR workflow_name
        VARCHAR strategy
        BOOLEAN contributed_to_profile
        TIMESTAMP created_at
    }
    
    gmail_oauth_tokens {
        SERIAL id PK
        TEXT user_id
        TEXT email
        TEXT encrypted_token
        TEXT encrypted_refresh_token
        TEXT token_uri
        TEXT client_id
        TEXT client_secret
        TEXT scopes
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    %% Relationships - User Management
    users ||--o{ user_account_profiles : "has"
    users ||--o{ user_basic_profiles : "has"
    users ||--o{ user_professional_profiles : "has"
    users ||--o{ user_communication_profiles : "has"
    users ||--o{ user_use_case_profiles : "has"
    users ||--o{ user_ai_preference_profiles : "has"
    users ||--o{ user_query_history_profiles : "has"
    users ||--o{ user_query_session_links : "has"
    user_professional_profiles }o--|| users : "managed_by"
    
    %% Relationships - Core to Workflow
    problem_definitions ||--o{ agent_recipes : "maps_to"
    problem_definitions ||--o{ workflow_problem_identification : "maps_to"
    agent_recipes ||--o{ workflow_executions : "executes"
    
    %% Relationships - Shaping Sessions Hub
    shaping_sessions ||--o{ llm_trace_logs : "traces"
    shaping_sessions ||--o{ memory_events : "records"
    shaping_sessions ||--o{ session_state : "stores_state"
    shaping_sessions ||--o{ journey_state : "tracks"
    shaping_sessions ||--o{ workflow_plans : "generates"
    shaping_sessions ||--o{ workflow_executions : "links_to"
    shaping_sessions ||--o{ tool_usage_logs : "uses_tools"
    shaping_sessions ||--o{ prompt_usage : "uses_prompts"
    shaping_sessions ||--o{ user_query_session_links : "links_to"
    
    %% Relationships - LLM Infrastructure
    llm_providers ||--o{ llm_config : "configures"
    llm_providers ||--o{ llm_models : "provides"
    llm_models ||--o{ llm_system_rules : "governed_by"
    llm_models ||--o{ user_llm_preferences : "preferred_by"
    
    %% Relationships - Prompt Management
    prompt_templates ||--o{ prompt_history : "versioned_in"
    prompt_templates ||--o{ prompt_usage : "used_in"
    
    %% Relationships - Tools
    tools ||--o{ tool_parameters : "has"
    tools ||--o{ tool_execution_conditions : "conditionally_executes"
    tools ||--o{ tool_usage_logs : "logged_in"
    tool_execution_conditions }o--|| tools : "targets"
    
    %% Relationships - Task Catalog
    task_catalog ||--o{ task_group_memberships : "grouped_in"
    task_groups ||--o{ task_group_memberships : "contains"
    task_groups ||--o{ task_groups : "parent_of"
    task_catalog ||--o{ task_catalog_history : "versioned_in"
    
    %% Relationships - Workflow Planning
    workflow_plans ||--o{ workflow_plan_phases : "contains"
    workflow_plan_phases ||--o{ workflow_plan_steps : "contains"
    workflow_plan_steps ||--o{ workflow_plan_enhancements : "enhanced_by"
    
    %% Relationships - Memory & Feedback
    memory_events ||--o{ message_feedback : "receives_feedback"
    
    %% Relationships - Interactions
    interactions ||--o{ user_query_session_links : "linked_to"
```

## Schema Organization by Domain

### 1. User Management & Authentication

**Core Tables:**
- `users` - Central user identity table with auth_id and email
- `user_account_profiles` - User preferences and settings
- `user_basic_profiles` - Personal information (name, contact, timezone)
- `user_professional_profiles` - Work/organizational information
- `user_communication_profiles` - Communication preferences
- `user_use_case_profiles` - Workflow patterns and use cases
- `user_ai_preference_profiles` - AI interaction preferences
- `user_query_history_profiles` - Query patterns and statistics
- `user_communication_preferences` - Conversational formatting preferences
- `user_query_session_links` - Links user queries to sessions
- `gmail_oauth_tokens` - Encrypted OAuth tokens for Gmail API

**Patient Data:**
- `user_profiles` - Synthetic patient profiles (EMR, system, health plan data)

### 2. Workflow & Session Management

**Core Session Tables:**
- `shaping_sessions` - Central hub for workflow sessions (GATHERING, PLANNING, EXECUTING, etc.)
- `workflow_problem_identification` - Legacy shaping session table
- `workflow_executions` - Execution history of recipes
- `journey_state` - Progress tracking for workflow sessions
- `session_state` - Orchestrator session state cache
- `user_activity` - Sidebar history for user activity

**Key Relationships:**
- `shaping_sessions` is the central hub referenced by:
  - `llm_trace_logs`, `memory_events`, `session_state`, `journey_state`
  - `workflow_plans`, `workflow_executions`, `tool_usage_logs`

### 3. LLM & AI Infrastructure

**Provider & Model Management:**
- `llm_providers` - AI providers (Google Vertex, OpenAI, Anthropic, Ollama)
- `llm_config` - Encrypted configuration for providers
- `llm_models` - Available LLM models with cost and capability metadata
- `llm_system_rules` - Global and module-level model governance rules
- `user_llm_preferences` - User-level model preferences

**Observability:**
- `llm_trace_logs` - Complete audit trail of LLM calls (inputs, outputs, tokens, latency)

**Prompt Management:**
- `prompt_templates` - Versioned prompt templates (module:domain:mode:step pattern)
- `prompt_history` - Version history for prompts
- `prompt_usage` - Analytics for prompt usage

### 4. Tools & Task Catalog

**Tool Library:**
- `tools` - Tool definitions with schema, execution metadata, and implementation details
- `tool_parameters` - Normalized tool parameters
- `tool_execution_conditions` - Conditional execution rules (if/then, on_success, on_failure)
- `tool_usage_logs` - Tool execution tracking and analytics

**Task Catalog:**
- `task_catalog` - Master reference for all tasks (rich metadata: classification, contract, automation, policy, etc.)
- `task_groups` - Hierarchical grouping of tasks
- `task_group_memberships` - Many-to-many relationship between tasks and groups
- `task_catalog_history` - Version history for tasks

### 5. Workflow Planning & Execution

**Planning Tables:**
- `workflow_plans` - Main workflow plans with lifecycle tracking
- `workflow_plan_phases` - Phases within a plan
- `workflow_plan_steps` - Individual steps with tool configurations
- `workflow_plan_enhancements` - Audit trail of agent/user enhancements
- `eligibility_plan_templates` - Deterministic plan templates for eligibility workflows

**Key Relationships:**
- `workflow_plans` → `workflow_plan_phases` → `workflow_plan_steps`
- Plans reference `shaping_sessions` and optionally `eligibility_plan_templates`

### 6. Memory & Events

- `memory_events` - Canonical event log for agent memory buckets (THINKING, ARTIFACTS, PERSISTENCE, OUTPUT)
- `message_feedback` - User feedback (thumbs up/down) on memory events

### 7. Audit & Logging

- `audit_logs` - System-wide audit trail (CREATE, UPDATE, DELETE, VIEW, LOGIN actions)
- `user_activity` - User activity tracking for sidebar history

### 8. Core Tables

- `interactions` - Raw chat history between users and the system
- `agent_recipes` - Workflow recipes (steps, goals, metadata)
- `problem_definitions` - Problem taxonomy (domain, name, description)
- `schema_version` - Migration tracking

## Key Foreign Key Relationships

### Central Hubs

**`shaping_sessions` (id)** is referenced by:
- `llm_trace_logs.session_id`
- `memory_events.session_id`
- `session_state.session_id`
- `journey_state.session_id`
- `workflow_plans.session_id`
- `workflow_executions.shaping_session_id`
- `tool_usage_logs.session_id`
- `prompt_usage.session_id`
- `user_query_session_links.session_id`

**`users` (id)** is referenced by:
- All user profile tables (1:1 relationships)
- `user_query_session_links.user_id`
- `user_professional_profiles.manager_id` (self-referential)

### LLM Infrastructure Chain

- `llm_providers` → `llm_config` (provider_id)
- `llm_providers` → `llm_models` (provider_id)
- `llm_models` → `llm_system_rules` (model_id)
- `llm_models` → `user_llm_preferences` (model_id)

### Workflow Planning Hierarchy

- `workflow_plans` → `workflow_plan_phases` (plan_id)
- `workflow_plan_phases` → `workflow_plan_steps` (phase_id)
- `workflow_plan_steps` → `workflow_plan_enhancements` (step_id)

### Tool Relationships

- `tools` → `tool_parameters` (tool_id)
- `tools` → `tool_execution_conditions` (tool_id)
- `tools` → `tool_execution_conditions.action_target_tool_id` (self-referential)

### Task Catalog Structure

- `task_catalog` → `task_group_memberships` (task_key)
- `task_groups` → `task_group_memberships` (group_key)
- `task_groups` → `task_groups.parent_group_key` (self-referential)
- `task_catalog` → `task_catalog_history` (task_key)

## Notes

1. **User ID Format**: The schema uses `VARCHAR(255)` for `user_id` in many tables to support Google Auth Subject IDs. The `users` table provides the centralized identity with `auth_id` and `email`.

2. **JSONB Usage**: Extensive use of JSONB for flexible schema storage:
   - State management (gate_state, draft_plan, transcript)
   - Tool definitions and configurations
   - Task metadata (classification, contract, automation, etc.)
   - User preferences and profiles

3. **Soft Deletes**: Some tables support soft deletes via `deleted_at` timestamps (e.g., `llm_providers`).

4. **Versioning**: Multiple tables support versioning:
   - `agent_recipes.version`
   - `prompt_templates.version` with `prompt_history`
   - `task_catalog.version` with `task_catalog_history`
   - `workflow_plans.version`

5. **Migration Tracking**: The `schema_version` table tracks applied migrations.

