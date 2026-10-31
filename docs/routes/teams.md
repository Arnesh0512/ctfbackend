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

This JWT is used by all other team routes in the backend for authentication.

---

### Error Responses

| Status Code | Reason | Example Response |
| :--- | :--- | :--- |
| `401 Unauthorized` | Invalid username or password | `{"detail": "Invalid team credentials"}` |
| `422 Unprocessable Entity` | Missing input fields | `{"detail": [{"loc": ["body", "password"], "msg": "Field required"}]}` |
