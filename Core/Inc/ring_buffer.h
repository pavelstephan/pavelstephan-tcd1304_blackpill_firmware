/**
 ******************************************************************************
 * @file    ring_buffer.h
 * @brief   Interrupt-safe ring buffer for byte data
 * @author  Phase 1A - Transport Layer Foundation
 ******************************************************************************
 * @attention
 *
 * This ring buffer is designed to be interrupt-safe:
 * - Single producer, single consumer
 * - Producer (ISR) only modifies head
 * - Consumer (main loop) only modifies tail
 * - Uses volatile to prevent compiler optimization issues
 *
 ******************************************************************************
 */

#ifndef RING_BUFFER_H
#define RING_BUFFER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* Ring buffer structure */
typedef struct {
    volatile uint8_t *buffer;       // Pointer to data storage
    volatile uint16_t head;          // Write position (modified by producer/ISR)
    volatile uint16_t tail;          // Read position (modified by consumer/main)
    uint16_t size;                   // Buffer size (must be power of 2 for efficiency)
} ring_buffer_t;

/* Function prototypes */

/**
 * @brief Initialize a ring buffer
 * @param rb Pointer to ring buffer structure
 * @param buffer Pointer to storage array
 * @param size Size of buffer (recommend power of 2: 256, 512, 1024, etc.)
 */
void ring_buffer_init(ring_buffer_t *rb, volatile uint8_t *buffer, uint16_t size);

/**
 * @brief Write a single byte to the ring buffer
 * @param rb Pointer to ring buffer
 * @param data Byte to write
 * @return true if successful, false if buffer is full
 * @note This is ISR-safe (can be called from interrupt)
 */
bool ring_buffer_write(ring_buffer_t *rb, uint8_t data);

/**
 * @brief Read a single byte from the ring buffer
 * @param rb Pointer to ring buffer
 * @param data Pointer to store the read byte
 * @return true if successful, false if buffer is empty
 * @note This should be called from main loop, not ISR
 */
bool ring_buffer_read(ring_buffer_t *rb, uint8_t *data);

/**
 * @brief Write multiple bytes to the ring buffer
 * @param rb Pointer to ring buffer
 * @param data Pointer to data array
 * @param length Number of bytes to write
 * @return Number of bytes actually written
 * @note Writes as many bytes as possible, stops if buffer fills up
 */
uint16_t ring_buffer_write_multiple(ring_buffer_t *rb, const uint8_t *data, uint16_t length);

/**
 * @brief Read multiple bytes from the ring buffer
 * @param rb Pointer to ring buffer
 * @param data Pointer to destination array
 * @param length Maximum number of bytes to read
 * @return Number of bytes actually read
 */
uint16_t ring_buffer_read_multiple(ring_buffer_t *rb, uint8_t *data, uint16_t length);

/**
 * @brief Check how many bytes are available to read
 * @param rb Pointer to ring buffer
 * @return Number of bytes available
 */
uint16_t ring_buffer_available(ring_buffer_t *rb);

/**
 * @brief Check how much free space is available
 * @param rb Pointer to ring buffer
 * @return Number of bytes free
 */
uint16_t ring_buffer_free_space(ring_buffer_t *rb);

/**
 * @brief Check if buffer is empty
 * @param rb Pointer to ring buffer
 * @return true if empty, false otherwise
 */
bool ring_buffer_is_empty(ring_buffer_t *rb);

/**
 * @brief Check if buffer is full
 * @param rb Pointer to ring buffer
 * @return true if full, false otherwise
 */
bool ring_buffer_is_full(ring_buffer_t *rb);

/**
 * @brief Clear/reset the ring buffer
 * @param rb Pointer to ring buffer
 * @note Not ISR-safe - only call when interrupts are disabled or from main
 */
void ring_buffer_clear(ring_buffer_t *rb);

/**
 * @brief Peek at next byte without removing it
 * @param rb Pointer to ring buffer
 * @param data Pointer to store the peeked byte
 * @return true if successful, false if buffer is empty
 */
bool ring_buffer_peek(ring_buffer_t *rb, uint8_t *data);

#endif /* RING_BUFFER_H */
