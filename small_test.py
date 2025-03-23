import os

network_path = "/Volumes/screenshots/Dremio"

if os.path.exists(network_path):
    print(f"Path '{network_path}' exists.")
    if os.access(network_path, os.R_OK):
        print(f"Path '{network_path}' is readable.")
        try:
            contents = os.listdir(network_path)
            print(f"Contents of '{network_path}': {contents[:5]}")
        except Exception as e:
            print(f"Could not list contents: {e}")
    else:
        print(f"Path '{network_path}' is NOT readable.")
else:
    print(f"Path '{network_path}' does NOT exist.")

test_file = os.path.join(network_path, "test_write.txt")

if os.access(network_path, os.W_OK):
    print(f"Path '{network_path}' is writable.")
    try:
        with open(test_file, "w") as f:
            f.write("Test write successful.\n")
        print(f"Successfully wrote to '{test_file}'.")
        os.remove(test_file)
        print(f"Successfully removed '{test_file}'.")
    except Exception as e:
        print(f"Error during write/remove: {e}")
else:
    print(f"Path '{network_path}' is NOT writable.")
