import socket
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import time
import platform
import subprocess
import sys

# ===== Step 1: Read username & password from data.txt =====
def read_credentials():
    try:
        with open("data.txt", "r") as f:
            lines = f.read().splitlines()
            username = lines[0].strip()
            password = lines[1].strip()
            return username, password
    except FileNotFoundError:
        print("❌ Error: data.txt file not found!")
        print("📝 Please create data.txt with:")
        print("   Line 1: Username")
        print("   Line 2: Password")
        sys.exit(1)
    except IndexError:
        print("❌ Error: data.txt must contain at least 2 lines (username and password)")
        sys.exit(1)

USERNAME, PASSWORD = read_credentials()

PORT = 554
MAX_CHANNELS = 8   # maximum number of channels to test

# ===== Step 2: Auto-detect LAN Networks (Pure Python) =====
def get_local_ip():
    """Get the local IP address"""
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return None

def get_windows_network_info():
    """Get network info on Windows using ipconfig"""
    networks = []
    try:
        # Run ipconfig command
        result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                line = line.strip()
                if 'IPv4 Address' in line and ':' in line:
                    ip = line.split(':')[-1].strip()
                    if ip and not ip.startswith('127.') and not ip.startswith('169.254'):
                        # Extract network portion
                        ip_parts = ip.split('.')
                        if len(ip_parts) == 4:
                            network_base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
                            if network_base not in [net.split('.')[:-1] for net in networks]:
                                networks.append(network_base)
                                print(f"🔍 Found network: {network_base}.0/24 (from {ip})")
    except Exception as e:
        print(f"⚠️  Could not run ipconfig: {e}")
    return networks

