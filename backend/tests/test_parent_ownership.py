"""Integration tests for parent/guardian ownership scoping.

The audit's most reputationally consequential finding was self-disclosed
in the project's own "Future Work" section: any authenticated parent could
read every student's data, because there was no concept anywhere of "this
student belongs to this guardian." These tests prove, end-to-end through
real HTTP requests, that after linking a Student to a parent's User row
via `parent_id`:

  - list_students() only returns a parent's own children;
  - the wellness indicator 404s (not discloses via 403) a student that
    isn't the requesting parent's child;
  - the gamification leaderboard only shows a parent's own children;
  - admin/teacher remain unrestricted (school-wide visibility is required
    for their role);
  - only admin/teacher may assign a student's parent, and only to an
    account that actually has the 'parent' role.
"""

API = "/api/v1"


def _register_parent(client, email):
    """Registers a plain user then flips their role to 'parent' directly
    in the DB — mirrors the pattern already used by
    conftest.py::make_authenticated_client for non-default roles, but
    returns the raw user id (needed as `parent_id` for linking a student).
    """
    from backend.database import db as _db
    from backend.models import User

    resp = client.post(f"{API}/auth/register", json={"email": email, "password": "password123"})
    assert resp.status_code == 200
    user = User.query.filter_by(email=email).first()
    user.role = "parent"
    _db.session.commit()
    return user.id


class TestListStudentsOwnership:
    def test_parent_only_sees_own_children(self, app, make_authenticated_client):
        admin_client, admin_headers, _ = make_authenticated_client("owner.admin1@example.com", role="admin")

        with app.app_context():
            parent_a_id = _register_parent(admin_client, "parent.a1@example.com")
            parent_b_id = _register_parent(admin_client, "parent.b1@example.com")

        s1 = admin_client.post(
            f"{API}/students/", json={"name": "Child of A", "grade": "S3", "parent_id": parent_a_id}, headers=admin_headers
        ).get_json()["id"]
        admin_client.post(
            f"{API}/students/", json={"name": "Child of B", "grade": "S3", "parent_id": parent_b_id}, headers=admin_headers
        )

        # Log in directly rather than via make_authenticated_client, which
        # would try to re-register this already-registered email and 400.
        login_resp = admin_client.post(
            f"{API}/auth/login", json={"email": "parent.a1@example.com", "password": "password123"}
        )
        assert login_resp.status_code == 200
        headers = {"Authorization": f"Bearer {login_resp.get_json()['access_token']}"}

        resp = admin_client.get(f"{API}/students/", headers=headers)

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total"] == 1
        assert body["students"][0]["id"] == s1

    def test_admin_sees_all_students_regardless_of_parent_link(self, app, make_authenticated_client):
        admin_client, admin_headers, _ = make_authenticated_client("owner.admin2@example.com", role="admin")
        parent_id = _register_parent(admin_client, "parent.c1@example.com")

        admin_client.post(
            f"{API}/students/", json={"name": "Linked Child", "grade": "S3", "parent_id": parent_id}, headers=admin_headers
        )
        admin_client.post(f"{API}/students/", json={"name": "Unlinked Child", "grade": "S3"}, headers=admin_headers)

        resp = admin_client.get(f"{API}/students/", headers=admin_headers)

        assert resp.status_code == 200
        assert resp.get_json()["total"] == 2


class TestWellnessIndicatorOwnership:
    def test_parent_gets_404_for_child_that_is_not_theirs(self, app, make_authenticated_client):
        admin_client, admin_headers, _ = make_authenticated_client("owner.admin3@example.com", role="admin")
        other_parent_id = _register_parent(admin_client, "parent.d1@example.com")

        other_student_id = admin_client.post(
            f"{API}/students/",
            json={"name": "Someone Else's Child", "grade": "S3", "parent_id": other_parent_id},
            headers=admin_headers,
        ).get_json()["id"]

        _register_parent(admin_client, "parent.e1@example.com")
        login_resp = admin_client.post(
            f"{API}/auth/login", json={"email": "parent.e1@example.com", "password": "password123"}
        )
        headers = {"Authorization": f"Bearer {login_resp.get_json()['access_token']}"}

        resp = admin_client.get(f"{API}/wellness/indicator?student_id={other_student_id}", headers=headers)

        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "not_found"

    def test_parent_can_view_own_childs_indicator(self, app, make_authenticated_client):
        admin_client, admin_headers, _ = make_authenticated_client("owner.admin4@example.com", role="admin")
        parent_id = _register_parent(admin_client, "parent.f1@example.com")

        student_id = admin_client.post(
            f"{API}/students/", json={"name": "My Child", "grade": "S3", "parent_id": parent_id}, headers=admin_headers
        ).get_json()["id"]

        login_resp = admin_client.post(
            f"{API}/auth/login", json={"email": "parent.f1@example.com", "password": "password123"}
        )
        headers = {"Authorization": f"Bearer {login_resp.get_json()['access_token']}"}

        resp = admin_client.get(f"{API}/wellness/indicator?student_id={student_id}", headers=headers)

        assert resp.status_code == 200


