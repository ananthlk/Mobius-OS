# User Profile API Guide

This guide shows you how to access and manage comprehensive user profiles through the API.

## Base URL

The API base URL is typically:
- **Local Development**: `http://localhost:8000`
- **Production**: Set via `NEXT_PUBLIC_API_URL` environment variable

## Authentication

All endpoints require the `X-User-ID` header with the user's auth_id (Google OAuth Subject ID).

```bash
X-User-ID: <user_auth_id>
```

## Profile Endpoints

### Get All Profiles at Once

**GET** `/api/users/{user_id}/profiles/all`

Returns all 6 profile types in one response.

```bash
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/all
```

**Response:**
```json
{
  "basic": {
    "user_id": 2,
    "preferred_name": "John",
    "phone": "555-1234",
    "mobile": "555-5678",
    "timezone": "America/New_York",
    ...
  },
  "professional": {
    "user_id": 2,
    "job_title": "Software Engineer",
    "department": "Engineering",
    "organization": "Test Corp",
    ...
  },
  "communication": {
    "user_id": 2,
    "communication_style": "friendly",
    "tone_preference": "concise",
    ...
  },
  "use_case": {
    "user_id": 2,
    "primary_workflows": [...],
    "workflow_frequency": {...},
    ...
  },
  "ai_preference": {
    "user_id": 2,
    "preferred_strategy": "TABULA_RASA",
    "autonomy_level": "autonomous",
    ...
  },
  "query_history": {
    "user_id": 2,
    "most_common_queries": [...],
    "interaction_stats": {...},
    ...
  }
}
```

---

## Individual Profile Endpoints

### 1. Basic Profile

**GET** `/api/users/{user_id}/profiles/basic`
- Get basic personal information (name, contacts, timezone, etc.)

**PUT** `/api/users/{user_id}/profiles/basic`
- Update basic profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/basic

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "preferred_name": "John",
    "phone": "555-1234",
    "mobile": "555-5678",
    "timezone": "America/New_York",
    "locale": "en-US"
  }' \
  http://localhost:8000/api/users/2/profiles/basic
```

### 2. Professional Profile

**GET** `/api/users/{user_id}/profiles/professional`
- Get professional information (job title, department, manager, etc.)

**PUT** `/api/users/{user_id}/profiles/professional`
- Update professional profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/professional

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "job_title": "Software Engineer",
    "department": "Engineering",
    "organization": "Your Company",
    "manager_id": 1,
    "team_name": "Platform Team"
  }' \
  http://localhost:8000/api/users/2/profiles/professional
```

### 3. Communication Profile

**GET** `/api/users/{user_id}/profiles/communication`
- Get communication preferences

**PUT** `/api/users/{user_id}/profiles/communication`
- Update communication profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/communication

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "communication_style": "friendly",
    "tone_preference": "concise",
    "response_format_preference": "bullet_points",
    "preferred_language": "en",
    "engagement_level": "engaging"
  }' \
  http://localhost:8000/api/users/2/profiles/communication
```

### 4. Use Case Profile

**GET** `/api/users/{user_id}/profiles/use-case`
- Get workflow patterns and use cases

**PUT** `/api/users/{user_id}/profiles/use-case`
- Update use case profile (typically auto-populated from usage)

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/use-case

# Update (JSONB fields)
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "primary_workflows": [
      {"name": "eligibility_verification", "count": 5, "last_used": "2024-01-01T00:00:00Z"}
    ],
    "workflow_frequency": {
      "eligibility_verification": {"count": 5, "last_used": "2024-01-01T00:00:00Z"}
    }
  }' \
  http://localhost:8000/api/users/2/profiles/use-case
```

### 5. AI Preference Profile

**GET** `/api/users/{user_id}/profiles/ai-preference`
- Get AI interaction preferences

**PUT** `/api/users/{user_id}/profiles/ai-preference`
- Update AI preference profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/ai-preference

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "preferred_strategy": "TABULA_RASA",
    "autonomy_level": "autonomous",
    "confidence_threshold": 0.75,
    "escalation_rules": {"high_risk": "always_confirm"},
    "require_confirmation_for": ["payment_actions", "data_deletion"]
  }' \
  http://localhost:8000/api/users/2/profiles/ai-preference
