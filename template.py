from pathlib import Path

# Define the folder and file structure
structure = {
    
        "data/fire/.gitkeep",
        "data/smoke/.gitkeep",
        "data/normal/.gitkeep",
        "models/fire_smoke_model.h5",
        "src/train_model.py",
        "src/predict.py",
        "src/video_inference.py",
        "src/alert_system.py",
        "templates/index.html",
        "static/css/style.css",
        "app/app.py",
        "utils/preprocessing.py",
        "requirements.txt",
        "README.md",
        "setup.py",
        "main.py"

    
}

# Create the folders and files
for file in structure:
    file_path = Path(file)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.touch()

print("✅ Template folder structure created successfully.")

