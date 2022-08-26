import numpy as np
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib

import pickle
import json


class datastorage_class:
    name_list = {}
    title = []

    def __init__(self, name):
        self.name = name
        return

    def add_title(self, in_title):
        self.title = in_title

    def add_name(self, in_name, debug=0):
        # self.name_list.append(in_name)
        self.name_list[in_name] = []

        return

    def add_data(self, in_name, in_data, debug = 0):
        old_data = self.name_list[in_name]
        new_data = np.append(old_data, in_data)
        self.name_list[in_name] = new_data

        return

    def add_array(self, in_name, in_data, debug = 0):
        self.name_list[in_name] = in_data

        return
    
    def get_data(self, in_name):
        return self.name_list[in_name]

    def plot_data_no_x(self, ax, in_name, color=1, points_only=False, label='', title='', marker='', linewidth=1):
        values = self.name_list[in_name]
        fake_x = np.arange(0, values.size)

        if (points_only):
            self.plot_points(ax, fake_x, values, color=color, label=label, title=title, marker=marker, linewidth=linewidth)
        else:
            self.plot_results(ax, fake_x, values, color=color, label=label, title=title, marker=marker, linewidth=linewidth)
        
        ax.legend()
        ax.set(title=title)
        ax.grid(True)
        return

    def plot_data(self, ax, in_name_x, in_name_y, color=1, points_only=False, label='', title='', marker='', linewidth=1, x_offset=0):
        values_x = self.name_list[in_name_x] + x_offset
        values_y = self.name_list[in_name_y]

        if (points_only):
            self.plot_points(ax, values_x, values_y, color=color, label=label, title=title, marker=marker, linewidth=linewidth)
        else:
            self.plot_results(ax, values_x, values_y, color=color, label=label, title=title, marker=marker, linewidth=linewidth)

        ax.legend()
        ax.set(title=title)
        ax.grid(True)
        return

    # =================================================================================
    def plot_results(self, ax, time, value, color=1, label='', title='', marker='', linewidth=1):
        colors = dict(mcolors.CSS4_COLORS, **mcolors.CSS4_COLORS)
        dict_val = list(colors.values())[color]
        ax.plot(time, value, label=label, color=dict_val, marker=marker, linewidth=linewidth)
        ax.legend()
        ax.grid(True)
        return
    # =================================================================================

    def plot_points(self, ax, point_x, point_y, color=1, label='', title='', marker='.', linewidth=1):
        colors = dict(mcolors.CSS4_COLORS, **mcolors.CSS4_COLORS)
        dict_val = list(colors.values())[color]
        ax.scatter(point_x, point_y, label=label, color=dict_val, marker=marker, linewidth=linewidth)
        ax.legend()
        return

    def save_data(self, filename):
        with open(filename, 'wb') as filehandle:
            # store the data as binary data stream
            pickle.dump(self.name_list, filehandle)
            pickle.dump(self.title, filehandle)

        return

    def load_data(self, filename):
        with open(filename, 'rb') as filehandle:
            # store the data as binary data stream
            tmp_dict = pickle.load(filehandle)
            tmp_title = pickle.load(filehandle)

            for k,v in tmp_dict.items():
                self.add_name(k)
                self.add_data(k, v, 0)


            self.title = tmp_title








