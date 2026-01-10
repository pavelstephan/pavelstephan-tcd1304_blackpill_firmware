'''
 git repository: https://github.com/Ur-Namma/tcd1304_firmware.git

echo "# tcd1304_firmware" >> README.md
git init
git add README.md
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/Ur-Namma/tcd1304_firmware.git
git push -u origin main

git remote add origin https://github.com/Ur-Namma/tcd1304_firmware.git
git branch -M main
git push -u origin main



Changes to firmware

Transport layer architecture (all binary, ascii is only at the control layer interfacing with 
python):

Python/Mac
    ↕ (USB)
Ring Buffers (RX: 256 bytes, TX: 512 bytes)
    ↕
USB CDC HAL
    ↕
STM32 Hardware

ring buffer used for:

Receiving commands from Python (USB → ring buffer)
Sending responses to Python (ring buffer → USB)
Buffering data between interrupts and main loop

Changes in firmware
- added ring_buffer and USB transport
- In main.c:

Added interrupt-safe ring buffers
- Created a USB transport abstraction layer
- Integrated it with existing USB callbacks
- Modified 4 different files correctly

 #include "usb_transport.h" in USER CODE BEGIN Includes
 usb_transport_init(); in USER CODE BEGIN 2
 usb_transport_process(); in USER CODE BEGIN 3

In usbd_cdc_if.c:

 #include "usbd_cdc_if.h" in USER CODE BEGIN INCLUDE ← In first rev of code
 #include "usb_transport.h" in USER CODE BEGIN INCLUDE ← Added

 Call backs (object/function passed between USB tx and rx parties (ADC and python??) - callback 
 should return zero if it wants to be called again for more data. If it returns anything other 
 than zero, the TX/RX streaming comes to an end and it won't be called again)
 - usb_transport_rx_callback(Buf, *Len); in CDC_Receive_FS function - ADDED - NOTIFIES 
 USB WHEN TRANSFER COMPLETE

**

 I/O - data and control layer architecture: 

 ┌─────────────────────────────────────┐
│   USER/COMMAND LAYER                │  ← Python interfaces here
│   (ASCII, human-readable)           │
├─────────────────────────────────────┤
│   CONTROL/TRANSPORT LAYER           │  ← USB ring buffers
│   (Binary data movement)            │
├─────────────────────────────────────┤
│   DATA LAYER                        │  ← Frame marking happens HERE
│   (CCD → RAM with frame markers)   │
└─────────────────────────────────────┘

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

Frame structure:

Each frame is 7402 bytes and contains:

┌────────────────────────────────────────┐
│ START MARKER: "FRME" (4 bytes)        │  0x46524D45
├────────────────────────────────────────┤
│ FRAME COUNTER: uint16_t (2 bytes)     │  Wraps at 65535
├────────────────────────────────────────┤
│ PIXEL COUNT: uint16_t (2 bytes)       │  Always 3694
├────────────────────────────────────────┤
│ PIXEL DATA: 3694 × 2 bytes            │  7388 bytes of ADC values
│   (uint16_t array)                     │  12-bit ADC right-aligned
├────────────────────────────────────────┤
│ END MARKER: "ENDF" (4 bytes)          │  0x454E4446
├────────────────────────────────────────┤
│ CHECKSUM: CRC16 (2 bytes)             │  CRC-16-CCITT
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


Python integration strategy (data and control layers remain binary everywhere,
frame header is contract between data and control layer, and atomic unit of output
is always one commplete frame wrapped with the header, end marker and checksum)

Python is always in sync, cuz it searches for frame header and end marker.  Layers
are one big happy frame family.

# Search for start marker
START_MARKER = b'FRME'
END_MARKER = b'ENDF'

# Find frame boundaries
frame_start = data.find(START_MARKER)
if frame_start >= 0:
    frame_data = data[frame_start:frame_start + 7402]

Frame parsing:

import struct

# Unpack frame header
start_marker, frame_counter, pixel_count = struct.unpack('<IHH', frame_data[0:8])

# Extract pixel data (3694 uint16_t values)
pixels = struct.unpack('<3694H', frame_data[8:7396])

# Verify footer
end_marker, checksum = struct.unpack('<IH', frame_data[7396:7402])

Pixel labeling (can later be dynamically changed to reflect specific
wavelength ranges, instrument and environment specific)

# Pixel map for TCD1304DG
PIXEL_MAP = {
    'dummy_start': (0, 16),       # D0-D15
    'light_shield': (16, 29),     # D16-D28
    'transition_1': (29, 32),     # D29-D31
    'signal': (32, 3680),         # S0-S3647 (THE SPECTRAL DATA!)
    'transition_2': (3680, 3683), # D32-D34
    'dummy_end': (3683, 3694),    # D35-D45
}

# Extract signal pixels only
signal_pixels = pixels[32:3680]

# Label with wavelength (after calibration)
wavelengths = np.linspace(start_nm, end_nm, 3648)
spectrum = pd.DataFrame({
    'wavelength_nm': wavelengths,
    'intensity': signal_pixels
})

CRC16 Validation (in Python)

def crc16_ccitt(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
        crc &= 0xFFFF
    return crc

# Validate frame
calc_crc = crc16_ccitt(frame_data[0:7400])
if calc_crc == checksum:
    print("Frame valid!")


Python test:

# Basic connectivity test
while True:
    data = serial_port.read(7402)
    if data.startswith(b'FRME') and data[7396:7400] == b'ENDF':
        print(f"Valid frame received!")
        frame_count = struct.unpack('<H', data[4:6])[0]
        print(f"Frame #{frame_count}")


Firmware Test:

// In main loop, verify frame structure
if (ccd_data_layer_validate_frame(&current_frame) == CCD_FRAME_OK) {
    // Frame is valid
}

Data flow:

1. TIM2 triggers integration period (ICG pulse)
   └─> 630ms period (7500μs integration for 2 duty cycles)

2. TIM4 triggers ADC conversions
   └─> One conversion per pixel shift clock

3. DMA transfers ADC values to CCDPixelBuffer[]
   └─> 3694 samples collected

4. HAL_ADC_ConvCpltCallback() fires
   └─> Calls ccd_data_layer_process_readout()
       ├─> Adds frame markers
       ├─> Increments frame counter
       ├─> Calculates CRC16 checksum
       └─> Returns complete CCD_Frame_t structure

5. Complete frame sent via CDC_Transmit_FS()
   └─> 7402 bytes transmitted over USB

6. Python receives complete, validated frame
   └─> Never partial data!



Questions? Issues?

Frame too large? Check USB_TX_BUFFER_SIZE
Missing frames? Check frame counter gaps
Bad checksums? Verify endianness in Python
Wrong pixel count? Should always be 3694

'''

