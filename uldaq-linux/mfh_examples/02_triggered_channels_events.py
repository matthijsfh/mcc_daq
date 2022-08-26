from __future__ import print_function


import sys
sys.path.append('./datastorage')
import datastorage_class as ds
import matplotlib.pyplot as plt
import addcopyfighandler
import mplcursors
import numpy as np
from matplotlib.ticker import (MultipleLocator, AutoMinorLocator)

from time import sleep
from os import system

from sys import stdout
from collections import namedtuple
from uldaq import (get_daq_device_inventory, DaqDevice, AInScanFlag,
                   DaqEventType, ScanOption, InterfaceType, AiInputMode,
                   create_float_buffer, ULException, EventCallbackArgs, DaqInChanDescriptor)


def prepare_datastorage():
    #--------------------------------------------------------------------------
    # Create the datastorage
    #--------------------------------------------------------------------------
    DsData = ds.datastorage_class('datastorage')

    return DsData


def process_data(DsData, TraceData, TraceSettings):
    
    for j in range(TraceSettings.channel_count):

        TmpData  = create_float_buffer(1, TraceSettings.samples_per_channel)
        TimeData = create_float_buffer(1, TraceSettings.samples_per_channel)

        TraceNameTxt = "Trace{:1d}".format(j + TraceSettings.low_channel)  
        
        for i in range(TraceSettings.samples_per_channel):
            TmpData[i] = TraceData[i * TraceSettings.channel_count + j]
            TimeData[i] = i / TraceSettings.samplerate * 1000
        
        DsData.add_data(TraceNameTxt, TmpData)

        if (j == 0):
            DsData.add_data("Time", TimeData)
    
    
    plot_measurement(DsData, TraceSettings)
        
    return


def plot_measurement(DsData, TraceSettings):
    
    fig, axes = plt.subplots(1, 1)
    plt.minorticks_on()
    plt.tight_layout()

    for j in range(TraceSettings.channel_count):
        TraceNameTxt = "Trace{:1d}".format(j + TraceSettings.low_channel)
        label_trace  = "Channel {:d}".format(j + TraceSettings.low_channel)
    
        DsData.plot_data(axes, "Time", TraceNameTxt, color=21+j, points_only=False, label=label_trace,  title='', marker='', linewidth=1)
    
    axes.grid(visible=True)
    axes.set(ylabel='Voltage [V]', xlabel='Time [mSec]')
    axes.set_title(DsData.title)
    
    # Option to add datalabels
    mplcursors.cursor(axes, multiple=True)
    
    return fig, axes

def select_device_by_mac(mac):
    
    descriptor_index = -1;
    
    devices = get_daq_device_inventory(InterfaceType.ANY)
    number_of_devices = len(devices)
    
    if number_of_devices == 0:
        raise RuntimeError('Error: No DAQ devices found')

    print('Found', number_of_devices, 'DAQ device(s):')
    
    for i in range(number_of_devices):
        print('  [', i, '] ', devices[i].product_name, ' (',
              devices[i].unique_id, ')', sep='')
        
        if ( mac == devices[i].unique_id):
            print("Using device [{:d}]".format(i))
            descriptor_index = i

    if descriptor_index not in range(number_of_devices):
        raise RuntimeError('Error: Invalid descriptor index')

    # Create the DAQ device from the descriptor at the specified index.
    daq_device = DaqDevice(devices[descriptor_index])

    return daq_device


