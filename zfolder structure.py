import os

def print_folder_structure(start_path, indent=''):
    for item in os.listdir(start_path):
        path = os.path.join(start_path, item)
        if os.path.isdir(path):
            print(f"{indent}📁 {item}/")
            print_folder_structure(path, indent + '    ')
        else:
            print(f"{indent}📄 {item}")

# Change this path to your Flask project root
project_root = '.'  # or specify full path: 'D:/projects/song-cluster-app'
print(f"📂 Project Structure: {os.path.abspath(project_root)}\n")
print_folder_structure(project_root)