def get_linux_network_info():
    """Get network info on Linux using ip or ifconfig"""
    networks = []
    try:
        # Try 'ip addr' first
        result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'inet ' in line and 'scope global' in line:
                    parts = line.strip().split()
                    for part in parts:
                        if '/' in part and '.' in part:
                            ip_with_mask = part.split('/')[0]
                            if not ip_with_mask.startswith('127.') and not ip_with_mask.startswith('169.254'):
                                ip_parts = ip_with_mask.split('.')
                                if len(ip_parts) == 4:
                                    network_base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
                                    if network_base not in networks:
                                        networks.append(network_base)
                                        print(f"🔍 Found network: {network_base}.0/24 (from {ip_with_mask})")
    except Exception:
        # Fallback to ifconfig
        try:
            result = subprocess.run(['ifconfig'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'inet ' in line:
                        parts = line.strip().split()
                        for i, part in enumerate(parts):
                            if part == 'inet' and i + 1 < len(parts):
                                ip = parts[i + 1]
                                if not ip.startswith('127.') and not ip.startswith('169.254'):
                                    ip_parts = ip.split('.')
                                    if len(ip_parts) == 4:
                                        network_base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
                                        if network_base not in networks:
                                            networks.append(network_base)
                                            print(f"🔍 Found network: {network_base}.0/24 (from {ip})")
        except Exception as e:
            print(f"⚠️  Could not run network commands: {e}")
    
    return networks

def get_socket_based_networks():
    """Fallback method using socket to detect networks"""
    networks = []
    
    # Method 1: Get local IP and derive network
    local_ip = get_local_ip()
    if local_ip:
        ip_parts = local_ip.split('.')
        if len(ip_parts) == 4:
            network_base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
            networks.append(network_base)
            print(f"🔍 Detected primary network: {network_base}.0/24 (from {local_ip})")
    
    # Method 2: Try to connect to common router IPs to find more networks
    common_gateways = [
        "192.168.1.1", "192.168.0.1", "192.168.2.1", 
        "10.0.0.1", "10.1.1.1", "172.16.0.1"
    ]
    
    for gateway in common_gateways:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((gateway, 80))
            sock.close()
            
            if result == 0:  # Connection successful
                ip_parts = gateway.split('.')
                network_base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
                if network_base not in networks:
                    networks.append(network_base)
                    print(f"🔍 Found reachable network: {network_base}.0/24 (gateway: {gateway})")
        except:
            pass
    
    return networks

def get_local_networks():
    """Automatically detect local network ranges using built-in methods"""
    networks = []
    
    print("🔍 Auto-detecting LAN networks...")
    
    # Try OS-specific methods first
    system = platform.system().lower()
    
    if system == "windows":
        networks = get_windows_network_info()
    elif system in ["linux", "darwin"]:  # Linux or macOS
        networks = get_linux_network_info()
    
    # If no networks found or fallback needed
    if not networks:
        print("⚠️  Using socket-based detection...")
        networks = get_socket_based_networks()
    
    # If still no networks, use common defaults
    if not networks:
        print("⚠️  Using common network defaults...")
        networks = ['192.168.1', '192.168.0', '10.0.0']
        for net in networks:
            print(f"🔍 Default network: {net}.0/24")
    
    # Remove duplicates
    networks = list(set(networks))
    
    return networks

def get_network_range_info():
    """Get comprehensive network information"""
    networks = get_local_networks()
    
    print(f"📡 Found {len(networks)} potential network(s):")
    for i, net in enumerate(networks, 1):
        print(f"   {i}. {net}.0/24")
    
    return networks

# ===== Step 3: Fast RTSP Scanner =====
def check_rtsp(ip, port=554, timeout=0.3):
    """Check if RTSP port is open"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((ip, port))
        sock.close()
        return ip
    except:
        return None

def test_rtsp_stream(ip, username, password, channel=1, port=554, timeout=5):
    """Test if RTSP stream actually works"""
    url = f"rtsp://{username}:{password}@{ip}:{port}/cam/realmonitor?channel={channel}&subtype=1"
    
    try:
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Try to read a frame with timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            ret, frame = cap.read()
            if ret and frame is not None:
                cap.release()
                return True
            time.sleep(0.1)
        
        cap.release()
        return False
        
    except Exception as e:
        return False

def validate_camera_channels(ip, username, password, max_channels=8):
    """Check which channels are working on this IP and return their details"""
    working_channels = {}  # Changed to dictionary to store channel info
    
    print(f"🔧 Testing channels on {ip}...")
    
    for channel in range(1, max_channels + 1):
        print(f"    Testing channel {channel}...", end=' ')
        
        if test_rtsp_stream(ip, username, password, channel, timeout=3):
            # Store working channel with its RTSP URL
            url = f"rtsp://{username}:{password}@{ip}:554/cam/realmonitor?channel={channel}&subtype=1"
            working_channels[f"Cam{channel}"] = url
            print("✅ success")
        else:
            print("❌ failed")
    
    return working_channels

def scan_rtsp_network(base_ip, start=1, end=254, max_workers=100):
    """Scan a network range for RTSP devices"""
    ips = [f"{base_ip}.{i}" for i in range(start, end + 1)]
    rtsp_hosts = []
    print(f"🔍 Scanning {len(ips)} IPs for RTSP (port {PORT}) on {base_ip}.0/24...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_rtsp, ip): ip for ip in ips}
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            if completed % 50 == 0:  # Progress indicator
                print(f"   Progress: {completed}/{len(ips)} IPs scanned...")
            if result:
                rtsp_hosts.append(result)
                print(f"🎥 RTSP port open: {result}")

    return rtsp_hosts

def scan_all_networks(networks):
    """Scan all detected networks for RTSP devices"""
    all_rtsp_devices = []
    
    for network in networks:
        print(f"\n{'='*60}")
        print(f"🌐 Scanning network: {network}.0/24")
        print(f"{'='*60}")
        
        devices = scan_rtsp_network(network, 1, 254)
        all_rtsp_devices.extend(devices)
        
        if devices:
            print(f"✅ Found {len(devices)} RTSP device(s) on {network}.0/24")
        else:
            print(f"❌ No RTSP devices found on {network}.0/24")
    
    return all_rtsp_devices

# ===== Main Execution =====
def main():
    print("🚀 RTSP Camera Discovery Tool")
    print("=" * 50)
    
    # Auto-detect networks
    networks = get_network_range_info()
    
    # Scan all networks
    print(f"\n🔍 Starting RTSP Discovery on {len(networks)} network(s)...")
    rtsp_devices = scan_all_networks(networks)
    
    if not rtsp_devices:
        print("\n❌ No RTSP devices found on any network")
        print("🔧 Troubleshooting tips:")
        print("   1. Check if cameras are powered on")
        print("   2. Verify cameras are connected to the same network")
        print("   3. Check firewall settings")
        print("   4. Try different credentials in data.txt")
        print("\n⏹️  Exiting automatically...")
        sys.exit(1)
    
    print(f"\n✅ Found {len(rtsp_devices)} RTSP device(s): {rtsp_devices}")
    
    # Test each device for working channels
    print(f"\n🔧 Testing camera channels...")
    best_device = None
    best_working_channels = {}
    max_working_channels = 0
    
    for device_ip in rtsp_devices:
        working_channels = validate_camera_channels(device_ip, USERNAME, PASSWORD, MAX_CHANNELS)
        
        print(f"📊 {device_ip}: {len(working_channels)}/{MAX_CHANNELS} channels working: {list(working_channels.keys())}")
        
        if len(working_channels) > max_working_channels:
            max_working_channels = len(working_channels)
            best_device = device_ip
            best_working_channels = working_channels
    
    # Select best device
    if best_device is None or not best_working_channels:
        print("\n❌ No working RTSP streams found on any device")
        print("🔧 Please check:")
        print("   1. Username and password in data.txt")
        print("   2. Camera RTSP settings")
        print("   3. Network connectivity")
        print("\n⏹️  Exiting automatically...")
        sys.exit(1)
    
    print(f"\n🎯 Selected device: {best_device} ({max_working_channels}/{MAX_CHANNELS} channels working)")
    
    # Save ONLY working cameras to lan.txt
    try:
        with open("lan.txt", "w", encoding='utf-8') as f:
            # Write header with proper line break
            f.write(f"# Camera Configuration File\n")
            f.write(f"# Auto-generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Device IP: {best_device}\n")
            f.write(f"# Working Channels: {max_working_channels}/{MAX_CHANNELS}\n")
            f.write(f"# Format: CamName=RTSP_URL\n")
            f.write(f"# Note: Only working cameras are listed below\n")
            f.write(f"\n")  # Empty line for readability
            
            # Write ONLY working camera URLs
            for cam_name, url in best_working_channels.items():
                f.write(f"{cam_name}={url}\n")
        
        print(f"\n📁 Successfully updated lan.txt with {len(best_working_channels)} WORKING cameras from {best_device}")
        
        # Display the generated content
        print(f"\n📋 Generated lan.txt content:")
        print("=" * 50)
        with open("lan.txt", "r") as f:
            print(f.read())
        print("=" * 50)
        
        if max_working_channels < MAX_CHANNELS:
            print(f"⚠️  INFO: Only {max_working_channels}/{MAX_CHANNELS} channels are working and saved to lan.txt")
            print("🔧 Non-working channels were automatically excluded")
        else:
            print(f"🎉 Perfect! All {MAX_CHANNELS} channels are working!")
            
    except Exception as e:
        print(f"❌ Error writing lan.txt: {e}")
        sys.exit(1)
    
    print(f"\n✅ Process completed successfully!")
    print(f"📝 lan.txt now contains ONLY the {len(best_working_channels)} working cameras")
    print("🚀 Ready to start next program automatically...")
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)