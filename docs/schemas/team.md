# Team Schema Specification

This document details the database representation and Pydantic schemas for **Teams** in Mayasabha.

---

## 1. Database Table: `teams`

```sql
CREATE TABLE IF NOT EXISTS "teams" (
    "team_id" UUID NOT NULL,
    "team_name" VARCHAR(256) NOT NULL,
    "team_members" TEXT ARRAY,
    "leader_details" JSONB NOT NULL,
    "username" VARCHAR(256) NOT NULL UNIQUE,
    "password" VARCHAR(256) NOT NULL,
    "points" DECIMAL NOT NULL DEFAULT 0.00 CHECK (points >= 0),
    "powerups_used" INTEGER NOT NULL DEFAULT 0,
    "playthrough" TIME NOT NULL DEFAULT '00:00:00',
    "has_reached_delhi" BOOLEAN NOT NULL DEFAULT false,
    "current_path_id" UUID,
    "current_question_id" UUID,
    "frozen_until" TIMESTAMPTZ,
    "developer_time" TIME DEFAULT '00:00:00',
    "skip" UUID,
    PRIMARY KEY("team_id"),
    CONSTRAINT fk_teams_current_path_id_paths FOREIGN KEY ("current_path_id") REFERENCES "paths"("path_id") ON DELETE SET NULL,
    CONSTRAINT check_leader_details_fields CHECK (
        leader_details ? 'name' AND
        leader_details ? 'contact' AND
        leader_details ? 'email' AND
        leader_details ? 'enrollment' AND
        leader_details ? 'college'
    )
);
```

### Field Definitions

| Column | Data Type | Nullable | Default | Description |
| :--- | :--- | :---: | :--- | :--- |
| `team_id` | `UUID` | No | `uuid.uuid4()` | Unique primary key for the team |
| `team_name` | `VARCHAR(256)` | No | - | Display name of the team |
| `team_members`| `TEXT[]` | Yes | `[]` | List of team member names (excluding leader) |
| `leader_details` | `JSONB` | No | - | Leader info: `name`, `contact`, `email`, `enrollment`, `college` |
| `username` | `VARCHAR(256)` | No | - | Unique login identifier |
| `password` | `VARCHAR(256)` | No | - | Argon2-hashed password |
| `points` | `NUMERIC(10,2)` | No | `0.00` | Team score (cannot be negative) |
| `powerups_used` | `INTEGER` | No | `0` | Count of power-ups consumed |
| `playthrough` | `TIME` | No | `'00:00:00'` | Active game time clock |
| `has_reached_delhi`| `BOOLEAN` | No | `false` | Victory flag |
| `current_path_id`| `UUID` | Yes | `NULL` | FK to currently chosen route |
| `current_question_id`| `UUID` | Yes | `NULL` | Current question being attempted |
| `frozen_until`| `TIMESTAMPTZ` | Yes | `NULL` | Lockout expiration timestamp |
| `developer_time`| `TIME` | Yes | `'00:00:00'` | Debug/developer timer |
| `skip` | `UUID` | Yes | `NULL` | Question skipped |

---

## 2. Pydantic Models

### `LeaderDetails`
```python
class LeaderDetails(BaseModel):
    name: str = Field(..., min_length=1, max_length=256, description="Leader full name")
    contact: str = Field(..., min_length=1, max_length=64, description="Leader contact phone number")
    email: str = Field(..., min_length=1, max_length=256, description="Leader email address")
    enrollment: str = Field(..., min_length=1, max_length=128, description="Leader enrollment number / student ID")
    college: str = Field(..., min_length=1, max_length=256, description="Leader college or institute name")
```

### `CreateTeamIn` (Request)
```python
class CreateTeamIn(BaseModel):
    team_name: str = Field(..., min_length=1, max_length=256)
    team_members: list[str] = Field(default_factory=list)
    leader_details: LeaderDetails
    username: str = Field(..., min_length=1, max_length=256)
    password: str = Field(..., min_length=1, max_length=256)
```

### `TeamOut` (Response)
Returns all team fields with `points` formatted as `Decimal` string (`"0.00"`), `playthrough` as `"00:00:00"`, and `has_reached_delhi` as `false`.