def main():
    
    """Analog input scan with events example."""
    global RATE
    daq_device = None
    ai_device = None
    ai_info = None
    range_index = 0

    #--------------------------------------------------------------------------
    # Measurement settings
    # available_sample_count = samples per data packet
    # larger number = low number of packets = low number of interrupts / events
    #--------------------------------------------------------------------------
    TraceSettings = namedtuple("MyStruct", "low_channel high_channel samples_per_channel samplerate available_sample_count channel_count")
    TraceSettings.low_channel                 = 0
    TraceSettings.high_channel                = 3
    TraceSettings.samples_per_channel         = 10000       # samples to take per channel
    TraceSettings.available_sample_count      = 10000       # amount of samples per data packet
    TraceSettings.samplerate                  = 5000        # sample rate
    TraceSettings.channel_count               = 0
    
    #--------------------------------------------------------------------------
    # Datastorage class to handle data & plotting    
    #--------------------------------------------------------------------------
    DsData = prepare_datastorage()
    DsData.title = "Measurement Data @ {:.0f} Hz".format(TraceSettings.samplerate)
    DsData.add_name("Time")
    
    for i in range(TraceSettings.high_channel - TraceSettings.low_channel + 1):
        TraceNameTxt = "Trace{:1d}".format(i + TraceSettings.low_channel)  
        print(TraceNameTxt)
        DsData.add_name(TraceNameTxt)
        

    #--------------------------------------------------------------------------
    #
    #--------------------------------------------------------------------------
    flags = AInScanFlag.DEFAULT
    event_types = (DaqEventType.ON_DATA_AVAILABLE
                   | DaqEventType.ON_END_OF_INPUT_SCAN
                   | DaqEventType.ON_INPUT_SCAN_ERROR)

    scan_params = namedtuple('scan_params', 'buffer high_chan low_chan descriptor status')

    #--------------------------------------------------------------------------
    # Main loop
    #--------------------------------------------------------------------------
    try:
        daq_device = select_device_by_mac("00:80:2F:34:9D:81")
    
        # Get the AiDevice object and verify that it is valid.
        ai_device = daq_device.get_ai_device()
        if ai_device is None:
            raise RuntimeError('Error: The DAQ device does not support analog input')
    
        # Verify the device supports hardware pacing for analog input.
        ai_info = ai_device.get_info()
        if not ai_info.has_pacer():
            raise RuntimeError('\nError: The specified DAQ device does not support hardware paced analog input')
    
        # Establish a connection to the DAQ device.
        descriptor = daq_device.get_descriptor()
        print('\nConnecting to', descriptor.dev_string, '- please wait...')
        # For Ethernet devices using a connection_code other than the default
        # value of zero, change the line below to enter the desired code.
        daq_device.connect(connection_code=0)
    
        # The default input mode is SINGLE_ENDED.
        input_mode = AiInputMode.SINGLE_ENDED
        # If SINGLE_ENDED input mode is not supported, set to DIFFERENTIAL.
        if ai_info.get_num_chans_by_mode(AiInputMode.SINGLE_ENDED) <= 0:
            input_mode = AiInputMode.DIFFERENTIAL
    
        # Get the number of channels and validate the high channel number.
        number_of_channels = ai_info.get_num_chans_by_mode(input_mode)
        
        if TraceSettings.high_channel >= number_of_channels:
            TraceSettings.high_channel = number_of_channels - 1
            
        TraceSettings.channel_count = TraceSettings.high_channel - TraceSettings.low_channel + 1
    
        # Get a list of supported ranges and validate the range index.
        ranges = ai_info.get_ranges(input_mode)
        if range_index >= len(ranges):
            range_index = len(ranges) - 1
    
    
        #--------------------------------------------------------------------------
        # Main loop
        #--------------------------------------------------------------------------
        # scan_options  = ScanOption.CONTINUOUS | ScanOption.EXTTRIGGER
        scan_options  = ScanOption.EXTTRIGGER | ScanOption.BLOCKIO
        trigger_types = ai_info.get_trigger_types()
        
        print(trigger_types)
        
        #--------------------------------------------------------------------------
        # E-1608: only external trigger seems to work
        # Triggering on analog signal values does NOT work.
        # Trigger types as listed below work.
        # [<TriggerType.POS_EDGE: 1>, <TriggerType.NEG_EDGE: 2>, <TriggerType.HIGH: 4>, <TriggerType.LOW: 8>]
        #--------------------------------------------------------------------------
        
        # Does not do anything. External trigger used.
        trigger_channel = 0
        ai_device.set_trigger(trigger_types[0], trigger_channel, 0.1, 0, 0)
        
       
        # Allocate a buffer to receive the data.
        TraceData = create_float_buffer(TraceSettings.channel_count, TraceSettings.samples_per_channel)
    
        # Store the user data for use in the callback function.
        scan_status = {'complete': False, 'error': False}
        user_data = scan_params(TraceData, TraceSettings.high_channel, TraceSettings.low_channel, descriptor, scan_status)
    
        # Enable the event to be notified every time 100 samples are available.
        
        daq_device.enable_event(event_types, TraceSettings.available_sample_count,
                                event_callback_function, user_data)
    
        print('\n', descriptor.dev_string, 'ready', sep='')
        print('    Function demonstrated: daq_device.enable_event()')
        print('    Channels: ', TraceSettings.low_channel, '-', TraceSettings.high_channel)
        print('    Input mode: ', input_mode.name)
        print('    Range: ', ranges[range_index].name)
        print('    Samples per channel: ', TraceSettings.samples_per_channel)
        print('    Rate: ', TraceSettings.samplerate, 'Hz')
        print('    Scan options:', display_scan_options(scan_options))
    
        # system('clear')
    
        # Start the finite acquisition.
        TraceSettings.samplerate = ai_device.a_in_scan(TraceSettings.low_channel, TraceSettings.high_channel, input_mode,
                                   ranges[range_index], TraceSettings.samples_per_channel,
                                   TraceSettings.samplerate, scan_options, flags, TraceData)
    
        # Wait here until the scan is done ... events will be handled in the
        # event handler (eventCallbackFunction).
        # The scan_status values are set in the event handler callback.
        while not scan_status['complete'] and not scan_status['error']:
            sleep(0.1)

    except KeyboardInterrupt:
        pass
    except (ValueError, NameError, SyntaxError):
        pass
    except RuntimeError as error:
        print('\n', error)
    finally:
        process_data(DsData, TraceData, TraceSettings)
    
        if daq_device:
            if daq_device.is_connected():
                # Stop the acquisition if it is still running.
                if ai_device and ai_info and ai_info.has_pacer():
                    ai_device.scan_stop()
                daq_device.disable_event(event_types)
                daq_device.disconnect()
            daq_device.release()


