#!/bin/bash

# Script helper để chạy hệ thống tính tiền đỗ xe
# Sử dụng: ./run_system.sh [producer|spark|gui|all]
#
# Cấu hình IP:
# - Máy 1 (Producer): 192.168.80.116
# - Máy 2 (Kafka+Spark): 192.168.80.212
# - Máy 3 (GUI): 192.168.80.67

KAFKA_BROKER="${KAFKA_BROKER:-192.168.80.212:9092}"
SPARK_MASTER="${SPARK_MASTER:-local[*]}"

case "$1" in
    producer)
        echo "🚗 Khởi động Producer..."
        python parking_json_stream.py --kafka-broker "$KAFKA_BROKER"
        ;;
    spark)
        echo "🚀 Khởi động Spark Streaming..."
        spark-submit \
            --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
            --master "$SPARK_MASTER" \
            parking_spark_streaming.py
        ;;
    gui)
        echo "🖥️  Khởi động GUI Consumer..."
        python parking_gui_consumer.py --kafka-broker "$KAFKA_BROKER"
        ;;
    all)
        echo "⚠️  Lưu ý: Chạy tất cả trên cùng một máy (chỉ để test)"
        echo "Trong môi trường thực tế, chạy từng component trên máy riêng"
        echo ""
        echo "Để chạy song song, mở 3 terminal:"
        echo "  Terminal 1: ./run_system.sh producer"
        echo "  Terminal 2: ./run_system.sh spark"
        echo "  Terminal 3: ./run_system.sh gui"
        ;;
    *)
        echo "Sử dụng: $0 [producer|spark|gui|all]"
        echo ""
        echo "Ví dụ:"
        echo "  $0 producer    # Chạy Producer (Máy 1)"
        echo "  $0 spark       # Chạy Spark (Máy 2)"
        echo "  $0 gui         # Chạy GUI (Máy 3)"
        echo ""
        echo "Biến môi trường:"
        echo "  KAFKA_BROKER  - Địa chỉ Kafka broker (mặc định: 192.168.80.212:9092)"
        echo "  SPARK_MASTER  - Spark master URL (mặc định: local[*])"
        echo ""
        echo "IP các máy:"
        echo "  Máy 1 (Producer): 192.168.80.116"
        echo "  Máy 2 (Kafka+Spark): 192.168.80.212"
        echo "  Máy 3 (GUI): 192.168.80.67"
        exit 1
        ;;
esac

