# QUY TRÌNH LÀM VIỆC TRÊN 3 MÁY - HỆ THỐNG TÍNH TIỀN ĐỖ XE THỜI GIAN THỰC

## TỔNG QUAN KIẾN TRÚC

Hệ thống được chia thành 3 máy với các nhiệm vụ khác nhau:

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   MÁY 1     │      │   MÁY 2     │      │   MÁY 3     │
│  PRODUCER   │─────▶│   KAFKA +   │─────▶│  SPARK +    │
│             │      │    SPARK    │      │    GUI      │
│  Camera AI  │      │  Processing │      │  Consumer   │
│  Simulator  │      │             │      │             │
└─────────────┘      └─────────────┘      └─────────────┘
```

---

## MÁY 1: PRODUCER (Data Source)

### Vai trò:
- Mô phỏng camera AI gửi thông tin trạng thái đỗ xe
- Stream dữ liệu JSON lên Kafka topic

### Cấu hình:
- **IP/Hostname**: `192.168.80.116`
- **Kafka Broker**: `192.168.80.212:9092` (Máy 2)
- **Kafka Topic**: `parking-events`

### Các bước thực hiện:

1. **Cài đặt môi trường:**
```bash
# Cài đặt Kafka Python client
pip install kafka-python

# Hoặc
pip install confluent-kafka
```

2. **Chạy Producer:**
```bash
# Gửi dữ liệu lên Kafka broker trên Máy 2
python parking_json_stream.py --kafka-broker 192.168.80.212:9092

# Hoặc sử dụng biến môi trường
export KAFKA_BROKER=192.168.80.212:9092
python parking_json_stream.py
```

3. **Dữ liệu được gửi:**
- Mỗi sự kiện là JSON với format:
```json
{
  "timestamp": "2024-01-15 10:30:45",
  "timestamp_unix": 1705302645,
  "license_plate": "29A-12345",
  "location": "A1",
  "status_code": "PARKED"
}
```

4. **Các trạng thái:**
- `ENTERING`: Xe đang vào
- `PARKED`: Xe đã đỗ
- `MOVING`: Xe đang di chuyển
- `EXITING`: Xe đang ra

---

## MÁY 2: KAFKA + SPARK PROCESSING

### Vai trò:
- Kafka: Nhận và lưu trữ dữ liệu stream từ Máy 1
- Spark: Xử lý dữ liệu real-time với Stateful Processing
  - Tính toán thời gian đỗ xe
  - Tính tiền theo block 10 phút
  - Theo dõi trạng thái các vị trí

### Cấu hình:
- **IP/Hostname**: `192.168.80.212`
- **Kafka Broker**: `192.168.80.212:9092` (hoặc `localhost:9092` nếu chạy local)
- **Spark Master**: `local[*]` hoặc `spark://master:7077`
- **Checkpoint Directory**: `/tmp/spark-checkpoint-parking`

### Các bước thực hiện:

1. **Khởi động Kafka:**
```bash
# Khởi động Zookeeper
bin/zookeeper-server-start.sh config/zookeeper.properties

# Khởi động Kafka Server
bin/kafka-server-start.sh config/server.properties

# Tạo topic
bin/kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic parking-events \
  --partitions 3 \
  --replication-factor 1
```

2. **Chạy Spark Streaming Application:**
```bash
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  --master local[*] \
  parking_spark_streaming.py
```

3. **Xử lý Stateful với Spark:**

**a) State Schema:**
```python
# Lưu trữ trạng thái mỗi vị trí đỗ xe
state_schema = StructType([
    StructField("location", StringType()),
    StructField("license_plate", StringType()),
    StructField("entry_time", TimestampType()),
    StructField("last_update", TimestampType()),
    StructField("parked_blocks", IntegerType()),  # Số block 10 phút
    StructField("total_cost", DoubleType()),
    StructField("status", StringType())
])
```

**b) Logic xử lý:**
- Nhận dữ liệu từ Kafka topic `parking-events`
- Group by `location` để theo dõi từng vị trí
- Khi nhận `ENTERING` hoặc `PARKED`: 
  - Cập nhật `entry_time` nếu chưa có
  - Tính số block 10 phút: `(current_time - entry_time) // 600`
  - Tính tiền: `parked_blocks * price_per_block`
