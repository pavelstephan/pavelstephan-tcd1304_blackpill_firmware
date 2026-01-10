/**
 ******************************************************************************
 * @file    usb_transport.h
 * @brief   USB CDC transport layer with ring buffers
 * @author  Phase 1B - Transport Layer
 ******************************************************************************
 * @attention
 *
 * This layer provides:
 * - Ring-buffered USB RX (commands from Python)
 * - Ring-buffered USB TX (responses to Python)
 * - Non-blocking send/receive
 * - Separation of data path (frames) from control path (commands)
 *
 ******************************************************************************
 */

#ifndef USB_TRANSPORT_H
#define USB_TRANSPORT_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* Transport configuration */
#define USB_RX_BUFFER_SIZE  256   // Command receive buffer
#define USB_TX_BUFFER_SIZE  512   // Response transmit buffer

/* Function prototypes */

/**
 * @brief Initialize the USB transport layer
 * @note Call this once during startup, after USB initialization
 */
void usb_transport_init(void);

/**
 * @brief Process USB transport (call from main loop)
 * @note This handles sending queued data when USB is ready
 */
void usb_transport_process(void);

/**
 * @brief Check if data is available to read
 * @return Number of bytes available in RX buffer
 */
uint16_t usb_transport_available(void);

/**
 * @brief Read a single byte from RX buffer
 * @param data Pointer to store the byte
 * @return true if successful, false if buffer empty
 */
bool usb_transport_read_byte(uint8_t *data);

/**
 * @brief Read multiple bytes from RX buffer
 * @param buffer Destination buffer
 * @param length Maximum bytes to read
 * @return Number of bytes actually read
 */
uint16_t usb_transport_read(uint8_t *buffer, uint16_t length);

/**
 * @brief Read a line of text (until \n or \r\n)
 * @param buffer Destination buffer
 * @param max_length Maximum buffer size (including null terminator)
 * @return Number of bytes read (not including null terminator), 0 if no complete line
 */
uint16_t usb_transport_read_line(char *buffer, uint16_t max_length);

/**
 * @brief Write a single byte to TX buffer
 * @param data Byte to write
 * @return true if successful, false if buffer full
 */
bool usb_transport_write_byte(uint8_t data);

/**
 * @brief Write multiple bytes to TX buffer
 * @param buffer Source buffer
 * @param length Number of bytes to write
 * @return Number of bytes actually written
 */
uint16_t usb_transport_write(const uint8_t *buffer, uint16_t length);

/**
 * @brief Write a null-terminated string
 * @param str String to write
 * @return Number of bytes written
 */
uint16_t usb_transport_write_string(const char *str);

/**
 * @brief Send data directly via USB (bypass TX buffer)
 * @param buffer Data to send
 * @param length Number of bytes
 * @return true if successful, false if USB busy
 * @note Use this for frame data (large transfers), not commands
 */
bool usb_transport_send_direct(const uint8_t *buffer, uint16_t length);

/**
 * @brief Called by USB CDC receive callback (internal use)
 * @param buffer Received data
 * @param length Number of bytes received
 */
void usb_transport_rx_callback(uint8_t *buffer, uint32_t length);

/**
 * @brief Called by USB CDC transmit complete callback (internal use)
 */
void usb_transport_tx_complete_callback(void);  // ← ADDED

/**
 * @brief Check if USB is busy transmitting
 * @return true if busy, false if ready
 */
bool usb_transport_is_tx_busy(void);

/**
 * @brief Get statistics (for debugging)
 */
typedef struct {
    uint32_t rx_bytes_total;
    uint32_t tx_bytes_total;
    uint32_t rx_overflow_count;
    uint32_t tx_overflow_count;
} usb_transport_stats_t;

void usb_transport_get_stats(usb_transport_stats_t *stats);
void usb_transport_reset_stats(void);

#endif /* USB_TRANSPORT_H */
