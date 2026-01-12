
(changelogs on the bottom of this page)

In this repo you will complete firmware and a bunch of related files representing
the primary elements of the firmware and ultimately, control code for the TCD1304 sensor
controled by the an STM32F401CCU6 'blackpill' MCU.  Initially I made my own board, but
I came across curiousscientist's blog and youtube channel and decided I would use his most
recent board (ordered from PCBWay from the link on his site).  That said, it should work
with any control board, but you may need to invert the output in the receiving device/
computer.  In other words (and this is important), the board I am using DOES NOT invert 
(higher charge in pixel well equals 'darker' value).  This must be accomodated in 
python or in the processing code, eg:

def invert_signal(pixels):
    """Invert CCD signal so light = high values, dark = low values"""
    return ADC_MAX_VALUE - pixels

... and applied globally to all pixel data (or you will have bespoke code and a lot of headached
as soon as it's parsed, so all downstream code treats light=high.  Many of the test scripts
in the python file were written before adding the global invert function, and so their
outputs may look wonky. Additionally, I added start/stop controls over USB output later,
and so some scripts may need to have the USB start command send to the MCU to function 
(THE DEFAULT USB OUTOUT STATE IS GATED OFF from about 011026.

Note the code was written using the STM Cube IDE and HAL libraries/functions (no RTOS), 
and it should be completely OS intependent (ie, work with a control computer running
any OS).  

https://curiousscientist.tech/blog/tcd1304-linear-ccd-driving-the-ccd 

This was becuase his design is super slick in many important ways, uses minimal parts very 
efficiently, and is off-the-shelf orderable in a form factor is small and perfect for my use-case.  
Anything I would have built would be bigger, messier and probably lower performing than
his board, so I used that and and his STMCube IDE tutorial, 
extensively, to set up the timers and basic, rudimentary firmare, which I then built-upon
to this point.  This firmware is essentially done, but there are elements that I may need
to tweak in later releases.  I also cannot yet say whether the control board or the firmware
have any little issues I need to clean up, as many of those will be use-case specific and
really must be determined in my real-world spectrometer environment.  I will update if
I encounter any issues worth mentioning or correcting.


My use-case is reflective uv-viz-nir spectrometry across essentially the complete spectral 
range of the sensor, from roughly 390nm to about 1100nm, although that is probabily pushing 
things a bit at the extreme ends of that range, due to sensor performance in those wavelenth 
bands.  I research and collect ancient beads, gemstones, metals and various other small-sizes 
artifacts (you can find some of my papers on academia.com by searching my name), and I needed
a high-resolution, highly linear spectrometer for various testing/analysis purposes, and so
I built one (including a full spectrum, instrument-grade lightsource) using high quality parts
where required, and cheap but functional parts where not required.  Later, I may post the
design, because it is unique but very powerful and precise for my use-case, and something
others can probably improve further, which I welcome.

Final housekeeping notes: this readme any other readmes were written real-time while working through 
the project phases and so they have funtioned for me as both on-going code notes, but also, 
I hope, they provide detailed descriptions or the firmare and python archtectures, its elements, 
and some easy paths to modify, extend, or refine the re-usable pieces of the code (eg. the various 
layers of the comms stack, the ring buffer code, etc), which I tried to write and make discrete so 
that those elements can be used in other projects, where applicable.  To be clear, I am not a developer, 
and although the design/implimentation is my own, I used Claud extensively to crank out python 
test scripts and to refince elements of the logic that we tricky for me to figure out or code.  
It has become a truly remarkable platform (Claud), code-wise, and I will continue to use it extensivly.
Finally, the sensor is super, um, sensitive.  That is, people shine lasers on this, which the 
hardware is designed to accomodate, and thus int times like 10-20us, won't generate much signal
in typical lighting environments (in the case of the non-inverting nature of this board, low
light will look like saturation unless inverted in code).    

About the firmware and software architecture

A bunch of great, and some not so great, control firmware can be found for this sensor 
for teensy and various STM32F MCUs, but I encountered several recurring issues with the ones
I tried (specific to my needs), and so I decided it was ultimtely easier for me to just to write 
from scratch.  The primary design principle, like any firmware I have written, is that it should 
be as fast, robust, flexible, linear, and accurate as possible, outputting immediately usable, 
framed (but unprocessed) signal that is is close to the theoretical performance limits of the sensor 
as possible.  There is only so much user input/sensor-level control required to use this sensor
for nearly any use-case, and so I intentionally avoided writing a CLI, or coding any non-essential
sensor control knobs in the firmware. In other words, you should be able to set it and forget it, 
get immediately usable singal framed specifically for this sensor, then do all data-grooming and 
signal processing/analysis in python.  In other, other words, I think the comms stack and sensor 
control are all instument-grade and fully functional, but in a lightweight code footprint, with,
I think, easy signal and control access from python (or any control/processing code on the other
end, the code was written so that any device/computer can fully utilize the sensor without the
need to change the firmware in any way).  Specifially, NO signal processing is done in the firmware, 
and no non-essential sensor functions are coded. That is to say, so long as the signal receieved
by the control computer is accurate and high-integrity and framed in some parsable and processable
way, I feel it's best to leave calibration, averaging, grooming (discarding outlier bits or
fames, for example) and any other processing to the control device.  At least this is my preference,
and it makes for simple but highly functional and robust firmware, IMHO.

The comms stack is written in three discrete logical layers: a data, control, and command layer,
the source code for which (as well as the ring_buffer code) I have posted.  The first two of those 
layers are all binary, end-to-end, and the the latter, the command layer (used by python to control 
sensor function/settings, etc) is ascii, but interfaces with the control and data layers after simple 
translation to/from binary.  As another key design principle, I tried to always operate the sensor 
per its design parameters (optimized to Toshiba design guidelines) and the same way (or possibly 
in some cases in better ways) as this or similiar CCD sensors are controlled/operated in lab-grade,
off-the-shelf spectrometers (such as ocean optics or hamamamtsu).
 
Thus, the code is written so that the sensor output received by the control computer is always
one full frame equal to a full reading of all sensor elements (pixels) - more on this shortly.  
These frames are clearly marked (in ascii) so that the control devise can easily identify, parse 
and process the signal.  Similiarly, only the minimum viable (but all necessary) sensor controls
and features are coded in the firmware.  These are the following: start/stop/status, and integration
time.  As far as I can tell, this is all that is really required, or would be needed, 
since sample lenght can be controlled with start/stop (because at no point will any partial
reading arrive at the control device), and 'shutter speed'/FPS and gain/sensitivity can
be fully controlled be (both are a product of) integration time. I use an external light source
that I do not need to be triggered by the code, for now, but I will add an optional light-source
trigger and intensity control (where applicable) to the firmware at a later date.  

Note the int_time in this version is from 10-10,0000 microseconds.  This was just a range 
of convenience, I will change it to range from 10us to the max theoretical int_time of the 
sensor and this MCU in a few days, but note that the timers are dynamically chagned by the firmware
based on that user-input, and the firmware is written so that this range can be extended by chaning 
a number or two in the code.  I will post the revision with the longer int_time range in a few
days (or when I get around to it).

To run firmware:

Just flash the MCU with the firmware (TCD1304_firmware_v2.ioc). The Src, Inc, USB, etc. files are 
provided informationally, they are already compiled in that .ioc file.  Onced flashed, if
your sensor is conncted correctly with working hardware (per pin assignment below), the code will/
should output a continuos stream of frames (full sensor reads) at the default into time
of 20us (unless changed).  Why 20us?  The sensor is very sensative, and this time
doesn't saturate the pixels in everyday light (which would not be ideal when testing).

Pins:

PA6 - Fm
PA0 - ICG
PA2 - SH
OS - USB

I have also included a bunch of test scriptsin python (in the /python folder) that can be used both 
to test the firmware and its various elements, but also as useful scripts that can be ran if any of 
those elements are changed or modified in the future.  Those should be self-explanitary and 
they will throw explicit error messages when problems are encounted.  I will post the control
code when it's done, or use your own or someone elses.  Just assign pixel numers/labels to the
frame pixels, format in some usable way (I format Pn, Sn - pixel number and singnal value at that
pixel), in a simple two column .csv file (the standard in spectrometry, mostly).


Code/Architectural/Sensor Details

TCD1304DG Sensor Specifications

Total elements per readout: 3694
Effective signal pixels: 3648 (S0-S3647)
Dummy pixels: 46 (light-shielded + test outputs)

Pixel layout (TCD1304DG):

D0-D15:   16 dummy outputs (light-shielded)
D16-D28:  13 light-shielded outputs
D29-D31:   3 transition elements
S0-S3647: 3648 SIGNAL PIXELS (this is your spectral data!)
D32-D45:  14 dummy outputs

Logical comms/control layers (all bi-directional)

┌─────────────────────────────────────┐
│   USER/COMMAND LAYER                │  ← Python interfaces here
│   (ASCII, human-readable)           │
├─────────────────────────────────────┤
│   CONTROL/TRANSPORT LAYER           │  ← USB ring buffers
│   (Binary data movement)            │
├─────────────────────────────────────┤
│   DATA LAYER                        │  ← Frame marking happens HERE
│   (CCD → RAM with frame markers)    │
└─────────────────────────────────────┘

Header files for each layer (in Core/Src and Core/Inc), plus ring buffer:
- ccd_data_layer.c/.h
- usb_tranport_layer.c/.h
- commmand_layer.c/.h
- ring_buffer.c/.h


Frame structure:

Each frame is 7402 bytes and contains:

┌────────────────────────────────────────┐
│ START MARKER: "FRME" (4 bytes)         │  0x46524D45
├────────────────────────────────────────┤
│ FRAME COUNTER: uint16_t (2 bytes)      │  Wraps at 65535
├────────────────────────────────────────┤
│ PIXEL COUNT: uint16_t (2 bytes)        │  Always 3694
├────────────────────────────────────────┤
│ PIXEL DATA: 3694 × 2 bytes             │  7388 bytes of ADC values
│   (uint16_t array)                     │  12-bit ADC right-aligned
├────────────────────────────────────────┤
│ END MARKER: "ENDF" (4 bytes)           │  0x454E4446
├────────────────────────────────────────┤
│ CHECKSUM: CRC16 (2 bytes)              │  CRC-16-CCITT
└────────────────────────────────────────┘
Total: 7402 bytes

Buffer management in main.c:

#define CCDBuffer 6000
volatile uint16_t CCDPixelBuffer[CCDBuffer];

Why 6000?

Current sensor needs: 3694 pixels
Frame needs: 3694 pixels
Headroom for variable integration times
RAM is plentiful (64KB on STM32F401)
Proven working in original implementation

USB buffer size:

#define USB_TX_BUFFER_SIZE  8192  // Or larger - needs min 7408

Python integration strategy - data and control layers remain binary everywhere,
frame header is contract between data and control layer, and atomic unit of output
is always one commplete frame wrapped with the header, end marker and checksum)

