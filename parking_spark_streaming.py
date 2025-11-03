"""
Spark Streaming Application - Xử lý dữ liệu đỗ xe real-time với Stateful Processing

Yêu cầu:
- Đọc dữ liệu từ Kafka topic 'parking-events'
- Xử lý stateful để theo dõi trạng thái từng vị trí đỗ xe
- Tính toán thời gian đỗ và tiền phải trả (theo block 10 phút)
- Gửi kết quả lên Kafka topic 'parking-status'
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, window, current_timestamp, 
    when, lit, expr, struct, to_json, max as spark_max
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, 
    TimestampType, DoubleType, LongType
)
import os
import sys

# Cấu hình
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
INPUT_TOPIC = os.getenv('INPUT_TOPIC', 'parking-events')
OUTPUT_TOPIC = os.getenv('OUTPUT_TOPIC', 'parking-status')
CHECKPOINT_DIR = os.getenv('CHECKPOINT_DIR', '/tmp/spark-checkpoint-parking')
PRICE_PER_BLOCK = float(os.getenv('PRICE_PER_BLOCK', '15000'))  # Giá mỗi block 10 phút

def create_spark_session():
    """Tạo Spark Session với cấu hình phù hợp"""
    spark = SparkSession.builder \
        .appName("ParkingFeeCalculator") \
        .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_DIR) \
        .config("spark.sql.shuffle.partitions", "3") \
        .config("spark.streaming.kafka.maxRatePerPartition", "100") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark

def get_input_schema():
    """Schema của dữ liệu đầu vào từ Kafka"""
    return StructType([
        StructField("timestamp", StringType()),
        StructField("timestamp_unix", LongType()),
        StructField("license_plate", StringType()),
        StructField("location", StringType()),
        StructField("status_code", StringType())
    ])

def calculate_parking_fee(entry_time_seconds, current_time_seconds, price_per_block):
    """
    Tính tiền đỗ xe theo block 10 phút
    
    Args:
        entry_time_seconds: Thời gian vào (Unix timestamp)
        current_time_seconds: Thời gian hiện tại (Unix timestamp)
        price_per_block: Giá mỗi block 10 phút
    
    Returns:
        (parked_blocks, total_cost)
    """
    duration_seconds = current_time_seconds - entry_time_seconds
    duration_minutes = duration_seconds / 60.0
    # Tính số block (làm tròn lên)
    parked_blocks = int((duration_minutes + 9) // 10)  # Tương đương math.ceil(duration_minutes / 10)
    if parked_blocks < 1:
        parked_blocks = 1  # Tối thiểu 1 block
    total_cost = parked_blocks * price_per_block
    return parked_blocks, total_cost

def process_parking_events(spark):
    """Xử lý streaming dữ liệu đỗ xe với stateful processing"""
    
    print("=" * 60)
    print("🚀 KHỞI ĐỘNG SPARK STREAMING - TÍNH TIỀN ĐỖ XE")
    print("=" * 60)
    print(f"📥 Kafka Input: {KAFKA_BOOTSTRAP_SERVERS}/{INPUT_TOPIC}")
    print(f"📤 Kafka Output: {KAFKA_BOOTSTRAP_SERVERS}/{OUTPUT_TOPIC}")
    print(f"💰 Giá mỗi block 10 phút: {PRICE_PER_BLOCK:,.0f} VNĐ")
    print(f"💾 Checkpoint: {CHECKPOINT_DIR}")
    print("=" * 60)
    
    # Đọc stream từ Kafka
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", INPUT_TOPIC) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    # Parse JSON từ value
    schema = get_input_schema()
    df_parsed = df.select(
        col("key").cast("string").alias("kafka_key"),
        from_json(col("value").cast("string"), schema).alias("data"),
        col("timestamp").alias("processing_time")
    ).select(
        col("kafka_key"),
        col("data.timestamp").alias("event_timestamp"),
        col("data.timestamp_unix").alias("event_timestamp_unix"),
        col("data.license_plate").alias("license_plate"),
        col("data.location").alias("location"),
        col("data.status_code").alias("status_code"),
        col("processing_time")
    )
    
    # Xử lý stateful với mapGroupsWithState
    # Tuy nhiên, Spark Structured Streaming không hỗ trợ mapGroupsWithState trực tiếp trong Python
    # Sử dụng cách tiếp cận với window và aggregation
    
    # Tạo watermark để xử lý late data
    df_with_watermark = df_parsed \
        .withWatermark("processing_time", "10 minutes") \
        .select(
            col("location"),
            col("license_plate"),
            col("status_code"),
            col("event_timestamp_unix"),
            col("processing_time")
        )
    
    # Group by location và lấy event mới nhất cho mỗi location
    # Sử dụng window để nhóm theo location
    df_grouped = df_with_watermark \
        .groupBy(
            col("location"),
            window(col("processing_time"), "5 minutes", "1 minute").alias("time_window")
        ) \
        .agg(
            spark_max("event_timestamp_unix").alias("latest_timestamp"),
            spark_max(struct(
                col("event_timestamp_unix"),
                col("license_plate"),
                col("status_code")
            )).alias("latest_event")
        ) \
        .select(
            col("location"),
            col("latest_event.license_plate").alias("license_plate"),
            col("latest_event.status_code").alias("status_code"),
            col("latest_timestamp").alias("event_timestamp_unix")
        )
    
    # Tính toán thời gian đỗ và tiền
    current_time_expr = expr("unix_timestamp()").cast("long")
    
    df_calculated = df_grouped \
        .withColumn("current_timestamp_unix", current_time_expr) \
        .withColumn(
            "entry_time_unix",
            when(col("status_code").isin(["ENTERING", "PARKED"]), col("event_timestamp_unix"))
            .otherwise(None)
        ) \
        .withColumn(
            "parked_duration_seconds",
            when(col("status_code").isin(["PARKED", "MOVING"]), 
                 col("current_timestamp_unix") - col("entry_time_unix"))
            .otherwise(None)
        ) \
        .withColumn(
            "parked_duration_minutes",
            when(col("parked_duration_seconds").isNotNull(),
                 col("parked_duration_seconds") / 60.0)
            .otherwise(None)
        ) \
        .withColumn(
            "parked_blocks",
            when(col("parked_duration_minutes").isNotNull(),
                 expr(f"cast(ceiling((parked_duration_minutes + 9) / 10) as int)"))
            .otherwise(None)
        ) \
        .withColumn(
            "parked_blocks",
            when(col("parked_blocks").isNull(), lit(1))
            .when(col("parked_blocks") < 1, lit(1))
            .otherwise(col("parked_blocks"))
        ) \
        .withColumn(
            "total_cost",
            when(col("parked_blocks").isNotNull(),
                 col("parked_blocks") * lit(PRICE_PER_BLOCK))
            .otherwise(lit(0.0))
        ) \
        .withColumn(
            "status",
            when(col("status_code") == "EXITING", lit("EMPTY"))
            .when(col("status_code").isin(["ENTERING", "PARKED", "MOVING"]), lit("OCCUPIED"))
            .otherwise(lit("UNKNOWN"))
        )
    
    # Tạo output JSON
    df_output = df_calculated \
        .select(
            col("location"),
            col("status"),
            col("license_plate"),
            col("parked_duration_minutes"),
            col("parked_blocks"),
            col("total_cost"),
            col("event_timestamp_unix"),
            current_timestamp().alias("last_update")
        ) \
        .withColumn(
            "output_json",
            to_json(struct(
                col("location"),
                col("status"),
                col("license_plate"),
                col("parked_duration_minutes"),
                col("parked_blocks"),
                col("total_cost"),
                col("event_timestamp_unix"),
                col("last_update")
            ))
        )
    
    # Ghi kết quả lên Kafka
    query = df_output \
        .select(
            col("location").alias("key"),
            col("output_json").alias("value")
        ) \
        .writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("topic", OUTPUT_TOPIC) \
        .option("checkpointLocation", CHECKPOINT_DIR) \
        .outputMode("update") \
        .start()
    
    print("\n✅ Spark Streaming đang chạy...")
    print("📊 Xem Spark UI tại: http://localhost:4040")
    print("⚠️  Nhấn Ctrl+C để dừng\n")
    
    # Đợi query
    query.awaitTermination()

def main():
    """Hàm main"""
    spark = None
    try:
        spark = create_spark_session()
        process_parking_events(spark)
    except KeyboardInterrupt:
        print("\n⚠️  Đã dừng bởi người dùng (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if spark:
            spark.stop()
            print("\n✅ Đã dừng Spark Session")

if __name__ == "__main__":
    main()

