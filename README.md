# AI-Based Smart Attendance Monitoring System

A complete Python 3.14-compatible internship project using FastAPI, OpenCV, SQLite, and a responsive web dashboard.

## Main features

- Student registration with a face photograph
- OpenCV face detection and normalized face embeddings
- Browser webcam scanner
- Separate desktop webcam attendance scanner
- Automatic daily attendance
- Duplicate attendance prevention
- Present, absent, and attendance-rate statistics
- Student management
- Attendance history and date filtering
- CSV report download
- REST API documentation
- SQLite database
- GitHub Actions check
- Professional GitHub-ready folder structure

## Run in VS Code on Windows

Open the extracted folder in VS Code. Select **Terminal > New Terminal**, then run:

```powershell
py -3.14 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python run.py
```

Open the dashboard:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

## Run desktop webcam scanner

Keep the web server running. Open another VS Code terminal:

```powershell
.venv\Scripts\activate
python scripts/camera_attendance.py
```

Press **Q** to close the camera.

## Face-recognition method

1. OpenCV detects the largest face using a Haar Cascade.
2. The face is converted to grayscale.
3. It is resized to 64 x 64 pixels.
4. Histogram equalization improves lighting consistency.
5. The image is normalized into a compact numerical embedding.
6. Cosine similarity compares the live face with saved students.
7. Attendance is marked when the similarity crosses the threshold.

This implementation avoids older native `dlib`-based packages that are often difficult to install with new Python versions.

## Upload to GitHub

```powershell
git init
git add .
git commit -m "Initial commit: AI smart attendance system"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

## Important privacy note

This is an educational biometric prototype. Obtain consent before collecting face photographs, restrict access to the database and images, and follow applicable privacy rules before using it in a real institution.