Python is always in sync, cuz it searches for frame header and end marker, grabbing
data starting and ending as such in frame incraments.  

Command layer 

Command layer is is bi-directional and ASCII, with '\n' (newline char) as marker of end of command input.
IT is used to controls sensor functions (eg., setting of int time, start/stop/status,
future commmands between python and firmware, etc.).  Command is only acted upon/actioned
by recieving code when it encounters the \n (newline) signal.

A note on start/stop approach:  the CCD is designed to run coninuously, and it is ran as such in 
Hamamatsu and Ocean Optics spectrometers using this CCD (which is optimal, since starting and stopping
timers between MCU and sensor might effect linearity or accuracy).  Thus the firmware is written so that 
sensor is continuously reading per the timers established in the code, and only the USB output is gated/triggered-on/off with start/stop commands.

┌─────────────────────────────────────────┐
│         USB CDC Virtual COM Port        │
├─────────────────────────────────────────┤
│                                         │
│  Mac → STM32:  ser.write(b'START\n')    │
│                    ↓                    │
│              USB Hardware               │
│                    ↓                    │
│       CDC_Receive_FS() [callback]       │
│                    ↓                    │
│                    ↓                    │
│         RX Ring Buffer                  │
│                                         │
│  ─────────────────────────────────────  │
│                                         │
│  STM32 → Mac:  CDC_Transmit_FS(data)    │
│                    ↓                    │
│              USB Hardware               │
│                    ↓                    │
│         ser.read() in Python            │
│                                         │
└─────────────────────────────────────────┘

