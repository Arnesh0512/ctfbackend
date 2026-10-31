# Teams Routes (`/teams`)

Endpoints for team authentication and game interaction following the decoupled architecture.

---

## Team Route 1: Team Login

Authenticates a team registered by an administrator with their `username` and `password`, returning a signed JWT access token.

* **Method:** `POST`
* **Path:** `/teams/login`
* **Authentication:** **None** (Public endpoint - Not JWT protected)
* **Status Code:** `200 OK`
* **Tags:** `teams`

### Request Body (`application/json`)

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `username` | `string` | **Yes** | Team login username created by admin |
| `password` | `string` | **Yes** | Team login password |

#### Example Request:
```json
{
  "username": "garuda_2026",
  "password": "StrongSecretPassword123!"
}
```

---

### Response Body (`200 OK`)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "team_id": "a37e11d5-eafa-464d-91e4-95dc941ad371",
  "role": "team"
}
```

### JWT Token Claims
The generated token is signed using the 64-byte `JWT_SECRET` in `.env` with HMAC-SHA256 (`HS256`):
```json
{
  "team_id": "a37e11d5-eafa-464d-91e4-95dc941ad371",
  "role": "team",
  "username": "garuda_2026",
  "team_name": "Garuda CTF",
  "iat": 1793455488,
  "exp": 1793469888
}
```

---

## Team Route 2: Get Team Profile

Fetches the profile details of the authenticated team using their JWT access token.

* **Method:** `GET`
* **Path:** `/teams/profile`
* **Authentication:** **JWT Bearer Required** (`Authorization: Bearer <team_token>`)
* **Status Code:** `200 OK`
* **Tags:** `teams`

### Response Body (`200 OK`)

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
  }
}
```

---

### Error Responses

| Status Code | Reason | Example Response |
| :--- | :--- | :--- |
| `401 Unauthorized` | Invalid username/password on login, or missing/expired JWT | `{"detail": "Not authenticated"}` |
| `403 Forbidden` | Valid JWT provided, but role is not `team` (e.g. admin token used) | `{"detail": "Forbidden: Team privilege required"}` |
| `404 Not Found` | Team associated with token no longer exists in database | `{"detail": "Team not found"}` |
| `422 Unprocessable Entity` | Missing input fields | `{"detail": [{"loc": ["body", "password"], "msg": "Field required"}]}` |