```

### 6. Query History Profile

**GET** `/api/users/{user_id}/profiles/query-history`
- Get query history and statistics (read-only, auto-populated)

```bash
# Get (read-only, auto-populated from usage)
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/query-history
```

---

## Session Links

**GET** `/api/users/{user_id}/session-links?limit=50`

Get all session links (queries linked to shaping_sessions).

```bash
curl -H "X-User-ID: your_auth_id" \
  "http://localhost:8000/api/users/2/session-links?limit=50"
```

**Response:**
```json
{
  "links": [
    {
      "id": 1,
      "user_id": 2,
      "session_id": 162,
      "interaction_id": "...",
      "query_text": "I need to verify patient eligibility",
      "query_category": null,
      "module": "workflow",
      "workflow_name": "eligibility_verification",
      "strategy": "TABULA_RASA",
      "session_status": "GATHERING",
      "consultant_strategy": "TABULA_RASA",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

---

## Frontend Integration Example (React/Next.js)

```typescript
// Get all profiles
const fetchAllProfiles = async (userId: number) => {
  const response = await fetch(`${apiUrl}/api/users/${userId}/profiles/all`, {
    headers: {
      'X-User-ID': session?.user?.id || ''
    }
  });
  return await response.json();
};

// Update basic profile
const updateBasicProfile = async (userId: number, updates: any) => {
  const response = await fetch(`${apiUrl}/api/users/${userId}/profiles/basic`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': session?.user?.id || ''
    },
    body: JSON.stringify(updates)
  });
  return await response.json();
};

// Get session links
const fetchSessionLinks = async (userId: number, limit = 50) => {
  const response = await fetch(
    `${apiUrl}/api/users/${userId}/session-links?limit=${limit}`,
    {
      headers: {
        'X-User-ID': session?.user?.id || ''
      }
    }
  );
  return await response.json();
};
```

---

## Profile Fields Reference

### Basic Profile Fields
- `preferred_name` - User's preferred name
- `phone` - Phone number
- `mobile` - Mobile number
- `alternate_email` - Alternate email
- `timezone` - Timezone (e.g., "America/New_York")
- `locale` - Locale (e.g., "en-US")
- `avatar_url` - Avatar image URL
- `bio` - User bio/description

### Professional Profile Fields
- `job_title` - Job title
- `department` - Department name
- `organization` - Organization/company name
- `manager_id` - Manager's user ID (references users.id)
- `team_name` - Team name
- `employee_id` - Employee ID
- `office_location` - Office location
- `start_date` - Start date (DATE format)

### Communication Profile Fields
- `communication_style` - "casual", "formal", "friendly", "professional"
- `tone_preference` - "concise", "detailed", "balanced"
- `response_format_preference` - "bullet_points", "structured", "conversational"
- `preferred_language` - Language code (e.g., "en")
- `notification_preferences` - JSONB object
- `engagement_level` - "engaging", "minimal", "detailed"

### Use Case Profile Fields (JSONB)
- `primary_workflows` - Array of workflow objects
- `workflow_frequency` - Object mapping workflow names to frequency data
- `module_preferences` - JSONB object
- `task_patterns` - Array of task patterns
- `domain_expertise` - Array of domain expertise areas

### AI Preference Profile Fields
- `preferred_strategy` - "TABULA_RASA", "EVIDENCE_BASED", "CREATIVE"
- `autonomy_level` - "autonomous", "consultative", "balanced"
- `confidence_threshold` - Decimal (0.0-1.0)
- `escalation_rules` - JSONB object
- `require_confirmation_for` - Array of action types
- `preferred_model_preferences` - JSONB object
- `strategy_preferences` - JSONB object
- `task_category_preferences` - JSONB object
- `task_domain_preferences` - JSONB object

### Query History Profile Fields (Read-only, Auto-populated)
- `most_common_queries` - Array of query objects with counts
- `query_categories` - Object mapping categories to counts
- `search_patterns` - Array of search patterns
- `question_templates` - Array of question templates
- `interaction_stats` - Statistics object (total_queries, avg_query_length, etc.)

---

## Notes

1. **User ID**: The `{user_id}` in URLs is the internal integer ID from the `users` table, not the auth_id
2. **Auto-population**: Query history and use case profiles are automatically updated when users interact with the system
3. **JSONB Fields**: Some fields (like `workflow_frequency`, `escalation_rules`) are JSONB and accept nested objects/arrays
4. **Read-only Fields**: Query history profile is read-only and automatically populated
5. **Session Links**: These are automatically created when workflow interactions occur






This guide shows you how to access and manage comprehensive user profiles through the API.

## Base URL

The API base URL is typically:
- **Local Development**: `http://localhost:8000`
- **Production**: Set via `NEXT_PUBLIC_API_URL` environment variable

## Authentication

All endpoints require the `X-User-ID` header with the user's auth_id (Google OAuth Subject ID).

```bash
X-User-ID: <user_auth_id>
```

## Profile Endpoints

### Get All Profiles at Once

**GET** `/api/users/{user_id}/profiles/all`

Returns all 6 profile types in one response.

```bash
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/all
```

**Response:**
```json
{
  "basic": {
    "user_id": 2,
    "preferred_name": "John",
    "phone": "555-1234",
    "mobile": "555-5678",
    "timezone": "America/New_York",
    ...
  },
  "professional": {
    "user_id": 2,
    "job_title": "Software Engineer",
    "department": "Engineering",
    "organization": "Test Corp",
    ...
  },
  "communication": {
    "user_id": 2,
    "communication_style": "friendly",
    "tone_preference": "concise",
    ...
  },
  "use_case": {
    "user_id": 2,
    "primary_workflows": [...],
    "workflow_frequency": {...},
    ...
  },
  "ai_preference": {
    "user_id": 2,
    "preferred_strategy": "TABULA_RASA",
    "autonomy_level": "autonomous",
    ...
  },
  "query_history": {
    "user_id": 2,
    "most_common_queries": [...],
    "interaction_stats": {...},
    ...
  }
}
```

---

## Individual Profile Endpoints

### 1. Basic Profile

**GET** `/api/users/{user_id}/profiles/basic`
- Get basic personal information (name, contacts, timezone, etc.)

**PUT** `/api/users/{user_id}/profiles/basic`
- Update basic profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/basic

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "preferred_name": "John",
    "phone": "555-1234",
    "mobile": "555-5678",
    "timezone": "America/New_York",
    "locale": "en-US"
  }' \
  http://localhost:8000/api/users/2/profiles/basic
```

### 2. Professional Profile

**GET** `/api/users/{user_id}/profiles/professional`
- Get professional information (job title, department, manager, etc.)

**PUT** `/api/users/{user_id}/profiles/professional`
- Update professional profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/professional

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "job_title": "Software Engineer",
    "department": "Engineering",
    "organization": "Your Company",
    "manager_id": 1,
    "team_name": "Platform Team"
  }' \
  http://localhost:8000/api/users/2/profiles/professional
```

### 3. Communication Profile

**GET** `/api/users/{user_id}/profiles/communication`
- Get communication preferences

**PUT** `/api/users/{user_id}/profiles/communication`
- Update communication profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/communication

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "communication_style": "friendly",
    "tone_preference": "concise",
    "response_format_preference": "bullet_points",
    "preferred_language": "en",
    "engagement_level": "engaging"
  }' \
  http://localhost:8000/api/users/2/profiles/communication
```

### 4. Use Case Profile

**GET** `/api/users/{user_id}/profiles/use-case`
- Get workflow patterns and use cases

**PUT** `/api/users/{user_id}/profiles/use-case`
- Update use case profile (typically auto-populated from usage)

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/use-case

# Update (JSONB fields)
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "primary_workflows": [
      {"name": "eligibility_verification", "count": 5, "last_used": "2024-01-01T00:00:00Z"}
    ],
    "workflow_frequency": {
      "eligibility_verification": {"count": 5, "last_used": "2024-01-01T00:00:00Z"}
    }
  }' \
  http://localhost:8000/api/users/2/profiles/use-case
```

### 5. AI Preference Profile

**GET** `/api/users/{user_id}/profiles/ai-preference`
- Get AI interaction preferences

**PUT** `/api/users/{user_id}/profiles/ai-preference`
- Update AI preference profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/ai-preference

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "preferred_strategy": "TABULA_RASA",
    "autonomy_level": "autonomous",
    "confidence_threshold": 0.75,
    "escalation_rules": {"high_risk": "always_confirm"},
    "require_confirmation_for": ["payment_actions", "data_deletion"]
  }' \
  http://localhost:8000/api/users/2/profiles/ai-preference
