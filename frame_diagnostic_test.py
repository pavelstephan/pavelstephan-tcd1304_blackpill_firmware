#!/usr/bin/env python3
"""
Quick Diagnostic - Verify frame markers are correct
This script checks if the firmware is sending properly formatted markers
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
        ser = serial.Serial(port, 115200, timeout=1)
        print("✅ Connected!")
        print("\n" + "="*80)
        print("DIAGNOSTIC MODE - Checking for frame markers")
        print("="*80)
        print("\nReading data for 5 seconds...")
        
        buffer = b''
        start_time = time.time()
        
        # Collect data for 5 seconds
        while time.time() - start_time < 5:
            data = ser.read(4096)
            if data:
                buffer += data
        
        ser.close()
        
        print(f"\n📊 Collected {len(buffer)} bytes")
        print("\n" + "="*80)
        print("MARKER ANALYSIS")
        print("="*80)
        
        # Check for correct markers
        frme_count = buffer.count(b'FRME')
        endf_count = buffer.count(b'ENDF')
        
        # Check for old corrupted markers
        fdne_count = buffer.count(b'FDNE')
        emrf_count = buffer.count(b'EMRF')
        
        print(f"\n✅ CORRECT MARKERS:")
        print(f"   'FRME' found: {frme_count} times")
        print(f"   'ENDF' found: {endf_count} times")
        
        if frme_count > 0 and endf_count > 0:
            print(f"\n🎉 SUCCESS! Frame markers are working correctly!")
            print(f"   Detected ~{frme_count} complete frames in 5 seconds")
            
            if frme_count == endf_count:
                print(f"   ✅ Marker counts match - frame integrity looks good")
            else:
                print(f"   ⚠️  Warning: Marker count mismatch (may be buffer truncation)")
        else:
            print(f"\n❌ FAIL: No correct markers found")
        
        print(f"\n❌ OLD CORRUPTED MARKERS (should be 0):")
        print(f"   'FDNE' found: {fdne_count} times")
        print(f"   'EMRF' found: {emrf_count} times")
        
        if fdne_count > 0 or emrf_count > 0:
            print(f"\n⚠️  WARNING: Still seeing corrupted markers!")
            print(f"   The firmware may not have been updated correctly.")
            print(f"   Please verify you replaced the ccd_data_layer files and rebuilt.")
        
        # Show sample of data around first marker
        if frme_count > 0:
            first_marker_idx = buffer.find(b'FRME')
            print(f"\n" + "="*80)
            print(f"SAMPLE DATA AROUND FIRST 'FRME' MARKER")
            print(f"="*80)
            
            # Show 32 bytes before and after
            start = max(0, first_marker_idx - 16)
            end = min(len(buffer), first_marker_idx + 32)
            sample = buffer[start:end]
            
            print(f"\nHex view (marker at offset {first_marker_idx}):")
            for i in range(0, len(sample), 16):
                chunk = sample[i:i+16]
                hex_str = ' '.join([f'{b:02x}' for b in chunk])
                ascii_str = ''.join([chr(b) if 32 <= b < 127 else '.' for b in chunk])
                print(f"  {start+i:06d}: {hex_str:<48} | {ascii_str}")
        
        # Check for diagnostic messages
        print(f"\n" + "="*80)
        print(f"DIAGNOSTIC MESSAGES")
        print(f"="*80)
        
        if b'CALLBACK!' in buffer:
            callback_count = buffer.count(b'CALLBACK!')
            print(f"✅ Found 'CALLBACK!' message {callback_count} times")
            print(f"   ADC callback is executing")
        else:
            print(f"❌ No 'CALLBACK!' messages found")
            print(f"   ADC may not be triggering")
        
        if b'NEW_CALLBACK_RUNNING' in buffer:
            print(f"✅ Found 'NEW_CALLBACK_RUNNING' message")
            print(f"   New code is executing")
        
        if b'FRAME_ERROR' in buffer:
            error_count = buffer.count(b'FRAME_ERROR')
            print(f"⚠️  Found {error_count} 'FRAME_ERROR' messages")
            print(f"   Frame processing may have issues")
        
        print(f"\n" + "="*80)
        print(f"RECOMMENDATION")
        print(f"="*80)
        
        if frme_count > 0 and endf_count > 0 and fdne_count == 0 and emrf_count == 0:
            print(f"\n🎉 EXCELLENT! Your firmware is working correctly.")
            print(f"   You can now run the full frame viewer:")
            print(f"   ./ccd_frame_viewer.py")
        elif frme_count > 0:
            print(f"\n✅ GOOD! Correct markers detected.")
            print(f"   Some corruption present but firmware is updated.")
            print(f"   Try running the full frame viewer.")
        else:
            print(f"\n❌ PROBLEM: No correct markers detected.")
            print(f"   Please verify:")
            print(f"   1. You copied the corrected ccd_data_layer.h and .c files")
            print(f"   2. You rebuilt the firmware (clean build recommended)")
            print(f"   3. You flashed the new firmware to the STM32")
            print(f"   4. The device reset after flashing")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()