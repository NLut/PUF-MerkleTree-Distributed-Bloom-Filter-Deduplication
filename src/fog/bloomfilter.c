#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>
#include <time.h>

#define BLOOM_SIZE 3333333
#define MAX_TYPES 5
#define MAX_RECORDS 200000
#define MAX_LINE 256
#define RESET_INTERVAL 20000

typedef struct {
    char *records[MAX_RECORDS];        // For hash check: timestamp:value
    char *full_lines[MAX_RECORDS];     // For export: full original line
    char *non_dupes[MAX_RECORDS];      // Dedupe: timestamp:value
    char *non_dupe_lines[MAX_RECORDS]; // Dedupe: original line
    int count;
    int non_dupe_count;
    char type[32];
} SensorTypeGroup;

typedef struct {
    SensorTypeGroup *group;
    int duplicate_count;
} ThreadData;

uint32_t hash1(const char *str) {
    uint32_t hash = 5381;
    while (*str) hash = ((hash << 5) + hash) + (uint8_t)(*str++);
    return hash % BLOOM_SIZE;
}

uint32_t hash2(const char *str) {
    uint32_t hash = 0;
    while (*str) hash = (*str++) + (hash << 6) + (hash << 16) - hash;
    return hash % BLOOM_SIZE;
}

uint32_t hash3(const char *str) {
    uint32_t hash = 2166136261u;
    while (*str) hash = (hash ^ (uint8_t)(*str++)) * 16777619;
    return hash % BLOOM_SIZE;
}

double get_memory_usage_mb() {
    FILE *fp = fopen("/proc/self/status", "r");
    if (!fp) return -1.0;
    char line[128];
    while (fgets(line, sizeof(line), fp)) {
        if (strncmp(line, "VmRSS:", 6) == 0) {
            unsigned long mem_kb;
            sscanf(line, "VmRSS: %lu kB", &mem_kb);
            fclose(fp);
            return mem_kb / 1024.0;
        }
    }
    fclose(fp);
    return -1.0;
}

void *process_group(void *arg) {
    ThreadData *data = (ThreadData *)arg;
    SensorTypeGroup *group = data->group;

    uint8_t **bit_arrays = malloc(3 * sizeof(uint8_t *));
    for (int i = 0; i < 3; i++)
        bit_arrays[i] = calloc(BLOOM_SIZE, sizeof(uint8_t));

    for (int i = 0; i < group->count; i++) {
        if (i > 0 && i % RESET_INTERVAL == 0)
            for (int j = 0; j < 3; j++)
                memset(bit_arrays[j], 0, BLOOM_SIZE);

        const char *key = group->records[i];
        uint32_t h1 = hash1(key);
        uint32_t h2 = hash2(key);
        uint32_t h3 = hash3(key);

        int found = bit_arrays[0][h1] && bit_arrays[1][h2] && bit_arrays[2][h3];
        bit_arrays[0][h1] = bit_arrays[1][h2] = bit_arrays[2][h3] = 1;

        if (found) {
            data->duplicate_count++;
        } else {
            group->non_dupes[group->non_dupe_count] = strdup(key);
            group->non_dupe_lines[group->non_dupe_count++] = strdup(group->full_lines[i]);
        }
    }

    for (int i = 0; i < 3; i++) free(bit_arrays[i]);
    free(bit_arrays);
    return NULL;
}

void load_csv(const char *filename, SensorTypeGroup groups[], int *group_count) {
    FILE *file = fopen(filename, "r");
    if (!file) {
        perror("File open failed");
        exit(1);
    }

    char line[MAX_LINE];
    fgets(line, MAX_LINE, file); // skip header

    while (fgets(line, MAX_LINE, file)) {
        char temp[MAX_LINE];
        strncpy(temp, line, MAX_LINE);
        temp[strcspn(temp, "\n")] = 0;

        char *did        = strtok(temp, ",");
        char *timestamp  = strtok(NULL, ",");
        char *type       = strtok(NULL, ",");
        char *value      = strtok(NULL, ",");
        strtok(NULL, ","); // skip leaf
        strtok(NULL, ","); // skip tag

        if (!did || !timestamp || !type || !value) continue;

        char key[128];
        snprintf(key, sizeof(key), "%s:%s", timestamp, value);

        int i, found = 0;
        for (i = 0; i < *group_count; i++) {
            if (strcmp(groups[i].type, type) == 0) {
                found = 1;
                break;
            }
        }

        if (!found) {
            if (*group_count >= MAX_TYPES) {
                fprintf(stderr, "Exceeded MAX_TYPES\n");
                continue;
            }
            strcpy(groups[*group_count].type, type);
            groups[*group_count].count = 0;
            groups[*group_count].non_dupe_count = 0;
            i = (*group_count)++;
        }

        if (groups[i].count < MAX_RECORDS) {
            groups[i].records[groups[i].count] = strdup(key);
            groups[i].full_lines[groups[i].count] = strdup(line);
            groups[i].count++;
        } else {
            fprintf(stderr, "Exceeded MAX_RECORDS for type: %s\n", groups[i].type);
        }
    }

    fclose(file);
}

void export_non_duplicates(const char *filename, SensorTypeGroup groups[], int group_count) {
    FILE *out = fopen(filename, "w");
    if (!out) {
        perror("Output file open failed");
        return;
    }

    fprintf(out, "device_id,timestamp,type,value,leaf,tag\n");
    for (int i = 0; i < group_count; i++) {
        for (int j = 0; j < groups[i].non_dupe_count; j++) {
            fprintf(out, "%s", groups[i].non_dupe_lines[j]);
        }
    }

    fclose(out);
}

int main() {
    SensorTypeGroup groups[MAX_TYPES];
    int group_count = 0;

    printf("Loading CSV...\n");
    load_csv("records.csv", groups, &group_count);

    pthread_t threads[MAX_TYPES];
    ThreadData thread_data[MAX_TYPES];

    clock_t start = clock();

    for (int i = 0; i < group_count; i++) {
        thread_data[i].group = &groups[i];
        thread_data[i].duplicate_count = 0;
        pthread_create(&threads[i], NULL, process_group, &thread_data[i]);
    }

    int total_records = 0, total_duplicates = 0;
    for (int i = 0; i < group_count; i++) {
        pthread_join(threads[i], NULL);
        total_records += groups[i].count;
        total_duplicates += thread_data[i].duplicate_count;
    }

    clock_t end = clock();
    double elapsed = (double)(end - start) / CLOCKS_PER_SEC;

    printf("\n=== Distributed Bloom Filter Summary ===\n");
    printf("Total Records Processed: %d\n", total_records);
    printf("Total Duplicates Detected: %d\n", total_duplicates);
    printf("Processing Time: %.4f sec\n", elapsed);

    double memory_mb = get_memory_usage_mb();
    if (memory_mb > 0)
        printf("Total Memory Used (RSS): %.2f MB\n", memory_mb);
    else
        printf("Memory usage info not available.\n");

    export_non_duplicates("non_duplicates.csv", groups, group_count);

    for (int i = 0; i < group_count; i++) {
        for (int j = 0; j < groups[i].count; j++) {
            free(groups[i].records[j]);
            free(groups[i].full_lines[j]);
        }
        for (int j = 0; j < groups[i].non_dupe_count; j++) {
            free(groups[i].non_dupes[j]);
            free(groups[i].non_dupe_lines[j]);
        }
    }

    return 0;
}
