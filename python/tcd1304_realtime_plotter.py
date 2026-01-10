#!/usr/bin/env python3
"""
Real-time CCD Sensor Plotter
Displays live spectral data from the TCD1304 sensor with matplotlib
"""

import serial
import serial.tools.list_ports
import struct
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import sys

# Frame structure constants
CCD_PIXEL_COUNT = 3694
FRAME_START_MARKER = b'FRME'
FRAME_END_MARKER = b'ENDF'
FRAME_HEADER_SIZE = 8
FRAME_PIXEL_SIZE = CCD_PIXEL_COUNT * 2
FRAME_FOOTER_SIZE = 6
FRAME_TOTAL_SIZE = FRAME_HEADER_SIZE + FRAME_PIXEL_SIZE + FRAME_FOOTER_SIZE

class CCDRealtimePlotter:
    def __init__(self, serial_port, buffer_size=10):
        """
        Initialize the real-time plotter
        
        Args:
            serial_port: Serial port path (e.g., '/dev/cu.usbmodem...')
            buffer_size: Number of frames to average for smoother display
        """
        self.ser = serial.Serial(serial_port, 115200, timeout=0.1)
        self.buffer = b''
        self.buffer_size = buffer_size
        self.frame_history = deque(maxlen=buffer_size)
        
        # Current data
        self.current_spectrum = np.zeros(CCD_PIXEL_COUNT)
        self.pixel_indices = np.arange(CCD_PIXEL_COUNT)
        
        # Statistics
        self.frame_count = 0
        self.dropped_frames = 0
        
        # Setup the plot
        self.setup_plot()
        
    def setup_plot(self):
        """Setup the matplotlib figure and axes"""
        plt.style.use('dark_background')  # Dark theme looks cool for spectroscopy!
        
        self.fig, (self.ax_main, self.ax_stats) = plt.subplots(2, 1, 
                                                                 figsize=(14, 8),
                                                                 gridspec_kw={'height_ratios': [3, 1]})
        
        # Main spectrum plot
        self.line_spectrum, = self.ax_main.plot(self.pixel_indices, 
                                                  self.current_spectrum, 
                                                  color='cyan', 
                                                  linewidth=1.5,
                                                  label='Signal')
        
        # Mark dummy pixel regions
        self.ax_main.axvspan(0, 32, alpha=0.2, color='red', label='Dummy (Pre)')
        self.ax_main.axvspan(3680, 3694, alpha=0.2, color='red', label='Dummy (Post)')
        
        self.ax_main.set_xlim(0, CCD_PIXEL_COUNT)
        self.ax_main.set_ylim(0, 4095)  # 12-bit ADC range
        self.ax_main.set_xlabel('Pixel Index', fontsize=12)
        self.ax_main.set_ylabel('ADC Value (12-bit)', fontsize=12)
        self.ax_main.set_title('TCD1304 Real-Time Spectral Data', fontsize=14, fontweight='bold')
        self.ax_main.grid(True, alpha=0.3)
        self.ax_main.legend(loc='upper right')
        
        # Statistics plot (showing min/max/avg over time)
        self.stats_frames = deque(maxlen=100)
        self.stats_min = deque(maxlen=100)
        self.stats_max = deque(maxlen=100)
        self.stats_avg = deque(maxlen=100)
        
        self.line_min, = self.ax_stats.plot([], [], 'b-', linewidth=1, label='Min', alpha=0.7)
        self.line_max, = self.ax_stats.plot([], [], 'r-', linewidth=1, label='Max', alpha=0.7)
        self.line_avg, = self.ax_stats.plot([], [], 'g-', linewidth=1.5, label='Avg')
        
        self.ax_stats.set_xlim(0, 100)
        self.ax_stats.set_ylim(0, 4095)
        self.ax_stats.set_xlabel('Frame Number (last 100)', fontsize=10)
        self.ax_stats.set_ylabel('ADC Value', fontsize=10)
        self.ax_stats.set_title('Statistics Over Time', fontsize=11)
        self.ax_stats.grid(True, alpha=0.3)
        self.ax_stats.legend(loc='upper right')
        
        # Info text
        self.info_text = self.fig.text(0.02, 0.02, '', fontsize=10, 
                                        family='monospace',
                                        color='yellow')
        
        plt.tight_layout()
        
    def parse_frame(self, frame_bytes):
        """Parse a complete frame"""
        if len(frame_bytes) != FRAME_TOTAL_SIZE:
            return None
            
        # Check markers
        if frame_bytes[0:4] != FRAME_START_MARKER:
            return None
        if frame_bytes[FRAME_TOTAL_SIZE-6:FRAME_TOTAL_SIZE-2] != FRAME_END_MARKER:
            return None
        
        # Parse header
        frame_counter, pixel_count = struct.unpack('<HH', frame_bytes[4:8])
        
        if pixel_count != CCD_PIXEL_COUNT:
            return None
        
        # Parse pixel data
        pixel_data_bytes = frame_bytes[8:8+FRAME_PIXEL_SIZE]
        pixel_data = np.array(struct.unpack(f'<{CCD_PIXEL_COUNT}H', pixel_data_bytes))
        
        return pixel_data
    
    def read_frame(self):
        """Read and parse a frame from serial"""
        # Read available data
        data = self.ser.read(4096)
        if len(data) > 0:
            self.buffer += data
        
        # Look for frame
        while FRAME_START_MARKER in self.buffer:
            start_idx = self.buffer.find(FRAME_START_MARKER)
            
            # Check if we have enough data
            if len(self.buffer) >= start_idx + FRAME_TOTAL_SIZE:
                frame_bytes = self.buffer[start_idx:start_idx + FRAME_TOTAL_SIZE]
                
                # Parse frame
                pixel_data = self.parse_frame(frame_bytes)
                
                if pixel_data is not None:
                    self.frame_count += 1
                    
                    # Add to history for averaging
                    self.frame_history.append(pixel_data)
                    
                    # Update current spectrum (averaged over buffer)
                    if len(self.frame_history) > 0:
                        self.current_spectrum = np.mean(self.frame_history, axis=0)
                    
                    # Update statistics
                    self.stats_frames.append(self.frame_count)
                    self.stats_min.append(np.min(pixel_data))
                    self.stats_max.append(np.max(pixel_data))
                    self.stats_avg.append(np.mean(pixel_data))
                    
                    # Remove processed frame
                    self.buffer = self.buffer[start_idx + FRAME_TOTAL_SIZE:]
                    return True
                else:
                    self.dropped_frames += 1
                    self.buffer = self.buffer[start_idx + 4:]
            else:
                break
        
        # Keep buffer size reasonable
        if len(self.buffer) > 50000:
            self.buffer = self.buffer[-50000:]
        
        return False
    
    def update_plot(self, frame):
        """Animation update function"""
        # Read new frame
        self.read_frame()
        
        # Update main spectrum plot
        self.line_spectrum.set_ydata(self.current_spectrum)
        
        # Auto-scale y-axis with some padding
        if len(self.current_spectrum) > 0:
            ymin = max(0, np.min(self.current_spectrum) - 100)
            ymax = min(4095, np.max(self.current_spectrum) + 100)
            self.ax_main.set_ylim(ymin, ymax)
        
        # Update statistics plot
        if len(self.stats_frames) > 0:
            x_data = list(range(len(self.stats_frames)))
            self.line_min.set_data(x_data, list(self.stats_min))
            self.line_max.set_data(x_data, list(self.stats_max))
            self.line_avg.set_data(x_data, list(self.stats_avg))
            
            self.ax_stats.set_xlim(0, max(100, len(self.stats_frames)))
        
        # Update info text
        if self.frame_count > 0:
            dummy_pre = self.current_spectrum[0:32]
            signal = self.current_spectrum[32:-14]
            dummy_post = self.current_spectrum[-14:]
            
            info = (f"Frames: {self.frame_count:6d} | "
                   f"Dropped: {self.dropped_frames:4d} | "
                   f"FPS: ~{self.frame_count / max(1, self.frame_count * 0.02):.1f} | "
                   f"Signal Avg: {np.mean(signal):7.1f} | "
                   f"Dummy Avg: {np.mean(np.concatenate([dummy_pre, dummy_post])):7.1f}")
            self.info_text.set_text(info)
    
    def run(self):
        """Start the real-time plotting"""
        print("🚀 Starting real-time plotter...")
        print("📊 Close the plot window to stop")
        
        # Create animation (update every 50ms = ~20 FPS display)
        self.ani = FuncAnimation(self.fig, self.update_plot, 
                                interval=50, blit=False, cache_frame_data=False)
        
        plt.show()
        
        self.ser.close()
        print(f"\n✅ Stopped. Total frames: {self.frame_count}")

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
    print("=" * 80)
    print("TCD1304 REAL-TIME SPECTRAL PLOTTER")
    print("=" * 80)
    
    # Find port
    port = find_serial_port()
    if not port:
        port = input("\nEnter serial port manually: ").strip()
    
    if not port:
        print("❌ No port specified")
        return
    
    try:
        # Create plotter
        print(f"\n🔌 Connecting to {port}...")
        plotter = CCDRealtimePlotter(port, buffer_size=5)
        
        print("✅ Connected!")
        print("\n📈 Plot controls:")
        print("   - Close window to stop")
        print("   - Plot updates automatically")
        print("   - Averaging over last 5 frames for smoother display")
        print("")
        
        # Run the plotter
        plotter.run()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()