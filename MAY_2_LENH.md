# LỆNH CHẠY TRÊN MÁY 2 (192.168.80.212)

## 📋 Thứ tự thực hiện

### Bước 1: Khởi động Zookeeper (Terminal 1)

```bash
# Di chuyển đến thư mục Kafka
cd /path/to/kafka

# Khởi động Zookeeper
bin/zookeeper-server-start.sh config/zookeeper.properties
```

Giữ terminal này mở, Zookeeper cần chạy liên tục.

---

### Bước 2: Khởi động Kafka Server (Terminal 2)

```bash
# Di chuyển đến thư mục Kafka
cd /path/to/kafka

# Khởi động Kafka Server
bin/kafka-server-start.sh config/server.properties
```

**⚠️ QUAN TRỌNG**: Trước khi chạy, đảm bảo đã cấu hình Kafka để chấp nhận kết nối từ xa:

Sửa file `config/server.properties`:
```properties
listeners=PLAINTEXT://0.0.0.0:9092
advertised.listeners=PLAINTEXT://192.168.80.212:9092
```

Giữ terminal này mở, Kafka server cần chạy liên tục.

---

### Bước 3: Tạo Kafka Topics (Terminal 3)

Sau khi Kafka đã khởi động, mở terminal mới và chạy:

```bash
# Di chuyển đến thư mục Kafka
cd /path/to/kafka

# Tạo topic parking-events
bin/kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic parking-events \
  --partitions 3 \
  --replication-factor 1

# Tạo topic parking-status
bin/kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic parking-status \
  --partitions 3 \
  --replication-factor 1

# Kiểm tra topics đã tạo
bin/kafka-topics.sh --list --bootstrap-server localhost:9092
```

Sau khi tạo xong topics, có thể đóng terminal này.

---

### Bước 4: Chạy Spark Streaming (Terminal 4)

```bash
# Di chuyển đến thư mục project
cd /home/thuypm/Desktop/ttu/bigdata/hw2

# Chạy Spark Streaming
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  --master local[*] \
  parking_spark_streaming.py
```

Giữ terminal này mở, Spark Streaming sẽ chạy liên tục và xử lý dữ liệu.

---

## ✅ Tóm tắt - Máy 2 cần chạy:

1. **Zookeeper** (Terminal 1) - Chạy liên tục
2. **Kafka Server** (Terminal 2) - Chạy liên tục
3. **Tạo Topics** (Terminal 3) - Chạy một lần
4. **Spark Streaming** (Terminal 4) - Chạy liên tục

---

## 🔍 Kiểm tra hoạt động

### Kiểm tra Kafka đang chạy:
```bash
# Xem danh sách topics
bin/kafka-topics.sh --list --bootstrap-server localhost:9092

# Xem dữ liệu đang đến (nếu Producer đã chạy)
bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic parking-events --from-beginning

# Xem dữ liệu output từ Spark
bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic parking-status --from-beginning
```

### Xem Spark UI:
Mở browser tại: `http://localhost:4040` hoặc `http://192.168.80.212:4040`

---

## 🛑 Dừng hệ thống

Khi cần dừng, nhấn `Ctrl+C` trong các terminal theo thứ tự ngược lại:
1. Dừng Spark Streaming (Terminal 4)
2. Dừng Kafka Server (Terminal 2)
3. Dừng Zookeeper (Terminal 1)

