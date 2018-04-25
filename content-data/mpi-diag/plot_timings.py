#!/usr/bin/env python3
# -*- coding: <utf8> -*-

import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter, AutoMinorLocator
from cycler import cycler

# Configure matplotlib
plt.style.use('bmh')
font_size = 14
use_tex = True

# Font
if not use_tex:
	plt.rcParams['font.family'] = 'sans-serif'
	plt.rcParams['font.sans-serif'] = "Noto Sans"
	plt.rcParams['font.size'] = font_size
else:
	plt.rcParams['text.usetex'] = True
	plt.rcParams['text.latex.unicode'] = True
	plt.rcParams['font.size'] = font_size
	plt.rcParams['font.family'] = 'serif'
	plt.rcParams['font.sans-serif'] = "Computer Modern"

# X-ticks
plt.rcParams['xtick.labelsize'] = font_size
plt.rcParams['xtick.direction'] = 'in'
plt.rcParams['xtick.top'] = False
plt.rcParams['xtick.minor.visible'] = True
plt.rcParams['xtick.major.size'] = 6
plt.rcParams['xtick.minor.size'] = 4
plt.rcParams['xtick.major.width'] = 2
plt.rcParams['xtick.minor.width'] = 1

# Y-ticks
plt.rcParams['ytick.labelsize'] = font_size
plt.rcParams['ytick.direction'] = 'in'
plt.rcParams['ytick.right'] = True
plt.rcParams['ytick.minor.visible'] = True
plt.rcParams['ytick.major.size'] = 6
plt.rcParams['ytick.minor.size'] = 4
plt.rcParams['ytick.major.width'] = 2
plt.rcParams['ytick.minor.width'] = 1

# Axes
plt.rcParams['axes.labelsize'] = font_size
plt.rcParams['axes.labelweight'] = 'normal'
plt.rcParams['axes.linewidth'] = 2
plt.rcParams['axes.edgecolor'] = 'black'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['axes.grid'] = False

# Color cycler
plt.rcParams['lines.linewidth'] = 3
plt.rcParams['axes.prop_cycle'] = cycler('color', ['black',  '#b2182b', '#92c5de', '#f4a582']) + cycler('linestyle', ['--']*4) #, '#fddbc7', '#d1e5f0', '#67a9cf', '#2166ac'])

# Legend
plt.rcParams['legend.facecolor'] = "white"
plt.rcParams['legend.frameon'] = False

def main():
	systems = ['larger', 'smaller']
	labels = ['SL', 'SL + redistribute']
	bar_width = 1.
	figsize = plt.rcParams['figure.figsize']
	figsize[0] *= 2
	fig, axarr = plt.subplots(ncols=2)
	for i, system in enumerate(systems):
		ax = axarr[i]
		timings = np.loadtxt('sl_redistribute_performance_{0:s}.txt'.format(system))
		num_nodes = [int(i) for i in timings[:, 0]]
		indices = np.arange(4*len(num_nodes), step=4)
		for j in range(1, timings.shape[1]):
			ax.bar(indices+(j-1)*bar_width, timings[:, j], bar_width, label=labels[i])

		ax.legend(labels=labels) #, loc='upper left', bbox_to_anchor=(0.1, 1.04))
		if system == 'larger':
			ax.set_ylim([0,700])
		else:
			ax.set_ylim([0,140])

		ax.xaxis.set_ticks_position('none')
		ax.minorticks_off()
		ax.xaxis.set_ticks(indices+bar_width/2)
		ax.set_xticklabels(num_nodes)
		ax.set_xlabel("Number of nodes")

	axarr[0].set_ylabel("Total runtime (s)")
	fig.subplots_adjust(wspace=0.1)
	plt.savefig('sl_redistribute_performance.png', bbox_inches='tight', format='png', dpi=300)
	plt.show()

def get_ideal_scaling(num_nodes, first_element):
	vec = np.zeros(len(num_nodes))
	for i in range(len(vec)):
		if i == 0:
			vec[i] = first_element
		else:
			vec[i] = first_element/(num_nodes[i]/num_nodes[0])

	return vec


if __name__ == '__main__':
	main()