/**
  ******************************************************************************
  * @file           : command_layer.c
  * @brief          : Command Layer Implementation
  ******************************************************************************
  * @attention
  *
  * This layer processes ASCII commands from USB CDC and dispatches them
  * to appropriate handler functions. Commands are newline-delimited.
  *
  * Supported Commands:
  * - START              : Begin transmitting frames
  * - STOP               : Stop transmitting frames
  * - STATUS             : Query current state
  * - SET_INT_TIME:xxx   : Set integration time (stub for future)
  *
  ******************************************************************************
  */

#include "command_layer.h"
#include "usb_transport.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include "main.h"  // For htim5 access for variable int time

/* External timer handle from main.c */
extern TIM_HandleTypeDef htim5;  // ← ADD THIS LINE

/* Private variables */
static Acquisition_State_t acquisition_state = ACQ_STATE_IDLE;
static uint32_t integration_time_us = 20;  // Default 20µs (matches your current hardware)
static char command_buffer[CMD_BUFFER_SIZE];
static uint8_t command_index = 0;

/* Private function prototypes */
static void parse_and_execute_command(const char* cmd);
static void send_response(const char* response);

/**
 * @brief Initialize the command layer
 */
Command_Status_t command_layer_init(void)
{
    acquisition_state = ACQ_STATE_IDLE;  // Start in IDLE (not transmitting)
    integration_time_us = 20;
    command_index = 0;
    memset(command_buffer, 0, CMD_BUFFER_SIZE);

    // Send ready message
    send_response("TCD1304_READY\n");

    return CMD_OK;
}

/**
 * @brief Process incoming commands from USB
 *
 * This function should be called repeatedly from the main loop.
 * It reads bytes from the USB RX buffer and accumulates them until
 * a newline is received, then parses and executes the command.
 */
void command_layer_process(void)
{
    // Read available bytes from RX ring buffer
    while (usb_transport_available()) {
        uint8_t byte;

        if (!usb_transport_read_byte(&byte)) {
            break;  // No more data
        }

        // Check for command terminator
        if (byte == '\n' || byte == '\r') {
            if (command_index > 0) {
                // Null-terminate and process command
                command_buffer[command_index] = '\0';
                parse_and_execute_command(command_buffer);
                command_index = 0;
            }
        }
        else if (command_index < (CMD_BUFFER_SIZE - 1)) {
            // Add to buffer
            command_buffer[command_index++] = (char)byte;
        }
        else {
            // Buffer overflow - reset
            command_index = 0;
            send_response("ERROR:CMD_TOO_LONG\n");
        }
    }
}

/**
 * @brief Parse and execute a command string
 */
static void parse_and_execute_command(const char* cmd)
{
    // Remove any trailing whitespace
    char clean_cmd[CMD_BUFFER_SIZE];
    strncpy(clean_cmd, cmd, CMD_BUFFER_SIZE - 1);
    clean_cmd[CMD_BUFFER_SIZE - 1] = '\0';

    // Trim trailing spaces/returns
    int len = strlen(clean_cmd);
    while (len > 0 && (clean_cmd[len-1] == ' ' || clean_cmd[len-1] == '\r')) {
        clean_cmd[--len] = '\0';
    }

    // Parse commands
    if (strcmp(clean_cmd, "START") == 0) {
        command_handle_start();
    }
    else if (strcmp(clean_cmd, "STOP") == 0) {
        command_handle_stop();
    }
    else if (strcmp(clean_cmd, "STATUS") == 0) {
        command_handle_get_status();
    }
    else if (strncmp(clean_cmd, "SET_INT_TIME:", 13) == 0) {
        // Extract parameter
        const char* param_str = &clean_cmd[13];
        uint32_t int_time = (uint32_t)atoi(param_str);

        Command_Status_t status = command_handle_set_integration_time(int_time);

        if (status == CMD_OK) {
            send_response("OK:INT_TIME_SET\n");
        } else if (status == CMD_ERROR_NOT_IMPLEMENTED) {
            send_response("ERROR:NOT_IMPLEMENTED\n");
        } else {
            send_response("ERROR:INVALID_PARAM\n");
        }
    }
    else {
        // Unknown command
        char response[64];
        snprintf(response, sizeof(response), "ERROR:UNKNOWN_CMD:%s\n", clean_cmd);
        send_response(response);
    }
}

/**
 * @brief Send a response string back to host
 */
static void send_response(const char* response)
{
    usb_transport_write_string(response);
}

/**
 * @brief Check if acquisition is enabled
 */
bool command_layer_is_acquiring(void)
{
    return (acquisition_state == ACQ_STATE_RUNNING);
}

/**
 * @brief Get current acquisition state
 */
Acquisition_State_t command_layer_get_state(void)
{
    return acquisition_state;
}

/**
 * @brief Get current integration time
 */
uint32_t command_layer_get_integration_time(void)
{
    return integration_time_us;
}

/* ============================================================================
   Command Handlers
   ============================================================================ */

/**
 * @brief Start acquisition
 */
void command_handle_start(void)
{
    acquisition_state = ACQ_STATE_RUNNING;
    send_response("OK:STARTED\n");
}

/**
 * @brief Stop acquisition
 */
void command_handle_stop(void)
{
    acquisition_state = ACQ_STATE_IDLE;
    send_response("OK:STOPPED\n");
}

/**
 * @brief Set integration time (STUB - for future timer reconfiguration)
 */
/**
 * @brief Set integration time and reconfigure TIM5
 */
/**
 * @brief Set integration time and reconfigure TIM5
 */
Command_Status_t command_handle_set_integration_time(uint32_t microseconds)
{
    // Must be stopped to change integration time
    if (acquisition_state == ACQ_STATE_RUNNING) {
        send_response("ERROR:MUST_STOP_FIRST\n");
        return CMD_ERROR_BUSY;
    }

    // Validate range
    if (microseconds < 10 || microseconds > 100000) {
        send_response("ERROR:RANGE_10_TO_100000\n");
        return CMD_ERROR_INVALID_PARAM;
    }

    // Stop TIM5 (SH)
    HAL_TIM_PWM_Stop(&htim5, TIM_CHANNEL_3);

    // Calculate new ARR: (84MHz × integration_time_us) / 1MHz - 1
    uint32_t arr_value = (84 * microseconds) - 1;

    // CCR stays constant at 4µs = 336 clocks
    uint32_t ccr_value = 335;

    // Update TIM5 registers
    __HAL_TIM_SET_AUTORELOAD(&htim5, arr_value);
    __HAL_TIM_SET_COMPARE(&htim5, TIM_CHANNEL_3, ccr_value);

    // Reset counter for clean start
    __HAL_TIM_SET_COUNTER(&htim5, 0);

    // Restart TIM5
    HAL_TIM_PWM_Start(&htim5, TIM_CHANNEL_3);

    // Update stored value
    integration_time_us = microseconds;

    // Send success response
    char response[64];
    snprintf(response, sizeof(response), "OK:INT_TIME_SET:%lu\n",
             (unsigned long)microseconds);
    send_response(response);

    return CMD_OK;
}
/**
 * @brief Send status information
 */
void command_handle_get_status(void)
{
    char response[128];

    const char* state_str = (acquisition_state == ACQ_STATE_RUNNING) ? "RUNNING" : "IDLE";

    snprintf(response, sizeof(response),
             "STATUS:%s,INT_TIME:%lu\n",
             state_str,
             (unsigned long)integration_time_us);

    send_response(response);
}
