# Admin Routes (`/admin`)

Administrative endpoints following the decoupled architecture (`routes`, `schemas`, `verify`, `utils`).

---

## Admin Route 1: Admin Login

Authenticates an administrator with preexisting database credentials and returns a signed JWT access token.

* **Method:** `POST`
* **Path:** `/admin/login`
* **Status Code:** `200 OK`
* **Tags:** `admin`

### Request Body (`application/json`)

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `admin_name` | `string` | **Yes** | Admin name as stored in the database |
| `passcode` | `string` | **Yes** | Secret passcode (supports plaintext match or Argon2 hash) |

#### Example Request:
```json
{
  "admin_name": "admin",
  "passcode": "admin123"
}
```

### Response Body (`200 OK`)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "admin_id": "c0000000-0000-0000-0000-000000000001",
  "role": "admin"
}
```

### JWT Token Claims
The generated token is signed using the 64-byte `JWT_SECRET` in `.env` using HMAC-SHA256 (`HS256`):
```json
{
  "admin_id": "c0000000-0000-0000-0000-000000000001",
  "role": "admin",
  "admin_name": "admin",
  "iat": 1793443161,
  "exp": 1793457561
}
```

---

## Admin Route 2: Create Team

Creates a new team login in the CTF event with user-supplied credentials and automatically populated initial game state.

* **Method:** `POST`
* **Path:** `/admin/teams`
* **Status Code:** `201 Created`
* **Tags:** `admin`

### Request Body (`application/json`)

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `team_name` | `string` | **Yes** | Display name of the team (1–256 chars) |
| `team_members` | `string[]` | No | List of member names (defaults to `[]`) |
| `leader_details` | `object` | **Yes** | Leader contact object containing `name`, `contact`, `email`, `enrollment`, and `college` |
| `username` | `string` | **Yes** | Unique login username (1–256 chars) |
| `password` | `string` | **Yes** | Plaintext password (hashed with Argon2 before storage) |

#### Example Request:
```json
{
  "team_name": "Garuda CTF",
  "team_members": ["Arnesh", "Rohan"],
  "leader_details": {
    "name": "Arnesh Leader",
    "contact": "+91 9876543210",
    "email": "leader@garuda.in",
    "enrollment": "05116403221",
    "college": "USICT"
  },
  "username": "garuda_2026",
  "password": "StrongSecretPassword123!"
}
```

### Autofilled Defaults (Internal)
When creating the team, the system automatically assigns:
* `team_id`: Generated `UUIDv4`
* `password`: Hashed using `argon2`
* `points`: `0.00`
* `powerups_used`: `0`
* `playthrough`: `"00:00:00"` (time)
* `has_reached_delhi`: `false` (boolean)
* `current_path_id`: `null`
* `current_question_id`: `null`
* `frozen_until`: `null`
* `developer_time`: `"00:00:00"` (time)
* `skip`: `null`

### Response Body (`201 Created`)

```json
{
  "team_id": "a37e11d5-eafa-464d-91e4-95dc941ad371",
  "team_name": "Garuda CTF",
  "team_members": ["Arnesh", "Rohan"],
  "leader_details": {
    "name": "Arnesh Leader",
    "contact": "+91 9876543210",
    "email": "leader@garuda.in",
    "enrollment": "05116403221",
    "college": "USICT"
  },
  "username": "garuda_2026",
  "points": "0.00",
  "powerups_used": 0,
  "playthrough": "00:00:00",
  "has_reached_delhi": false,
  "current_path_id": null,
  "current_question_id": null,
  "frozen_until": null,
  "developer_time": "00:00:00",
  "skip": null
}
```

---

### Error Responses

| Status Code | Reason | Example Response |
| :--- | :--- | :--- |
| `401 Unauthorized` | Invalid `admin_name` or `passcode` | `{"detail": "Invalid admin credentials"}` |
| `409 Conflict` | Username already in use | `{"detail": "Username 'garuda_2026' is already in use."}` |
| `422 Unprocessable Entity` | Missing input fields | `{"detail": [{"loc": ["body", "passcode"], "msg": "Field required"}]}` |