class TestLeaderboardOwnership:
    def test_parent_only_sees_own_children_on_leaderboard(self, app, make_authenticated_client):
        admin_client, admin_headers, _ = make_authenticated_client("owner.admin5@example.com", role="admin")
        parent_id = _register_parent(admin_client, "parent.g1@example.com")

        my_child_id = admin_client.post(
            f"{API}/students/", json={"name": "My Leaderboard Child", "grade": "S3", "parent_id": parent_id}, headers=admin_headers
        ).get_json()["id"]
        other_child_id = admin_client.post(
            f"{API}/students/", json={"name": "Other Leaderboard Child", "grade": "S3"}, headers=admin_headers
        ).get_json()["id"]

        admin_client.post(f"{API}/gamify/award", json={"student_id": my_child_id, "xp": 10}, headers=admin_headers)
        admin_client.post(f"{API}/gamify/award", json={"student_id": other_child_id, "xp": 99}, headers=admin_headers)

        login_resp = admin_client.post(
            f"{API}/auth/login", json={"email": "parent.g1@example.com", "password": "password123"}
        )
        headers = {"Authorization": f"Bearer {login_resp.get_json()['access_token']}"}

        resp = admin_client.get(f"{API}/gamify/leaderboard", headers=headers)

        assert resp.status_code == 200
        rows = resp.get_json()["leaderboard"]
        assert len(rows) == 1
        assert rows[0]["student_id"] == my_child_id


class TestAssignParentEndpoint:
    def test_parent_role_cannot_assign_guardianship(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("assign.parent.denied@example.com", role="parent")

        student_resp = client.post(f"{API}/students/", json={"name": "X", "grade": "S3"}, headers=headers)
        # A parent isn't blocked from creating a student in this pass's
        # scope (mutation gating was explicitly out of scope — see the
        # accompanying report), so this may succeed; what matters is the
        # PATCH below being denied regardless of that outcome.
        student_id = student_resp.get_json().get("id", 1)

        resp = client.patch(f"{API}/students/{student_id}/parent", json={"parent_id": None}, headers=headers)

        assert resp.status_code == 403

    def test_admin_can_assign_a_valid_parent(self, make_authenticated_client):
        admin_client, admin_headers, _ = make_authenticated_client("assign.admin1@example.com", role="admin")
        parent_id = _register_parent(admin_client, "parent.h1@example.com")
        student_id = admin_client.post(
            f"{API}/students/", json={"name": "Assignable Child", "grade": "S3"}, headers=admin_headers
        ).get_json()["id"]

        resp = admin_client.patch(
            f"{API}/students/{student_id}/parent", json={"parent_id": parent_id}, headers=admin_headers
        )

        assert resp.status_code == 200
        assert resp.get_json()["parent_id"] == parent_id

    def test_assigning_a_non_parent_account_is_rejected(self, make_authenticated_client):
        admin_client, admin_headers, other_admin_id = make_authenticated_client(
            "assign.admin2@example.com", role="admin"
        )
        student_id = admin_client.post(
            f"{API}/students/", json={"name": "Rejectable Child", "grade": "S3"}, headers=admin_headers
        ).get_json()["id"]

        resp = admin_client.patch(
            f"{API}/students/{student_id}/parent", json={"parent_id": other_admin_id}, headers=admin_headers
        )

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"

    def test_create_student_rejects_non_parent_parent_id(self, make_authenticated_client):
        admin_client, admin_headers, other_admin_id = make_authenticated_client(
            "create.rejects.nonparent@example.com", role="admin"
        )

        resp = admin_client.post(
            f"{API}/students/",
            json={"name": "Bad Link", "grade": "S3", "parent_id": other_admin_id},
            headers=admin_headers,
        )

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"
