import subprocess
import sys
import importlib

def read_requirements_file(filename="requirements.txt"):
    """Reads the requirements.txt file and returns a list of dependencies."""
    try:
        with open(filename, "r") as file:
            # Read all lines, strip out any whitespace, and remove comments
            dependencies = [line.strip() for line in file if line.strip() and not line.startswith("#")]
        return dependencies
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        sys.exit(1)

def is_package_installed(package_name):
    """Check if a package is installed by trying to import it."""
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False

def install_package(package_name):
    """Install a single package using pip."""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])
        print(f"SUCCESS: {package_name} has been installed.")
    except subprocess.CalledProcessError as e:
        print(f"FAILURE: {package_name} could not be installed. Reason: {e}")
        return False
    return True

def main():
    # Read dependencies from requirements.txt
    dependencies = read_requirements_file()

    # Loop through each dependency
    for dep in dependencies:
        package_name = dep.split("==")[0]  # Get the package name (ignoring version)
        
        if is_package_installed(package_name):
            print(f"SUCCESS: {package_name} is already installed and working correctly.")
        else:
            print(f"FAILURE: {package_name} is not installed. Installing...")
            if install_package(dep):  # Install with version if specified
                print(f"SUCCESS: {package_name} has been installed.")
            else:
                print(f"FAILURE: {package_name} could not be installed.")

if __name__ == "__main__":
    main()
