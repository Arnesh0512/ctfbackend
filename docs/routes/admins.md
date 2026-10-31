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

---

## Admin Route 2: Create Team

Creates a new team login in the CTF event with user-supplied credentials and automatically populated initial game state.

* **Method:** `POST`
* **Path:** `/admin/teams`
* **Headers:** `Authorization: Bearer <admin_token>`
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

---

## Admin Route 3: Fetch All Teams

Fetches all teams with their display name, login username, password hash, leader name, and leader enrollment.

* **Method:** `GET`
* **Path:** `/admin/teams`
* **Headers:** `Authorization: Bearer <admin_token>`
* **Status Code:** `200 OK`
* **Tags:** `admin`

### Response Body (`200 OK`)

```json
[
  {
    "team_id": "95a65100-0000-0000-0000-000000000001",
    "team_name": "Full Leader Team",
    "username": "team_95a651",
    "password": "$argon2id$v=19$m=65536,t=3,p=4$...",
    "leader_name": "Arnesh Leader",
    "leader_enrollment": "05116403221"
  },
  {
    "team_id": "4b0bc9bf-deb9-4dbc-b7e9-6fdb83ded7f7",
    "team_name": "IEEE Alpha Squad",
    "username": "team_ieee_942405",
    "password": "$argon2id$v=19$m=65536,t=3,p=4$...",
    "leader_name": "Arnesh Leader",
    "leader_enrollment": "N/A"
  }
]
```

---

### Error Responses

| Status Code | Reason | Example Response |
| :--- | :--- | :--- |
| `401 Unauthorized` | Missing, invalid, or expired JWT Bearer token | `{"detail": "Not authenticated"}` |
| `403 Forbidden` | JWT does not have admin privileges | `{"detail": "Forbidden: Admin privilege required"}` |
| `409 Conflict` | Team username already in use | `{"detail": "Username 'garuda_2026' is already in use."}` |
