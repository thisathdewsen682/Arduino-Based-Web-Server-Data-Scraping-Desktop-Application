import sys
import requests
from bs4 import BeautifulSoup
import re
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget, QPushButton, QLineEdit, QLabel, QHBoxLayout, QMessageBox
)
from PyQt5.QtWidgets import QMenu
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from datetime import datetime
import json
import threading
import queue

# Configuration file
CONFIG_FILE = "ip_config.json"

# Function to load IPs and titles with min/max temperature and humidity from the configuration file
def load_ips():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("ips", [])
    return []

# Function to save IPs and titles to the configuration file
def save_ips(self):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"ips": self.ip_list}, f, indent=4)

# Function to fetch temperature and humidity for a given IP
def get_temperature_and_humidity(ip):
    url = f"http://{ip}"  # Create the URL based on the IP address
    try:
        response = requests.get(url, timeout=5)

        # Log the response content for debugging
        print(f"Response from {ip}: {response.status_code} - {response.text[:200]}")  # Log first 200 characters

        if response.status_code != 200:
            print(f"Non-200 response for IP {ip}: {response.status_code}")
            return None, None  # Return no data for non-200 responses

        # Parse the response
        soup = BeautifulSoup(response.text, 'html.parser')

        # Scrape Temperature and Humidity
        temperature_text = soup.find(string=re.compile("TEMPERATURE", re.IGNORECASE))
        temperature = None
        if temperature_text:
            temp_match = re.search(r"[-+]?\d*\.\d+|\d+", temperature_text)
            if temp_match:
                temperature = temp_match.group()

        humidity_text = soup.find(string=re.compile("HUMIDITY", re.IGNORECASE))
        humidity = None
        if humidity_text:
            humidity_match = re.search(r"[-+]?\d*\.\d+|\d+", humidity_text)
            if humidity_match:
                humidity = humidity_match.group()

        # Log parsed results
        print(f"Parsed data for {ip} - Temperature: {temperature}, Humidity: {humidity}")

        return temperature, humidity
    except requests.exceptions.RequestException as e:
        print(f"Request exception for {ip}: {e}")
        return None, None


class TempHumidityMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Temperature and Humidity Data")
        self.resize(900, 700)

        # Load IP data
        self.ip_list = load_ips() if load_ips() else []

        # Data queue for threading
        self.data_queue = queue.Queue()

        # Table widget setup
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "","DHM No", "Barcode No","Location", "Temperature (°C)", "Humidity (%)", 
            "Min/Max Temp (°C)", "Min/Max Humidity (%)"  # New columns
        ])
        self.table.setRowCount(0)

        # Enable context menu
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)


        # Center table in window
        self.table.setMinimumWidth(600)  # Optional: Set a minimum width for the table
        self.table.horizontalHeader().setDefaultSectionSize(200)  # Default column width: 200px
        self.table.setFont(QFont("Arial", 14, QFont.Bold))  # Set bold font with a larger size
        self.table.setStyleSheet("""
    QTableWidget {
        background-color: #f9f9f9;
        alternate-background-color: #f0f0f0;
        gridline-color: #dcdcdc;
        border: 1px solid #dcdcdc;
    }
    QHeaderView::section {
        background-color: #e6e6e6;
        font-weight: bold;
        font-size: 12pt;
        padding: 4px;
        border: none;
    }
    QTableWidget::item {
        padding: 4px;
    }
    QTableWidget::item:selected {
        background-color: #cde4f5;
        color: #000000;
    }
""")


        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # Prevent editing
        self.table.horizontalHeader().setStretchLastSection(True)  # Stretch last column
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
      
        self.table.horizontalHeader().setDefaultSectionSize(180)  # Default width for other columns
        self.table.horizontalHeader().setSectionResizeMode(1, self.table.horizontalHeader().ResizeToContents)
        
        # Optional: Adjust font size and alignment for the table headers
        self.table.horizontalHeader().setFont(QFont("Arial", 13, QFont.Bold))

        # Real-time clock
        self.clock_label = QLabel()
        self.clock_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.clock_label.setStyleSheet("color: blue;")
        self.clock_label.setAlignment(Qt.AlignCenter)
        self.update_clock()  # Initialize the clock display

        # Timer for clock updates
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)  # Update every second

        # Input fields for adding IP
        self.ip_input = QLineEdit()
        self.title_input = QLineEdit()
        self.location_input = QLineEdit()  # New input field for Location
        self.barcode_input = QLineEdit()  # New input field for barcode
        self.min_temp_input = QLineEdit()
        self.max_temp_input = QLineEdit()
        self.min_humidity_input = QLineEdit()
        self.max_humidity_input = QLineEdit()

        self.add_ip_button = QPushButton("Add IP")
        self.add_ip_button.clicked.connect(self.add_ip)

        # Layout for adding IPs
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("IP Address:"))
        input_layout.addWidget(self.ip_input)
        input_layout.addWidget(QLabel("DHM No:"))
        input_layout.addWidget(self.title_input)
        input_layout.addWidget(QLabel("Barcode No:"))  # Add label for barcode
        input_layout.addWidget(self.barcode_input) 
        input_layout.addWidget(QLabel("Location:"))  # Add label for location
        input_layout.addWidget(self.location_input)  # Add location input field
        # Add barcode input field
        input_layout.addWidget(QLabel("Min Temp:"))
        input_layout.addWidget(self.min_temp_input)
        input_layout.addWidget(QLabel("Max Temp:"))
        input_layout.addWidget(self.max_temp_input)
        input_layout.addWidget(QLabel("Min Humidity:"))
        input_layout.addWidget(self.min_humidity_input)
        input_layout.addWidget(QLabel("Max Humidity:"))
        input_layout.addWidget(self.max_humidity_input)
        input_layout.addWidget(self.add_ip_button)

        # Header layout
        header_layout = QVBoxLayout()

        # Title Header
        title_container = QWidget()
        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(20, 10, 20, 0)  # Add margins for spacing
        self.title_label = QLabel("Kohoku Lanka Digital Hygrometer Monitoring System")
        self.title_label.setFont(QFont("Arial", 20, QFont.Bold))  # Larger font for title
        self.title_label.setAlignment(Qt.AlignCenter)  # Center-align the title

        self.title_label.setStyleSheet("""
    background-color: #2e8b57;  /* Green background */
    color: white;               /* White text */
    padding: 15px;              /* Extra padding */
    border-radius: 10px;        /* Rounded corners for style */
""")  # Dark blue text

        title_layout.addWidget(self.title_label)
        title_container.setLayout(title_layout)

        # Clock Header
        time_container = QWidget()
        time_layout = QHBoxLayout()
        time_layout.setContentsMargins(20, 0, 20, 10)  # Add margins for spacing
        self.clock_label.setFont(QFont("Arial", 16, QFont.Bold))  # Slightly smaller font for the clock
        self.clock_label.setAlignment(Qt.AlignRight)  # Align the clock to the right
        self.clock_label.setStyleSheet("color: black;")  # Black text for the clock
        time_layout.addWidget(self.clock_label)
        time_container.setLayout(time_layout)

        # Add title and clock headers to the main header layout
        header_layout.addWidget(title_container)
        header_layout.addWidget(time_container)

        # Add spacing below the header
        header_layout.addSpacing(10)

        # Add the input layout below the headers
        header_layout.addLayout(input_layout)

        




    

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)  # Center the main layout
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.table)

        # Central widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Start background data updater
        self.start_background_worker()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.process_queue)
        self.update_timer.start(500)

        self.ip_data_rows = {}

    def update_clock(self):
        """Update the clock display with the current date and time."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Adding date (Year-Month-Day)
        self.clock_label.setText(f"{current_time}")

   
    def create_centered_item(self, text):
        """Helper to create a centered table item."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item


    def save_ips(self):  # Move the save_ips function inside the class
     with open(CONFIG_FILE, "w") as f:
        json.dump({"ips": self.ip_list}, f, indent=4)


    
    def add_ip(self):
        ip = self.ip_input.text().strip()
        title = self.title_input.text().strip()
        barcode = self.barcode_input.text().strip()  # Capture the barcode
        location = self.location_input.text().strip()  # Capture the location
        min_temp = float(self.min_temp_input.text()) if self.min_temp_input.text() else None
        max_temp = float(self.max_temp_input.text()) if self.max_temp_input.text() else None
        min_humidity = float(self.min_humidity_input.text()) if self.min_humidity_input.text() else None
        max_humidity = float(self.max_humidity_input.text()) if self.max_humidity_input.text() else None

        if ip and title and location:  # Ensure location is also provided
            new_id = len(self.ip_list) + 1
            self.ip_list.append({
                'id': new_id, 
                'ip': ip,
                'title': title,
                'barcode': barcode,  # Add the barcode to the data
                'location': location,  # Store the location
                'min_temp': min_temp,
                'max_temp': max_temp,
                'min_humidity': min_humidity,
                'max_humidity': max_humidity
            })
            self.save_ips()  # Save the IP data to the file
            QMessageBox.information(self, "Success", f"IP address {ip} added successfully!")
            self.ip_input.clear()
            self.title_input.clear()
            self.barcode_input.clear()  # Clear the barcode input
            self.location_input.clear()  # Clear the location input
            self.min_temp_input.clear()
            self.max_temp_input.clear()
            self.min_humidity_input.clear()
            self.max_humidity_input.clear()
        else:
            QMessageBox.warning(self, "Warning", "Please enter IP, title, and location.")

    def restart_app(self):
        """Restart the application programmatically."""
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def start_background_worker(self):
        
        def worker():
            while True:
                for ip_data in self.ip_list:
                    id =  ip_data['id']
                    title = ip_data.get('title', f"Data for IP: {ip_data['ip']}")
                    ip = ip_data['ip']
                    barcode = ip_data.get('barcode', None)
                    min_temp = ip_data.get('min_temp', None)
                    max_temp = ip_data.get('max_temp', None)
                    min_humidity = ip_data.get('min_humidity', None)
                    max_humidity = ip_data.get('max_humidity', None)
                    temperature, humidity = get_temperature_and_humidity(ip)
                    

                    # Add the data to the queue for the main thread to process
                    self.data_queue.put((id, ip, title, temperature, humidity, min_temp, max_temp, min_humidity, max_humidity))

        threading.Thread(target=worker, daemon=True).start()

    def process_queue(self):
        while not self.data_queue.empty():
            id, ip, title, temperature, humidity, min_temp, max_temp, min_humidity, max_humidity = self.data_queue.get()

            # Skip if IP is no longer valid
            if ip not in [item['ip'] for item in self.ip_list]:
                continue

            # Get location or mark as Unknown
            barcode = next((item['barcode'] for item in self.ip_list if item['ip'] == ip), "Unknown")
            location = next((item['location'] for item in self.ip_list if item['ip'] == ip), "Unknown")

            if ip in self.ip_data_rows:
                # Update the existing row
                row = self.ip_data_rows[ip]
            else:
                # Insert a new row
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.ip_data_rows[ip] = row

            # Update row data
            self.table.setItem(row, 0, QTableWidgetItem(str(id)))
            self.table.hideColumn(0)
            self.table.setItem(row, 1, QTableWidgetItem(title))
            self.table.setItem(row, 2, QTableWidgetItem(barcode))
            self.table.setItem(row, 3, QTableWidgetItem(location))
            self.table.setColumnWidth(6, 250)
            # Stretch the last column to fill the remaining width
            self.table.horizontalHeader().setStretchLastSection(True)

            temp_item = QTableWidgetItem(f"{temperature} °C" if temperature else "N/A")
            humidity_item = QTableWidgetItem(f"{humidity} %" if humidity else "N/A")
            min_max_temp_item = QTableWidgetItem(
                f"{min_temp if min_temp else 'N/A'} / {max_temp if max_temp else 'N/A'}"
            )
            min_max_humidity_item = QTableWidgetItem(
                f"{min_humidity if min_humidity else 'N/A'} / {max_humidity if max_humidity else 'N/A'}"
            )

            # Color coding for temperature
            if temperature:
                temp_value = float(temperature)
                if (min_temp is not None and temp_value < min_temp) or (max_temp is not None and temp_value > max_temp):
                    temp_item.setBackground(QColor("red"))
                    temp_item.setForeground(QColor("white"))
                else:
                    temp_item.setBackground(QColor("green"))
                    temp_item.setForeground(QColor("white"))

            # Color coding for humidity
            if humidity:
                humidity_value = float(humidity)
                if (min_humidity is not None and humidity_value < min_humidity) or (max_humidity is not None and humidity_value > max_humidity):
                    humidity_item.setBackground(QColor("red"))
                    humidity_item.setForeground(QColor("white"))
                else:
                    humidity_item.setBackground(QColor("green"))
                    humidity_item.setForeground(QColor("white"))

            # Add data to table
            self.table.setItem(row, 4, temp_item)
            self.table.setItem(row, 5, humidity_item)
            self.table.setItem(row, 6, min_max_temp_item)
            self.table.setItem(row, 7, min_max_humidity_item)

            self.table.resizeColumnToContents(3)


    def delete_row_by_id(self):
        row = self.table.currentRow()
        if row >= 0:
            row_id = self.table.item(row, 0).text().strip()
            ip_to_delete = next((item['ip'] for item in self.ip_list if str(item['id']) == row_id), None)

            if ip_to_delete is None:
                QMessageBox.warning(self, "Error", "Could not find the IP to delete.")
                return

            # Remove the row from the table
            self.table.removeRow(row)

            # Remove the IP entry from self.ip_list
            self.ip_list = [item for item in self.ip_list if str(item['id']) != row_id]

            # Save the updated list to the JSON file
            try:
                with open(CONFIG_FILE, "w") as json_file:
                    json.dump({"ips": self.ip_list}, json_file, indent=4)
                QMessageBox.information(self, "Deleted", f"IP address with ID {row_id} has been deleted.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to update JSON file: {str(e)}")

            # Rebuild ip_data_rows to match current table state
            self.ip_data_rows = {
                self.table.item(row_idx, 1).text(): row_idx  # Rebuild using visible rows
                for row_idx in range(self.table.rowCount())
            }

            # Remove stale data from the queue
            temp_queue = queue.Queue()
            while not self.data_queue.empty():
                data = self.data_queue.get()
                if data[1] != ip_to_delete:  # Skip entries for the deleted IP
                    temp_queue.put(data)
            self.data_queue = temp_queue

        else:
            QMessageBox.warning(self, "Warning", "Please select a row to delete.")



    def show_context_menu(self, pos):
 
        context_menu = QMenu(self)
        delete_action = context_menu.addAction("Delete")
        delete_action.triggered.connect(self.delete_row_by_id)
        context_menu.exec_(self.table.mapToGlobal(pos))


    def delete_row_by_id(self):
        row = self.table.currentRow()
        if row >= 0:
            row_id = self.table.item(row, 0).text().strip()
            ip_to_delete = next((item['ip'] for item in self.ip_list if str(item['id']) == row_id), None)

            if ip_to_delete is None:
                QMessageBox.warning(self, "Error", "Could not find the IP to delete.")
                return

            # Remove the row from the table
            self.table.removeRow(row)

            # Remove the IP entry from self.ip_list
            self.ip_list = [item for item in self.ip_list if str(item['id']) != row_id]

            # Save the updated list to the JSON file
            try:
                with open(CONFIG_FILE, "w") as json_file:
                    json.dump({"ips": self.ip_list}, json_file, indent=4)
                QMessageBox.information(self, "Deleted", f"IP address with ID {row_id} has been deleted.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to update JSON file: {str(e)}")

            # Remove the IP from ip_data_rows and reassign row indices
            self.ip_data_rows = {
            ip: (idx if idx < row else idx - 1)
            for ip, idx in self.ip_data_rows.items()
            if ip != ip_to_delete
        }

            # Ensure no stale data in the queue
            temp_queue = queue.Queue()
            while not self.data_queue.empty():
                data = self.data_queue.get()
                if data[1] != ip_to_delete:  # Skip entries for the deleted IP
                    temp_queue.put(data)
            self.data_queue = temp_queue

        else:
            QMessageBox.warning(self, "Warning", "Please select a row to delete.")



    
            
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TempHumidityMonitor()
    window.show()
    sys.exit(app.exec())
