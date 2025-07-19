#!/usr/bin/env python3

import json

import requests


def test_auth():
    base_url = "http://localhost:8000"

    print("=== Testing Registration ===")
    register_data = {
        "email": "nlptest@example.com",
        "password": "password123",
        "first_name": "NLP",
        "last_name": "Test",
    }

    response = requests.post(
        f"{base_url}/auth/register",
        data=register_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    print(f"Registration status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Registration successful: {result.get('user', {}).get('email')}")
        token = result.get("accessToken")
        print(f"Token received: {token[:20] if token else 'None'}...")
        return token
    else:
        print(f"Registration failed: {response.text}")

        print("\n=== Testing Login ===")
        login_data = {"email": "nlptest@example.com", "password": "password123"}

        response = requests.post(
            f"{base_url}/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        print(f"Login status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Login successful: {result.get('user', {}).get('email')}")
            token = result.get("accessToken")
            print(f"Token received: {token[:20] if token else 'None'}...")
            return token
        else:
            print(f"Login failed: {response.text}")
            return None


if __name__ == "__main__":
    test_auth()
