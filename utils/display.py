def print_title(title):
    print("\n" + "=" * 60)
    print(title.center(60))
    print("=" * 60)

def print_menu():
    print("\n" + "=" * 50)
    print("       TRAFFIC SIGNAL SIMULATOR")
    print("=" * 50)
    print("1. Run Adaptive Traffic Simulation")
    print("2. Run Fixed Traffic Simulation")
    print("3. Display Road Network")
    print("4. Test Shortest Route")
    print("5. Compare Adaptive vs Fixed")
    print("6. Exit")
    print("=" * 50)

def get_choice():
    while True:
        try:
            choice = int(input("Enter your choice: "))
            if 1 <= choice <= 6:
                return choice
            print("Please enter a number between 1 and 6.")
        except ValueError:
            print("Invalid input. Enter a number.")
