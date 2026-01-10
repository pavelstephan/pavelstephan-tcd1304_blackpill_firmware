/**
  ******************************************************************************
  * @file           : ccd_data_layer.h
  * @brief          : CCD Data Layer Header - CORRECTED VERSION
  ******************************************************************************
  * @attention
  *
  * This layer ensures that only complete, validated frames are passed
  * to upper layers. It enforces the frame contract at the hardware boundary.
  *
  * FIXED: Frame markers are now properly formatted as ASCII byte sequences
  * instead of 32-bit integers, ensuring Python can find them.
  *
  ******************************************************************************
  */

#ifndef CCD_DATA_LAYER_H
#define CCD_DATA_LAYER_H

#include <stdint.h>
#include <stdbool.h>

/* CCD Sensor Configuration */
#define CCD_PIXEL_COUNT    3694    // Total pixels: D0-D31 (32) + S1-S3648 (3648) + D32-D45 (14)

/* Frame Status Codes */
typedef enum {
    CCD_FRAME_OK = 0,
    CCD_FRAME_ERROR_INVALID_DATA = 1,
    CCD_FRAME_ERROR_SIZE = 2,
    CCD_FRAME_ERROR_CHECKSUM = 3
} CCD_Frame_Status_t;

/**
 * @brief Complete CCD Frame Structure - CORRECTED VERSION
 *
 * This structure is designed to be transmitted as-is over USB CDC.
 * All fields are properly aligned for direct binary transmission.
 *
 * Frame Format:
 * - 4 bytes: "FRME" (ASCII start marker)
 * - 2 bytes: frame_counter (uint16_t, little-endian)
 * - 2 bytes: pixel_count (uint16_t, little-endian)
 * - 7388 bytes: pixel_data (3694 × uint16_t, little-endian)
 * - 4 bytes: "ENDF" (ASCII end marker)
 * - 2 bytes: checksum (uint16_t, little-endian, CRC16-CCITT)
 *
 * Total: 7402 bytes per frame
 */
typedef struct __attribute__((packed)) {
    uint8_t  start_marker[4];           // "FRME" as ASCII bytes
    uint16_t frame_counter;              // Increments with each frame
    uint16_t pixel_count;                // Should always be 3694
    uint16_t pixel_data[CCD_PIXEL_COUNT]; // Raw 12-bit ADC values in 16-bit containers
    uint8_t  end_marker[4];             // "ENDF" as ASCII bytes
    uint16_t checksum;                   // CRC16-CCITT over all preceding data
} CCD_Frame_t;

/* Calculate frame size */
#define FRAME_HEADER_SIZE    8      // start_marker(4) + frame_counter(2) + pixel_count(2)
#define FRAME_PIXEL_SIZE     (CCD_PIXEL_COUNT * 2)  // 3694 pixels × 2 bytes = 7388 bytes
#define FRAME_FOOTER_SIZE    6      // end_marker(4) + checksum(2)
#define FRAME_TOTAL_SIZE     (FRAME_HEADER_SIZE + FRAME_PIXEL_SIZE + FRAME_FOOTER_SIZE)  // 7402 bytes

/* Function Prototypes */

/**
 * @brief Initialize the CCD data layer
 * @return CCD_FRAME_OK on success
 */
CCD_Frame_Status_t ccd_data_layer_init(void);

/**
 * @brief Process raw ADC buffer into a complete frame
 * @param adc_buffer Pointer to raw ADC data (must contain at least CCD_PIXEL_COUNT values)
 * @param frame_out Pointer to frame structure to populate
 * @return CCD_FRAME_OK on success, error code otherwise
 */
CCD_Frame_Status_t ccd_data_layer_process_readout(const volatile uint16_t* adc_buffer,
                                                    CCD_Frame_t* frame_out);

/**
 * @brief Validate a frame's integrity
 * @param frame Pointer to frame to validate
 * @return CCD_FRAME_OK if valid, error code otherwise
 */
CCD_Frame_Status_t ccd_data_layer_validate_frame(const CCD_Frame_t* frame);

/**
 * @brief Calculate CRC16 checksum
 * @param data Pointer to data
 * @param length Length of data in bytes
 * @return CRC16-CCITT checksum
 */
uint16_t ccd_data_layer_calculate_crc16(const uint8_t* data, uint32_t length);

/**
 * @brief Get the current frame counter value
 * @return Current frame counter
 */
uint16_t ccd_data_layer_get_frame_count(void);

/**
 * @brief Reset the frame counter to zero
 */
void ccd_data_layer_reset_counter(void);

#endif /* CCD_DATA_LAYER_H */