- Khi nhận `EXITING`:
  - Tính tiền cuối cùng
  - Xóa khỏi state hoặc đánh dấu "TRỐNG"

**c) Output:**
- Gửi kết quả xử lý lên Kafka topic `parking-status` 
- Format output:
```json
{
  "location": "A1",
  "status": "OCCUPIED",
  "license_plate": "29A-12345",
  "parked_duration_minutes": 25,
  "parked_blocks": 3,
  "total_cost": 45000,
  "entry_time": "2024-01-15 10:30:00",
  "last_update": "2024-01-15 10:55:00"
}
```

---

## MÁY 3: SPARK CONSUMER + GUI

### Vai trò:
- Nhận dữ liệu đã xử lý từ Kafka topic `parking-status`
- Hiển thị GUI real-time với:
  - Danh sách vị trí có xe và vị trí trống
  - Thông tin chi tiết: biển số, thời gian đỗ, tiền phải trả
  - Cập nhật tự động theo thời gian thực

### Cấu hình:
- **IP/Hostname**: `192.168.80.67`
- **Kafka Broker**: `192.168.80.212:9092` (kết nối đến Máy 2)
- **Kafka Topic**: `parking-status`

### Các bước thực hiện:

1. **Chạy Consumer và GUI:**
```bash
# Kết nối đến Kafka broker trên Máy 2
python parking_gui_consumer.py --kafka-broker 192.168.80.212:9092

# Hoặc sử dụng biến môi trường
export KAFKA_BROKER=192.168.80.212:9092
python parking_gui_consumer.py
```

2. **Giao diện hiển thị:**

```
╔═══════════════════════════════════════════════════════════════╗
║          HỆ THỐNG QUẢN LÝ ĐỖ XE - BÁO CÁO THỜI GIAN THỰC      ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  📍 VỊ TRÍ CÓ XE:                                             ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ A1 │ 29A-12345 │ Đã đỗ: 25 phút │ Tiền: 45,000 VNĐ    │  ║
║  │ B3 │ 30B-67890 │ Đã đỗ: 12 phút │ Tiền: 20,000 VNĐ    │  ║
║  │ C5 │ 51C-22222 │ Đã đỗ: 35 phút │ Tiền: 60,000 VNĐ    │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                               ║
║  🚗 VỊ TRÍ TRỐNG:                                             ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ A2, A3, A4, A5, A6, A7, A8, A9, A10                     │  ║
║  │ B1, B2, B4, B5, B6, B7, B8, B9, B10                     │  ║
║  │ ...                                                      │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                               ║
║  ⏰ Cập nhật lúc: 2024-01-15 10:55:30                         ║
╚═══════════════════════════════════════════════════════════════╝
```

3. **Cập nhật real-time:**
- Đọc từ Kafka topic `parking-status`
- Tự động cập nhật GUI mỗi khi có dữ liệu mới
- Hiển thị tất cả 60 vị trí (A1-A10, B1-B10, ..., F1-F10)

---

## LUỒNG DỮ LIỆU CHI TIẾT

### 1. Camera AI → Kafka (Máy 1 → Máy 2)

```
parking_json_stream.py
    ↓ (gửi JSON)
Kafka Producer
    ↓ (stream)
Kafka Topic: parking-events
```

### 2. Kafka → Spark Processing (Trong Máy 2)

```
Spark Streaming
    ↓ (đọc từ Kafka)
parking-events topic
    ↓ (xử lý stateful)
State Store (lưu trạng thái từng vị trí)
    ↓ (tính toán)
- Thời gian đỗ
- Số block 10 phút
- Tiền phải trả
    ↓ (gửi kết quả)
parking-status topic
```

### 3. Kafka → GUI (Máy 2 → Máy 3)

```
Kafka Consumer
    ↓ (đọc từ Kafka)
parking-status topic
    ↓ (parse JSON)
GUI Application
    ↓ (hiển thị)
Tkinter/PyQt Dashboard
```

