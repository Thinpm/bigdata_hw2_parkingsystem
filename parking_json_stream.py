import time
import random
import json
import os
from datetime import datetime
from enum import Enum

try:
    from kafka import KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("Cảnh báo: kafka-python chưa được cài đặt. Chạy: pip install kafka-python")

class ParkingStatus(Enum):
    """Các trạng thái của xe trong bãi đỗ"""
    ENTERING = "Đang vào"
    PARKED = "Đã đỗ"
    MOVING = "Đang di chuyển"
    EXITING = "Đang ra"

class ParkingEvent:
    """Class đại diện cho một sự kiện đỗ xe"""
    
    # Danh sách biển số xe có sẵn (mở rộng)
    LICENSE_PLATES = [
        "29A-12345", "29A-54321", "29A-67890", "29A-11111", "29A-99999",
        "30B-12345", "30B-67890", "30B-33333", "30B-88888", "30B-55555",
        "51C-11111", "51C-22222", "51C-44444", "51C-77777", "51C-12121",
        "59D-98765", "59D-45678", "59D-13579", "59D-24680", "59D-86420",
        "79D-99999", "79D-10101", "79D-20202", "79D-30303", "79D-40404",
        "92E-54321", "92E-65432", "92E-76543", "92E-87654", "92E-98765",
        "15F-88888", "15F-11122", "15F-33344", "15F-55566", "15F-77788",
        "43G-22222", "43G-12389", "43G-45612", "43G-78945", "43G-32165",
        "60H-10203", "60H-40506", "60H-70809", "60H-20406", "60H-50810"
    ]
    
    # Danh sách vị trí đỗ (mở rộng đến tầng F)
    PARKING_LOCATIONS = [
        # Tầng A
        "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10",
        # Tầng B
        "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10",
        # Tầng C
        "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10",
        # Tầng D
        "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
        # Tầng E
        "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10",
        # Tầng F (VIP)
        "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10"
    ]
    
    def __init__(self, occupied_locations=None, active_license_plates=None):
        # Chọn biển số chưa được sử dụng
        if active_license_plates:
            available_plates = [plate for plate in self.LICENSE_PLATES if plate not in active_license_plates]
            if available_plates:
                self.license_plate = random.choice(available_plates)
            else:
                # Nếu hết biển số, chọn random (trường hợp này không nên xảy ra)
                self.license_plate = random.choice(self.LICENSE_PLATES)
        else:
            self.license_plate = random.choice(self.LICENSE_PLATES)
        
        # Chọn vị trí còn trống
        if occupied_locations:
            available_locations = [loc for loc in self.PARKING_LOCATIONS if loc not in occupied_locations]
            if available_locations:
                self.location = random.choice(available_locations)
            else:
                # Nếu hết chỗ, chọn random (trường hợp này không nên xảy ra)
                self.location = random.choice(self.PARKING_LOCATIONS)
        else:
            self.location = random.choice(self.PARKING_LOCATIONS)
        
        self.status = ParkingStatus.ENTERING
        self.parked_count = 0
        self.parked_duration = 0
        
    def next_status(self, occupied_locations=None, active_license_plates=None):
        """Chuyển sang trạng thái tiếp theo theo logic"""
        if self.status == ParkingStatus.ENTERING:
            self.status = ParkingStatus.PARKED
            self.parked_duration = random.randint(20, 200)
            self.parked_count = 0
            
        elif self.status == ParkingStatus.PARKED:
            self.parked_count += 1
            
            if self.parked_count >= self.parked_duration:
                self.status = ParkingStatus.MOVING
                
        elif self.status == ParkingStatus.MOVING:
            self.status = ParkingStatus.EXITING
            
        else:
            # Nếu đã ra, tạo xe mới với vị trí và biển số trống
            self.__init__(occupied_locations, active_license_plates)
    
    def get_event_info(self):
        """Lấy thông tin sự kiện dưới dạng dictionary"""
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp_unix": int(time.time()),
            "license_plate": self.license_plate,
            "location": self.location,
            "status_code": self.status.name
        }

