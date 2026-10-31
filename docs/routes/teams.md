# Teams Routes (`/teams`)

Endpoints for team authentication and game interaction following the decoupled architecture.

---

## Team Route 1: Team Login

Authenticates a team registered by an administrator with their `username` and `password`. The JWT token is set directly in a secure **`HttpOnly` cookie** (`team_token`) so that client-side JavaScript and the user cannot view or extract it, protecting against XSS attacks.

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

### Response Headers
```http
Set-Cookie: team_token=eyJhbGciOiJIUzI1NiIsInR5c...; Max-Age=14400; Path=/; HttpOnly; SameSite=lax
```

### Response Body (`200 OK`)

The JWT is **not** exposed in the response body to prevent user / script inspection:
```json
{
  "message": "Login successful",
  "team_id": "a37e11d5-eafa-464d-91e4-95dc941ad371",
  "role": "team"
}
```

---

## Team Route 2: Get Team Profile

Fetches the profile details of the authenticated team. Authentication is handled automatically via the secure `team_token` **`HttpOnly` cookie** sent by the browser (or via `Authorization: Bearer <token>` fallback in Swagger UI / API tools).

* **Method:** `GET`
* **Path:** `/teams/profile`
* **Authentication:** **`team_token` HttpOnly Cookie** or **JWT Bearer**
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
| `401 Unauthorized` | Invalid username/password on login, or missing/expired cookie | `{"detail": "Not authenticated"}` |
| `403 Forbidden` | Valid JWT provided, but role is not `team` (e.g. admin token used) | `{"detail": "Forbidden: Team privilege required"}` |
| `404 Not Found` | Team associated with token no longer exists in database | `{"detail": "Team not found"}` |
| `422 Unprocessable Entity` | Missing input fields | `{"detail": [{"loc": ["body", "password"], "msg": "Field required"}]}` |