Command layer files: /Src/command_layer.c and /Inc/command_layer.h
Code to call command layer in main: 

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>
#include "usbd_cdc_if.h"
#include "usb_transport.h"  // ← ADDED for USB transport code
#include "ccd_data_layer.h"  // ← ADDED for CCD frame management
#include "command_layer.h"   // ← ADDED FOR COMMAND layer
/* USER CODE END

inits:
// Initialize USB transport layer
  usb_transport_init();
  // Initialize CCD data layer
  ccd_data_layer_init();
  // Initialize command layer
  command_layer_init();

Snippet of treatment of command_layer in command_layer.c (in Src folder):

/**
 * @brief Process incoming commands from USB
 *
 * This function should be called repeatedly from the main loop.
 * It reads bytes from the USB RX buffer and accumulates them until
 * a newline is received, then parses and executes the command.
 /
void command_layer_process(void)
{
    // Read available bytes from RX ring buffer
    while (usb_transport_available()) {
        uint8_t byte;

        if (!usb_transport_read_byte(&byte)) {
            break;  // No more data
        } ...


Command implimentation snippet from command_layer.c

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
    else if (strncmp(clean_cmd, "SET_INT ...


Command layer functioning workflow, STATUS example:

Private state variables set up in command_layer.c, eg:
// Private variables 
static Acquisition_State_t acquisition_state = ACQ_STATE_IDLE;
static uint32_t integration_time_us = 20;  // Default 20µs

When python sends command 'STATUS', it is parsed in command_layer.c, 
else if (strcmp(clean_cmd, "STATUS") == 0) {
    command_handle_get_status();  // ← Calls this function
}

... and variables as per below are updated

// When you send START:
void command_handle_start(void)
{
    acquisition_state = ACQ_STATE_RUNNING;  // ← Updates state
    send_response("OK:STARTED\n");
}

// When you send STOP:
void command_handle_stop(void)
{
    acquisition_state = ACQ_STATE_IDLE;     // ← Updates state
    send_response("OK:STOPPED\n");
}

// When you send SET_INT_TIME:xxx (future):
Command_Status_t command_handle_set_integration_time(uint32_t microseconds)
{
    integration_time_us = microseconds;      // ← Updates time
    // ... timer reconfiguration code ...
}

ADDING NEW COMMANDS

// Step 1 - Add new handler function (command_layer.c)
void command_handle_your_new_feature(void)
{
    // Do whatever you need
    some_setting = true;
    
    // Send response back
    send_response("OK:FEATURE_ENABLED\n");
}

//Step 2- Add to parser:

else if (strcmp(clean_cmd, "YOUR_COMMAND") == 0) {
    command_handle_your_new_feature();
}

// Step 3 - Use it from python:

ser.write(b'YOUR_COMMAND\n')
response = ser.readline()
// Get: "OK:FEATURE_ENABLED"


Questions? Issues?
Frame too large? Check USB_TX_BUFFER_SIZE
Missing frames? Check frame counter gaps
Bad checksums? Verify endianness in Python
Wrong pixel count? Should always be 3694

CHANGELOGS:

0101 Changelog"
- added prescaler to dynamically change int time and increate total int time range
from earlier 10-100,0000us to 10us-10 SECONDS time ( 10 μs to 10 seconds (10,000,000 μs). 
- Requires STOP first: Prevents timer changes during acquisition
- Calculates frame time: Always 3694 × integration_time (reads all pixels)
-- Uses prescalers intelligently
-- ≤1000 μs: PSC=0 (84 MHz) for precision
-- 1000 μs: PSC=83 (1 MHz) for simplicity
-- Updates both timers: TIM5 (SH) and TIM2 (ICG) stay synchronized
-- Provides feedback: Returns integration time, frame time, and FPS


Intgrating pre-scalers in python:

# Stop acquisition
ser.write(b'STOP\n')
response = ser.readline()
print(response)  # "OK:STOPPED"

# Set integration time to 1000 μs (1 ms)
ser.write(b'SET_INT_TIME:1000\n')
response = ser.readline()
print(response)  # "OK:INT_TIME=1000us,FRAME_TIME=3694ms,FPS=0.2"

'''
ser.write(b'SET_INT_TIME:10\n')        # 10 μs (minimum)
ser.write(b'SET_INT_TIME:100\n')       # 100 μs
ser.write(b'SET_INT_TIME:1000\n')      # 1 ms (1,000 μs)
ser.write(b'SET_INT_TIME:10000\n')     # 10 ms (10,000 μs)
ser.write(b'SET_INT_TIME:100000\n')    # 100 ms (100,000 μs)
ser.write(b'SET_INT_TIME:1000000\n')   # 1 second (1,000,000 μs)
ser.write(b'SET_INT_TIME:10000000\n')  # 10 seconds (10,000,000 μs) - MAXIMUM
'''

# Check status
ser.write(b'STATUS\n')
response = ser.readline()
print(response)  # "STATUS:IDLE,INT_TIME:1000us,FRAME_TIME:3694ms,FPS:0"

# Start acquisition
ser.write(b'START\n')
response = ser.readline()
print(response)  # "OK:STARTED"

