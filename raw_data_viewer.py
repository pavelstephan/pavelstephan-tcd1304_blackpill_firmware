#!/usr/bin/env python3
"""
Raw data viewer - See exactly what the device is sending
"""

import serial
import serial.tools.list_ports
import sys
import time

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
        print("RAW DATA VIEW (Ctrl+C to stop)")
        print("=" * 80)
        
        buffer = b''
        packet_count = 0
        
        while True:
            data = ser.read(1000)  # Read up to 1000 bytes
            
            if len(data) > 0:
                buffer += data
                packet_count += 1
                
                print(f"\n📦 Packet #{packet_count} ({len(data)} bytes)")
                print("-" * 80)
                
                # Show hex
                hex_str = ' '.join([f'{b:02x}' for b in data[:100]])
                print(f"HEX: {hex_str}")
                
                # Show ASCII (replace non-printable with '.')
                ascii_str = ''.join([chr(b) if 32 <= b < 127 else '.' for b in data[:100]])
                print(f"ASCII: {ascii_str}")
                
                # Look for our markers
                if b'FRME' in buffer:
                    pos = buffer.find(b'FRME')
                    print(f"\n🎯 FOUND 'FRME' at position {pos}!")
                
                if b'ENDF' in buffer:
                    pos = buffer.find(b'ENDF')
                    print(f"🎯 FOUND 'ENDF' at position {pos}!")
                
                if b'***NEW_CALLBACK_RUNNING***' in buffer:
                    print(f"\n✅ FOUND DIAGNOSTIC MESSAGE!")
                
                if b'FRAME_ERROR' in buffer:
                    print(f"\n⚠️ FOUND FRAME_ERROR MESSAGE!")
                
                # Keep last 20KB in buffer
                if len(buffer) > 20000:
                    buffer = buffer[-20000:]
            
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n\nStopped by user")
        ser.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()