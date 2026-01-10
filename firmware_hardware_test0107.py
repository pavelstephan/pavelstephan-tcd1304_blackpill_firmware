#!/usr/bin/env python3
"""
TCD1304DG CCD Firmware Test Suite
Tests frame reception, parsing, validation, and pixel mapping
"""

import serial
import serial.tools.list_ports
import struct
import time
import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict
import sys

# Frame structure constants (must match firmware)
FRAME_START_MARKER = b'FRME'
FRAME_END_MARKER = b'ENDF'
CCD_PIXEL_COUNT = 3694
FRAME_TOTAL_SIZE = 7402

# TCD1304DG Pixel Map
PIXEL_MAP = {
    'dummy_start': (0, 16),       # D0-D15: Initial dummy pixels
    'light_shield': (16, 29),     # D16-D28: Light-shielded outputs
    'transition_1': (29, 32),     # D29-D31: Transition elements
    'signal': (32, 3680),         # S0-S3647: THE SPECTRAL DATA!
    'transition_2': (3680, 3683), # Transition elements
    'dummy_end': (3683, 3694),    # D35-D45: Final dummy pixels
}


def crc16_ccitt(data: bytes) -> int:
    """Calculate CRC16-CCITT checksum (polynomial 0x1021)"""
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


def find_serial_port() -> Optional[str]:
    """Auto-detect the STM32 USB CDC device"""
    print("🔍 Searching for STM32 device...")
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        # Look for STM32 VID/PID or common identifiers
        if 'STM' in port.description.upper() or 'USB' in port.description.upper():
            print(f"✅ Found potential device: {port.device} - {port.description}")
            return port.device
    
    print("\n❌ No STM32 device auto-detected.")
    print("Available ports:")
    for port in ports:
        print(f"  - {port.device}: {port.description}")
    
    return None


def test_1_connectivity(ser: serial.Serial) -> bool:
    """Test 1: Basic USB connectivity"""
    print("\n" + "="*60)
    print("TEST 1: Basic Connectivity")
    print("="*60)
    
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Try to read some data
        print("Reading raw data from device...")
        data = ser.read(100)
        
        if len(data) > 0:
            print(f"✅ SUCCESS: Received {len(data)} bytes")
            print(f"First 20 bytes (hex): {data[:20].hex()}")
            return True
        else:
            print("❌ FAIL: No data received")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def test_2_frame_detection(ser: serial.Serial, timeout: float = 5.0) -> Optional[bytes]:
    """Test 2: Detect frame markers in data stream"""
    print("\n" + "="*60)
    print("TEST 2: Frame Marker Detection")
    print("="*60)
    
    ser.reset_input_buffer()
    print(f"Searching for frame start marker (FRME) for up to {timeout}s...")
    
    start_time = time.time()
    buffer = b''
    
    while (time.time() - start_time) < timeout:
        if ser.in_waiting > 0:
            buffer += ser.read(ser.in_waiting)
            
            # Search for start marker
            start_pos = buffer.find(FRAME_START_MARKER)
            if start_pos >= 0:
                print(f"✅ Found FRME marker at position {start_pos}")
                
                # Try to get complete frame
                remaining = FRAME_TOTAL_SIZE - (len(buffer) - start_pos)
                if remaining > 0:
                    print(f"Reading remaining {remaining} bytes...")
                    buffer += ser.read(remaining)
                
                frame_data = buffer[start_pos:start_pos + FRAME_TOTAL_SIZE]
                
                if len(frame_data) >= FRAME_TOTAL_SIZE:
                    # Check for end marker
                    end_marker_pos = 7396
                    end_marker = frame_data[end_marker_pos:end_marker_pos + 4]
                    
                    if end_marker == FRAME_END_MARKER:
                        print(f"✅ Found ENDF marker at correct position")
                        print(f"✅ SUCCESS: Complete frame detected ({len(frame_data)} bytes)")
                        return frame_data
                    else:
                        print(f"⚠️  End marker mismatch: got {end_marker.hex()}")
                        
            # Keep buffer manageable
            if len(buffer) > FRAME_TOTAL_SIZE * 2:
                buffer = buffer[-FRAME_TOTAL_SIZE:]
        
        time.sleep(0.01)
    
    print(f"❌ FAIL: No complete frame detected within {timeout}s")
    print(f"Buffer size: {len(buffer)} bytes")
    if FRAME_START_MARKER in buffer:
        print("⚠️  Start marker found but complete frame not received")
    return None