def event_callback_function(event_callback_args):
    # type: (EventCallbackArgs) -> None
    """
    The callback function called in response to an event condition.

    Args:
        event_callback_args: Named tuple :class:`EventCallbackArgs` used to pass
            parameters to the user defined event callback function
            :class`DaqEventCallback`.
            The named tuple contains the following members
            event_type - the condition that triggered the event
            event_data - additional data that specifies an event condition
            user_data - user specified data
    """

    event_type = DaqEventType(event_callback_args.event_type)
    event_data = event_callback_args.event_data
    user_data  = event_callback_args.user_data

    if (event_type == DaqEventType.ON_DATA_AVAILABLE
            or event_type == DaqEventType.ON_END_OF_INPUT_SCAN):
        reset_cursor()
        print('Active DAQ device: ',
              user_data.descriptor.dev_string, ' (',
              user_data.descriptor.unique_id, ')\n', sep='')
        clear_eol()
        print('eventType: ', event_type.name)

        chan_count = user_data.high_chan - user_data.low_chan + 1
        scan_count = event_data
        total_samples = scan_count * chan_count

        clear_eol()
        print('eventData: ', event_data, '\n')
        # print('actual scan rate = ', '{:.6f}'.format(RATE), 'Hz\n')

        # Using the remainder after dividing by the buffer length handles wrap
        # around conditions if the example is changed to a CONTINUOUS scan.
        index = (total_samples - chan_count) % user_data.buffer._length_
        # clear_eol()
        # print('currentIndex = ', index, '\n')

        # for i in range(chan_count):
        #     clear_eol()
        #     print('chan =',
        #           i + user_data.low_chan,
        #           '{:10.6f}'.format(user_data.buffer[index + i]))

    if event_type == DaqEventType.ON_INPUT_SCAN_ERROR:
        exception = ULException(event_data)
        print(exception)
        user_data.status['error'] = True

    if event_type == DaqEventType.ON_END_OF_INPUT_SCAN:
        print('\nThe scan is complete\n')
        user_data.status['complete'] = True


def display_scan_options(bit_mask):
    """Create a displays string for all scan options."""
    options = []
    if bit_mask == ScanOption.DEFAULTIO:
        options.append(ScanOption.DEFAULTIO.name)
    for option in ScanOption:
        if option & bit_mask:
            options.append(option.name)
    return ', '.join(options)


def reset_cursor():
    """Reset the cursor in the terminal window."""
    stdout.write('\033[1;1H')


def clear_eol():
    """Clear all characters to the end of the line."""
    stdout.write('\x1b[2K')


if __name__ == '__main__':
    main()
