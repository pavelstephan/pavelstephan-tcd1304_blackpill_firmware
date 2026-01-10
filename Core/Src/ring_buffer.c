/**
 ******************************************************************************
 * @file    ring_buffer.c
 * @brief   Ring buffer implementation
 ******************************************************************************
 */

#include "ring_buffer.h"

/**
 * @brief Initialize a ring buffer
 */
void ring_buffer_init(ring_buffer_t *rb, volatile uint8_t *buffer, uint16_t size)
{
    rb->buffer = buffer;
    rb->size = size;
    rb->head = 0;
    rb->tail = 0;
}

/**
 * @brief Write a single byte to the ring buffer
 */
bool ring_buffer_write(ring_buffer_t *rb, uint8_t data)
{
    uint16_t next_head = (rb->head + 1) % rb->size;

    // Check if buffer is full
    if (next_head == rb->tail) {
        return false;  // Buffer full
    }

    // Write data and advance head
    rb->buffer[rb->head] = data;
    rb->head = next_head;

    return true;
}

/**
 * @brief Read a single byte from the ring buffer
 */
bool ring_buffer_read(ring_buffer_t *rb, uint8_t *data)
{
    // Check if buffer is empty
    if (rb->head == rb->tail) {
        return false;  // Buffer empty
    }

    // Read data and advance tail
    *data = rb->buffer[rb->tail];
    rb->tail = (rb->tail + 1) % rb->size;

    return true;
}

/**
 * @brief Write multiple bytes to the ring buffer
 */
uint16_t ring_buffer_write_multiple(ring_buffer_t *rb, const uint8_t *data, uint16_t length)
{
    uint16_t written = 0;

    for (uint16_t i = 0; i < length; i++) {
        if (!ring_buffer_write(rb, data[i])) {
            break;  // Buffer full, stop writing
        }
        written++;
    }

    return written;
}

/**
 * @brief Read multiple bytes from the ring buffer
 */
uint16_t ring_buffer_read_multiple(ring_buffer_t *rb, uint8_t *data, uint16_t length)
{
    uint16_t read_count = 0;

    for (uint16_t i = 0; i < length; i++) {
        if (!ring_buffer_read(rb, &data[i])) {
            break;  // Buffer empty, stop reading
        }
        read_count++;
    }

    return read_count;
}

/**
 * @brief Check how many bytes are available to read
 */
uint16_t ring_buffer_available(ring_buffer_t *rb)
{
    if (rb->head >= rb->tail) {
        return rb->head - rb->tail;
    } else {
        return rb->size - rb->tail + rb->head;
    }
}

/**
 * @brief Check how much free space is available
 */
uint16_t ring_buffer_free_space(ring_buffer_t *rb)
{
    // We always keep one slot empty to distinguish full from empty
    return rb->size - ring_buffer_available(rb) - 1;
}

/**
 * @brief Check if buffer is empty
 */
bool ring_buffer_is_empty(ring_buffer_t *rb)
{
    return (rb->head == rb->tail);
}

/**
 * @brief Check if buffer is full
 */
bool ring_buffer_is_full(ring_buffer_t *rb)
{
    uint16_t next_head = (rb->head + 1) % rb->size;
    return (next_head == rb->tail);
}

/**
 * @brief Clear/reset the ring buffer
 */
void ring_buffer_clear(ring_buffer_t *rb)
{
    rb->head = 0;
    rb->tail = 0;
}

/**
 * @brief Peek at next byte without removing it
 */
bool ring_buffer_peek(ring_buffer_t *rb, uint8_t *data)
{
    // Check if buffer is empty
    if (rb->head == rb->tail) {
        return false;  // Buffer empty
    }

    // Read data WITHOUT advancing tail
    *data = rb->buffer[rb->tail];

    return true;
}