```

### 6. Query History Profile

**GET** `/api/users/{user_id}/profiles/query-history`
- Get query history and statistics (read-only, auto-populated)

```bash
# Get (read-only, auto-populated from usage)
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/query-history
```

---

## Session Links

**GET** `/api/users/{user_id}/session-links?limit=50`

Get all session links (queries linked to shaping_sessions).

```bash
curl -H "X-User-ID: your_auth_id" \
  "http://localhost:8000/api/users/2/session-links?limit=50"
```

**Response:**
```json
{
  "links": [
    {
      "id": 1,
      "user_id": 2,
      "session_id": 162,
      "interaction_id": "...",
      "query_text": "I need to verify patient eligibility",
      "query_category": null,
      "module": "workflow",
      "workflow_name": "eligibility_verification",
      "strategy": "TABULA_RASA",
      "session_status": "GATHERING",
      "consultant_strategy": "TABULA_RASA",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

---

## Frontend Integration Example (React/Next.js)

```typescript
// Get all profiles
const fetchAllProfiles = async (userId: number) => {
  const response = await fetch(`${apiUrl}/api/users/${userId}/profiles/all`, {
    headers: {
      'X-User-ID': session?.user?.id || ''
    }
  });
  return await response.json();
};

// Update basic profile
const updateBasicProfile = async (userId: number, updates: any) => {
  const response = await fetch(`${apiUrl}/api/users/${userId}/profiles/basic`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': session?.user?.id || ''
    },
    body: JSON.stringify(updates)
  });
  return await response.json();
};

// Get session links
const fetchSessionLinks = async (userId: number, limit = 50) => {
  const response = await fetch(
    `${apiUrl}/api/users/${userId}/session-links?limit=${limit}`,
    {
      headers: {
        'X-User-ID': session?.user?.id || ''
      }
    }
  );
  return await response.json();
};
```

---

## Profile Fields Reference

### Basic Profile Fields
- `preferred_name` - User's preferred name
- `phone` - Phone number
- `mobile` - Mobile number
- `alternate_email` - Alternate email
- `timezone` - Timezone (e.g., "America/New_York")
- `locale` - Locale (e.g., "en-US")
- `avatar_url` - Avatar image URL
- `bio` - User bio/description

### Professional Profile Fields
- `job_title` - Job title
- `department` - Department name
- `organization` - Organization/company name
- `manager_id` - Manager's user ID (references users.id)
- `team_name` - Team name
- `employee_id` - Employee ID
- `office_location` - Office location
- `start_date` - Start date (DATE format)

### Communication Profile Fields
- `communication_style` - "casual", "formal", "friendly", "professional"
- `tone_preference` - "concise", "detailed", "balanced"
- `response_format_preference` - "bullet_points", "structured", "conversational"
- `preferred_language` - Language code (e.g., "en")
- `notification_preferences` - JSONB object
- `engagement_level` - "engaging", "minimal", "detailed"

### Use Case Profile Fields (JSONB)
- `primary_workflows` - Array of workflow objects
- `workflow_frequency` - Object mapping workflow names to frequency data
- `module_preferences` - JSONB object
- `task_patterns` - Array of task patterns
- `domain_expertise` - Array of domain expertise areas

### AI Preference Profile Fields
- `preferred_strategy` - "TABULA_RASA", "EVIDENCE_BASED", "CREATIVE"
- `autonomy_level` - "autonomous", "consultative", "balanced"
- `confidence_threshold` - Decimal (0.0-1.0)
- `escalation_rules` - JSONB object
- `require_confirmation_for` - Array of action types
- `preferred_model_preferences` - JSONB object
- `strategy_preferences` - JSONB object
- `task_category_preferences` - JSONB object
- `task_domain_preferences` - JSONB object

### Query History Profile Fields (Read-only, Auto-populated)
- `most_common_queries` - Array of query objects with counts
- `query_categories` - Object mapping categories to counts
- `search_patterns` - Array of search patterns
- `question_templates` - Array of question templates
- `interaction_stats` - Statistics object (total_queries, avg_query_length, etc.)

---

## Notes

1. **User ID**: The `{user_id}` in URLs is the internal integer ID from the `users` table, not the auth_id
2. **Auto-population**: Query history and use case profiles are automatically updated when users interact with the system
3. **JSONB Fields**: Some fields (like `workflow_frequency`, `escalation_rules`) are JSONB and accept nested objects/arrays
4. **Read-only Fields**: Query history profile is read-only and automatically populated
5. **Session Links**: These are automatically created when workflow interactions occur





This guide shows you how to access and manage comprehensive user profiles through the API.

## Base URL

The API base URL is typically:
- **Local Development**: `http://localhost:8000`
- **Production**: Set via `NEXT_PUBLIC_API_URL` environment variable

## Authentication

All endpoints require the `X-User-ID` header with the user's auth_id (Google OAuth Subject ID).

```bash
X-User-ID: <user_auth_id>
```

## Profile Endpoints

### Get All Profiles at Once

**GET** `/api/users/{user_id}/profiles/all`

Returns all 6 profile types in one response.

```bash
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/all
```

**Response:**
```json
{
  "basic": {
    "user_id": 2,
    "preferred_name": "John",
    "phone": "555-1234",
    "mobile": "555-5678",
    "timezone": "America/New_York",
    ...
  },
  "professional": {
    "user_id": 2,
    "job_title": "Software Engineer",
    "department": "Engineering",
    "organization": "Test Corp",
    ...
  },
  "communication": {
    "user_id": 2,
    "communication_style": "friendly",
    "tone_preference": "concise",
    ...
  },
  "use_case": {
    "user_id": 2,
    "primary_workflows": [...],
    "workflow_frequency": {...},
    ...
  },
  "ai_preference": {
    "user_id": 2,
    "preferred_strategy": "TABULA_RASA",
    "autonomy_level": "autonomous",
    ...
  },
  "query_history": {
    "user_id": 2,
    "most_common_queries": [...],
    "interaction_stats": {...},
    ...
  }
}
```

---

## Individual Profile Endpoints

### 1. Basic Profile

**GET** `/api/users/{user_id}/profiles/basic`
- Get basic personal information (name, contacts, timezone, etc.)

**PUT** `/api/users/{user_id}/profiles/basic`
- Update basic profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/basic

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "preferred_name": "John",
    "phone": "555-1234",
    "mobile": "555-5678",
    "timezone": "America/New_York",
    "locale": "en-US"
  }' \
  http://localhost:8000/api/users/2/profiles/basic
```

### 2. Professional Profile

**GET** `/api/users/{user_id}/profiles/professional`
- Get professional information (job title, department, manager, etc.)

**PUT** `/api/users/{user_id}/profiles/professional`
- Update professional profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/professional

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "job_title": "Software Engineer",
    "department": "Engineering",
    "organization": "Your Company",
    "manager_id": 1,
    "team_name": "Platform Team"
  }' \
  http://localhost:8000/api/users/2/profiles/professional
```

### 3. Communication Profile

**GET** `/api/users/{user_id}/profiles/communication`
- Get communication preferences

**PUT** `/api/users/{user_id}/profiles/communication`
- Update communication profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/communication

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "communication_style": "friendly",
    "tone_preference": "concise",
    "response_format_preference": "bullet_points",
    "preferred_language": "en",
    "engagement_level": "engaging"
  }' \
  http://localhost:8000/api/users/2/profiles/communication
```

### 4. Use Case Profile

**GET** `/api/users/{user_id}/profiles/use-case`
- Get workflow patterns and use cases

**PUT** `/api/users/{user_id}/profiles/use-case`
- Update use case profile (typically auto-populated from usage)

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/use-case

# Update (JSONB fields)
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "primary_workflows": [
      {"name": "eligibility_verification", "count": 5, "last_used": "2024-01-01T00:00:00Z"}
    ],
    "workflow_frequency": {
      "eligibility_verification": {"count": 5, "last_used": "2024-01-01T00:00:00Z"}
    }
  }' \
  http://localhost:8000/api/users/2/profiles/use-case
```

### 5. AI Preference Profile

**GET** `/api/users/{user_id}/profiles/ai-preference`
- Get AI interaction preferences

**PUT** `/api/users/{user_id}/profiles/ai-preference`
- Update AI preference profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/ai-preference

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "preferred_strategy": "TABULA_RASA",
    "autonomy_level": "autonomous",
    "confidence_threshold": 0.75,
    "escalation_rules": {"high_risk": "always_confirm"},
    "require_confirmation_for": ["payment_actions", "data_deletion"]
  }' \
  http://localhost:8000/api/users/2/profiles/ai-preference
