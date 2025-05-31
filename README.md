# PUF-MerkleTree-Distributed-Bloom-Filter-Deduplication





## Distributed Bloom Filter Deduplication for IIoT Sensor Data

This C project implements a **distributed Bloom filter-based deduplication** system for large-scale **IIoT sensor data** stored in CSV format. It detects duplicates efficiently using a time-resetting Bloom filter per data type and exports only non-duplicate records.


## Project Structure

```

├── bloomfilter.c           # The main bloomfilter source file 
├── records.csv             # Input CSV file (IIoT raw sensor data)
├── non_duplicates.csv      # Output CSV file (deduplicated records)
├── README.md               # Project documentation

````

---

## Input CSV Format

The system expects an input file named `records.csv` in the following format:

```csv
device_id,timestamp,type,value,leaf,tag
temp_sensor_01,2025-06-01T12:00:00,temperature,25.5,leafA,tagX
temp_sensor_02,2025-06-01T12:00:01,temperature,25.6,leafB,tagY
...
````

Each line represents a unique IIoT sensor reading.


## How It Works

* Groups records by `type` (e.g., temperature, humidity)
* Each thread processes one group using a 3-hash Bloom filter
* Resets the bit array after `RESET_INTERVAL` entries to limit false positives
* Non-duplicate records are written to `non_duplicates.csv`

---

## Compilation & Run

### Compile

```bash
gcc bloomfilter.c -o bloomfilter
```

### ▶ Run

```bash
./bloomfilter
```

### 💡 Output Example

```txt
=== Distributed Bloom Filter Summary ===
Total Records Processed: 1000000
Total Duplicates Detected: 120000
Processing Time: 4.3720 sec
Total Memory Used (RSS): 22.34 MB
```

The output file `non_duplicates.csv` will contain all unique records in the original CSV format.

---

## ⚙️ Configuration

You can modify these parameters in `bloomfilter.c`:

```c
#define BLOOM_SIZE     333333   // Bloom filter size (bits)
#define MAX_TYPES      5         // Max number of sensor types
#define MAX_RECORDS    50000    // Max records per type (not more than 50000) (if more than 50000, it will cause segmentation failed(linux default))
#define RESET_INTERVAL 20000     // Reset Bloom filter every N records
```

---

## Notes

* Uses `/proc/self/status` to fetch real memory (RSS) on **Linux**
* Designed to be run on **Linux-based VM or Edge devices**
* Handles up to 200k records with low memory footprint
* In case to check whether the output is having duplicated record or not you can change the load file name to check duplication in this line.
  ```
  load_csv("records.csv", groups, &group_count);
  ```


## License

This project is open-source and provided for educational and research purposes.


