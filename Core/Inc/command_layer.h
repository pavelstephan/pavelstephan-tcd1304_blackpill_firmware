/**
  ******************************************************************************
  * @file           : command_layer.h
  * @brief          : Command Layer Header - ASCII Command Processing
  ******************************************************************************
  * @attention
  *
  * This layer provides bidirectional ASCII command/control communication
  * between Python and the STM32 firmware over USB CDC.
  *
  * Commands are newline-delimited ASCII strings (e.g., "START\n")
  * Responses are also newline-delimited for easy parsing.
  *
  ******************************************************************************
  */

#ifndef COMMAND_LAYER_H
#define COMMAND_LAYER_H

#include <stdint.h>
#include <stdbool.h>

/* Command buffer size */
#define CMD_BUFFER_SIZE  64

/* Command status codes */
typedef enum {
    CMD_OK = 0,
    CMD_ERROR_UNKNOWN = 1,
    CMD_ERROR_INVALID_PARAM = 2,
    CMD_ERROR_NOT_IMPLEMENTED = 3,
    CMD_ERROR_BUSY = 4  // ← ADDED for var int time
} Command_Status_t;

/* Acquisition state */
typedef enum {
    ACQ_STATE_IDLE = 0,      // Not transmitting frames
    ACQ_STATE_RUNNING = 1     // Actively transmitting frames
} Acquisition_State_t;

/**
 * @brief Initialize the command layer
 * @return CMD_OK on success
 */
Command_Status_t command_layer_init(void);

/**
 * @brief Process incoming commands (call from main loop)
 *
 * This function checks the USB RX buffer for incoming ASCII commands,
 * parses them, and dispatches to appropriate handlers.
 */
void command_layer_process(void);

/**
 * @brief Check if acquisition is currently enabled
 * @return true if frames should be transmitted, false otherwise
 */
bool command_layer_is_acquiring(void);

/**
 * @brief Get current acquisition state
 * @return Current state (IDLE or RUNNING)
 */
Acquisition_State_t command_layer_get_state(void);

/**
 * @brief Get current integration time setting
 * @return Integration time in microseconds
 */
uint32_t command_layer_get_integration_time(void);

/* ============================================================================
   Command Handlers (can be called directly or via command string)
   ============================================================================ */

/**
 * @brief Start frame acquisition/transmission
 */
void command_handle_start(void);

/**
 * @brief Stop frame acquisition/transmission
 */
void command_handle_stop(void);

/**
 * @brief Set integration time (STUB - for future implementation)
 * @param microseconds Integration time in microseconds
 * @return CMD_OK if successful, error code otherwise
 */
Command_Status_t command_handle_set_integration_time(uint32_t microseconds);

/**
 * @brief Send status information back to host
 */
void command_handle_get_status(void);

#endif /* COMMAND_LAYER_H */
