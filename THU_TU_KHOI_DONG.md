# 🚀 THỨ TỰ KHỞI ĐỘNG HỆ THỐNG

## ⚡ Thứ tự đúng:

### 1️⃣ **MÁY 2 (192.168.80.212) - CHẠY ĐẦU TIÊN** ⭐

**Lý do**: Máy 2 chứa Kafka server - là trung tâm của hệ thống. Tất cả máy khác đều cần kết nối đến đây.

**Thực hiện**:
```bash
# Terminal 1: Zookeeper
bin/zookeeper-server-start.sh config/zookeeper.properties

# Terminal 2: Kafka Server (sau khi Zookeeper đã chạy)
bin/kafka-server-start.sh config/server.properties

# Terminal 3: Tạo topics (sau khi Kafka đã chạy)
bin/kafka-topics.sh --create --bootstrap-server localhost:9092 --topic parking-events --partitions 3 --replication-factor 1
bin/kafka-topics.sh --create --bootstrap-server localhost:9092 --topic parking-status --partitions 3 --replication-factor 1

# Terminal 4: Spark Streaming (sau khi Kafka đã sẵn sàng)
cd /home/thuypm/Desktop/ttu/bigdata/hw2
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 --master local[*] parking_spark_streaming.py
```

**Kiểm tra**: Đảm bảo Kafka đang chạy và có thể kết nối:
```bash
bin/kafka-topics.sh --list --bootstrap-server localhost:9092
```

---

### 2️⃣ **MÁY 1 (192.168.80.116) - CHẠY THỨ HAI**

**Lý do**: Sau khi Kafka đã sẵn sàng, Producer mới có thể gửi dữ liệu lên.

**Thực hiện**:
```bash
python parking_json_stream.py --kafka-broker 192.168.80.212:9092
```

**Kiểm tra**: Xem có lỗi kết nối không. Nếu thành công sẽ thấy:
```
✅ Đã kết nối Kafka broker: 192.168.80.212:9092
✅ Topic: parking-events
📤 Đã gửi 10 events lên Kafka...
```

---

### 3️⃣ **MÁY 3 (192.168.80.67) - CHẠY CUỐI CÙNG**

**Lý do**: GUI Consumer cần đợi Spark Streaming xử lý và gửi dữ liệu lên topic `parking-status`.

**Thực hiện**:
```bash
python parking_gui_consumer.py --kafka-broker 192.168.80.212:9092
```

**Kiểm tra**: Cửa sổ GUI sẽ hiển thị và bắt đầu nhận dữ liệu.

---

## 📊 Sơ đồ thời gian:

```
Thời gian →
     |
     |  Máy 2: Kafka + Spark
     |  ════════════════════════════════════ (chạy liên tục)
     |
     |          Máy 1: Producer
     |          ════════════════════════════ (bắt đầu gửi dữ liệu)
     |
     |                      Máy 3: GUI
     |                      ════════════════ (bắt đầu hiển thị)
```

---

## ✅ Checklist khởi động:

### Trên Máy 2:
- [ ] Zookeeper đã khởi động
- [ ] Kafka Server đã khởi động
- [ ] Topics đã được tạo (`parking-events`, `parking-status`)
- [ ] Spark Streaming đã khởi động và không có lỗi
- [ ] Kiểm tra có thể kết nối từ xa: `nc -zv 192.168.80.212 9092` (từ Máy 1 hoặc Máy 3)

### Trên Máy 1:
- [ ] Kafka broker trên Máy 2 đã sẵn sàng
- [ ] Producer đã kết nối thành công
- [ ] Đang gửi dữ liệu (thấy log "Đã gửi X events...")

### Trên Máy 3:
- [ ] Spark Streaming trên Máy 2 đã xử lý dữ liệu
- [ ] GUI đã mở và kết nối Kafka
- [ ] Đang hiển thị dữ liệu real-time

---

## 🔄 Dừng hệ thống:

**Thứ tự ngược lại**:
1. Dừng Máy 3 (GUI) - Ctrl+C
2. Dừng Máy 1 (Producer) - Ctrl+C
3. Dừng Máy 2:
   - Spark Streaming - Ctrl+C
   - Kafka Server - Ctrl+C
   - Zookeeper - Ctrl+C

---

## 🐛 Xử lý lỗi nếu chạy sai thứ tự:

### Lỗi: Producer không kết nối được Kafka
→ **Giải pháp**: Chưa khởi động Kafka trên Máy 2 hoặc chưa cấu hình đúng

### Lỗi: GUI không hiển thị dữ liệu
→ **Giải pháp**: Chưa chạy Producer (Máy 1) hoặc Spark Streaming (Máy 2) chưa xử lý

### Lỗi: Spark không đọc được dữ liệu
→ **Giải pháp**: Producer chưa chạy hoặc topic chưa được tạo

---

## 💡 Tóm tắt:

```
MÁY 2 (Kafka + Spark) → MÁY 1 (Producer) → MÁY 3 (GUI)
    (chạy trước)         (chạy sau)        (chạy cuối)
```