```

### 6. Query History Profile

**GET** `/api/users/{user_id}/profiles/query-history`
- Get query history and statistics (read-only, auto-populated)

```bash
# Get (read-only, auto-populated from usage)
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/query-history
```

---

## Session Links

**GET** `/api/users/{user_id}/session-links?limit=50`

Get all session links (queries linked to shaping_sessions).

```bash
curl -H "X-User-ID: your_auth_id" \
  "http://localhost:8000/api/users/2/session-links?limit=50"
```

**Response:**
```json
{
  "links": [
    {
      "id": 1,
      "user_id": 2,
      "session_id": 162,
      "interaction_id": "...",
      "query_text": "I need to verify patient eligibility",
      "query_category": null,
      "module": "workflow",
      "workflow_name": "eligibility_verification",
      "strategy": "TABULA_RASA",
      "session_status": "GATHERING",
      "consultant_strategy": "TABULA_RASA",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

---

## Frontend Integration Example (React/Next.js)

```typescript
// Get all profiles
const fetchAllProfiles = async (userId: number) => {
  const response = await fetch(`${apiUrl}/api/users/${userId}/profiles/all`, {
    headers: {
      'X-User-ID': session?.user?.id || ''
    }
  });
  return await response.json();
};

// Update basic profile
const updateBasicProfile = async (userId: number, updates: any) => {
  const response = await fetch(`${apiUrl}/api/users/${userId}/profiles/basic`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': session?.user?.id || ''
    },
    body: JSON.stringify(updates)
  });
  return await response.json();
};

// Get session links
const fetchSessionLinks = async (userId: number, limit = 50) => {
  const response = await fetch(
    `${apiUrl}/api/users/${userId}/session-links?limit=${limit}`,
    {
      headers: {
        'X-User-ID': session?.user?.id || ''
      }
    }
  );
  return await response.json();
};
```

---

## Profile Fields Reference

### Basic Profile Fields
- `preferred_name` - User's preferred name
- `phone` - Phone number
- `mobile` - Mobile number
- `alternate_email` - Alternate email
- `timezone` - Timezone (e.g., "America/New_York")
- `locale` - Locale (e.g., "en-US")
- `avatar_url` - Avatar image URL
- `bio` - User bio/description

### Professional Profile Fields
- `job_title` - Job title
- `department` - Department name
- `organization` - Organization/company name
- `manager_id` - Manager's user ID (references users.id)
- `team_name` - Team name
- `employee_id` - Employee ID
- `office_location` - Office location
- `start_date` - Start date (DATE format)

### Communication Profile Fields
- `communication_style` - "casual", "formal", "friendly", "professional"
- `tone_preference` - "concise", "detailed", "balanced"
- `response_format_preference` - "bullet_points", "structured", "conversational"
- `preferred_language` - Language code (e.g., "en")
- `notification_preferences` - JSONB object
- `engagement_level` - "engaging", "minimal", "detailed"

### Use Case Profile Fields (JSONB)
- `primary_workflows` - Array of workflow objects
- `workflow_frequency` - Object mapping workflow names to frequency data
- `module_preferences` - JSONB object
- `task_patterns` - Array of task patterns
- `domain_expertise` - Array of domain expertise areas

### AI Preference Profile Fields
- `preferred_strategy` - "TABULA_RASA", "EVIDENCE_BASED", "CREATIVE"
- `autonomy_level` - "autonomous", "consultative", "balanced"
- `confidence_threshold` - Decimal (0.0-1.0)
- `escalation_rules` - JSONB object
- `require_confirmation_for` - Array of action types
- `preferred_model_preferences` - JSONB object
- `strategy_preferences` - JSONB object
- `task_category_preferences` - JSONB object
- `task_domain_preferences` - JSONB object

### Query History Profile Fields (Read-only, Auto-populated)
- `most_common_queries` - Array of query objects with counts
- `query_categories` - Object mapping categories to counts
- `search_patterns` - Array of search patterns
- `question_templates` - Array of question templates
- `interaction_stats` - Statistics object (total_queries, avg_query_length, etc.)

---

## Notes

1. **User ID**: The `{user_id}` in URLs is the internal integer ID from the `users` table, not the auth_id
2. **Auto-population**: Query history and use case profiles are automatically updated when users interact with the system
3. **JSONB Fields**: Some fields (like `workflow_frequency`, `escalation_rules`) are JSONB and accept nested objects/arrays
4. **Read-only Fields**: Query history profile is read-only and automatically populated
5. **Session Links**: These are automatically created when workflow interactions occur






This guide shows you how to access and manage comprehensive user profiles through the API.

## Base URL

The API base URL is typically:
- **Local Development**: `http://localhost:8000`
- **Production**: Set via `NEXT_PUBLIC_API_URL` environment variable

## Authentication

All endpoints require the `X-User-ID` header with the user's auth_id (Google OAuth Subject ID).

```bash
X-User-ID: <user_auth_id>
```

## Profile Endpoints

### Get All Profiles at Once

**GET** `/api/users/{user_id}/profiles/all`

Returns all 6 profile types in one response.

```bash
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/all
```

**Response:**
```json
{
  "basic": {
    "user_id": 2,
    "preferred_name": "John",
    "phone": "555-1234",
    "mobile": "555-5678",
    "timezone": "America/New_York",
    ...
  },
  "professional": {
    "user_id": 2,
    "job_title": "Software Engineer",
    "department": "Engineering",
    "organization": "Test Corp",
    ...
  },
  "communication": {
    "user_id": 2,
    "communication_style": "friendly",
    "tone_preference": "concise",
    ...
  },
  "use_case": {
    "user_id": 2,
    "primary_workflows": [...],
    "workflow_frequency": {...},
    ...
  },
  "ai_preference": {
    "user_id": 2,
    "preferred_strategy": "TABULA_RASA",
    "autonomy_level": "autonomous",
    ...
  },
  "query_history": {
    "user_id": 2,
    "most_common_queries": [...],
    "interaction_stats": {...},
    ...
  }
}
```

---

## Individual Profile Endpoints

### 1. Basic Profile

**GET** `/api/users/{user_id}/profiles/basic`
- Get basic personal information (name, contacts, timezone, etc.)

**PUT** `/api/users/{user_id}/profiles/basic`
- Update basic profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/basic

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "preferred_name": "John",
    "phone": "555-1234",
    "mobile": "555-5678",
    "timezone": "America/New_York",
    "locale": "en-US"
  }' \
  http://localhost:8000/api/users/2/profiles/basic
```

### 2. Professional Profile

**GET** `/api/users/{user_id}/profiles/professional`
- Get professional information (job title, department, manager, etc.)

**PUT** `/api/users/{user_id}/profiles/professional`
- Update professional profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/professional

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "job_title": "Software Engineer",
    "department": "Engineering",
    "organization": "Your Company",
    "manager_id": 1,
    "team_name": "Platform Team"
  }' \
  http://localhost:8000/api/users/2/profiles/professional
```

### 3. Communication Profile

**GET** `/api/users/{user_id}/profiles/communication`
- Get communication preferences

**PUT** `/api/users/{user_id}/profiles/communication`
- Update communication profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/communication

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "communication_style": "friendly",
    "tone_preference": "concise",
    "response_format_preference": "bullet_points",
    "preferred_language": "en",
    "engagement_level": "engaging"
  }' \
  http://localhost:8000/api/users/2/profiles/communication
```

### 4. Use Case Profile

**GET** `/api/users/{user_id}/profiles/use-case`
- Get workflow patterns and use cases

**PUT** `/api/users/{user_id}/profiles/use-case`
- Update use case profile (typically auto-populated from usage)

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/use-case

# Update (JSONB fields)
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "primary_workflows": [
      {"name": "eligibility_verification", "count": 5, "last_used": "2024-01-01T00:00:00Z"}
    ],
    "workflow_frequency": {
      "eligibility_verification": {"count": 5, "last_used": "2024-01-01T00:00:00Z"}
    }
  }' \
  http://localhost:8000/api/users/2/profiles/use-case
```

### 5. AI Preference Profile

**GET** `/api/users/{user_id}/profiles/ai-preference`
- Get AI interaction preferences

**PUT** `/api/users/{user_id}/profiles/ai-preference`
- Update AI preference profile

```bash
# Get
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/ai-preference

# Update
curl -X PUT -H "X-User-ID: your_auth_id" \
  -H "Content-Type: application/json" \
  -d '{
    "preferred_strategy": "TABULA_RASA",
    "autonomy_level": "autonomous",
    "confidence_threshold": 0.75,
    "escalation_rules": {"high_risk": "always_confirm"},
    "require_confirmation_for": ["payment_actions", "data_deletion"]
  }' \
  http://localhost:8000/api/users/2/profiles/ai-preference
```

### 6. Query History Profile

**GET** `/api/users/{user_id}/profiles/query-history`
- Get query history and statistics (read-only, auto-populated)

```bash
# Get (read-only, auto-populated from usage)
curl -H "X-User-ID: your_auth_id" \
  http://localhost:8000/api/users/2/profiles/query-history
```

---

## Session Links

**GET** `/api/users/{user_id}/session-links?limit=50`

Get all session links (queries linked to shaping_sessions).

```bash
curl -H "X-User-ID: your_auth_id" \
  "http://localhost:8000/api/users/2/session-links?limit=50"
```

**Response:**
```json
{
  "links": [
    {
      "id": 1,
      "user_id": 2,
      "session_id": 162,
      "interaction_id": "...",
      "query_text": "I need to verify patient eligibility",
      "query_category": null,
      "module": "workflow",
      "workflow_name": "eligibility_verification",
      "strategy": "TABULA_RASA",
      "session_status": "GATHERING",
      "consultant_strategy": "TABULA_RASA",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

---

## Frontend Integration Example (React/Next.js)

```typescript
// Get all profiles
const fetchAllProfiles = async (userId: number) => {
  const response = await fetch(`${apiUrl}/api/users/${userId}/profiles/all`, {
    headers: {
      'X-User-ID': session?.user?.id || ''
    }
  });
  return await response.json();
};

// Update basic profile
const updateBasicProfile = async (userId: number, updates: any) => {
  const response = await fetch(`${apiUrl}/api/users/${userId}/profiles/basic`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': session?.user?.id || ''
    },
    body: JSON.stringify(updates)
  });
  return await response.json();
};

