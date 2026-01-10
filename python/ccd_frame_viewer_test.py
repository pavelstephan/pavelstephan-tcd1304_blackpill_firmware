#!/usr/bin/env python3
"""
CCD Frame Viewer - Test script for corrected firmware
This script searches for properly formatted frames with ASCII markers
"""

import serial
import serial.tools.list_ports
import struct
import sys
import time

# Frame structure constants (must match firmware)
CCD_PIXEL_COUNT = 3694
FRAME_START_MARKER = b'FRME'
FRAME_END_MARKER = b'ENDF'
FRAME_HEADER_SIZE = 8   # start_marker(4) + frame_counter(2) + pixel_count(2)
FRAME_PIXEL_SIZE = CCD_PIXEL_COUNT * 2  # 7388 bytes
FRAME_FOOTER_SIZE = 6   # end_marker(4) + checksum(2)
FRAME_TOTAL_SIZE = FRAME_HEADER_SIZE + FRAME_PIXEL_SIZE + FRAME_FOOTER_SIZE  # 7402 bytes

def find_serial_port():
    """Auto-detect the STM32 USB CDC device"""
    print("🔍 Searching for STM32 device...")
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        if 'STM' in port.description.upper() or 'USB' in port.description.upper():
            print(f"✅ Found: {port.device} - {port.description}")
            return port.device
    
    print("❌ No STM32 device found")
    return None

def parse_frame(frame_bytes):
    """
    Parse a complete frame into its components
    Returns: (frame_counter, pixel_count, pixel_data, checksum) or None if invalid
    """
    if len(frame_bytes) != FRAME_TOTAL_SIZE:
        print(f"❌ Invalid frame size: {len(frame_bytes)} (expected {FRAME_TOTAL_SIZE})")
        return None
    
    # Check markers
    start_marker = frame_bytes[0:4]
    end_marker = frame_bytes[FRAME_TOTAL_SIZE-6:FRAME_TOTAL_SIZE-2]
    
    if start_marker != FRAME_START_MARKER:
        print(f"❌ Invalid start marker: {start_marker}")
        return None
        
    if end_marker != FRAME_END_MARKER:
        print(f"❌ Invalid end marker: {end_marker}")
        return None
    
    # Parse header
    frame_counter, pixel_count = struct.unpack('<HH', frame_bytes[4:8])
    
    # Parse pixel data
    pixel_data_bytes = frame_bytes[8:8+FRAME_PIXEL_SIZE]
    pixel_data = struct.unpack(f'<{CCD_PIXEL_COUNT}H', pixel_data_bytes)
    
    # Parse checksum
    checksum = struct.unpack('<H', frame_bytes[FRAME_TOTAL_SIZE-2:FRAME_TOTAL_SIZE])[0]
    
    return frame_counter, pixel_count, pixel_data, checksum

def analyze_pixel_data(pixel_data):
    """Analyze the pixel data for basic statistics"""
    min_val = min(pixel_data)
    max_val = max(pixel_data)
    avg_val = sum(pixel_data) / len(pixel_data)
    
    # Analyze dummy pixels (first 32 and last 14)
    dummy_pixels_start = pixel_data[0:32]
    dummy_pixels_end = pixel_data[-14:]
    dummy_avg = (sum(dummy_pixels_start) + sum(dummy_pixels_end)) / 46
    
    # Analyze signal pixels (middle 3648)
    signal_pixels = pixel_data[32:-14]
    signal_avg = sum(signal_pixels) / len(signal_pixels)
    
    return {
        'min': min_val,
        'max': max_val,
        'avg': avg_val,
        'dummy_avg': dummy_avg,
        'signal_avg': signal_avg
    }

def save_frame_to_csv(pixel_data, frame_number, filename=None):
    """Save a frame to CSV format with pixel labels"""
    if filename is None:
        filename = f"frame_{frame_number:04d}.csv"
    
    # Create pixel labels
    labels = []
    # D0-D31 (first 32 dummy pixels)
    labels.extend([f'D{i}' for i in range(32)])
    # S1-S3648 (signal pixels)
    labels.extend([f'S{i+1}' for i in range(3648)])
    # D32-D45 (last 14 dummy pixels)
    labels.extend([f'D{i+32}' for i in range(14)])
    
    # Write CSV
    with open(filename, 'w') as f:
        f.write("pixel,value,normalized\n")
        for label, value in zip(labels, pixel_data):
            normalized = value / 4095.0  # 12-bit ADC: 0-4095
            f.write(f"{label},{value},{normalized:.10f}\n")
    
    print(f"💾 Saved frame to {filename}")

def main():
    port = find_serial_port()
    if not port:
        port = input("\nEnter serial port manually: ").strip()
    
    if not port:
        print("No port specified")
        return
    
    print(f"\n🔌 Connecting to {port}...")
    
    try:
        ser = serial.Serial(port, 115200, timeout=0.1)
        print("✅ Connected!\n")
        print("=" * 80)
        print("FRAME VIEWER - Press Ctrl+C to stop")
        print("=" * 80)
        
        buffer = b''
        frame_count = 0
        last_save_time = time.time()
        
        while True:
            # Read available data
            data = ser.read(4096)
            
            if len(data) > 0:
                buffer += data
                
                # Look for frame start marker
                while FRAME_START_MARKER in buffer:
                    start_idx = buffer.find(FRAME_START_MARKER)
                    
                    # Check if we have enough data for a complete frame
                    if len(buffer) >= start_idx + FRAME_TOTAL_SIZE:
                        # Extract potential frame
                        frame_bytes = buffer[start_idx:start_idx + FRAME_TOTAL_SIZE]
                        
                        # Parse frame
                        result = parse_frame(frame_bytes)
                        
                        if result:
                            frame_counter, pixel_count, pixel_data, checksum = result
                            frame_count += 1
                            
                            print(f"\n🎯 FRAME #{frame_count}")
                            print(f"   Frame Counter: {frame_counter}")
                            print(f"   Pixel Count: {pixel_count}")
                            print(f"   Checksum: 0x{checksum:04X}")
                            
                            # Analyze pixel data
                            stats = analyze_pixel_data(pixel_data)
                            print(f"   Pixel Stats:")
                            print(f"      Min: {stats['min']:4d} (0x{stats['min']:03X})")
                            print(f"      Max: {stats['max']:4d} (0x{stats['max']:03X})")
                            print(f"      Avg: {stats['avg']:7.1f}")
                            print(f"      Dummy Avg: {stats['dummy_avg']:7.1f}")
                            print(f"      Signal Avg: {stats['signal_avg']:7.1f}")
                            
                            # Auto-save first frame and then every 10 seconds
                            current_time = time.time()
                            if frame_count == 1 or (current_time - last_save_time) > 10:
                                save_frame_to_csv(pixel_data, frame_counter)
                                last_save_time = current_time
                            
                            # Remove processed frame from buffer
                            buffer = buffer[start_idx + FRAME_TOTAL_SIZE:]
                        else:
                            # Invalid frame, skip past this start marker
                            buffer = buffer[start_idx + 4:]
                    else:
                        # Not enough data yet, break and wait for more
                        break
                
                # Keep buffer size reasonable (keep last 20KB)
                if len(buffer) > 20000:
                    buffer = buffer[-20000:]
            
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n\n✅ Stopped by user")
        print(f"📊 Total frames received: {frame_count}")
        ser.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()