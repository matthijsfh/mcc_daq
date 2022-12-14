"""
File:                       ULAI13.py

Library Call Demonstrated:  mcculw.ul.a_in_scan(), sampling mode options.

Purpose:                    Scans a range of A/D Input Channels and stores
                            the sample data in an array using a user
                            specified sampling mode.

Demonstration:              Displays the analog input on 8 channels.

Other Library Calls:        mcculw.ul.win_buf_alloc()
                                or mcculw.ul.win_buf_alloc_32()
                            mcculw.ul.win_buf_free()
                            mcculw.to_eng_units()
                                or mcculw.ul.to_eng_units_32()

Special Requirements:       Device must have an A/D converter.
                            Analog signals on two input channels.
                            Board must support the mode selected.
"""
from __future__ import absolute_import, division, print_function
from builtins import *  # @UnusedWildImport

import tkinter as tk
from tkinter import messagebox, StringVar
from ctypes import cast, POINTER, c_ushort, c_ulong

from mcculw import ul
from mcculw.enums import ScanOptions
from mcculw.ul import ULError
from mcculw.device_info import DaqDeviceInfo

try:
    from ui_examples_util import UIExample, show_ul_error
except ImportError:
    from .ui_examples_util import UIExample, show_ul_error


class ULAI13(UIExample):
    def __init__(self, master=None):
        super(ULAI13, self).__init__(master)
        # By default, the example detects all available devices and selects the
        # first device listed.
        # If use_device_detection is set to False, the board_num property needs
        # to match the desired board number configured with Instacal.
        use_device_detection = True
        self.board_num = 0

        try:
            if use_device_detection:
                self.configure_first_detected_device()

            self.device_info = DaqDeviceInfo(self.board_num)
            self.ai_info = self.device_info.get_ai_info()
            if self.ai_info.is_supported and self.ai_info.supports_scan:
                self.create_widgets()
            else:
                self.create_unsupported_widgets()
        except ULError:
            self.create_unsupported_widgets(True)

    def start_scan(self):
        low_chan = self.get_low_channel_num()
        high_chan = self.get_high_channel_num()

        if low_chan > high_chan:
            messagebox.showerror(
                "Error",
                "Low Channel Number must be greater than or equal to High "
                "Channel Number")
            self.start_button["state"] = tk.NORMAL
            return

        rate = 100
        points_per_channel = 10
        num_channels = high_chan - low_chan + 1
        total_count = points_per_channel * num_channels
        scan_options = self.get_scan_options()

        range_ = self.ai_info.supported_ranges[0]

        # Allocate a buffer for the scan
        if self.ai_info.resolution <= 16:
            # Use the win_buf_alloc method for devices with a resolution <=
            # 16
            memhandle = ul.win_buf_alloc(total_count)
        else:
            # Use the win_buf_alloc_32 method for devices with a resolution
            # > 16
            memhandle = ul.win_buf_alloc_32(total_count)

        # Check if the buffer was successfully allocated
        if not memhandle:
            messagebox.showerror("Error", "Failed to allocate memory")
            self.start_button["state"] = tk.NORMAL
            return

        try:
            # Run the scan
            ul.a_in_scan(self.board_num, low_chan, high_chan, total_count,
                         rate, range_, memhandle, scan_options)

            # Convert the memhandle to a ctypes array
            # Note: the ctypes array will only be valid until win_buf_free
            # is called.
            # A copy of the buffer can be created using win_buf_to_array
            # or win_buf_to_array_32 before the memory is freed. The copy
            # can be used at any time.
            if self.ai_info.resolution <= 16:
                # Use the memhandle_as_ctypes_array method for devices with
                # a resolution <= 16
                array = cast(memhandle, POINTER(c_ushort))
            else:
                # Use the memhandle_as_ctypes_array_32 method for devices
                # with a resolution > 16
                array = cast(memhandle, POINTER(c_ulong))

            # Display the values
            self.display_values(array, range_, total_count, low_chan, high_chan)
        except ULError as e:
            show_ul_error(e)
        finally:
            # Free the allocated memory
            ul.win_buf_free(memhandle)
            self.start_button["state"] = tk.NORMAL

    def display_values(self, array, range_, total_count, low_chan, high_chan):
        new_data_frame = tk.Frame(self.results_group)

        channel_text = []

        # Add the headers
        for chan_num in range(low_chan, high_chan + 1):
            channel_text.append("Channel " + str(chan_num) + "\n")

        chan_count = high_chan - low_chan + 1

        # Add (up to) the first 10 values for each channel to the text
        chan_num = low_chan
        for data_index in range(0, min(chan_count * 10, total_count)):
            if self.ai_info.resolution <= 16:
                eng_value = ul.to_eng_units(self.board_num, range_,
                                            array[data_index])
            else:
                eng_value = ul.to_eng_units_32(self.board_num, range_,
                                               array[data_index])
            channel_text[chan_num - low_chan] += ('{:.3f}'.format(eng_value)
                                                  + "\n")
            chan_num = low_chan if chan_num == high_chan else chan_num + 1

        # Add the labels for each channel
        for chan_num in range(low_chan, high_chan + 1):
            chan_label = tk.Label(new_data_frame, justify=tk.LEFT, padx=3)
            chan_label["text"] = channel_text[chan_num - low_chan]
            chan_label.grid(row=0, column=chan_num - low_chan)

        self.data_frame.destroy()
        self.data_frame = new_data_frame
        self.data_frame.grid()

    def start(self):
        self.start_button["state"] = tk.DISABLED
        self.start_scan()

    def get_low_channel_num(self):
        if self.ai_info.num_chans == 1:
            return 0
        try:
            return int(self.low_channel_entry.get())
        except ValueError:
            return 0

    def get_high_channel_num(self):
        if self.ai_info.num_chans == 1:
            return 0
        try:
            return int(self.high_channel_entry.get())
        except ValueError:
            return 0

    def get_scan_options(self):
        mode_value = self.mode_var.get()

        if mode_value == "singleio":
            return ScanOptions.SINGLEIO
        elif mode_value == "dmaio":
            return ScanOptions.DMAIO
        elif mode_value == "blockio":
            return ScanOptions.BLOCKIO
        else:
            return 0

    def validate_channel_entry(self, p):
        if p == '':
            return True
        try:
            value = int(p)
            if value < 0 or value > self.ai_info.num_chans - 1:
                return False
        except ValueError:
            return False

        return True

    def create_widgets(self):
        '''Create the tkinter UI'''
        self.device_label = tk.Label(self)
        self.device_label.pack(fill=tk.NONE, anchor=tk.NW)
        self.device_label["text"] = ('Board Number ' + str(self.board_num)
                                     + ": " + self.device_info.product_name
                                     + " (" + self.device_info.unique_id + ")")

        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.X, anchor=tk.NW)

        curr_row = 0
        if self.ai_info.num_chans > 1:
            channel_vcmd = self.register(self.validate_channel_entry)

            low_channel_entry_label = tk.Label(main_frame)
            low_channel_entry_label["text"] = "Low Channel Number:"
            low_channel_entry_label.grid(
                row=curr_row, column=0, sticky=tk.W)

            self.low_channel_entry = tk.Spinbox(
                main_frame, from_=0,
                to=max(self.ai_info.num_chans - 1, 0),
                validate='key', validatecommand=(channel_vcmd, '%P'))
            self.low_channel_entry.grid(
                row=curr_row, column=1, sticky=tk.W)

            curr_row += 1
            high_channel_entry_label = tk.Label(main_frame)
            high_channel_entry_label["text"] = "High Channel Number:"
            high_channel_entry_label.grid(
                row=curr_row, column=0, sticky=tk.W)

            self.high_channel_entry = tk.Spinbox(
                main_frame, from_=0, validate='key',
                to=max(self.ai_info.num_chans - 1, 0),
                validatecommand=(channel_vcmd, '%P'))
            self.high_channel_entry.grid(
                row=curr_row, column=1, sticky=tk.W)
            initial_value = min(self.ai_info.num_chans - 1, 3)
            self.high_channel_entry.delete(0, tk.END)
            self.high_channel_entry.insert(0, str(initial_value))

            curr_row += 1

        mode_group = tk.LabelFrame(self, text="Mode", padx=3, pady=3)
        mode_group.pack(anchor=tk.W, padx=3, pady=3)

        self.mode_var = StringVar(value="default")
        radio_button_options = [
            ("Default", "default"),
            ("Single IO", "singleio"),
            ("DMA IO", "dmaio"),
            ("Block IO", "blockio"),
        ]

        for text, value in radio_button_options:
            rb = tk.Radiobutton(
                mode_group, text=text, variable=self.mode_var,
                value=value, borderwidth=0)
            rb.pack(anchor=tk.NW, padx=3, pady=0)

        self.results_group = tk.LabelFrame(
            self, text="Results", padx=3, pady=3)
        self.results_group.pack(fill=tk.X, anchor=tk.NW, padx=3, pady=3)

        self.data_frame = tk.Frame(self.results_group)
        self.data_frame.grid()

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
    ULAI13(master=tk.Tk()).mainloop()
