#!/usr/bin/env python3
"""Simulate a minimal mobile app: request OTP, verify it, upload an image.

Run with the project's virtualenv python so `requests` is available:
  .venv/bin/python3 scripts/simulate_mobile.py
"""
import json
import mimetypes
import os
import sqlite3
import sys
import tempfile
import time
import urllib.parse
import urllib.request


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = "http://127.0.0.1:8000/api"
DB_PATH = os.path.join(ROOT_DIR, "backend", "db.sqlite3")
PHONE = "221770000000"
TOKEN_PATH = os.path.join(ROOT_DIR, "simulated_token.txt")


def request_otp(phone: str):
    url = f"{BASE_URL}/auth/request-otp/"
    data = json.dumps({"phone": phone}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
            print("request_otp ->", resp.getcode(), body)
            return resp.getcode(), body
    except urllib.error.HTTPError as e:
        print("request_otp ->", e.code, e.read().decode())
        return e.code, e.read().decode()


def get_latest_otp_code():
    if not os.path.exists(DB_PATH):
        print("DB not found:", DB_PATH)
        return None
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("select code from api_otprequest order by id desc limit 1;")
    row = cur.fetchone()
    con.close()
    if not row:
        return None
    return row[0]


def verify_otp(phone: str, code: str):
    url = f"{BASE_URL}/auth/verify-otp/"
    data = json.dumps({"phone_number": phone, "otp_code": code}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
            print("verify_otp ->", resp.getcode(), body)
            try:
                return json.loads(body).get("token")
            except Exception:
                return None
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print("verify_otp ->", e.code, body)
        return None


def encode_multipart(fields, files, boundary=None):
    if boundary is None:
        boundary = "----WebKitFormBoundary" + str(int(time.time() * 1000))
    lines = []
    for (key, value) in fields.items():
        lines.append(f"--{boundary}")
        lines.append(f"Content-Disposition: form-data; name=\"{key}\"")
        lines.append("")
        lines.append(str(value))
    for (key, filename, value) in files:
        lines.append(f"--{boundary}")
        ctype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        lines.append(f"Content-Disposition: form-data; name=\"{key}\"; filename=\"{filename}\"")
        lines.append(f"Content-Type: {ctype}")
        lines.append("")
        if isinstance(value, bytes):
            lines.append(value)
        else:
            lines.append(value.decode() if isinstance(value, bytearray) else value)
    lines.append(f"--{boundary}--")
    lines.append("")
    body = b""
    for item in lines:
        if isinstance(item, bytes):
            body += item + b"\r\n"
        else:
            body += item.encode() + b"\r\n"
    content_type = f"multipart/form-data; boundary={boundary}"
    return content_type, body


def upload_test_image(token: str):
    url = f"{BASE_URL}/upload-image/"
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(b"test image from simulate_mobile\n")
    with open(path, "rb") as f:
        file_bytes = f.read()
    filename = os.path.basename(path)
    content_type, body = encode_multipart({}, [("image", filename, file_bytes)])
    headers = {"Content-Type": content_type, "Authorization": f"Token {token}"}
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            result = resp.read().decode()
            print("upload ->", resp.getcode(), result)
            return resp.getcode(), result
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print("upload ->", e.code, body)
        return e.code, body
    finally:
        try:
            os.remove(path)
        except Exception:
            pass


def main():
    print("Base URL:", BASE_URL)
    request_otp(PHONE)
    # small wait for DB write
    time.sleep(0.4)
    code = get_latest_otp_code()
    if not code:
        print("No OTP code found in DB. Exiting.")
        sys.exit(2)
    print("Found OTP code:", code)
    token = verify_otp(PHONE, code)
    if not token:
        print("Verify failed. Exiting.")
        sys.exit(3)
    print("Received token:", token)
    # save token to simulate secure store
    with open(TOKEN_PATH, "w") as f:
        f.write(token)
    upload_test_image(token)


if __name__ == "__main__":
    main()
