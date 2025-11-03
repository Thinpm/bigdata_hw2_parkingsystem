# HƯỚNG DẪN NHANH - CHẠY HỆ THỐNG

## 📍 Thông tin IP các máy

- **Máy 1 (Producer)**: `192.168.80.116`
- **Máy 2 (Kafka + Spark)**: `192.168.80.212`
- **Máy 3 (GUI Consumer)**: `192.168.80.67`

---

## 🚀 Các bước chạy hệ thống

### Bước 1: Khởi động Kafka trên Máy 2 (192.168.80.212)

```bash
# 1. Khởi động Zookeeper
bin/zookeeper-server-start.sh config/zookeeper.properties

# 2. Khởi động Kafka Server (mở terminal mới)
bin/kafka-server-start.sh config/server.properties

# 3. Tạo topics (mở terminal mới)
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

**⚠️ QUAN TRỌNG**: Trước khi chạy, cần cấu hình Kafka để chấp nhận kết nối từ xa:

Sửa file `config/server.properties` trên Máy 2:
```properties
# Tìm dòng này và sửa thành:
listeners=PLAINTEXT://0.0.0.0:9092
advertised.listeners=PLAINTEXT://192.168.80.212:9092
```

Sau đó restart Kafka server.

---

### Bước 2: Chạy Spark Streaming trên Máy 2 (192.168.80.212)

```bash
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  --master local[*] \
  parking_spark_streaming.py
```

---

### Bước 3: Chạy Producer trên Máy 1 (192.168.80.116)

```bash
# Cài đặt dependencies (nếu chưa có)
pip install kafka-python

# Chạy Producer
python parking_json_stream.py --kafka-broker 192.168.80.212:9092

# Hoặc sử dụng script helper
./run_system.sh producer
```

---

### Bước 4: Chạy GUI Consumer trên Máy 3 (192.168.80.67)

```bash
# Cài đặt dependencies (nếu chưa có)
pip install kafka-python

# Chạy GUI
python parking_gui_consumer.py --kafka-broker 192.168.80.212:9092

# Hoặc sử dụng script helper
./run_system.sh gui
```

---

## ✅ Kiểm tra hoạt động

### Kiểm tra kết nối mạng:

Trên Máy 1 và Máy 3, kiểm tra kết nối đến Máy 2:
```bash
nc -zv 192.168.80.212 9092
# hoặc
telnet 192.168.80.212 9092
```

### Kiểm tra dữ liệu trên Kafka:

Trên Máy 2:
```bash
# Xem dữ liệu input từ Producer
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic parking-events --from-beginning

# Xem dữ liệu output từ Spark (trong terminal khác)
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic parking-status --from-beginning
```

---

## 🔧 Xử lý lỗi

### Lỗi: "Connection refused" khi Producer hoặc GUI kết nối Kafka

**Nguyên nhân**: Kafka chưa được cấu hình để chấp nhận kết nối từ xa.

**Giải pháp**: 
1. Kiểm tra file `config/server.properties` trên Máy 2
2. Đảm bảo có:
   ```
   listeners=PLAINTEXT://0.0.0.0:9092
   advertised.listeners=PLAINTEXT://192.168.80.212:9092
   ```
3. Restart Kafka server

### Lỗi: Firewall chặn kết nối

**Giải pháp**: Mở port 9092 trên Máy 2:
```bash
# Ubuntu/Debian
sudo ufw allow 9092/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=9092/tcp
sudo firewall-cmd --reload
```

---

## 📊 Thứ tự khởi động đúng

1. ✅ **Kafka** trên Máy 2 (bước 1)
2. ✅ **Spark Streaming** trên Máy 2 (bước 2)
3. ✅ **Producer** trên Máy 1 (bước 3)
4. ✅ **GUI Consumer** trên Máy 3 (bước 4)

---

## 📝 Lưu ý

- Đảm bảo tất cả máy cùng mạng LAN (192.168.80.x)
- Kiểm tra kết nối mạng trước khi chạy
- Spark UI có thể xem tại: `http://192.168.80.212:4040` (trên Máy 2)

---

## 🆘 Hỗ trợ

Xem chi tiết trong các file:
- `QUY_TRINH_3_MAY.md` - Tài liệu chi tiết quy trình
- `README.md` - Hướng dẫn đầy đủ
- `config.txt` - Thông tin cấu hình IP

