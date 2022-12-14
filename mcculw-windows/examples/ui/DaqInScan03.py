"""
File:                       DaqInScan03.py

Library Call Demonstrated:  mcculw.ul.daq_in_scan()
                            mcculw.ul.get_tc_values()

Purpose:                    Synchronously scans Analog channels, Digital ports,
                            and Thermocouple channels in the foreground.

Demonstration:              Collects data on Analog Channels 5, FirstPortA,
                            CJCs 0, 1 and Thermocouple channels 0, 1.

Other Library Calls:        mcculw.ul.win_buf_alloc()
                            mcculw.ul.win_buf_free()
                            mcculw.ul.d_config_port()
                            mcculw.ul.c_config_scan()

Special Requirements:       Device must support mcculw.ul.daq_in_scan() and
                            temperature inputs.
                            Thermocouples must be wired to temperature channels
                            selected.
"""
from __future__ import absolute_import, division, print_function
from builtins import *  # @UnusedWildImport

import tkinter as tk
from tkinter import messagebox
from enum import Enum
from ctypes import cast, POINTER, c_ushort

from mcculw import ul
from mcculw.enums import (DigitalPortType, ChannelType, ULRange, CounterMode,
                          CounterDebounceTime, CounterEdgeDetection,
                          DigitalIODirection, TempScale, ErrorCode,
                          CounterTickSize)
from mcculw.ul import ULError
from mcculw.device_info import DaqDeviceInfo

try:
    from ui_examples_util import UIExample, show_ul_error
except ImportError:
    from .ui_examples_util import UIExample, show_ul_error


