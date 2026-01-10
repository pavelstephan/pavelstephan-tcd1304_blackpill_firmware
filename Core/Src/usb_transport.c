/**
 ******************************************************************************
 * @file    usb_transport.c
 * @brief   USB CDC transport layer implementation
 ******************************************************************************
 */

#include "usb_transport.h"
#include "ring_buffer.h"
#include "usbd_cdc_if.h"
#include <string.h>

/* Private variables */
static volatile uint8_t rx_buffer_storage[USB_RX_BUFFER_SIZE];
static volatile uint8_t tx_buffer_storage[USB_TX_BUFFER_SIZE];

static ring_buffer_t rx_ring_buffer;
static ring_buffer_t tx_ring_buffer;

static volatile bool tx_in_progress = false;

static usb_transport_stats_t stats = {0};

/* Private function prototypes */
static void tx_flush(void);

/**
 * @brief Initialize the USB transport layer
 */
void usb_transport_init(void)
{
    // Initialize ring buffers
    ring_buffer_init(&rx_ring_buffer, rx_buffer_storage, USB_RX_BUFFER_SIZE);
    ring_buffer_init(&tx_ring_buffer, tx_buffer_storage, USB_TX_BUFFER_SIZE);

    tx_in_progress = false;

    // Reset statistics
    usb_transport_reset_stats();
}

/**
 * @brief Process USB transport (call from main loop)
 */
void usb_transport_process(void)
{
    // Try to flush TX buffer if not already transmitting
    if (!tx_in_progress && !ring_buffer_is_empty(&tx_ring_buffer)) {
        tx_flush();
    }
}

/**
 * @brief Check if data is available to read
 */
uint16_t usb_transport_available(void)
{
    return ring_buffer_available(&rx_ring_buffer);
}

/**
 * @brief Read a single byte from RX buffer
 */
bool usb_transport_read_byte(uint8_t *data)
{
    return ring_buffer_read(&rx_ring_buffer, data);
}

/**
 * @brief Read multiple bytes from RX buffer
 */
uint16_t usb_transport_read(uint8_t *buffer, uint16_t length)
{
    return ring_buffer_read_multiple(&rx_ring_buffer, buffer, length);
}

/**
 * @brief Read a line of text (until \n or \r\n)
 */
uint16_t usb_transport_read_line(char *buffer, uint16_t max_length)
{
    uint16_t count = 0;
    uint8_t byte;

    // Read until newline or buffer full
    while (count < (max_length - 1)) {  // Leave room for null terminator
        if (!ring_buffer_peek(&rx_ring_buffer, &byte)) {
            // No more data available
            return 0;  // No complete line yet
        }

        // Check for newline
        if (byte == '\n' || byte == '\r') {
            // Consume the newline character
            ring_buffer_read(&rx_ring_buffer, &byte);

            // If it's \r, check for following \n and consume it too
            if (byte == '\r') {
                if (ring_buffer_peek(&rx_ring_buffer, &byte) && byte == '\n') {
                    ring_buffer_read(&rx_ring_buffer, &byte);
                }
            }

            // Add null terminator
            buffer[count] = '\0';
            return count;
        }

        // Regular character - read and add to buffer
        ring_buffer_read(&rx_ring_buffer, &byte);
        buffer[count++] = (char)byte;
    }

    // Buffer full but no newline found - this shouldn't happen with proper protocol
    buffer[max_length - 1] = '\0';
    return 0;  // Indicate error (line too long)
}

/**
 * @brief Write a single byte to TX buffer
 */
bool usb_transport_write_byte(uint8_t data)
{
    bool success = ring_buffer_write(&tx_ring_buffer, data);

    if (success) {
        stats.tx_bytes_total++;
    } else {
        stats.tx_overflow_count++;
    }

    return success;
}

/**
 * @brief Write multiple bytes to TX buffer
 */
uint16_t usb_transport_write(const uint8_t *buffer, uint16_t length)
{
    uint16_t written = ring_buffer_write_multiple(&tx_ring_buffer, buffer, length);

    stats.tx_bytes_total += written;

    if (written < length) {
        stats.tx_overflow_count++;
    }

    return written;
}

/**
 * @brief Write a null-terminated string
 */
uint16_t usb_transport_write_string(const char *str)
{
    return usb_transport_write((const uint8_t*)str, strlen(str));
}

/**
 * @brief Send data directly via USB (bypass TX buffer)
 */
bool usb_transport_send_direct(const uint8_t *buffer, uint16_t length)
{
    if (tx_in_progress) {
        return false;  // USB busy
    }

    // Send directly via USB CDC
    uint8_t result = CDC_Transmit_FS((uint8_t*)buffer, length);

    if (result == USBD_OK) {
        tx_in_progress = true;
        stats.tx_bytes_total += length;
        return true;
    }

    return false;
}

/**
 * @brief Called by USB CDC receive callback
 */
void usb_transport_rx_callback(uint8_t *buffer, uint32_t length)
{
    // Write received data to ring buffer
    uint16_t written = ring_buffer_write_multiple(&rx_ring_buffer, buffer, (uint16_t)length);

    stats.rx_bytes_total += written;

    if (written < length) {
        stats.rx_overflow_count++;
    }
}

/**
 * @brief Check if USB is busy transmitting
 */
bool usb_transport_is_tx_busy(void)
{
    return tx_in_progress;
}

/**
 * @brief Flush TX buffer to USB (private function)
 */
static void tx_flush(void)
{
    if (tx_in_progress) {
        return;  // Already transmitting
    }

    // Determine how many bytes to send
    uint16_t available = ring_buffer_available(&tx_ring_buffer);

    if (available == 0) {
        return;  // Nothing to send
    }

    // Limit to reasonable packet size (USB CDC typically uses 64 byte packets)
    uint16_t to_send = (available > 64) ? 64 : available;

    // Copy data from ring buffer to temporary buffer
    static uint8_t temp_buffer[64];
    uint16_t read_count = ring_buffer_read_multiple(&tx_ring_buffer, temp_buffer, to_send);

    // Send via USB CDC
    if (CDC_Transmit_FS(temp_buffer, read_count) == USBD_OK) {
        tx_in_progress = true;
    } else {
        // Failed to send - put data back in ring buffer
        // (This is a simplification - in production might want better error handling)
        ring_buffer_write_multiple(&tx_ring_buffer, temp_buffer, read_count);
    }
}

/**
 * @brief Transmission complete callback (to be called from USB CDC)
 */
void usb_transport_tx_complete_callback(void)
{
    tx_in_progress = false;
}

/**
 * @brief Get statistics
 */
void usb_transport_get_stats(usb_transport_stats_t *stats_out)
{
    stats_out->rx_bytes_total = stats.rx_bytes_total;
    stats_out->tx_bytes_total = stats.tx_bytes_total;
    stats_out->rx_overflow_count = stats.rx_overflow_count;
    stats_out->tx_overflow_count = stats.tx_overflow_count;
}

/**
 * @brief Reset statistics
 */
void usb_transport_reset_stats(void)
{
    stats.rx_bytes_total = 0;
    stats.tx_bytes_total = 0;
    stats.rx_overflow_count = 0;
    stats.tx_overflow_count = 0;
}