def test_3_frame_parsing(frame_data: bytes) -> Optional[Dict]:
    """Test 3: Parse frame structure"""
    print("\n" + "="*60)
    print("TEST 3: Frame Parsing")
    print("="*60)
    
    if len(frame_data) != FRAME_TOTAL_SIZE:
        print(f"❌ FAIL: Wrong frame size: {len(frame_data)} (expected {FRAME_TOTAL_SIZE})")
        return None
    
    try:
        # Parse header
        start_marker = struct.unpack('<I', frame_data[0:4])[0]
        frame_counter = struct.unpack('<H', frame_data[4:6])[0]
        pixel_count = struct.unpack('<H', frame_data[6:8])[0]
        
        print(f"Start Marker: 0x{start_marker:08X} ({'FRME' if start_marker == 0x46524D45 else 'INVALID'})")
        print(f"Frame Counter: {frame_counter}")
        print(f"Pixel Count: {pixel_count} (expected {CCD_PIXEL_COUNT})")
        
        # Parse pixel data
        pixels = struct.unpack(f'<{CCD_PIXEL_COUNT}H', frame_data[8:8 + CCD_PIXEL_COUNT * 2])
        
        # Parse footer
        end_marker = struct.unpack('<I', frame_data[7396:7400])[0]
        checksum = struct.unpack('<H', frame_data[7400:7402])[0]
        
        print(f"End Marker: 0x{end_marker:08X} ({'ENDF' if end_marker == 0x454E4446 else 'INVALID'})")
        print(f"Checksum: 0x{checksum:04X}")
        
        # Validate
        if pixel_count != CCD_PIXEL_COUNT:
            print(f"❌ FAIL: Pixel count mismatch")
            return None
        
        if start_marker != 0x46524D45:
            print(f"❌ FAIL: Invalid start marker")
            return None
            
        if end_marker != 0x454E4446:
            print(f"❌ FAIL: Invalid end marker")
            return None
        
        print("✅ SUCCESS: Frame structure valid")
        
        return {
            'frame_counter': frame_counter,
            'pixel_count': pixel_count,
            'pixels': np.array(pixels, dtype=np.uint16),
            'checksum': checksum
        }
        
    except Exception as e:
        print(f"❌ FAIL: Parsing error: {e}")
        return None


def test_4_checksum_validation(frame_data: bytes, parsed_data: Dict) -> bool:
    """Test 4: Validate CRC16 checksum"""
    print("\n" + "="*60)
    print("TEST 4: Checksum Validation")
    print("="*60)
    
    try:
        # Calculate CRC16 over everything except checksum field
        data_to_check = frame_data[0:7400]
        calculated_crc = crc16_ccitt(data_to_check)
        received_crc = parsed_data['checksum']
        
        print(f"Calculated CRC16: 0x{calculated_crc:04X}")
        print(f"Received CRC16:   0x{received_crc:04X}")
        
        if calculated_crc == received_crc:
            print("✅ SUCCESS: Checksum valid!")
            return True
        else:
            print("❌ FAIL: Checksum mismatch")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def test_5_pixel_analysis(parsed_data: Dict) -> bool:
    """Test 5: Analyze pixel data"""
    print("\n" + "="*60)
    print("TEST 5: Pixel Data Analysis")
    print("="*60)
    
    pixels = parsed_data['pixels']
    
    print(f"\n📊 Overall Statistics:")
    print(f"  Min value: {pixels.min()}")
    print(f"  Max value: {pixels.max()}")
    print(f"  Mean value: {pixels.mean():.2f}")
    print(f"  Std dev: {pixels.std():.2f}")
    
    # Analyze by region
    print(f"\n📊 Statistics by Region:")
    for region_name, (start, end) in PIXEL_MAP.items():
        region_pixels = pixels[start:end]
        print(f"\n  {region_name.upper()} (pixels {start}-{end-1}):")
        print(f"    Count: {len(region_pixels)}")
        print(f"    Min: {region_pixels.min()}")
        print(f"    Max: {region_pixels.max()}")
        print(f"    Mean: {region_pixels.mean():.2f}")
        print(f"    Std: {region_pixels.std():.2f}")
    
    # Check for reasonable ADC values (12-bit ADC: 0-4095)
    if pixels.max() > 4095:
        print("\n⚠️  WARNING: Values exceed 12-bit ADC range")
        return False
    
    # Check if we're getting actual data (not all zeros)
    if pixels.max() == 0:
        print("\n⚠️  WARNING: All pixels are zero")
        return False
    
    print("\n✅ SUCCESS: Pixel data looks reasonable")
    return True


