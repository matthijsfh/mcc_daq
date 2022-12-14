"""
File:                       ULAI06.py

Library Call Demonstrated:  mcculw.ul.a_in_scan(), continuous background mode

Purpose:                    Scans a range of A/D Input Channels continuously
                            in the background and stores the data in an array.

Demonstration:              Continuously collects data on up to eight channels.

Other Library Calls:        mcculw.ul.win_buf_alloc()
                                or mcculw.ul.win_buf_alloc_32
                            mcculw.ul.win_buf_free()
                            mcculw.ul.to_eng_units()
                                or mcculw.ul.to_eng_units_32()
                            mcculw.ul.get_status()
                            mcculw.ul.stop_background()

Special Requirements:       Device must have an A/D converter.
                            Analog signals on up to eight input channels.
"""
from __future__ import absolute_import, division, print_function
from builtins import *  # @UnusedWildImport

import tkinter as tk
from tkinter import messagebox
from ctypes import cast, POINTER, c_ushort, c_ulong

from mcculw import ul
from mcculw.enums import ScanOptions, Status, FunctionType
from mcculw.ul import ULError
from mcculw.device_info import DaqDeviceInfo

try:
    from ui_examples_util import UIExample, show_ul_error
except ImportError:
    from .ui_examples_util import UIExample, show_ul_error