class DaqInScan03(UIExample):
    def __init__(self, master=None):
        super(DaqInScan03, self).__init__(master)
        # By default, the example detects all available devices and selects the
        # first device listed.
        # If use_device_detection is set to False, the board_num property needs
        # to match the desired board number configured with Instacal.
        use_device_detection = True
        self.board_num = 0

        self.num_chans = 6
        self.chan_list = []
        self.chan_type_list = []
        self.gain_list = []

        try:
            if use_device_detection:
                self.configure_first_detected_device()

            self.device_info = DaqDeviceInfo(self.board_num)
            if (self.device_info.supports_daq_input
                    and self.device_info.supports_temp_input):
                self.init_scan_channel_info()
                self.create_widgets()
            else:
                self.create_unsupported_widgets()
        except ULError:
            self.create_unsupported_widgets(True)

    def init_scan_channel_info(self):
        # For accurate thermocouple readings, the CJC channels and TC channels
        # must be associated properly. The TC channels must immediately follow
        # their associated CJCs in the channel list. Other channel types may be
        # placed in the channel list as long as they do not fall between a CJC
        # channel and its associated thermocouple channel.

        # Add an analog input channel
        self.chan_list.append(4)
        self.chan_type_list.append(ChannelType.ANALOG)
        self.gain_list.append(ULRange.BIP10VOLTS)

        # Add a digital input channel
        self.chan_list.append(DigitalPortType.FIRSTPORTA)
        self.chan_type_list.append(ChannelType.DIGITAL8)
        self.gain_list.append(ULRange.NOTUSED)

        # Add a CJC channel
        self.chan_list.append(0)
        self.chan_type_list.append(ChannelType.CJC)
        self.gain_list.append(ULRange.NOTUSED)

        # Add a TC channel
        self.chan_list.append(0)
        self.chan_type_list.append(ChannelType.TC)
        self.gain_list.append(ULRange.NOTUSED)

        # Add a CJC channel
        self.chan_list.append(1)
        self.chan_type_list.append(ChannelType.CJC)
        self.gain_list.append(ULRange.NOTUSED)

        # Add a TC channel
        self.chan_list.append(1)
        self.chan_type_list.append(ChannelType.TC)
        self.gain_list.append(ULRange.NOTUSED)

    def start_scan(self):
        rate = 100
        points_per_channel = 10
        total_count = points_per_channel * self.num_chans

        # Allocate a buffer for the scan
        memhandle = ul.win_buf_alloc(total_count)

        # Check if the buffer was successfully allocated
        if not memhandle:
            messagebox.showerror("Error", "Failed to allocate memory")
            self.start_button["state"] = tk.NORMAL
            return

        try:
            # Configure the digital port for input
            ul.d_config_port(self.board_num, DigitalPortType.FIRSTPORTA,
                             DigitalIODirection.IN)

            # Configure the counter channel
            ul.c_config_scan(self.board_num, 0, CounterMode.STOP_AT_MAX,
                             CounterDebounceTime.DEBOUNCE_NONE, 0,
                             CounterEdgeDetection.RISING_EDGE,
                             CounterTickSize.TICK20PT83ns, 0)

            # Run the scan
            ul.daq_in_scan(self.board_num, self.chan_list, self.chan_type_list,
                           self.gain_list, self.num_chans, rate, 0, total_count,
                           memhandle, 0)

            # Convert the TC values (optional parameter omitted)
            err, temp_data_array = ul.get_tc_values(
                self.board_num, self.chan_list, self.chan_type_list,
                self.num_chans, memhandle, 0, points_per_channel,
                TempScale.CELSIUS)

            if err == ErrorCode.OUTOFRANGE:
                messagebox.showwarning("Warning",
                                       "Temperature data is out of range")

            # Cast the memhandle to a ctypes pointer
            # Note: the ctypes array will only be valid until win_buf_free
            # is called.
            array = cast(memhandle, POINTER(c_ushort))

            # Display the values
            self.display_values(array, temp_data_array, total_count)
        except ULError as e:
            show_ul_error(e)
        finally:
            # Free the allocated memory
            ul.win_buf_free(memhandle)
            self.start_button["state"] = tk.NORMAL

    def display_values(self, array, temp_data_array, total_count):
        channel_text = {}

        # Add a string to the dictionary for each channel (excluding CJC
        # channels)
        for chan_num in range(0, self.num_chans):
            if self.chan_type_list[chan_num] != ChannelType.CJC:
                channel_text[chan_num] = ""

        # Add (up to) the first 10 values for each channel to the text
        # (excluding CJC channels)
        chan_num = 0
        temp_array_index = 0
        for data_index in range(0, min(self.num_chans * 10, total_count)):
            if self.chan_type_list[chan_num] != ChannelType.CJC:
                if self.chan_type_list[chan_num] == ChannelType.TC:
                    channel_text[chan_num] += str(
                        round(temp_data_array[temp_array_index], 3)) + "\n"
                    temp_array_index += 1
                else:
                    channel_text[chan_num] += str(array[data_index]) + "\n"
            if chan_num == self.num_chans - 1:
                chan_num = 0
            else:
                chan_num += 1

        # Update the labels for each channel
        for chan_num in channel_text:
            self.data_labels[chan_num]["text"] = channel_text[chan_num]

    def start(self):
        self.start_button["state"] = tk.DISABLED
        self.start_scan()

    def create_widgets(self):
        '''Create the tkinter UI'''
        self.device_label = tk.Label(self)
        self.device_label.pack(fill=tk.NONE, anchor=tk.NW)
        self.device_label["text"] = ('Board Number ' + str(self.board_num)
                                     + ": " + self.device_info.product_name
                                     + " (" + self.device_info.unique_id + ")")

        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.X, anchor=tk.NW)

        self.results_group = tk.LabelFrame(
            self, text="Results", padx=3, pady=3)
        self.results_group.pack(fill=tk.X, anchor=tk.NW, padx=3, pady=3)

        self.data_frame = tk.Frame(self.results_group)
        self.data_frame.grid()

        chan_header_label = tk.Label(
            self.data_frame, justify=tk.LEFT, padx=3)
        chan_header_label["text"] = "Channel:"
        chan_header_label.grid(row=0, column=0)

        type_header_label = tk.Label(
            self.data_frame, justify=tk.LEFT, padx=3)
        type_header_label["text"] = "Type:"
        type_header_label.grid(row=1, column=0)

        range_header_label = tk.Label(
            self.data_frame, justify=tk.LEFT, padx=3)
        range_header_label["text"] = "Range:"
        range_header_label.grid(row=2, column=0)

        self.data_labels = {}
        column = 0
        for chan_num in range(0, self.num_chans):
            # Don't display the CJC channels
            if self.chan_type_list[chan_num] != ChannelType.CJC:
                chan_label = tk.Label(
                    self.data_frame, justify=tk.LEFT, padx=3)
                chan_num_item = self.chan_list[chan_num]
                if isinstance(chan_num_item, Enum):
                    chan_label["text"] = self.chan_list[chan_num].name
                else:
                    chan_label["text"] = str(self.chan_list[chan_num])
                chan_label.grid(row=0, column=column)

                type_label = tk.Label(
                    self.data_frame, justify=tk.LEFT, padx=3)
                type_label["text"] = self.chan_type_list[chan_num].name
                type_label.grid(row=1, column=column)

                range_label = tk.Label(
                    self.data_frame, justify=tk.LEFT, padx=3)
                range_label["text"] = self.gain_list[chan_num].name
                range_label.grid(row=2, column=column)

                data_label = tk.Label(
                    self.data_frame, justify=tk.LEFT, padx=3)
                data_label.grid(row=3, column=column)
                self.data_labels[chan_num] = data_label

                column += 1

        button_frame = tk.Frame(self)
        button_frame.pack(fill=tk.X, side=tk.RIGHT, anchor=tk.SE)

        self.start_button = tk.Button(button_frame)
        self.start_button["text"] = "Start"
        self.start_button["command"] = self.start
        self.start_button.grid(row=0, column=0, padx=3, pady=3)

        quit_button = tk.Button(button_frame)
        quit_button["text"] = "Quit"
        quit_button["command"] = self.master.destroy
        quit_button.grid(row=0, column=1, padx=3, pady=3)


if __name__ == "__main__":
    # Start the example
    DaqInScan03(master=tk.Tk()).mainloop()
