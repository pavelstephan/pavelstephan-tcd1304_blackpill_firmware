# TCD1304 CCD Sensor Firmware Fix - Implementation Guide

## Problem Summary

The firmware was sending frame markers as 32-bit integers instead of ASCII byte sequences. This caused Python to see corrupted markers like "FDNE" and "EMRFu" instead of the intended "FRME" and "ENDF".

## Root Cause

The original code likely defined markers as:
```c
#define FRAME_START_MARKER 0x45524D46  // "FRME" as hex
```

When cast to a structure and sent over USB, these were transmitted as little-endian 32-bit integers, resulting in byte-swapped data that Python couldn't reliably parse.

## The Fix

The corrected code uses proper ASCII byte arrays:
```c
static const uint8_t FRAME_START_MARKER[4] = {'F', 'R', 'M', 'E'};
static const uint8_t FRAME_END_MARKER[4] = {'E', 'N', 'D', 'F'};
```

These are copied directly into the frame structure using `memcpy()`, ensuring Python receives the exact ASCII sequences b'FRME' and b'ENDF'.

## Files to Replace

### 1. ccd_data_layer.h
**Location:** Your STM32 project's `Inc/` or header directory
**Action:** Replace the existing file with the corrected version
**Key Changes:**
- `CCD_Frame_t` structure now uses `uint8_t start_marker[4]` and `uint8_t end_marker[4]`
- Added proper documentation explaining the frame format
- Added `__attribute__((packed))` to ensure no padding

### 2. ccd_data_layer.c
**Location:** Your STM32 project's `Src/` directory
**Action:** Replace the existing file with the corrected version
**Key Changes:**
- Markers defined as ASCII byte arrays
- Uses `memcpy()` to copy markers into frame structure
- Uses `memcmp()` for validation instead of integer comparison

### 3. main.c
**Location:** Your STM32 project's `Src/` directory
**Action:** No changes needed - the callback function is already correct!
**Current behavior:** 
- `HAL_ADC_ConvCpltCallback()` calls `ccd_data_layer_process_readout()`
- Sends complete frame via `CDC_Transmit_FS()`
- This will work perfectly with the corrected data layer

## Implementation Steps

### Step 1: Backup Your Current Code
```bash
# In your STM32 project directory
cp Inc/ccd_data_layer.h Inc/ccd_data_layer.h.backup
cp Src/ccd_data_layer.c Src/ccd_data_layer.c.backup
```

### Step 2: Replace the Files
1. Copy `ccd_data_layer.h` to your project's `Inc/` directory
2. Copy `ccd_data_layer.c` to your project's `Src/` directory

### Step 3: Rebuild the Firmware
1. Open your project in STM32CubeIDE
2. Build the project (Project → Build All)
3. Flash to your STM32F401CCU (Run → Debug or Run)

### Step 4: Test with Python
1. Make the Python script executable:
   ```bash
   chmod +x ccd_frame_viewer.py
   ```

2. Run the test script:
   ```bash
   ./ccd_frame_viewer.py
   ```

3. Expected output:
   ```
   🔍 Searching for STM32 device...
   ✅ Found: /dev/tty.usbmodemXXXX - STMicroelectronics Virtual COM Port
   🔌 Connecting to /dev/tty.usbmodemXXXX...
   ✅ Connected!
   
   🎯 FRAME #1
      Frame Counter: 0
      Pixel Count: 3694
      Checksum: 0xABCD
      Pixel Stats:
         Min:  250 (0x0FA)
         Max: 3890 (0xF32)
         Avg:  1500.5
         Dummy Avg:  255.2
         Signal Avg: 1520.8
   💾 Saved frame to frame_0000.csv
   ```

## Frame Format Reference

Each frame is **7402 bytes** total:

```
Offset | Size | Field          | Type      | Description
-------|------|----------------|-----------|---------------------------
0      | 4    | start_marker   | ASCII     | "FRME"
4      | 2    | frame_counter  | uint16_t  | Increments each frame
6      | 2    | pixel_count    | uint16_t  | Always 3694
8      | 7388 | pixel_data     | uint16_t[]| 3694 pixel values
7396   | 4    | end_marker     | ASCII     | "ENDF"
7400   | 2    | checksum       | uint16_t  | CRC16-CCITT
```

