# MAYASABHA API Documentation

Comprehensive API documentation for the **Mayasabha Indian Monument-Based CTF Platform**.

---

## Documentation Structure

```text
documentation/
├── README.md              # Documentation overview and sitemap (this file)
├── routes/                # Endpoint specifications organized by tag/router
│   └── admins.md          # Admin endpoints (/admins/*)
└── schemas/               # Data models and validation schemas
    ├── admin.md           # Admin entity & login schemas
    └── team.md            # Team entity & payload schemas
```

---

## Route Index

### `/admins` Router (New Implementation)
| Route # | Method | Path | Summary | Documentation |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `POST` | [`/admins/teams`](file:///C:/Users/Arnesh/Desktop/mayasabha/documentation/routes/admins.md#admin-route-1-create-team) | Create a new team with autofilled defaults | [admins.md](file:///C:/Users/Arnesh/Desktop/mayasabha/documentation/routes/admins.md) |
| **2** | `POST` | [`/admins/login`](file:///C:/Users/Arnesh/Desktop/mayasabha/documentation/routes/admins.md#admin-route-2-admin-login) | Admin login returning JWT with `admin_id` and `role` | [admins.md](file:///C:/Users/Arnesh/Desktop/mayasabha/documentation/routes/admins.md) |

---

## Schema Index

* [Admin Schema (`admin.md`)](file:///C:/Users/Arnesh/Desktop/mayasabha/documentation/schemas/admin.md): Database table structure, Pydantic models, and 64-byte JWT configuration.
* [Team Schema (`team.md`)](file:///C:/Users/Arnesh/Desktop/mayasabha/documentation/schemas/team.md): Covers database table structure, JSONB validation for `leader_details`, array types for `team_members`, and Pydantic request/response schemas.
