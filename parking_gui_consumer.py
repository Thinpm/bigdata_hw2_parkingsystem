"""
GUI Consumer - Hiển thị báo cáo real-time về trạng thái đỗ xe

Đọc dữ liệu từ Kafka topic 'parking-status' và hiển thị:
- Danh sách vị trí có xe (với thông tin: biển số, thời gian đỗ, tiền)
- Danh sách vị trí trống
- Cập nhật tự động theo thời gian thực
"""

import json
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
from collections import defaultdict
import threading
import os
import sys

try:
    from kafka import KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("Cảnh báo: kafka-python chưa được cài đặt. Chạy: pip install kafka-python")

# Tất cả các vị trí đỗ xe
ALL_LOCATIONS = [
    "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10",
    "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10",
    "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10",
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
    "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10",
    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10"
]

class ParkingGUI:
    def __init__(self, root, kafka_broker='localhost:9092', topic='parking-status'):
        self.root = root
        self.kafka_broker = kafka_broker
        self.topic = topic
        self.consumer = None
        self.running = False
        self.parking_data = {}  # {location: {status, license_plate, duration, blocks, cost, ...}}
        self.update_thread = None
        
        self.setup_ui()
        self.connect_kafka()
        
    def setup_ui(self):
        """Thiết lập giao diện"""
        self.root.title("HỆ THỐNG QUẢN LÝ ĐỖ XE - BÁO CÁO THỜI GIAN THỰC")
        self.root.geometry("1000x700")
        self.root.configure(bg='#f0f0f0')
        
        # Header
        header_frame = tk.Frame(self.root, bg='#2c3e50', height=60)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame,
            text="🚗 HỆ THỐNG QUẢN LÝ ĐỖ XE - BÁO CÁO THỜI GIAN THỰC",
            font=('Arial', 16, 'bold'),
            bg='#2c3e50',
            fg='white'
        )
        title_label.pack(pady=15)
        
        # Main content frame
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Vị trí có xe
        left_frame = tk.Frame(main_frame, bg='white', relief=tk.RAISED, borderwidth=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        occupied_label = tk.Label(
            left_frame,
            text="📍 VỊ TRÍ CÓ XE",
            font=('Arial', 14, 'bold'),
            bg='white',
            fg='#e74c3c'
        )
        occupied_label.pack(pady=10)
        
        # Treeview cho vị trí có xe
        occupied_tree_frame = tk.Frame(left_frame)
        occupied_tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.occupied_tree = ttk.Treeview(
            occupied_tree_frame,
            columns=('Location', 'Biển số', 'Thời gian đỗ', 'Số block', 'Tiền'),
            show='headings',
            height=15
        )
        
        self.occupied_tree.heading('Location', text='Vị trí')
        self.occupied_tree.heading('Biển số', text='Biển số')
        self.occupied_tree.heading('Thời gian đỗ', text='Đã đỗ (phút)')
        self.occupied_tree.heading('Số block', text='Block (10 phút)')
        self.occupied_tree.heading('Tiền', text='Tiền (VNĐ)')
        
        self.occupied_tree.column('Location', width=80)
        self.occupied_tree.column('Biển số', width=120)
        self.occupied_tree.column('Thời gian đỗ', width=120)
        self.occupied_tree.column('Số block', width=100)
        self.occupied_tree.column('Tiền', width=150)
        
        occupied_scrollbar = ttk.Scrollbar(occupied_tree_frame, orient=tk.VERTICAL, command=self.occupied_tree.yview)
        self.occupied_tree.configure(yscrollcommand=occupied_scrollbar.set)
        
        self.occupied_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        occupied_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right panel - Vị trí trống
        right_frame = tk.Frame(main_frame, bg='white', relief=tk.RAISED, borderwidth=2)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        empty_label = tk.Label(
            right_frame,
            text="🚗 VỊ TRÍ TRỐNG",
            font=('Arial', 14, 'bold'),
            bg='white',
            fg='#27ae60'
        )
        empty_label.pack(pady=10)
        
        # Text widget cho vị trí trống
        empty_text_frame = tk.Frame(right_frame)
        empty_text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.empty_text = scrolledtext.ScrolledText(
            empty_text_frame,
            font=('Courier', 10),
            bg='#f8f9fa',
            wrap=tk.WORD,
            height=15
        )
        self.empty_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        status_frame = tk.Frame(self.root, bg='#34495e', height=40)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(
            status_frame,
            text="⏰ Đang kết nối...",
            font=('Arial', 10),
            bg='#34495e',
            fg='white',
            anchor='w'
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.count_label = tk.Label(
            status_frame,
            text="",
            font=('Arial', 10),
            bg='#34495e',
            fg='white',
            anchor='e'
        )
        self.count_label.pack(side=tk.RIGHT, padx=10, pady=10)
        
    def connect_kafka(self):
        """Kết nối đến Kafka"""
        if not KAFKA_AVAILABLE:
            self.status_label.config(text="❌ kafka-python chưa được cài đặt")
            return
        
        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.kafka_broker,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                consumer_timeout_ms=1000,
                group_id='parking-gui-consumer'
            )
            self.status_label.config(text=f"✅ Đã kết nối Kafka: {self.kafka_broker}")
            self.start_consuming()
        except Exception as e:
            self.status_label.config(text=f"❌ Lỗi kết nối Kafka: {e}")
            print(f"Lỗi: {e}")
    
    def start_consuming(self):
        """Bắt đầu đọc dữ liệu từ Kafka trong thread riêng"""
        self.running = True
        self.update_thread = threading.Thread(target=self.consume_messages, daemon=True)
        self.update_thread.start()
    
    def consume_messages(self):
        """Đọc messages từ Kafka"""
        while self.running:
            try:
                if self.consumer:
                    for message in self.consumer:
                        if not self.running:
                            break
                        data = message.value
                        self.update_parking_data(data)
            except Exception as e:
                print(f"Lỗi khi đọc từ Kafka: {e}")
                import time
                time.sleep(1)
    
    def update_parking_data(self, data):
        """Cập nhật dữ liệu đỗ xe từ Kafka message"""
        try:
            location = data.get('location')
            if not location:
                return
            
            self.parking_data[location] = {
                'status': data.get('status', 'UNKNOWN'),
                'license_plate': data.get('license_plate', 'N/A'),
                'parked_duration_minutes': data.get('parked_duration_minutes'),
                'parked_blocks': data.get('parked_blocks', 0),
                'total_cost': data.get('total_cost', 0.0),
                'last_update': data.get('last_update', datetime.now().isoformat())
            }
            
            # Cập nhật UI trong main thread
            self.root.after(0, self.refresh_ui)
        except Exception as e:
            print(f"Lỗi khi cập nhật dữ liệu: {e}")
    
    def refresh_ui(self):
        """Làm mới giao diện"""
        # Xóa dữ liệu cũ
        for item in self.occupied_tree.get_children():
            self.occupied_tree.delete(item)
        
        # Cập nhật vị trí có xe
        occupied_locations = []
        for location, data in self.parking_data.items():
            if data.get('status') == 'OCCUPIED':
                duration = data.get('parked_duration_minutes')
                if duration is None:
                    duration = 0
                else:
                    duration = round(duration, 1)
                
                blocks = data.get('parked_blocks', 0)
                cost = data.get('total_cost', 0.0)
                license_plate = data.get('license_plate', 'N/A')
                
                self.occupied_tree.insert('', 'end', values=(
                    location,
                    license_plate,
                    f"{duration:.1f}",
                    blocks,
                    f"{cost:,.0f}"
                ))
                occupied_locations.append(location)
        
        # Cập nhật vị trí trống
        occupied_set = set(occupied_locations)
        empty_locations = [loc for loc in ALL_LOCATIONS if loc not in occupied_set]
        
        self.empty_text.delete('1.0', tk.END)
        
        # Nhóm theo tầng
        floors = {}
        for loc in empty_locations:
            floor = loc[0]
            if floor not in floors:
                floors[floor] = []
            floors[floor].append(loc)
        
        for floor in sorted(floors.keys()):
            self.empty_text.insert(tk.END, f"Tầng {floor}: ", 'floor_label')
            self.empty_text.insert(tk.END, ', '.join(sorted(floors[floor])))
            self.empty_text.insert(tk.END, '\n')
        
        self.empty_text.tag_config('floor_label', font=('Courier', 10, 'bold'))
        
        # Cập nhật status bar
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_label.config(text=f"⏰ Cập nhật lúc: {current_time}")
        
        occupied_count = len(occupied_locations)
        empty_count = len(empty_locations)
        total_count = len(ALL_LOCATIONS)
        self.count_label.config(
            text=f"Có xe: {occupied_count} | Trống: {empty_count} | Tổng: {total_count}"
        )
    
    def on_closing(self):
        """Xử lý khi đóng cửa sổ"""
        self.running = False
        if self.consumer:
            self.consumer.close()
        self.root.destroy()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='GUI Consumer - Hiển thị báo cáo đỗ xe real-time')
    parser.add_argument('--kafka-broker', type=str,
                       default=os.getenv('KAFKA_BROKER', 'localhost:9092'),
                       help='Địa chỉ Kafka broker')
    parser.add_argument('--topic', type=str, default='parking-status',
                       help='Tên Kafka topic để đọc')
    
    args = parser.parse_args()
    
    if not KAFKA_AVAILABLE:
        print("❌ Lỗi: kafka-python chưa được cài đặt")
        print("Chạy: pip install kafka-python")
        sys.exit(1)
    
    root = tk.Tk()
    app = ParkingGUI(root, kafka_broker=args.kafka_broker, topic=args.topic)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.on_closing()

if __name__ == "__main__":
    main()