---

## CẤU HÌNH MẠNG

Đảm bảo các máy có thể kết nối với nhau:

- **Máy 1 (192.168.80.116)** cần kết nối được đến Máy 2 (port 9092 - Kafka)
- **Máy 3 (192.168.80.67)** cần kết nối được đến Máy 2 (port 9092 - Kafka)
- **Máy 2 (192.168.80.212)** cần mở port 9092 để các máy khác kết nối
- Có thể dùng cùng một mạng LAN hoặc cấu hình firewall

### Kiểm tra kết nối:
```bash
# Từ Máy 1 hoặc Máy 3, kiểm tra kết nối đến Máy 2
telnet 192.168.80.212 9092
# hoặc
nc -zv 192.168.80.212 9092
```

### Cấu hình Kafka để chấp nhận kết nối từ xa:
Trên Máy 2, chỉnh sửa file `config/server.properties`:
```properties
# Thay đổi từ:
# listeners=PLAINTEXT://localhost:9092

# Thành:
listeners=PLAINTEXT://0.0.0.0:9092
advertised.listeners=PLAINTEXT://192.168.80.212:9092
```

---

## TÍNH TOÁN TIỀN ĐỖ XE

### Quy tắc:
- Tính theo **block 10 phút**
- Giá mỗi block: **15,000 VNĐ** (có thể thay đổi)

### Ví dụ:
- Xe đỗ 5 phút → 1 block → 15,000 VNĐ
- Xe đỗ 12 phút → 2 blocks → 30,000 VNĐ
- Xe đỗ 25 phút → 3 blocks → 45,000 VNĐ
- Xe đỗ 35 phút → 4 blocks → 60,000 VNĐ

### Công thức:
```python
parked_duration_seconds = current_time - entry_time
parked_duration_minutes = parked_duration_seconds / 60
parked_blocks = math.ceil(parked_duration_minutes / 10)
total_cost = parked_blocks * price_per_block
```

---

## KIỂM TRA HOẠT ĐỘNG

### Kiểm tra Máy 1 (Producer):
```bash
# Kiểm tra log khi chạy parking_json_stream.py
# Sẽ thấy các dòng JSON được in ra
```

### Kiểm tra Máy 2 (Kafka + Spark):
```bash
# Kiểm tra Kafka topic
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic parking-events --from-beginning

# Kiểm tra output topic
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic parking-status --from-beginning

# Kiểm tra Spark UI
# Mở browser: http://localhost:4040
```

### Kiểm tra Máy 3 (Consumer + GUI):
```bash
# Kiểm tra log của consumer
# Xem GUI có hiển thị dữ liệu không
```

---

## LƯU Ý QUAN TRỌNG

1. **Thứ tự khởi động:**
   - Khởi động Kafka trên Máy 2 trước
   - Khởi động Spark trên Máy 2
   - Sau đó khởi động Producer trên Máy 1
   - Cuối cùng khởi động GUI trên Máy 3

2. **Checkpoint trong Spark:**
   - Spark cần checkpoint directory để lưu state
   - Đảm bảo thư mục có quyền ghi

3. **Xử lý lỗi:**
   - Nếu Producer không kết nối được Kafka → kiểm tra firewall
   - Nếu Spark không đọc được dữ liệu → kiểm tra Kafka topic
   - Nếu GUI không hiển thị → kiểm tra Consumer có nhận được dữ liệu không

4. **Tối ưu hiệu năng:**
   - Có thể tăng số partition của Kafka topic để xử lý song song
   - Tăng batch interval của Spark nếu dữ liệu ít
   - Sử dụng windowing trong Spark để tính toán theo batch

---

## KẾT LUẬN

Hệ thống này mô phỏng một kiến trúc xử lý dữ liệu real-time thực tế:
- **Máy 1**: Data source (camera AI)
- **Máy 2**: Message broker (Kafka) + Processing engine (Spark)
- **Máy 3**: Client application (GUI)

Với kiến trúc này, hệ thống có thể mở rộng dễ dàng và xử lý được lượng dữ liệu lớn.

