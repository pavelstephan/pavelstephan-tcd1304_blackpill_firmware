Working project to develop extensible base firmware for tcd1304 controlled with
an STM32F401CCU6 'blackpill' MCU and control board designed by https://curiousscientist.tech/blog/tcd1304-linear-ccd-driving-the-ccd (huge shoutout, I used this blog extensivly to figure out timing
and create the first iteration of the firmware).  Why this board?  Because its very cleverly designed, 
using Vref for both signal and power, and the form factor is just super slick.  Anything I could 
have made would be lesser.

Note, this archive is currently very messy, with mutiple readmes that will be ultimately consolidated, but for now they are not meant to be pretty or well organized, but rather function as working code notes for me to track various elements of the stack.  I am not a developer, and this works for me for now.

About the firmware and software architecture

A bunch of great, and some not so great, control firmware can be found for this sensor but
I decided to write from scratch so that I could get what I need from it, without any overhead
of stuff I don't.  The design principle is to do as much as possible in python on my 
mac, and keep the firmware lightweight but with instrument-grade robustness and precision.  The firmware and python control-ware architecture architecture is designed in discrete data, control, and command layers, and saved in discrete files, where appropriate (for reuse purposes).  The first two of those layers are all binary, end-to-end, and the the latter, the command layer (used by python to control 
sensor function/settings, etc) is ascii. Thus, although binary to python, the data is easily convertable to essentially instantly use-able ASCII, without the need for complex data re-assembly, pixel level parsing, framing, etc.  This is because the data is framed in the commms stack and outputted to python as a
full sensor read of all pixels, dummy and sensing, with clearly marked start, stop and checksum in ascii within the frame in firmware, always.  The output will never be a partial read and easily checksum confirmed.  Why output dummy pixels?  Becuase for one thing, I think its a clean approach, but more importantly they include valuable signal, although non-sensing.  Specifically, the dummy pixels, which bookend the sensing pixels on the surface of the sensor (D0-D31 on one side of sensing pixels, D32-D45)  carry charge, but are blind to light.  Thus they are useful to establish baseline electrical and environmental 'black noise', dynamically (as conditions change, sample-period specifically), when calibrating.

Put simply the comms stack and signal integrity/accuracy are central to the firmware/software design, and
its just more work to code both full feature CLI and python or GUI control code.  

In terms of sensor controls, There is really only so much that one needs to control with this sensor, especially if the framing is independent of sensor/MCU timers (the sensor output/ADC and ring buffers, for example, are all set to accomodate a 'worst case' scenario, and thus there are small RAM compromises - still way below the thresholds of the MCU - but once configured, which I think I have done quite respectably, you can set them and forget them, and handle the rest in control software.  Currently the code has a fixed integration time of 20us, which is essentially the mimimum for this hardware, but the next version will include user-definable control over int time, sensor start/stop (thus sample lenght), and if needed, perhaps later FPS or some additional knobs.  Gain is essentially a product of int time, 
nearly everything else needed for lab-grade spectrometry can be done in software.   

See Info file for some python scripts to test various elements of hw and firmware

See other readmes for blow-by-blow notes on details.  Let me know if you find this helpful or have 
suggestions.


Details:


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



Questions? Issues?

Frame too large? Check USB_TX_BUFFER_SIZE
Missing frames? Check frame counter gaps
Bad checksums? Verify endianness in Python
Wrong pixel count? Should always be 3694