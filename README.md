# HỆ THỐNG TÍNH TIỀN ĐỖ XE THỜI GIAN THỰC

Hệ thống mô phỏng camera AI gửi thông tin đỗ xe, xử lý real-time với Kafka và Spark, và hiển thị báo cáo qua GUI.

## 📋 Tổng quan

Hệ thống bao gồm 3 thành phần chính chạy trên 3 máy:

1. **Producer (Máy 1)**: Mô phỏng camera AI, gửi dữ liệu lên Kafka
2. **Spark Processing (Máy 2)**: Xử lý dữ liệu real-time, tính toán tiền đỗ xe
3. **GUI Consumer (Máy 3)**: Hiển thị báo cáo real-time

## 🚀 Cài đặt

### Yêu cầu hệ thống

- Python 3.7+
- Apache Kafka
- Apache Spark 3.x
- Java 8+ (cho Kafka và Spark)

### Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### Cài đặt Spark và Kafka

Tham khảo tài liệu chính thức:
- [Kafka Quick Start](https://kafka.apache.org/quickstart)
- [Spark Getting Started](https://spark.apache.org/docs/latest/)

## 📁 Cấu trúc thư mục

```
hw2/
├── parking_json_stream.py      # Producer - gửi dữ liệu lên Kafka (Máy 1)
├── parking_spark_streaming.py   # Spark Streaming - xử lý dữ liệu (Máy 2)
├── parking_gui_consumer.py      # GUI Consumer - hiển thị báo cáo (Máy 3)
├── requirements.txt             # Python dependencies
├── README.md                    # File này
└── QUY_TRINH_3_MAY.md          # Tài liệu chi tiết quy trình 3 máy
```

## 🔧 Sử dụng

### 1. Khởi động Kafka (Máy 2)

```bash
# Khởi động Zookeeper
bin/zookeeper-server-start.sh config/zookeeper.properties

# Khởi động Kafka Server
bin/kafka-server-start.sh config/server.properties

# Tạo topics
bin/kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic parking-events \
  --partitions 3 \
  --replication-factor 1

bin/kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic parking-status \
  --partitions 3 \
  --replication-factor 1
```

### 2. Chạy Producer (Máy 1 - IP: 192.168.80.116)

```bash
# Gửi lên Kafka broker trên Máy 2
python parking_json_stream.py --kafka-broker 192.168.80.212:9092

# Hoặc chỉ in ra console (không cần Kafka)
python parking_json_stream.py --no-kafka

# Xem các tùy chọn
python parking_json_stream.py --help
```

### 3. Chạy Spark Streaming (Máy 2 - IP: 192.168.80.212)

```bash
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  --master local[*] \
  parking_spark_streaming.py
```

Hoặc với cấu hình tùy chỉnh:

```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
INPUT_TOPIC=parking-events \
OUTPUT_TOPIC=parking-status \
PRICE_PER_BLOCK=15000 \
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  --master local[*] \
  parking_spark_streaming.py
```

### 4. Chạy GUI Consumer (Máy 3 - IP: 192.168.80.67)

```bash
# Kết nối đến Kafka broker trên Máy 2
python parking_gui_consumer.py --kafka-broker 192.168.80.212:9092

# Xem các tùy chọn
python parking_gui_consumer.py --help
```

## 📊 Tính toán tiền đỗ xe

- **Đơn vị tính**: Block 10 phút
- **Giá mỗi block**: 15,000 VNĐ (có thể cấu hình)
- **Ví dụ**:
  - Đỗ 5 phút → 1 block → 15,000 VNĐ
  - Đỗ 12 phút → 2 blocks → 30,000 VNĐ
  - Đỗ 25 phút → 3 blocks → 45,000 VNĐ

## 🔍 Kiểm tra hoạt động

### Kiểm tra dữ liệu trên Kafka

```bash
# Xem dữ liệu input
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic parking-events --from-beginning

# Xem dữ liệu output
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic parking-status --from-beginning
```

### Spark UI

Mở browser tại: `http://localhost:4040` để xem thống kê Spark Streaming.

## 📝 Cấu hình

### Biến môi trường

- `KAFKA_BROKER`: Địa chỉ Kafka broker (mặc định: localhost:9092)
- `KAFKA_BOOTSTRAP_SERVERS`: Địa chỉ Kafka cho Spark (mặc định: localhost:9092)
- `INPUT_TOPIC`: Topic input (mặc định: parking-events)
- `OUTPUT_TOPIC`: Topic output (mặc định: parking-status)
- `PRICE_PER_BLOCK`: Giá mỗi block 10 phút (mặc định: 15000)

## 🐛 Xử lý lỗi

1. **Không kết nối được Kafka**: Kiểm tra firewall và địa chỉ broker
2. **Spark không đọc được dữ liệu**: Kiểm tra topic có tồn tại không
3. **GUI không hiển thị**: Kiểm tra Consumer có nhận được dữ liệu từ Kafka không

## 📚 Tài liệu chi tiết

Xem file `QUY_TRINH_3_MAY.md` để biết chi tiết về quy trình làm việc trên 3 máy.

## 👤 Tác giả

Hệ thống được phát triển cho bài tập Big Data - Hệ thống tính tiền đỗ xe thời gian thực.

