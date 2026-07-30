def test_register_success(client):
    response = client.post("/users", json={
        "name": "Test User",
        "email": "testuser@email.com",
        "age": 30,
        "password": "password123"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test User"
    assert data["email"] == "testuser@email.com"
    assert data["age"] == 30
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_email_fails(client):
    payload = {
        "name": "Test User",
        "email": "dupe@email.com",
        "age": 30,
        "password": "password123"
    }
    client.post("/users", json=payload)
    response = client.post("/users", json=payload)
    assert response.status_code in (400, 409)


def test_register_invalid_email_fails(client):
    response = client.post("/users", json={
        "name": "Test User",
        "email": "not-an-email",
        "age": 30,
        "password": "password123"
    })
    assert response.status_code == 422


def test_login_success(client):
    client.post("/users", json={
        "name": "Test User",
        "email": "testuser@email.com",
        "age": 30,
        "password": "password123"
    })

    response = client.post("/users/login", json={
        "email": "testuser@email.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user_id" in data


def test_login_wrong_password_fails(client):
    client.post("/users", json={
        "name": "Test User",
        "email": "testuser@email.com",
        "age": 30,
        "password": "password123"
    })

    response = client.post("/users/login", json={
        "email": "testuser@email.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


def test_login_nonexistent_user_fails(client):
    response = client.post("/users/login", json={
        "email": "doesnotexist@email.com",
        "password": "password123"
    })
    assert response.status_code == 401