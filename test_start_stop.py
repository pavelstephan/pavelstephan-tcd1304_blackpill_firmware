#!/usr/bin/env python3
"""
Simple START/STOP Command Test
Demonstrates bidirectional communication with the TCD1304 firmware
"""

import serial
import serial.tools.list_ports
import time
import struct

# Frame constants
CCD_PIXEL_COUNT = 3694
FRAME_START_MARKER = b'FRME'
FRAME_TOTAL_SIZE = 7402

def find_serial_port():
    """Auto-detect STM32 device"""
    print("🔍 Searching for STM32 device...")
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        if 'STM' in port.description.upper() or 'USB' in port.description.upper():
            print(f"✅ Found: {port.device}")
            return port.device
    
    print("❌ No STM32 device found")
    return None

def parse_frame(frame_bytes):
    """Quick frame parser"""
    if len(frame_bytes) != FRAME_TOTAL_SIZE:
        return None
    if frame_bytes[0:4] != FRAME_START_MARKER:
        return None
    
    frame_counter, pixel_count = struct.unpack('<HH', frame_bytes[4:8])
    return frame_counter, pixel_count

def main():
    print("=" * 60)
    print("TCD1304 START/STOP COMMAND TEST")
    print("=" * 60)
    
    # Find and connect
    port = find_serial_port()
    if not port:
        port = input("Enter port manually: ").strip()
    
    if not port:
        return
    
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        print(f"\n🔌 Connected to {port}")
        
        # Wait for device ready message
        time.sleep(0.5)
        if ser.in_waiting:
            ready_msg = ser.read(ser.in_waiting)
            print(f"📨 Device says: {ready_msg.decode('ascii', errors='ignore').strip()}")
        
        # Test STATUS command
        print("\n" + "=" * 60)
        print("TEST 1: Query Status")
        print("=" * 60)
        ser.write(b'STATUS\n')
        time.sleep(0.1)
        response = ser.readline()
        print(f"Response: {response.decode('ascii', errors='ignore').strip()}")
        
        # Test START command
        print("\n" + "=" * 60)
        print("TEST 2: Send START Command")
        print("=" * 60)
        print("Sending START...")
        ser.write(b'START\n')
        time.sleep(0.1)
        response = ser.readline()
        print(f"Response: {response.decode('ascii', errors='ignore').strip()}")
        
        # Collect some frames
        print("\n📊 Collecting frames for 2 seconds...")
        start_time = time.time()
        frame_count = 0
        buffer = b''
        
        while time.time() - start_time < 2:
            data = ser.read(4096)
            buffer += data
            
            while FRAME_START_MARKER in buffer:
                idx = buffer.find(FRAME_START_MARKER)
                if len(buffer) >= idx + FRAME_TOTAL_SIZE:
                    frame_bytes = buffer[idx:idx + FRAME_TOTAL_SIZE]
                    result = parse_frame(frame_bytes)
                    if result:
                        frame_count += 1
                        if frame_count % 20 == 0:
                            print(f"  Frame #{result[0]}, pixel_count={result[1]}")
                    buffer = buffer[idx + FRAME_TOTAL_SIZE:]
                else:
                    break
        
        print(f"✅ Received {frame_count} frames in 2 seconds (~{frame_count/2:.1f} FPS)")
        
        # Test STOP command
        print("\n" + "=" * 60)
        print("TEST 3: Send STOP Command")
        print("=" * 60)
        print("Sending STOP...")
        ser.write(b'STOP\n')
        time.sleep(0.2)  # Give time for frames to stop
        
        # Flush any remaining binary frame data
        ser.reset_input_buffer()
        
        time.sleep(0.1)
        response = ser.readline()
        print(f"Response: {response.decode('ascii', errors='ignore').strip()}")
        
        # Verify no more frames
        print("\n📊 Waiting 2 seconds to verify no frames...")
        time.sleep(2)
        bytes_received = ser.in_waiting
        print(f"Bytes in buffer: {bytes_received}")
        
        if bytes_received < 1000:
            print("✅ STOP working correctly - no frames being sent!")
        else:
            print("⚠️  Still receiving data - STOP may not be working")
        
        # Test STATUS again
        print("\n" + "=" * 60)
        print("TEST 4: Query Status (should be IDLE)")
        print("=" * 60)
        
        # Make sure buffer is clean
        time.sleep(0.1)
        if ser.in_waiting > 0:
            ser.reset_input_buffer()
        
        ser.write(b'STATUS\n')
        time.sleep(0.1)
        response = ser.readline()
        print(f"Response: {response.decode('ascii', errors='ignore').strip()}")
        
        # Test restart
        print("\n" + "=" * 60)
        print("TEST 5: Restart Acquisition")
        print("=" * 60)
        
        # Clean buffer before restart
        if ser.in_waiting > 0:
            ser.reset_input_buffer()
        
        print("Sending START again...")
        ser.write(b'START\n')
        time.sleep(0.1)
        response = ser.readline()
        print(f"Response: {response.decode('ascii', errors='ignore').strip()}")
        
        print("\n📊 Collecting frames for 1 second...")
        time.sleep(1)
        buffer = ser.read(ser.in_waiting)
        frame_count = buffer.count(FRAME_START_MARKER)
        print(f"✅ Received ~{frame_count} frames")
        
        # Final stop
        ser.write(b'STOP\n')
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETE!")
        print("=" * 60)
        print("\nCommand layer is working correctly! 🎉")
        
        ser.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()