def test_6_signal_pixels(parsed_data: Dict) -> pd.DataFrame:
    """Test 6: Extract and label signal pixels"""
    print("\n" + "="*60)
    print("TEST 6: Signal Pixel Extraction & Labeling")
    print("="*60)
    
    pixels = parsed_data['pixels']
    
    # Extract signal pixels (S0-S3647)
    signal_start, signal_end = PIXEL_MAP['signal']
    signal_pixels = pixels[signal_start:signal_end]
    
    print(f"Extracted {len(signal_pixels)} signal pixels")
    print(f"Signal range: {signal_pixels.min()} to {signal_pixels.max()}")
    print(f"Signal mean: {signal_pixels.mean():.2f}")
    
    # Create labeled dataframe
    # For now, just use pixel indices (later you'll add wavelength calibration)
    df = pd.DataFrame({
        'pixel_index': range(len(signal_pixels)),
        'pixel_label': [f'S{i}' for i in range(len(signal_pixels))],
        'intensity': signal_pixels,
        'wavelength_nm': np.nan  # Placeholder for future calibration
    })
    
    print(f"\n📊 Signal Pixel Summary:")
    print(df.describe())
    
    # Check for any saturated pixels (near max ADC value)
    saturated = (signal_pixels > 4000).sum()
    if saturated > 0:
        print(f"\n⚠️  WARNING: {saturated} pixels near saturation (>4000)")
    
    print("\n✅ SUCCESS: Signal pixels extracted and labeled")
    
    return df


def test_7_multiple_frames(ser: serial.Serial, num_frames: int = 5) -> bool:
    """Test 7: Capture multiple frames and check frame counter"""
    print("\n" + "="*60)
    print(f"TEST 7: Multiple Frame Capture ({num_frames} frames)")
    print("="*60)
    
    frame_counters = []
    ser.reset_input_buffer()
    
    for i in range(num_frames):
        print(f"\nCapturing frame {i+1}/{num_frames}...")
        
        # Find next frame
        frame_data = test_2_frame_detection(ser, timeout=3.0)
        if frame_data is None:
            print(f"❌ FAIL: Could not capture frame {i+1}")
            return False
        
        # Parse just the frame counter
        frame_counter = struct.unpack('<H', frame_data[4:6])[0]
        frame_counters.append(frame_counter)
        print(f"  Frame counter: {frame_counter}")
    
    print(f"\n📊 Frame Counter Sequence: {frame_counters}")
    
    # Check if counters are incrementing
    if len(set(frame_counters)) == len(frame_counters):
        print("✅ SUCCESS: All frame counters unique (incrementing properly)")
        return True
    else:
        print("⚠️  WARNING: Duplicate frame counters detected")
        return False


def save_spectrum(df: pd.DataFrame, filename: str = "spectrum_data.csv"):
    """Save spectrum data to CSV"""
    print(f"\n💾 Saving spectrum to {filename}...")
    df.to_csv(filename, index=False)
    print(f"✅ Saved {len(df)} data points")


def main():
    """Main test suite"""
    print("="*60)
    print("TCD1304DG CCD Firmware Test Suite")
    print("="*60)
    
    # Find serial port
    port = find_serial_port()
    if port is None:
        port = input("\nEnter serial port manually (e.g., /dev/cu.usbmodem1234): ").strip()
    
    if not port:
        print("❌ No port specified. Exiting.")
        return
    
    # Open serial connection
    print(f"\n🔌 Connecting to {port}...")
    try:
        ser = serial.Serial(
            port=port,
            baudrate=115200,  # Baudrate doesn't matter for USB CDC
            timeout=1.0
        )
        print("✅ Connected!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    time.sleep(2)  # Give device time to initialize
    
    # Run test suite
    results = {}
    
    # Test 1: Connectivity
    results['connectivity'] = test_1_connectivity(ser)
    if not results['connectivity']:
        print("\n⚠️  Basic connectivity failed. Check USB connection.")
        ser.close()
        return
    
    # Test 2: Frame detection
    frame_data = test_2_frame_detection(ser, timeout=5.0)
    results['frame_detection'] = frame_data is not None
    
    if not results['frame_detection']:
        print("\n⚠️  Frame detection failed. Firmware may not be running correctly.")
        ser.close()
        return
    
    # Test 3: Frame parsing
    parsed_data = test_3_frame_parsing(frame_data)
    results['frame_parsing'] = parsed_data is not None
    
    if not results['frame_parsing']:
        ser.close()
        return
    
    # Test 4: Checksum validation
    results['checksum'] = test_4_checksum_validation(frame_data, parsed_data)
    
    # Test 5: Pixel analysis
    results['pixel_analysis'] = test_5_pixel_analysis(parsed_data)
    
    # Test 6: Signal extraction
    spectrum_df = test_6_signal_pixels(parsed_data)
    results['signal_extraction'] = True
    
    # Test 7: Multiple frames
    results['multiple_frames'] = test_7_multiple_frames(ser, num_frames=5)
    
    # Save data
    save_spectrum(spectrum_df, filename="test_spectrum.csv")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20s}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} tests passed ({100*passed/total:.0f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Firmware is working perfectly! 🎉")
    else:
        print("\n⚠️  Some tests failed. Review output above for details.")
    
    ser.close()
    print("\n✅ Test suite complete!")


if __name__ == "__main__":
    main()