// Get session links
const fetchSessionLinks = async (userId: number, limit = 50) => {
  const response = await fetch(
    `${apiUrl}/api/users/${userId}/session-links?limit=${limit}`,
    {
      headers: {
        'X-User-ID': session?.user?.id || ''
      }
    }
  );
  return await response.json();
};
```

---

## Profile Fields Reference

### Basic Profile Fields
- `preferred_name` - User's preferred name
- `phone` - Phone number
- `mobile` - Mobile number
- `alternate_email` - Alternate email
- `timezone` - Timezone (e.g., "America/New_York")
- `locale` - Locale (e.g., "en-US")
- `avatar_url` - Avatar image URL
- `bio` - User bio/description

### Professional Profile Fields
- `job_title` - Job title
- `department` - Department name
- `organization` - Organization/company name
- `manager_id` - Manager's user ID (references users.id)
- `team_name` - Team name
- `employee_id` - Employee ID
- `office_location` - Office location
- `start_date` - Start date (DATE format)

### Communication Profile Fields
- `communication_style` - "casual", "formal", "friendly", "professional"
- `tone_preference` - "concise", "detailed", "balanced"
- `response_format_preference` - "bullet_points", "structured", "conversational"
- `preferred_language` - Language code (e.g., "en")
- `notification_preferences` - JSONB object
- `engagement_level` - "engaging", "minimal", "detailed"

### Use Case Profile Fields (JSONB)
- `primary_workflows` - Array of workflow objects
- `workflow_frequency` - Object mapping workflow names to frequency data
- `module_preferences` - JSONB object
- `task_patterns` - Array of task patterns
- `domain_expertise` - Array of domain expertise areas

### AI Preference Profile Fields
- `preferred_strategy` - "TABULA_RASA", "EVIDENCE_BASED", "CREATIVE"
- `autonomy_level` - "autonomous", "consultative", "balanced"
- `confidence_threshold` - Decimal (0.0-1.0)
- `escalation_rules` - JSONB object
- `require_confirmation_for` - Array of action types
- `preferred_model_preferences` - JSONB object
- `strategy_preferences` - JSONB object
- `task_category_preferences` - JSONB object
- `task_domain_preferences` - JSONB object

### Query History Profile Fields (Read-only, Auto-populated)
- `most_common_queries` - Array of query objects with counts
- `query_categories` - Object mapping categories to counts
- `search_patterns` - Array of search patterns
- `question_templates` - Array of question templates
- `interaction_stats` - Statistics object (total_queries, avg_query_length, etc.)

---

## Notes

1. **User ID**: The `{user_id}` in URLs is the internal integer ID from the `users` table, not the auth_id
2. **Auto-population**: Query history and use case profiles are automatically updated when users interact with the system
3. **JSONB Fields**: Some fields (like `workflow_frequency`, `escalation_rules`) are JSONB and accept nested objects/arrays
4. **Read-only Fields**: Query history profile is read-only and automatically populated
5. **Session Links**: These are automatically created when workflow interactions occur




