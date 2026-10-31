# Admin Schema Specification

This document details the database representation and Pydantic schemas for **Admins** in Mayasabha.

---

## 1. Database Table: `admins`

```sql
CREATE TABLE IF NOT EXISTS "admins" (
    "admin_id" UUID NOT NULL,
    "admin_name" VARCHAR(256) NOT NULL UNIQUE,
    "passcode" VARCHAR(256) NOT NULL,
    PRIMARY KEY("admin_id")
);
```

### Field Definitions

| Column | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `admin_id` | `UUID` | No | Primary key identifier |
| `admin_name` | `VARCHAR(256)` | No | Unique login username |
| `passcode` | `VARCHAR(256)` | No | Secret passcode (supports plaintext or Argon2 hash) |

---

## 2. Pydantic Models

### `AdminLoginIn` (Request)
```python
class AdminLoginIn(BaseModel):
    admin_name: str = Field(..., min_length=1, max_length=256)
    passcode: str = Field(..., min_length=1, max_length=256)
```

### `AdminLoginOut` (Response)
```python
class AdminLoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_id: uuid.UUID
    role: str = "admin"
```

---

## 3. JWT Configuration

* **Algorithm:** `HS256`
* **Secret Length:** 64 bytes (128 hex characters)
* **Claims Payload:**
  * `admin_id`: UUID string
  * `role`: `"admin"`
  * `iat`: Issued-at UTC timestamp
  * `exp`: Expiration UTC timestamp (`TOKEN_TTL_SECONDS`, default 4 hours)