class ULAI06(UIExample):
    def __init__(self, master=None):
        super(ULAI06, self).__init__(master)
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
            if self.ai_info.is_supported:
                self.create_widgets()
            else:
                self.create_unsupported_widgets()
        except ULError:
            self.create_unsupported_widgets(True)

    def start_scan(self):
        self.low_chan = self.get_low_channel_num()
        self.high_chan = self.get_high_channel_num()
        self.num_chans = self.high_chan - self.low_chan + 1

        if self.low_chan > self.high_chan:
            messagebox.showerror(
                "Error",
                "Low Channel Number must be greater than or equal to High "
                "Channel Number")
            self.set_ui_idle_state()
            return

        rate = 100
        points_per_channel = 1000

        # Some hardware requires that the total_count is an integer multiple
        # of the packet size. For this case, calculate a points_per_channel
        # that is equal to or just above the points_per_channel selected
        # which matches that requirement.
        if self.ai_info.packet_size != 1:
            packet_size = self.ai_info.packet_size
            remainder = points_per_channel % packet_size
            if remainder != 0:
                points_per_channel += packet_size - remainder

        total_count = points_per_channel * self.num_chans
        ai_range = self.ai_info.supported_ranges[0]
        scan_options = ScanOptions.BACKGROUND | ScanOptions.CONTINUOUS

        # Allocate a buffer for the scan
        if self.ai_info.resolution <= 16:
            # Use the win_buf_alloc method for devices with a resolution <=
            # 16
            self.memhandle = ul.win_buf_alloc(total_count)
        else:
            # Use the win_buf_alloc_32 method for devices with a resolution
            # > 16
            self.memhandle = ul.win_buf_alloc_32(total_count)

        if not self.memhandle:
            messagebox.showerror("Error", "Failed to allocate memory")
            self.set_ui_idle_state()
            return

        # Create the frames that will hold the data
        self.recreate_data_frame()

        try:
            # Run the scan
            ul.a_in_scan(self.board_num, self.low_chan, self.high_chan,
                         total_count, rate, ai_range, self.memhandle,
                         scan_options)
        except ULError as e:
            show_ul_error(e)
            self.set_ui_idle_state()
            return

        # Convert the memhandle to a ctypes array
        # Note: the ctypes array will no longer be valid after win_buf_free
        # is called.
        # A copy of the buffer can be created using win_buf_to_array
        # or win_buf_to_array_32 before the memory is freed. The copy can
        # be used at any time.
        if self.ai_info.resolution <= 16:
            # Use the memhandle_as_ctypes_array method for devices with a
            # resolution <= 16
            self.ctypes_array = cast(self.memhandle, POINTER(c_ushort))
        else:
            # Use the memhandle_as_ctypes_array_32 method for devices with a
            # resolution > 16
            self.ctypes_array = cast(self.memhandle, POINTER(c_ulong))

        # Start updating the displayed values
        self.update_displayed_values(ai_range)

    def update_displayed_values(self, ai_range):
        # Get the status from the device
        status, curr_count, curr_index = ul.get_status(self.board_num,
                                                       FunctionType.AIFUNCTION)

        # Display the status info
        self.update_status_labels(status, curr_count, curr_index)

        # Display the values
        self.display_values(ai_range, curr_index, curr_count)

        # Call this method again until the stop button is pressed
        if status == Status.RUNNING:
            self.after(100, self.update_displayed_values, ai_range)
        else:
            # Free the allocated memory
            ul.win_buf_free(self.memhandle)
            self.set_ui_idle_state()

    def update_status_labels(self, status, curr_count, curr_index):
        if status == Status.IDLE:
            self.status_label["text"] = "Idle"
        else:
            self.status_label["text"] = "Running"

        self.index_label["text"] = str(curr_index)
        self.count_label["text"] = str(curr_count)

    def display_values(self, range_, curr_index, curr_count):
        per_channel_display_count = 10
        array = self.ctypes_array
        low_chan = self.low_chan
        high_chan = self.high_chan
        channel_text = []

        # Add the headers
        for chan_num in range(low_chan, high_chan + 1):
            channel_text.append("Channel " + str(chan_num) + "\n")

        # If no data has been gathered, don't add data to the labels
        if curr_count > 1:
            chan_count = high_chan - low_chan + 1

            chan_num = low_chan
            # curr_index points to the start of the last completed channel
            # scan that was transferred between the board and the data
            #  buffer. Based on this, calculate the first index we want to
            # display using subtraction.
            first_index = max(
                curr_index - ((per_channel_display_count - 1) * chan_count),
                0)
            # Add (up to) the latest 10 values for each channel to the text
            for data_index in range(
                    first_index,
                    first_index + min(
                        chan_count * per_channel_display_count,
                        curr_count)):
                if self.ai_info.resolution <= 16:
                    eng_value = ul.to_eng_units(
                        self.board_num, range_, array[data_index])
                else:
                    eng_value = ul.to_eng_units_32(
                        self.board_num, range_, array[data_index])
                channel_text[chan_num -
                             low_chan] += '{:.3f}'.format(eng_value) + "\n"
                if chan_num == high_chan:
                    chan_num = low_chan
                else:
                    chan_num += 1

        # Update the labels for each channel
        for chan_num in range(low_chan, high_chan + 1):
            chan_index = chan_num - low_chan
            self.chan_labels[chan_index]["text"] = channel_text[chan_index]

    def recreate_data_frame(self):
        low_chan = self.low_chan
        high_chan = self.high_chan

        new_data_frame = tk.Frame(self.inner_data_frame)

        self.chan_labels = []
        # Add the labels for each channel
        for chan_num in range(low_chan, high_chan + 1):
            chan_label = tk.Label(new_data_frame, justify=tk.LEFT, padx=3)
            chan_label.grid(row=0, column=chan_num - low_chan)
            self.chan_labels.append(chan_label)

        self.data_frame.destroy()
        self.data_frame = new_data_frame
        self.data_frame.grid()

    def stop(self):
        ul.stop_background(self.board_num, FunctionType.AIFUNCTION)

    def set_ui_idle_state(self):
        self.high_channel_entry["state"] = tk.NORMAL
        self.low_channel_entry["state"] = tk.NORMAL
        self.start_button["command"] = self.start
        self.start_button["text"] = "Start"

    def start(self):
        self.high_channel_entry["state"] = tk.DISABLED
        self.low_channel_entry["state"] = tk.DISABLED
        self.start_button["command"] = self.stop
        self.start_button["text"] = "Stop"
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

        self.results_group = tk.LabelFrame(
            self, text="Results", padx=3, pady=3)
        self.results_group.pack(fill=tk.X, anchor=tk.NW, padx=3, pady=3)

        self.results_group.grid_columnconfigure(1, weight=1)

        curr_row = 0
        status_left_label = tk.Label(self.results_group)
        status_left_label["text"] = "Status:"
        status_left_label.grid(row=curr_row, column=0, sticky=tk.W)

        self.status_label = tk.Label(self.results_group)
        self.status_label["text"] = "Idle"
        self.status_label.grid(row=curr_row, column=1, sticky=tk.W)

        curr_row += 1
        index_left_label = tk.Label(self.results_group)
        index_left_label["text"] = "Index:"
        index_left_label.grid(row=curr_row, column=0, sticky=tk.W)

        self.index_label = tk.Label(self.results_group)
        self.index_label["text"] = "-1"
        self.index_label.grid(row=curr_row, column=1, sticky=tk.W)

        curr_row += 1
        count_left_label = tk.Label(self.results_group)
        count_left_label["text"] = "Count:"
        count_left_label.grid(row=curr_row, column=0, sticky=tk.W)

        self.count_label = tk.Label(self.results_group)
        self.count_label["text"] = "0"
        self.count_label.grid(row=curr_row, column=1, sticky=tk.W)

        curr_row += 1
        self.inner_data_frame = tk.Frame(self.results_group)
        self.inner_data_frame.grid(
            row=curr_row, column=0, columnspan=2, sticky=tk.W)

        self.data_frame = tk.Frame(self.inner_data_frame)
        self.data_frame.grid()

        button_frame = tk.Frame(self)
        button_frame.pack(fill=tk.X, side=tk.RIGHT, anchor=tk.SE)

        self.start_button = tk.Button(button_frame)
        self.start_button["text"] = "Start"
        self.start_button["command"] = self.start
        self.start_button.grid(row=0, column=0, padx=3, pady=3)

        self.quit_button = tk.Button(button_frame)
        self.quit_button["text"] = "Quit"
        self.quit_button["command"] = self.master.destroy
        self.quit_button.grid(row=0, column=1, padx=3, pady=3)


if __name__ == "__main__":
    # Start the example
    ULAI06(master=tk.Tk()).mainloop()