### Pixel Data Layout
```
Index   | Label  | Description
--------|--------|----------------------------------------
0-31    | D0-D31 | Dummy pixels (dark reference, pre)
32-3679 | S1-S3648| Signal pixels (actual sensor data)
3680-3693| D32-D45| Dummy pixels (dark reference, post)
```

## Python Frame Processing

The corrected firmware sends frames that Python can easily parse:

```python
import struct

# Find frame
start_idx = data.find(b'FRME')
frame_bytes = data[start_idx:start_idx + 7402]

# Parse header
frame_counter, pixel_count = struct.unpack('<HH', frame_bytes[4:8])

# Parse pixels (3694 uint16 values)
pixel_data = struct.unpack('<3694H', frame_bytes[8:7396])

# Now pixel_data is a tuple of 3694 integers ready to use!
dummy_pixels = pixel_data[0:32]      # First 32 dummy
signal_pixels = pixel_data[32:-14]   # Middle 3648 signal
dummy_pixels_end = pixel_data[-14:]  # Last 14 dummy
```

## CSV Output Format

The Python script automatically saves frames to CSV:

```csv
pixel,value,normalized
D0,245,0.0598413150
D1,248,0.0605721003
...
S1,1523,0.3720293398
S2,1567,0.3827827681
...
S3648,1489,0.3637120976
D32,251,0.0613028857
...
```

This format is ready for:
- Plotting in Python (matplotlib, pandas)
- Importing into Excel/Google Sheets
- Further calibration and wavelength mapping

## Troubleshooting

### "No frames found"
- Check that STM32 is properly connected via USB
- Verify the correct COM port is being used
- Ensure firmware was successfully flashed

### "Invalid frame size"
- Verify `FRAME_TOTAL_SIZE` matches between firmware and Python
- Check that `CCD_PIXEL_COUNT` is 3694 in both

### "Invalid start/end marker"
- Ensure you're using the corrected firmware files
- Verify the structure is `__attribute__((packed))`
- Check for any compiler padding issues

### Pixel values look wrong
- Remember: 12-bit ADC means values 0-4095
- Dummy pixels should be lower (dark reference)
- If all values are the same, check sensor integration time

## Next Steps

Once frames are being received correctly:

1. **Implement variable integration time**
   - Add command to set integration time from Python
   - Modify timer configurations accordingly

2. **Add frame rate control**
   - Implement user-configurable FPS
   - Add frame timing statistics

3. **Implement command layer**
   - Start/stop acquisition
   - Query device status
   - Adjust integration time dynamically

4. **Wavelength calibration**
   - Map pixel positions to wavelengths
   - Create calibration curves
   - Add wavelength column to CSV output

## Technical Notes

### Why ASCII Markers?
ASCII markers like "FRME" are easily searchable in a binary stream and human-readable when debugging. They're a standard technique for frame synchronization in binary protocols.

### Why CRC16-CCITT?
This checksum algorithm is:
- Fast to compute on embedded systems
- Good error detection (can detect any odd number of bit errors)
- Industry standard for serial communications
- Small overhead (2 bytes)

### Why 16-bit Pixel Values?
The STM32 ADC produces 12-bit values (0-4095), but storing them in 16-bit containers:
- Aligns with CPU word size (faster)
- Simplifies binary transmission
- Leaves room for future 16-bit ADC upgrades
- Standard practice for embedded ADC data

## Contact & Support

If you encounter issues:
1. Check the serial monitor for diagnostic messages
2. Verify "CALLBACK!" messages are appearing
3. Check for "FRAME_ERROR" messages indicating processing failures
4. Use the hex viewer mode in Python to inspect raw bytes

---
**Version:** 1.0 - Corrected Frame Marker Implementation  
**Date:** January 2026  
**Hardware:** STM32F401CCU + TCD1304 Linear CCD Sensor