def parking_stream_realtime(duration_minutes=30, event_interval=3, kafka_broker=None, kafka_topic="parking-events"):
    """
    Mô phỏng streaming các sự kiện đỗ xe trong thời gian thực và gửi lên Kafka
    
    Args:
        duration_minutes (int): Thời gian chạy streaming (phút)
        event_interval (float): Thời gian trung bình giữa các sự kiện (giây)
        kafka_broker (str): Địa chỉ Kafka broker (ví dụ: "localhost:9092" hoặc "192.168.1.20:9092")
        kafka_topic (str): Tên Kafka topic để gửi dữ liệu
    """
    # Khởi tạo Kafka Producer nếu có cấu hình
    producer = None
    if kafka_broker and KAFKA_AVAILABLE:
        try:
            producer = KafkaProducer(
                bootstrap_servers=kafka_broker,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                acks='all',  # Đợi tất cả replicas xác nhận
                retries=3,
                max_in_flight_requests_per_connection=1
            )
            print(f"✅ Đã kết nối Kafka broker: {kafka_broker}")
            print(f"✅ Topic: {kafka_topic}")
        except Exception as e:
            print(f"⚠️  Không thể kết nối Kafka: {e}")
            print("⚠️  Sẽ chỉ in ra console thay vì gửi lên Kafka")
            producer = None
    elif kafka_broker and not KAFKA_AVAILABLE:
        print("⚠️  kafka-python chưa được cài đặt. Chỉ in ra console.")
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    # Theo dõi các vị trí và biển số đang được sử dụng
    occupied_locations = set()
    active_license_plates = set()
    
    # Tạo nhiều xe ngẫu nhiên để mô phỏng bãi đỗ thực tế
    active_vehicles = []
    for _ in range(5):
        vehicle = ParkingEvent(occupied_locations, active_license_plates)
        active_vehicles.append(vehicle)
        occupied_locations.add(vehicle.location)
        active_license_plates.add(vehicle.license_plate)
    
    event_count = 0
    try:
        while time.time() < end_time:
            # Chọn ngẫu nhiên một xe để cập nhật trạng thái
            vehicle = random.choice(active_vehicles)
            
            # Lưu trạng thái, vị trí và biển số cũ
            old_status = vehicle.status
            old_location = vehicle.location
            old_license_plate = vehicle.license_plate
            
            event_data = vehicle.get_event_info()
            
            # Gửi lên Kafka hoặc in ra console
            if producer:
                try:
                    # Gửi lên Kafka với key là location để đảm bảo cùng location được xử lý trên cùng partition
                    future = producer.send(kafka_topic, key=vehicle.location.encode('utf-8'), value=event_data)
                    # Đợi xác nhận (non-blocking check)
                    future.get(timeout=1)
                    event_count += 1
                    if event_count % 10 == 0:
                        print(f"📤 Đã gửi {event_count} events lên Kafka...")
                except Exception as e:
                    print(f"❌ Lỗi khi gửi lên Kafka: {e}")
                    # Fallback: in ra console
                    print(json.dumps(event_data, ensure_ascii=False))
            else:
                # Chế độ console (không có Kafka)
                print(json.dumps(event_data, ensure_ascii=False))
                event_count += 1
                
            # Chuyển sang trạng thái tiếp theo
            vehicle.next_status(occupied_locations, active_license_plates)
            
            # Quản lý occupied_locations và active_license_plates
            if old_status == ParkingStatus.EXITING and vehicle.status == ParkingStatus.ENTERING:
                # Xe tạo mới với vị trí và biển số mới
                occupied_locations.discard(old_location)
                occupied_locations.add(vehicle.location)
                active_license_plates.discard(old_license_plate)
                active_license_plates.add(vehicle.license_plate)
            elif vehicle.status == ParkingStatus.EXITING and old_status != ParkingStatus.EXITING:
                # Xe vừa chuyển sang EXITING - giải phóng vị trí (giữ biển số đến khi xe bị xóa)
                occupied_locations.discard(vehicle.location)
            
            # Thêm xe mới ngẫu nhiên (mô phỏng xe mới vào bãi)
            if random.random() > 0.6 and len(active_vehicles) < 8:
                # Chỉ thêm nếu còn chỗ trống VÀ còn biển số
                if (len(occupied_locations) < len(ParkingEvent.PARKING_LOCATIONS) and 
                    len(active_license_plates) < len(ParkingEvent.LICENSE_PLATES)):
                    new_vehicle = ParkingEvent(occupied_locations, active_license_plates)
                    active_vehicles.append(new_vehicle)
                    occupied_locations.add(new_vehicle.location)
                    active_license_plates.add(new_vehicle.license_plate)
            
            # Xóa xe đã ra khỏi bãi
            if random.random() > 0.5:
                vehicles_to_remove = [v for v in active_vehicles if v.status == ParkingStatus.EXITING]
                for v in vehicles_to_remove:
                    active_vehicles.remove(v)
                    occupied_locations.discard(v.location)
                    active_license_plates.discard(v.license_plate)
            
            # Đảm bảo luôn có ít nhất 3 xe
            while (len(active_vehicles) < 3 and 
                   len(occupied_locations) < len(ParkingEvent.PARKING_LOCATIONS) and
                   len(active_license_plates) < len(ParkingEvent.LICENSE_PLATES)):
                new_vehicle = ParkingEvent(occupied_locations, active_license_plates)
                active_vehicles.append(new_vehicle)
                occupied_locations.add(new_vehicle.location)
                active_license_plates.add(new_vehicle.license_plate)
            
            # Delay ngẫu nhiên giữa các sự kiện
            delay = random.uniform(event_interval * 0.5, event_interval * 1.5)
            time.sleep(delay)
    
    except KeyboardInterrupt:
        print("\n⚠️  Đã dừng bởi người dùng (Ctrl+C)")
    
    finally:
        if producer:
            producer.flush()
            producer.close()
            print(f"\n✅ Hoàn thành! Tổng cộng đã gửi {event_count} events lên Kafka")
        else:
            print(f"\n✅ Hoàn thành! Tổng cộng đã tạo {event_count} events")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Mô phỏng camera AI gửi dữ liệu đỗ xe lên Kafka')
    parser.add_argument('--kafka-broker', type=str, 
                       default=os.getenv('KAFKA_BROKER', 'localhost:9092'),
                       help='Địa chỉ Kafka broker (mặc định: localhost:9092 hoặc từ biến môi trường KAFKA_BROKER)')
    parser.add_argument('--topic', type=str, default='parking-events',
                       help='Tên Kafka topic (mặc định: parking-events)')
    parser.add_argument('--duration', type=int, default=30,
                       help='Thời gian chạy streaming (phút, mặc định: 30)')
    parser.add_argument('--interval', type=float, default=3.0,
                       help='Thời gian trung bình giữa các sự kiện (giây, mặc định: 3.0)')
    parser.add_argument('--no-kafka', action='store_true',
                       help='Không gửi lên Kafka, chỉ in ra console')
    
    args = parser.parse_args()
    
    kafka_broker = None if args.no_kafka else args.kafka_broker
    
    print("=" * 60)
    print("🚗 HỆ THỐNG MÔ PHỎNG CAMERA AI - BÃI ĐỖ XE")
    print("=" * 60)
    
    # Streaming với cấu hình từ tham số
    parking_stream_realtime(
        duration_minutes=args.duration,
        event_interval=args.interval,
        kafka_broker=kafka_broker,
        kafka_topic=args.topic
    )
