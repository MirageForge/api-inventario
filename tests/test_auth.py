def test_login_successful(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin_test", "password": "SecretPass123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin_test", "password": "WrongPassword"}
    )
    assert response.status_code == 401
    assert "incorrectos" in response.json()["detail"].lower()


def test_get_current_user_me(client, admin_headers):
    response = client.get("/api/v1/auth/me", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin_test"
    assert data["role"] == "admin"


def test_unauthenticated_request_fails(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_operator_cannot_access_admin_user_list(client, operator_headers):
    response = client.get("/api/v1/auth/users", headers=operator_headers)
    assert response.status_code == 403


def test_register_regular_user_cannot_become_admin(client, admin_user):
    """Verifica que un nuevo registro público NO pueda auto-asignarse rol de admin."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "nuevo_usuario",
            "email": "nuevo@test.com",
            "full_name": "Nuevo Usuario",
            "password": "Password123!",
            "role": "admin"  # Intento de escalamiento de privilegios
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "operator"  # Debe ser forzado a OPERATOR
